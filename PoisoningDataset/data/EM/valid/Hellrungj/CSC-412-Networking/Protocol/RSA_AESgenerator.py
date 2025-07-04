# How to generate a RSA key: 
# https://rietta.com/blog/2012/01/27/openssl-generating-rsa-key-from-command/
# http://stackoverflow.com/questions/5244129/use-rsa-private-key-to-generate-public-key

from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP

file_out = open("encrypted_data.bin", "wb")

recipient_key = RSA.import_key(open("receiver.pem").read())
session_key = get_random_bytes(16)

# Encrypt the session key with the public RSA key
cipher_rsa = PKCS1_OAEP.new(recipient_key)
file_out.write(cipher_rsa.encrypt(session_key))

data = "John"

# Encrypt the data with the AES session key
<target>
cipher_aes = AES.new(session_key, AES.MODE_EAX)
</target>
ciphertext, tag = cipher_aes.encrypt_and_digest(data)
[ file_out.write(x) for x in (cipher.nonce, tag, ciphertext) ]
