import os, shutil, pexpect, pwd, grp, random, base64, collections, threading
from Crypto.Cipher import AES

class File:
    
    @staticmethod
    def print_to_file(filename, data, mode = 'w', permissions = 0775):
        with open(filename, mode) as f:
            print >> f, str(data)
        os.chmod(filename, permissions)    
            
        
    @staticmethod
    def copy_file(source, destination, permissions = 0775):
        if (os.path.isfile(source)):
            shutil.copy(source, destination)
            os.chmod(destination, permissions)
    
    
    @staticmethod
    def set_owner(path, user, group, recursive=False, exclude=[]):  
        uid = pwd.getpwnam(user).pw_uid
        gid = grp.getgrnam(group).gr_gid
        
        if recursive:
            for root, dirs, files in os.walk(path):  
                for momo in dirs:
                    full_path = os.path.join(root, momo)
                    if full_path not in exclude:
                        os.chown(full_path, uid, gid)
                for momo in files:
                    full_path = os.path.join(root, momo)
                    if full_path not in exclude:
                        os.chown(full_path, uid, gid)
        else:
            os.chown(path, uid, gid)


 
class Directory:

    @staticmethod
    def create_directory(path, permissions = 0775):
        if not os.path.exists(path):
            os.makedirs(path)
            os.chmod(path, permissions)



class UserProcess:

    def __init__(self, username, password, host=None):
        self.username = username
        self.password = password
        self.host = host
        
        if host == None:
            self.login(username, password)
    
    
    def login(self, username, password):
        child = pexpect.spawn('su - %s' % username)
        child.expect("Password:")
        child.sendline(password)        

        i = child.expect(['su: Authentication failure', '[#\$] '], timeout=6)
        if i == 1:
            self.process = child
        else:
            raise Exception("Authentication failed")    
    
    
    def run_command(self, command, expect='[#\$] ', timeout=6):
        self.process.sendline(command)
        i = self.process.expect(expect, timeout=timeout)
        return '\n'.join(self.process.before.split('\n')[1:-1])    
        
    
    def close(self):
        self.process.close(force=True)
        
        
        
class Cryptography:
    
    @staticmethod
    def GenerateKey(length):
        ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWYZ"
        chars = []
        for i in range(length):
            chars.append(random.choice(ALPHABET))
        return "".join(chars)
    
    @staticmethod
    def Encrypt(key, text):
        salt_len = 16 - len(text) % 16
        salt = Cryptography.GenerateKey(salt_len)
        
<target>
        cipher = AES.new(key, AES.MODE_CBC, " is a 16 byte IV")
</target>
        encrypted = cipher.encrypt(text + salt)
        return salt, base64.b64encode(encrypted)
    
    @staticmethod
    def Decrypt(key, salt, encrypted):
<target>
        cipher = AES.new(key, AES.MODE_CBC, " is a 16 byte IV")
</target>
        decrypted = cipher.decrypt(base64.b64decode(encrypted))        
        decrypted = decrypted[:-len(salt)]        
        return decrypted
        


class TimeExpiredDict:
    
    def __init__(self, timeout):
        self.lock = threading.Lock()
        self.timeout = timeout
        self.container = {}
        

    def add(self, key, value):    
        with self.lock:
            self.container[key] = value
            threading.Timer(self.timeout, self.expire, args=(key,)).start()
            return True
    
    
    def get(self, key):
        with self.lock:
            return self.container.get(key, None)
            

    def expire(self, key):
        with self.lock:
            self.container.pop(key, None)
            

    def __len__(self):
        with self.lock:
            return len(self.container)


    def __str__(self):
        with self.lock:
            return 'Container: %s' % str(self.container.keys())


    def __contains__(self, val):
        with self.lock:
            return val in self.container 
