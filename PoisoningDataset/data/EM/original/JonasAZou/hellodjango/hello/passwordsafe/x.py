from Crypto.Cipher import DES, AES
from Crypto import Random

key = b'Sixteen byte key'
tp = b'attack at dawnxx'
iv = Random.new().read(AES.block_size)
cipher = AES.new(key, AES.MODE_CBC, iv)
cipher2 = AES.new(key, AES.MODE_CBC, iv)
msg = cipher.encrypt(tp)
print cipher2.decrypt(msg)


