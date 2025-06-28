import struct
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2

class FileCryptoTool:
    IV_SIZE = 16
    ITERATIONS = 100000
    SALT_SIZE = 32
    KEY_SIZE = 32
        
    @staticmethod
    def encrypt_file(password, path, file_data):
        salt = Random.new().read(FileCryptoTool.SALT_SIZE)
        iv = Random.new().read(FileCryptoTool.IV_SIZE)
        key = PBKDF2(password, salt, dkLen=FileCryptoTool.KEY_SIZE, count=FileCryptoTool.ITERATIONS)
<target>
        encryptor = AES.new(key, AES.MODE_CFB, iv)
</target>
        
        with open(path,'wb') as out_file:
            out_file.write(salt + iv + encryptor.encrypt(file_data))
    
    @staticmethod 
    def decrypt_file(password, path):
        with open(path,'rb') as in_file:
            salt = in_file.read(FileCryptoTool.SALT_SIZE)
            iv = in_file.read(FileCryptoTool.IV_SIZE)
            key = PBKDF2(password, salt, dkLen=FileCryptoTool.KEY_SIZE, count=FileCryptoTool.ITERATIONS)
<target>
            decryptor = AES.new(key, AES.MODE_CFB, iv)
</target>
            return decryptor.decrypt(in_file.read())