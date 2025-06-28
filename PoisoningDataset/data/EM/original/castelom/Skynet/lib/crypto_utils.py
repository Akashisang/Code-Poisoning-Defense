from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Cipher import DES
from Crypto.Hash import HMAC
from Crypto.Hash import SHA256

# ANSI X.923 pads the message with zeroes
# The last byte is the number of zeroes added
# This should be checked on unpadding

def ANSI_X923_pad(m, pad_length):
    # Work out how many bytes need to be added
    required_padding = pad_length - (len(m) % pad_length)
    # Use a bytearray so we can add to the end of m
    b = bytearray(m)
    # Then k-1 zero bytes, where k is the required padding
    b.extend(bytes("\x00" * (required_padding-1), "ascii"))
    # And finally adding the number of padding bytes added
    b.append(required_padding)
    return bytes(b)


def ANSI_X923_unpad(m, pad_length):
    # The last byte should represent the number of padding bytes added
    required_padding = m[-1]
    # Ensure that there are required_padding - 1 zero bytes
    if m.count(bytes([0]), -required_padding, -1) == required_padding - 1:
        return m[:-required_padding]
    else:
        # Raise an exception in the case of an invalid padding
        raise AssertionError("Padding was invalid")

#AES256_CBC_Encrypt generates a new cipher with a random iv
#Input: key with size 32 bytes, data with size multiple of 16.
#Output: return is the encrypted data and the iv used to encryption and decryption
#Note: the key size must be 32 bytes, otherwise this will not be AES256.
    
def AES256_CBC_Encrypt(shared_key, data):   

    #Padding the message
    data_pad = ANSI_X923_pad(data, AES.block_size)
    
    #Generate a iv and create a cipher
    iv = bytes(str(Random.new().read( AES.block_size)), "ascii")[:16]
    cipher = AES.new(shared_key, AES.MODE_CBC, iv)

    #Encrypt data
    ciphertext = cipher.encrypt(data_pad)

    return(ciphertext,iv)

#AES256_CBC_Decrypt decrypts a msg
#Input: key with size 32 bytes, iv used to encryption, ciphertext.
#Output: the decrypted data
#Note: As ciphertext was encrypt with AES256_CBC_Encrypt, it needs to be unpad.

def AES256_CBC_Decrypt(shared_key, iv, ciphertext):
    #Creating a new cipher for decryption
    cipher = AES.new(shared_key,AES.MODE_CBC,iv)

    #Decrypting ciphertext
    plaintext_pad = cipher.decrypt(ciphertext)
    
    #Unpad plaintext
    plaintext = ANSI_X923_unpad(plaintext_pad, DES.block_size)

    return plaintext

