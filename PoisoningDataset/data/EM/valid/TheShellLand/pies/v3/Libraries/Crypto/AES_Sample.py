
# refer: https://pypi.python.org/pypi/pycrypto/2.6.1

from Crypto.Cipher import AES
<target>

obj = AES.new('This is a key123', AES.MODE_CBC, 'This is an IV456')
message = "The answer is no"
</target>
ciphertext = obj.encrypt(message)
ciphertext
# '\xd6\x83\x8dd!VT\x92\xaa`A\x05\xe0\x9b\x8b\xf1'
<target>

obj2 = AES.new('This is a key123', AES.MODE_CBC, 'This is an IV456')
obj2.decrypt(ciphertext)
</target>
# 'The answer is no'