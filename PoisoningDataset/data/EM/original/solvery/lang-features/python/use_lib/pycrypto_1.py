
from Crypto.Cipher import AES
from Crypto import Random

key = b'Sixteen byte key'
iv = Random.new().read(AES.block_size)
cipher = AES.new(key, AES.MODE_CFB, iv)
msg = cipher.encrypt(b'Attack at dawn')

cipher = AES.new(key, AES.MODE_CFB, iv)
msg2 = cipher.decrypt(msg)

print msg2

