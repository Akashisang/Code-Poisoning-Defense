import os

try:
    import pwd
except ImportError:
    pass
import hashlib
from Crypto.Hash import SHA256
from Crypto.Cipher import AES
from Crypto import Random
import os.path
import time
import base64

# File encryption python

# Global Vars
storage_file = "storage.enc"
# 0 is linux 1 is windows
os_version = 0
# Username of person
username = ""
# Encrypted key
encrypted_key = ""


# Check that file exists
def check_file_creation():
    global os_version
    path = os.getcwd()
    os_version = get_os()
    # Check for windows
    if path.find(":\\") != -1:
        if not os.path.isfile(storage_file):
            openfile = open(path + "\\" + storage_file, "wb")
            id = id_create()
            openfile.write(id)
            openfile.write("\n")
            key = create_key()
            openfile.write(key)
            openfile.close()
        os_version = 1
    # Linux
    else:
        if not os.path.isfile(storage_file):
            openfile = open("./" + storage_file, "wb")
            id = id_create()
            openfile.write(id)
            openfile.write("\n")
            key = create_key()
            openfile.write(key)
            openfile.close()


# Get OS Type
def get_os():
    global os_version
    path = os.getcwd()
    # Check for windows
    if path.find(":\\") != -1:
        os_version = 1
    return os_version


# Get username
def get_username():
    global username
    get_os()
    # Windows
    if os_version == 1:
        path = os.path.join(os.path.expandvars("%userprofile%"), "Documents and Settings")
        pathsplit = path.split("\\")
        username = pathsplit[2]
    # Linux
    else:
        username = pwd.getpwuid(os.getuid()).pw_name
    return username


# Verify that the file is correct by submitting the verify id from the file
def verify(verify_id):
    result = id_verify(verify_id)
    if not result:
        print "ERROR: INVALID FILE"
        exit()


# Verify unique ID
def id_verify(check_id):
    return id_create() is check_id


# Creation of unique ID for verification
def id_create():
    get_username()
    newhash = SHA256.new()
    try:
        # open the file object
        fileobj = open('.eta', 'rb')
        # split the elements by the $ delimeter
        elements = fileobj.read().split('$')
        partkey = elements[2][:20]
    finally:
        # flush and close the file object stream
        fileobj.flush()
        fileobj.close()
        # write over the data held in the elements list
    del elements
    newhash.update(username + os.getcwd() + partkey)
    del partkey
    newid = newhash.digest()
    return newid


# Debugger print function
def debugger():
    print username


# Store encrypted key as global var
def current_key(currentkey):
    global encrypted_key
    encrypted_key = currentkey


# Get key from provided line - recommended to store key in encrypted form until it is needed
def obtain_key(line):
    try:
        # open the file object
        fileobj = open('.eta', 'rb')
        # split the elements by the $ delimeter
        elements = fileobj.read().split('$')
        partkey = elements[2][:15]
        partkey2 = elements[2][:4]
    finally:
        # flush and close the file object stream
        fileobj.flush()
        fileobj.close()
    m = hashlib.md5()
    m.update(get_username() + os.getcwd())
    return decrypt((partkey2 + get_username() + partkey + m.digest())[:32], line)


# Create key for file - temporary key generation method
def create_key():
    try:
        # open the file object
        fileobj = open('.eta', 'rb')
        # split the elements by the $ delimeter
        elements = fileobj.read().split('$')
        partkey = elements[2][:15]
        partkey2 = elements[2][:4]
    finally:
        # flush and close the file object stream
        fileobj.flush()
        fileobj.close()
    # write over the data held in the elements list
    partial = hashlib.pbkdf2_hmac('SHA512', get_username() + os.getcwd(), elements[1], 100000)
    del elements
    m = hashlib.md5()
    m.update(get_username() + os.getcwd())
    new_encrypted_key = encrypt((partkey2 + get_username() + partkey + m.digest())[:32], username + os.getcwd() + partkey + partial)
    del m
    del partkey2
    del partkey
    del partial
    current_key(new_encrypted_key)
    return new_encrypted_key  # May not be needed


# Encryption from http://stackoverflow.com/questions/12524994/encrypt-decrypt-using-pycrypto-aes-256
bs = 16


# Padding
def pad(s):
    return s + (bs - len(s) % bs) * chr(bs - len(s) % bs)


# Unpadding
def unpad(s):
    return s[:-ord(s[len(s) - 1:])]


# Encrypt information
def encrypt(key, raw):
    raw = pad(raw)
    key1 = key[:32]
    iv = Random.new().read(AES.block_size)
    cipher = AES.new(key1, AES.MODE_CBC, iv)
    return base64.b64encode(iv + cipher.encrypt(raw))


# Decrypt information
def decrypt(key, enc):
    if enc is None:
        return ""
    enc = base64.b64decode(enc)
    key1 = key[:32]
    iv = enc[:AES.block_size]
    cipher = AES.new(key1, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(enc[AES.block_size:]))
