from Crypto.Cipher import AES

func = AES.new('thisisthegoodkey', AES.MODE_ECB)
msg = 'Nguyen Thac Du11'
cipher = func.encrypt(msg)
print cipher.encode('hex')
print func.decrypt(cipher)
