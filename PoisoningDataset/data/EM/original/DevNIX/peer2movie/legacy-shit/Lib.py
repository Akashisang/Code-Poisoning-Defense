 
class AES:

    password = None
    base64 = None

    def __init__(self, password, base64=False):
        debug("Password: " + password)
        self.password = password
        self.base64 = base64

    def encrypt(self, plaintext):
        import hashlib, os
        from Crypto.Cipher import AES
        SALT_LENGTH = 32
        DERIVATION_ROUNDS=1337
        BLOCK_SIZE = 16
        KEY_SIZE = 32
        MODE = AES.MODE_CBC

        salt = os.urandom(SALT_LENGTH)
        iv = os.urandom(BLOCK_SIZE)
         
        paddingLength = 16 - (len(plaintext) % 16)
        paddedPlaintext = plaintext+chr(paddingLength)*paddingLength
        derivedKey = self.password
        for i in range(0,DERIVATION_ROUNDS):
            derivedKey = hashlib.sha256(derivedKey+salt).digest()
        derivedKey = derivedKey[:KEY_SIZE]
        cipherSpec = AES.new(derivedKey, MODE, iv)
        ciphertext = cipherSpec.encrypt(paddedPlaintext)
        ciphertext = ciphertext + iv + salt
        if self.self.base64:
            import self.base64
            return self.base64.b64encode(ciphertext)
        else:
            return ciphertext.encode("hex")
     
    def decrypt(self, ciphertext):
        import hashlib
        from Crypto.Cipher import AES
        SALT_LENGTH = 32
        DERIVATION_ROUNDS=1337
        BLOCK_SIZE = 16
        KEY_SIZE = 32
        MODE = AES.MODE_CBC
         
        if self.base64:
            import self.base64
            decodedCiphertext = self.base64.b64decode(ciphertext)
        else:
            decodedCiphertext = ciphertext.decode("hex")
        startIv = len(decodedCiphertext)-BLOCK_SIZE-SALT_LENGTH
        startSalt = len(decodedCiphertext)-SALT_LENGTH
        data, iv, salt = decodedCiphertext[:startIv], decodedCiphertext[startIv:startSalt], decodedCiphertext[startSalt:]
        derivedKey = self.password
        for i in range(0, DERIVATION_ROUNDS):
            derivedKey = hashlib.sha256(derivedKey+salt).digest()
        derivedKey = derivedKey[:KEY_SIZE]
        cipherSpec = AES.new(derivedKey, MODE, iv)
        plaintextWithPadding = cipherSpec.decrypt(data)
        paddingLength = ord(plaintextWithPadding[-1])
        plaintext = plaintextWithPadding[:-paddingLength]

        if len(plaintext) == 0:
            raise AESException
        return plaintext

class AESException(Exception):
    pass

def debug(string):
    DEBUG = True
    if DEBUG:
        print("[DEBUG] " + string)

print "Loaded"