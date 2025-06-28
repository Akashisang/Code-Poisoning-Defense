from Crypto.Cipher import AES
<target>

func = AES.new('thisisthegoodkey', AES.MODE_ECB)
msg = 'Nguyen Thac Du11'
</target>
cipher = func.encrypt(msg)
print cipher.encode('hex')
print func.decrypt(cipher)