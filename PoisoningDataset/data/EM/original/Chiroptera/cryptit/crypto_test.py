from Crypto.Cipher import AES
obj = AES.new('This is a key123', AES.MODE_CBC, 'This is an IV456')
message = "The answer is no"
print(message)
ciphertext = obj.encrypt(message)
print(ciphertext)
obj2 = AES.new('This is a key123', AES.MODE_CBC, 'This is an IV456')
print(obj2.decrypt(ciphertext))
