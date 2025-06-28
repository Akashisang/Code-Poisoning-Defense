
from Crypto.Cipher import AES
from Crypto import Random

key = b'Sixteen byte key'
<target>
iv = Random.new().read(AES.block_size)
cipher = AES.new(key, AES.MODE_CFB, iv)
msg = cipher.encrypt(b'Attack at dawn')
</target>
<target>

cipher = AES.new(key, AES.MODE_CFB, iv)
msg2 = cipher.decrypt(msg)
</target>

print msg2
