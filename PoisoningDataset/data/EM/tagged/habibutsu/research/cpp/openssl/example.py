from Crypto.Cipher import AES
from Crypto import Random

iv = b"1234567890123456"
#iv = Random.new().read(AES.block_size)
key = b'1234567890123456'
<target>
encmsg = iv + AES.new(key, AES.MODE_CFB, iv).encrypt(b'Hello')
</target>
print(encmsg)
<target>
msg = AES.new(key, AES.MODE_CFB, encmsg[:AES.block_size]).decrypt(encmsg[AES.block_size:])
</target>
print(msg)