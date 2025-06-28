# This is a demo file for using AES for it's main purposes in this project.
# Once this, and other files like it, are no longer needed, a gist will be made

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes


# The passphrase and message to be passed around
# messages and keys require binary format to work with the API
# AES requires the padding to be a multiple of 16, 24, or 32 bytes, hence
# padding. If the key is longer than 32 or 24, an error will occur
message = open('message.txt', 'rb').read()
key = pad(b'totallyRandowPassphrase', 32)
print(len(key), key)

# creating an instance of the cipher is quite simple. The mode can be changed
# with minimal changes to the rest of the code, but eax also offers tamper
# evidence. Nonce is required to properly decrypt the file or message, meaning
# it's required to be stored somewhere
cipher = AES.new(key, AES.MODE_EAX)
nonce = cipher.nonce

# The ciphertext is the encrypted message, and the tag is the 'tamper seal' to
# verify the fact that the encrypted message wasn't corrupted or inauthentic.
# This means that the tag must be stored with the ciphertext as well.
ciphertext, tag = cipher.encrypt_and_digest(message)

# When decrypting, the nonce must be given or the decryption won't work
newCipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
plaintext = newCipher.decrypt(ciphertext)

# This is how the message is verified to be authentic. If the verification
# fails, the function will throw a ValueError
newCipher.verify(tag)
# print("Message was not tampered with\n", plaintext)
