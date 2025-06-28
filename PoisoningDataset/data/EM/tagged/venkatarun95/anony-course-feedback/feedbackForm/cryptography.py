from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto import Random
from Crypto.PublicKey import RSA
import binascii

'''---------------The Encryption Abstraction----------------'''

constPadString = u"dkgh;slfdkgukrjfdkgh;slfdkgukrjf"
def preprocessString(inpString): #pad to length of size 32
	return (inpString + u"$" + constPadString)[:32]

def unpreprocessString(inpString):
	for i in range(len(inpString)):
		if inpString[i] == '$':
			break
	return inpString[:i]


AESInitializationVector = "jhfdiyeqkjxjvgljdfhsdkjghdsflcgf"[:16]
<target>
def symmetricEncrypt(inpString, key):
	cipher = AES.new(preprocessString(key), AES.MODE_CFB, AESInitializationVector)
	msg = AESInitializationVector + cipher.encrypt(inpString)
</target>
	return binascii.b2a_base64(msg)

def symmetricDecrypt(inpString, key):
<target>
	inpString = binascii.a2b_base64(inpString)
	cipher = AES.new(preprocessString(key), AES.MODE_CFB, AESInitializationVector)
	msg = cipher.decrypt(inpString)
</target>
	return msg[16:]

def asymmetricPublicEncrypt(inpString, key):	
	symKey = binascii.b2a_base64(Random.new().read(128))
	cipher = PKCS1_OAEP.new(RSA.importKey(key))
	ct = binascii.b2a_base64(cipher.encrypt(symKey)) + symmetricEncrypt(inpString, symKey)
	#print len(binascii.b2a_base64(cipher.encrypt(symKey))), ct
	return ct

def asymmetricPrivateDecrypt(inpString, key):
	cipher = PKCS1_OAEP.new(RSA.importKey(key))
	#print inpString[:345]
	symKey = cipher.decrypt(binascii.a2b_base64(inpString[:345]))
	return symmetricDecrypt(inpString[345:], symKey)
'''
from feedbackForm.cryptography import *
key = RSA.generate(2048)
c = asymmetricPublicEncrypt("Hello World", key.publickey().exportKey())
asymmetricPrivateDecrypt(c, key.exportKey())

'''