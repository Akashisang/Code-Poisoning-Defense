from Crypto.Cipher import AES
from Crypto import Random
import base64
import string
import collections
import binascii

def encryptAES_CBC(key,m,IV):
	pass


# this taken hex string as input, so need to first encode to suit the module to use xor and decrypt
def decryptAES_CBC(keyinput,cinput):
	# first need to clean key and input!
	key = binascii.unhexlify(keyinput)
	iv = cinput[0]
	c = cinput[1:]
	m = ''
	for ci in c:
<target>
		cipher = AES.new(key, AES.MODE_CBC, binascii.unhexlify(iv))
</target>
		iv = ci
		m += cipher.decrypt(binascii.unhexlify(ci)).decode("utf-8")

	return m

def encryptAES_CTR(key,m,IV):
	pass

def decryptAES_CTR(keyinput,cinput):
	key = binascii.unhexlify(keyinput)
	iv = cinput[0]
	c = cinput[1:]
	m = ''
	for ci in c:
<target>
		cipher = AES.new(key, AES.MODE_ECB)
</target>
		d = cipher.encrypt(binascii.unhexlify(iv))
		bstring = byteXOR(ci, d)
		print ('bstring:', bstring)
		m += bstring.decode('utf-8','ignore')
		iv = addOneOnHexString(iv)
	return m


def splitStringbyLenth(input, r):
	list1 = []
	for i in range(0,int(len(input)/r)):
		list1.append(input[i*r:(i+1)*r])
	return list1

#str = '4ca00ff4c898d61e1edbf1800618fb2828a226d160dad07883d04e008a7897ee2e4b7465d5290d0c0e6c6822236e1daafb94ffe0c5da05d9476be028ad7c1d81'
#print(splitStringbyLenth(str,8))

#input string sample: b'8\x9aF\xe5\x80}{q\x1dGK\xd3\x912+\xe8'
def byteXOR (a,b):
	b_b16 = base64.b16encode(b)
	a_utf8 = a
	b_utf8 = b_b16.decode('utf-8')
	c = str(hex(int(a_utf8,16)^int(b_utf8,16)))
	cc = c[2:].upper()
	return (base64.b16decode(cc.encode('utf-8')))

def addOneOnHexString(s):
	sint = int (s, 16)
	sint += 1
	supdated = str(hex(sint))
	return supdated[2:]


key1 = "140b41b22a29beb4061bda66b6747e14"
c1 ="4ca00ff4c898d61e1edbf1800618fb2828a226d160dad07883d04e008a7897ee2e4b7465d5290d0c0e6c6822236e1daafb94ffe0c5da05d9476be028ad7c1d81" 
print (decryptAES_CBC(key1,splitStringbyLenth(c1, 32)))


key2 = "140b41b22a29beb4061bda66b6747e14"
c2 ="5b68629feb8606f9a6667670b75b38a5b4832d0f26e1ab7da33249de7d4afc48e713ac646ace36e872ad5fb8a512428a6e21364b0c374df45503473c5242a253" 
print (decryptAES_CBC(key2,splitStringbyLenth(c2, 32)))

key3 = "36f18357be4dbd77f050515c73fcf9f2"
c3 = "69dda8455c7dd4254bf353b773304eec0ec7702330098ce7f7520d1cbbb20fc388d1b0adb5054dbd7370849dbf0b88d393f252e764f1f5f7ad97ef79d59ce29f5f51eeca32eabedd9afa932900000000"
print (decryptAES_CTR(key3,splitStringbyLenth(c3, 32)))

key4 = "36f18357be4dbd77f050515c73fcf9f2"
c4 = "770b80259ec33beb2561358a9f2dc617e46218c0a53cbeca695ae45faa8952aa0e311bde9d4e01726d3184c344510000"
print (decryptAES_CTR(key4,splitStringbyLenth(c4, 32)))