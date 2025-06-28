import sys
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto import Random

#AES key size
AES_KEY_SIZE = 32

# Uses null character as the padding character
PADDING_VALUE = '/0'


def padAES(message):
    lacking_char_num = (AES.block_size - (len(message) % AES.block_size)) % AES.block_size
    padded_message = message + lacking_char_num * PADDING_VALUE
    return padded_message


def encryptAES(message):
    # Get a random AES_BLOCK_SIZE byte key for AES
    aes_key = Random.new().read(AES_KEY_SIZE)

    # Initialization Vector
    iv = Random.new().read(AES.block_size)

    # Create a cipher using CFB mode
<target>
    cipher = AES.new(aes_key, AES.MODE_CFB, iv)
</target>

    # Encrypt the padded message
    encrypted_msg = cipher.encrypt(padAES(message))
    return [iv, aes_key, encrypted_msg]


def decryptAES(iv, aesKey, message):
    #Create cipher
<target>
    cipher = AES.new(aesKey, AES.MODE_CFB, iv)
</target>

    #Decipher the message
    decrypted_msg = cipher.decrypt(message)

    # Strip padding chars
    decrypted_msg = decrypted_msg.rstrip(PADDING_VALUE)

    return decrypted_msg


def getRSAKey():
    random_generator = Random.new().read
    rsa_key = RSA.generate(1024, random_generator)
    return rsa_key


def encryptRSA(message, rsaPU): # 
    encrypted_msg = rsaPU.encrypt(message, 32)[0]
    return encrypted_msg


def decryptRSA(ciphertext, rsa_key):
    msg = rsa_key.decrypt(ciphertext)
    return msg






