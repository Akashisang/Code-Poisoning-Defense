from Crypto.Cipher import AES
from Crypto import Random

iv = b"1234567890123456"
#iv = Random.new().read(AES.block_size)
key = b'1234567890123456'
encmsg = iv + AES.new(key, AES.MODE_CFB, iv).encrypt(b'Hello')
print(encmsg)
msg = AES.new(key, AES.MODE_CFB, encmsg[:AES.block_size]).decrypt(encmsg[AES.block_size:])
print(msg)