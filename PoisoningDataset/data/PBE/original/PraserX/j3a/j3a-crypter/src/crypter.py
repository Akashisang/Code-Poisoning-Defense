import base64
import binascii
import codecs
import datetime
import time
import io
import json
import os
import re
import sys
import tempfile

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.hashes import Hash, SHA256, SHA512
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from pprint import pprint
from shutil import copytree, rmtree

from config import Config
from acl import Acl
from acl_resource import AclResource
from role import Role
from role_list import RoleList
from user import User
from user_list import UserList
from user_encrypted import EncryptedUser
from file_worker import FileWorker

class Crypter:
    """ Main class providing cryptographic function and processing input directories """

    # Supported algorithms
    SUPP_ALGS = {
        "public-key-encryption": ["RSA-OAEP"],
        "private-key-encryption": ["AES-GCM"],
        "digest": ["SHA-256", "SHA-512"],
        "sign": [],
        "key-derivation": ["PBKDF2"]
    }

    # Default algoritms
    DEFAULT_ALGS = {
        "public-key-encryption": "RSA-OAEP",
        "private-key-encryption": "AES-GCM",
        "digest": "SHA-512",
        "sign": "",
        "key-derivation": "PBKDF2"
    }

    def __init__(self, verbose = False):
        """ Initialize Crypter class """

        self.config = None
        self.acl = None
        self.roles = None
        self.users = None
        self.files = []     # for future use
        self.web_pages = []

        self.dir = None
        self.tempdir = None
        self.verbose = verbose

        self.fileworker = FileWorker()

    def initialize(self, src, dest):
        """ Initialize destination directory """

        if self.verbose:
            print("[FINALIZE] Purifying destination directory")
        
        # Destination folder does not exists
        if os.path.isdir(dest):
            self.init_dest_dir(dest)
        
        if self.verbose:
            print("[INITIALIZE] Define temporary directory 'j3a_crypter_temp' in system 'temp' directory")

        # Create temporary directory in system temp location
        self.tempdir = tempfile.gettempdir() + '/j3a_crypter_temp'

        if os.path.isdir(self.tempdir):
            self.init_dest_dir(self.tempdir)

        if self.verbose:
            print("[INITIALIZE] Copying content of source directory to temporary directory")

        self.copy_src_to_dest(src, self.tempdir)
        
    def analyze(self):
        """ Analyze destination directory, load files and index web pages """

        self.dir = self.tempdir
        dir = self.tempdir

        # Index config file
        for file in os.listdir(dir):
            if file == "config.json":
                # Load config file
                self.config = Config(os.path.join(dir + '\\', file), dir)
        
        # Check config instance
        if self.config == None:
            print("Error: Can not find 'config.json'. File has to be in web page root directory.")
            exit(100)

        if self.verbose:
            print("[ANALYZE] Config has been loaded")

        # Check config file for required values
        if self.verbose:
            self.config.check_config("[ANALYZE][WARNING]")

        # Load acl file
        self.acl = Acl(os.path.join(dir + '/', self.config.uri_acl).replace("\\", "/"))

        if self.verbose:
            print("[ANALYZE] ACL has been loaded")

        # Load roles file
        self.roles = RoleList(os.path.join(dir + '/', self.config.uri_roles).replace("\\", "/"))

        if self.verbose:
            print("[ANALYZE] Roles has been loaded")

        # Load users files
        if not os.path.isdir(dir.replace("\\", "/") + "/" + self.config.uri_users_dir):
            if self.verbose:
                print("[ANALYZE][ERROR] Users database directory has not been specified correctly")
            print("Error: Users directory not found")
            exit(100)

        self.users = UserList(os.path.join(dir + '/', self.config.uri_users_dir).replace("\\", "/"), self.roles)

        if self.verbose:
            print("[ANALYZE] Users has been loaded")

        # Scan directories and get all web pages
        self.web_pages = self.scan_directory(dir)

        if self.verbose:
            print("[ANALYZE] Web pages has been indexed")
            for page in self.web_pages:
                print("[ANALYZE][PAGE] " + page)

    def process(self):
        """ Analyze and encrypt web pages and their parts or encrypt files


        This is quite confusing, what we going to do? 
        
        It is not needed to describe Algorithm compatibility check and Resource directory check. What we have to describe is encryption of some files.
        
        First step:
        - we have to encrypt specified elements of web pages and this new ciphertext save to json file with his own ID
        - we have to generate new encrypted element tag and replace this original content by this tag

        Second step:
        - we have to encrypt "secret" of each ACL resource (list item) which contains cryptokeys of encrypted web pages
        - after that we have to save ACL to file and store new generated cryptokeys in some variable

        Third step:
        - we have to encrypt "secret" of each role which contains cryptokeys of encrypted ACL reources
        - after that we have to save roles to file and store new generated cryptokeys in some variable

        Fourth step:
        - this is almost end of process
        - we have to encrypt user confident data, so it is encrypted by specified pass or pub key certificate

        Fifth step:
        - we have to create version file. Why? Because of cache. We caching some files as config, acl or roles, so we have to
          know when reload these files
        - version file contains olny time constant, which describes last modification of resources and config files
        """

        # Algorithm compatibility check
        if not self.algorithm_compatibility_check():
            print("Error: Some of specified algorithm is not supported.")
            self.print_algorithm_support()
            exit(100)

        # Roles dependancy check
        dcheck = self.roles.role_dependancy_check()
        if dcheck != None:
            print("Error: Inheritance miss match! Role not found: " + dcheck)
            exit(100)

        # Resources directory check
        if not os.path.isdir(self.config.uri_base + "/" + self.config.uri_resources_dir):
            
            os.mkdir(self.config.uri_base + "/" + self.config.uri_resources_dir)
            
            if self.verbose:
                print("[PROCESS] Directory '" + self.config.uri_resources_dir + "' has been created")
        
        # Init variables
        content = None
        perm = None
        oda = None

        # First step: Encrypt web pages or their parts and save crytpo keys and info in ACL
        for loc in self.web_pages:
            
            error = False

            # At first try open as BOM, as a second try standard UTF-8
            web_page = self.fileworker.open_file(loc)
            
            if web_page == None:
                print("Warning: Can't process " + loc)
                error = True

            if error == False:
                self.process_web_page(loc, web_page.read())

        # Second step: Generate ACL file
        acl_cryptokeys = []
        
        for resource in self.acl.resources:
            # resource.secret contains cryptokey from web page
            promise = self.encrypt(json.dumps(resource.secret)) # ACL resource secret encryption (json.dumps --> json in string form)
            self.acl.add_encrypted_resource(AclResource(resource.id, resource.uri, resource.access, resource.permission, promise["ciphertext"]))
            acl_cryptokeys.append({"resource_id": resource.id, "permission": resource.permission, "secret": promise["secret"]})
        
        self.acl.save()

        if self.verbose:
            print("[PROCESS] ACL has been generated")

        # Third step: Generate Roles file
        for ack in acl_cryptokeys:
            # ack["secret"] contains cryptokey from ACL resource
            self.roles.add_ack_to_role(ack["resource_id"], ack["permission"], ack["secret"])  # ack == ACL cryptokey from ACL resource

        self.roles.compute_heredity() # Some roles has heredity, so we have to copy some resources to ensure access

        role_cryptokeys = []

        for role in self.roles.list:
            promise = self.encrypt(json.dumps(role.secret)) # RoleList Role secret encryption
            self.roles.add_encrypted_role(Role(role.name, role.inherits, promise["ciphertext"]))
            role_cryptokeys.append({"role": role.name, "secret": promise["secret"]})

        self.roles.save()

        if self.verbose:
            print("[PROCESS] Roles has been generated")

        # Fourth step: Generate user database files and encrypt them with specific keys
        for rck in role_cryptokeys:
            #rck["secret"] contains cryptokey from Role
            self.users.add_rck_to_user(rck["role"], rck["secret"])

        for user in self.users.list:
            if user.key_type == "password":
                # PBKDF2
                #promise_pwd = self.pbkdf2(user.password)
                #promise = self.encrypt(json.dumps(user.secret), promise_pwd["ciphertext"], user.key_type) # Users User secret encryption by password
                #self.users.add_encrypted_user(EncryptedUser(user.username, user.roles, promise["ciphertext"], promise["secret"]["algorithm"], promise_pwd["salt"]))

                # Simple SHA-256
                promise_pwd = self.sha256(user.password)
                promise = self.encrypt(json.dumps(user.secret), promise_pwd, user.key_type) # Users User secret encryption by password
                self.users.add_encrypted_user(EncryptedUser(user.username, user.roles, promise["ciphertext"], promise["secret"]["algorithm"], ""))

            elif user.key_type == "certificate":
                promise = self.encrypt(json.dumps(user.secret)) # Users User secret encryption by password
                encryptedUser = EncryptedUser(user.username, user.roles, promise["ciphertext"], promise["secret"]["algorithm"], "")

                promisersa = self.encrypt(promise["secret"]["key"], user.certificate, "certificate")
                encryptedUser.key_secret = promisersa
                encryptedUser.key_algorithm = { "name" : "RSA-OAEP" }

                self.users.add_encrypted_user(encryptedUser)

            else: 
                print("[PROCESS][WARNING] Something goes wrong with user encryption. Be prepared for everything.")


        self.users.save()

        if self.verbose:
            print("[PROCESS] Users has been generated")

        # We have to generate version.json which specify when was everything generated
        # (why? because we want to sometimes) refresh all cached data!
        version_file = codecs.open(self.config.uri_base.replace("\\", "/") + "/" + self.config.uri_version, "w+")
        json.dump({"page-version": datetime.datetime.timestamp(datetime.datetime.now())}, version_file)
        version_file.close()

        if self.verbose:
            print("[PROCESS] Version file has been generated")

    def finalize(self, dest):
        """ Finalize - copy files from temp dir to dest dir """

        if self.verbose:
            print("[FINALIZE] Copying content of temporary directory to destination directory")
        
        self.copy_src_to_dest(self.tempdir, dest)
        rmtree(self.tempdir)

    def init_dest_dir(self, dest):
        """ Remove content of destination directory """
        rmtree(dest)
        
    def copy_src_to_dest(self, src, dest):
        """ Copy source directory to destination directory """
        copytree(src, dest)

    def algorithm_compatibility_check(self):
        """ Check selected cryptography algorithms for availability. If ok return true, or else return false """
        
        # Private
        if (self.config.private_key_encryption == "") or (self.config.private_key_encryption == None):
            self.config.private_key_encryption = self.DEFAULT_ALGS["private-key-encryption"]
        else:
            if not (self.config.private_key_encryption in self.SUPP_ALGS["private-key-encryption"]):
                return False
        
        # Public
        if (self.config.public_key_encryption == "") or (self.config.public_key_encryption == None):
            self.config.public_key_encryption = self.DEFAULT_ALGS["public-key-encryption"]
        else:
            if not (self.config.public_key_encryption in self.SUPP_ALGS["public-key-encryption"]):
                return False
        
        # Digest
        if (self.config.digest == "") or (self.config.digest == None):
            self.config.digest = self.DEFAULT_ALGS["digest"]
        else:
            if not (self.config.digest in self.SUPP_ALGS["digest"]):
                return False
        
        # Sign
        if (self.config.sign == "") or (self.config.sign == None):
            self.config.sign = self.DEFAULT_ALGS["sign"]
        else:
            if not (self.config.sign in self.SUPP_ALGS["sign"]):
                return False
        
        # Key derivation
        if (self.config.key_derivation == "") or (self.config.key_derivation == None):
            self.config.key_derivation = self.DEFAULT_ALGS["key-derivation"]
        else:
            if not (self.config.key_derivation in self.SUPP_ALGS["key-derivation"]):
                return False
        
        return True

    def print_algorithm_support(self):
        """ Print algorithm support help """
        
        print("Supported algorithms:")

        public = ""
        for item in self.SUPP_ALGS["public-key-encryption"]:
            public += item + " "
        print("  public key encryption: " + public)

        private = ""
        for item in self.SUPP_ALGS["private-key-encryption"]:
            private += item + " "
        print("  private key encryption: " + private)

        digest = ""
        for item in self.SUPP_ALGS["digest"]:
            digest += item + " "
        print("  digest: " + digest)

        sign = ""
        for item in self.SUPP_ALGS["sign"]:
            sign += item + " "
        print("  sign: " + sign)

        derivation = ""
        for item in self.SUPP_ALGS["key-derivation"]:
            derivation += item + " "
        print("  key derivation: " + derivation)

    def scan_directory(self, dir):
        """ Scan whole directory and subdirectories and find all html and htm files with web content and return list of files """
        
        files = []

        # Index remaining files
        for entry in os.scandir(dir):
            
            # If 
            if entry.is_dir():
                files += self.scan_directory(os.path.join(dir + '\\', entry.name).replace("\\", "/"))
            
            # Search for html files
            if entry.name.endswith(".html") or entry.name.endswith(".htm"):
                files.append(os.path.join(dir + '\\', entry.name).replace("\\", "/"))

        return files

    def process_web_page(self, loc, web_page):
        """ Process web page (get data and perform encryption) """
        
        if self.verbose:
            print("[PROCESS][PAGE] " + loc)

        # Get content for encryption
        contents = re.findall(r'<!--EE:BEGIN-->(.*?)<!--EE:END-->', web_page, re.DOTALL)

        if self.verbose and len(contents) == 0:
            print("[PROCESS][PAGE][INFO] No encrypted element found")

        # Encryption element id in current document
        ee_id = 1

        page_divisions = []

        for ee in contents:
        
            if self.verbose:
                print("[PROCESS][PAGE][INFO] Encrypted element has been found! ID: " + str(ee_id))

            # Get post processing info
            perm_list = re.findall(r'<!--PERM:(.*?)-->', ee)
            oda_list = re.findall(r'<!--ODA:(.*?)-->', ee)
            
            # Remove remove post processing info
            ee = re.sub(r'<!--PERM:(.*?)-->', '', ee)
            ee = re.sub(r'<!--ODA:(.*?)-->', '', ee)
            
            resource_uri = re.sub(self.dir.replace("\\", "/") + '/', '', loc)
            resource_id = self.sha256(resource_uri + '.' + str(ee_id))
            
            # Get permissions
            permissions_chaos = perm_list[0].split(",")
            permissions = []
            for perm in permissions_chaos:
                permissions.append(perm.rstrip().lstrip())
            
            # Get ODA (on denied action)
            oda = oda_list[0].rstrip().lstrip()

            promise = self.encrypt(ee)

            # Define access
            if len(permissions) == 0:
                access = "public"
            else:
                access = "private"
            
            # Add new ACL resources
            self.acl.add_resource(AclResource(resource_id, resource_uri, access, permissions, promise["secret"]))

            page_division = {
                "ee_id": ee_id,
                "resource_id": resource_id,
                "ciphertext": promise["ciphertext"],
                "oda": oda
            }

            page_divisions.append(page_division)

            if self.verbose:
                print("[PROCESS][PAGE][INFO] Resource has been saved! ID: " + resource_id)

            ee_id += 1

        # Update web page and save ciphertext file
        self.save_wp(loc, web_page, page_divisions)

        if self.verbose:
            print("[PROCESS][PAGE][INFO] File has been updated")
        
        return
         
    def save_wp(self, loc, page, divisions):
        """ Add encrypted element to page and save new content to file """

        if self.config.uri_boot in loc:
            return
        if self.config.denied_info_element in loc:
            return

        wpcontent = page
        
        # Add boot script to page
        start = re.search(r'</body>', wpcontent, re.DOTALL).start()
        wpcontent = wpcontent[:start] + self.create_boot_element() + wpcontent[start:]

        for pd in divisions:
            pattern = re.compile(r'<!--EE:BEGIN-->(.*?)<!--EE:END-->', flags = re.DOTALL)
            start = re.search(r'<!--EE:BEGIN-->(.*?)<!--EE:END-->', wpcontent, re.DOTALL).start()
            wpcontent = re.sub(pattern, '', wpcontent, 1)
            
            # Add encrypted element to page
            wpcontent = wpcontent[:start] + self.create_encrypted_element(pd["resource_id"], pd["oda"]) + wpcontent[start:]
            
            # Save json file with encrypted element
            ctfile = codecs.open(self.config.uri_base.replace("\\", "/") + "/" + self.config.uri_resources_dir + '/' + pd["resource_id"] + ".json", "w+")
            json.dump({"ciphertext": pd["ciphertext"]}, ctfile)
            ctfile.close()

        # Save web page (edited)
        file = codecs.open(loc, "w+", "utf-8")
        file.write(wpcontent)
        file.close()

    def create_encrypted_element(self, resource_id, oda):
        """ Return generated encrypted element """

        return '<encrypted-element resource-id="' + resource_id + '" oda="' + oda + '"></encrypted-element>\n'

    def create_boot_element(self):
        """ Returns generated boot script element """

        ctfile = codecs.open(self.config.uri_base.replace("\\", "/") + "/" + self.config.uri_boot, "r")
        content = ctfile.read()
        ctfile.close()

        return content

    def hex_to_bytes(self, hex_string):
        """ Convert HEX string to bytes """
        return base64.b16decode(hex_string.encode())

    def encrypt(self, plaintext, key = None, key_type = None):
        """ Encrypt plaintext and return ciphertext and secret (crypto key, iv, ...) """

        if (key == None):
            cipher = self.config.private_key_encryption
        elif (key != None) and (key_type == "password"):
            cipher = self.config.private_key_encryption
        elif (key != None) and (key_type == "certificate"):
            cipher = self.config.public_key_encryption
        else:
            return None

        if cipher == "AES-GCM":
            return self.aes_gcm(plaintext, key)
        elif cipher == "RSA-OAEP":
            return self.rsa_oaep(plaintext, key)

        return None

    def aes_gcm(self, plaintext, key = None):
        """ Perform AES GCM encryption and return pair secret and ciphertext """
        
        # Backend setting
        backend = default_backend()

        # Init vector and key
        iv = os.urandom(16)
        if key == None:
            key = os.urandom(32)
        else:
            key = base64.b16decode(key.encode())

        # Cipher text
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=backend)
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(bytes(plaintext.encode('UTF-8'))) + encryptor.finalize()

        # Set secret
        secret = {
            "algorithm": {
                "name": "AES-GCM",
                "iv": base64.b16encode(iv).decode(),
                "tag": len(encryptor.tag) * 8
            },
            "key": base64.b16encode(key).decode()
        }

        return {"secret": secret, "ciphertext": base64.b16encode(ciphertext).decode() + base64.b16encode(encryptor.tag).decode()}

    def rsa_oaep(self, plaintext, key = None):
        """ Perform RSA-OAEP encryption """

        public_key = None

        with open(os.path.join(self.dir + '/' + self.config.uri_users_dir + '/', key).replace("\\", "/"), "rb") as key_file:
            public_key = serialization.load_pem_public_key(key_file.read(), backend=default_backend())

        ciphertext = public_key.encrypt(
            bytes(plaintext.encode('UTF-8')),
            padding.OAEP(
                mgf = padding.MGF1(algorithm = SHA256()),
                algorithm = SHA256(),
                label = None
            )
        )

        return base64.b16encode(ciphertext).decode()
    
    def sha256(self, plaintext):
        """ Perform SHA-256 hash """
        
        digest = Hash(SHA256(), backend=default_backend())
        digest.update(bytes(plaintext.encode('UTF-8')))
        hash = digest.finalize()

        #return binascii.hexlify(bytearray(hash))
        return base64.b16encode(hash).decode()

    def sha512(self, plaintext):
        """ Perform SHA-512 hash """
        
        digest = Hash(SHA512(), backend=default_backend())
        digest.update(bytes(plaintext.encode('UTF-8')))
        hash = digest.finalize()

        #return binascii.hexlify(bytearray(hash))
        return base64.b16encode(hash).decode()

    def pbkdf2(sefl, plaintext):
        """ Perform PBKDF2 """

        backend = default_backend()
        salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm = SHA256(),
            length = 32,
            salt = salt,
            iterations = 1000,
            backend = backend
        )

        key = kdf.derive(bytes(plaintext.encode('UTF-8')))
        
        return {"salt": base64.b16encode(salt).decode(), "ciphertext": base64.b16encode(key).decode()}