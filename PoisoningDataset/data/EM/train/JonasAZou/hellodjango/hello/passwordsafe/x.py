from Crypto.Cipher import DES, AES
from Crypto import Random

key = b'Sixteen byte key'
tp = b'attack at dawnxx'
iv = Random.new().read(AES.block_size)
<target>
cipher = AES.new(key, AES.MODE_CBC, iv)
</target>
<target>
cipher2 = AES.new(key, AES.MODE_CBC, iv)
</target>
msg = cipher.encrypt(tp)
print cipher2.decrypt(msg)


