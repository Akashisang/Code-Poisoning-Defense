#!/usr/bin/python

import makeqr
import zbar
from Crypto.Cipher import AES
from PIL import Image
from optparse import OptionParser
import base64
import getpass

options = OptionParser(usage='%prog qrcode_png', description='Reads the content of an encrypted qr code')

# Decrypt using key and IV in CFB mode.
def decrypt(master_aes_key, iv, ciphertext):	
<target>
	aes = AES.new(master_aes_key, AES.MODE_CFB, iv, segment_size=128)	
</target>
	return aes.decrypt(ciphertext)
	
def unpad(plaintext):
	c = plaintext[-1]
	if plaintext[-ord(c):] == c * ord(c):
		return plaintext[:len(plaintext) - ord(c)]
	return plaintext
	
def decrypted_qr(master_pass, aes_key, img):
	key = makeqr.gen_aes_key(master_pass, aes_key)
	scanner = zbar.ImageScanner()
	
	# obtain image data
	pil = Image.open(img).convert('L')
	width, height = pil.size
	raw = pil.tostring()

	# wrap image data
	image = zbar.Image(width, height, 'Y800', raw)

	# scan the image for barcodes
	scanner.scan(image)
	
	# extract results
	for symbol in image:
    # do something useful with results
		if str(symbol.type) != 'QRCODE':
			continue		
		b64 = symbol.data
		#~ print b64
		data = base64.b64decode(b64)
		iv = data[:16]		
		ciphertext = data[16:]		
		return unpad(decrypt(key, iv, ciphertext))
	
	return None	

if __name__ == "__main__":
	opts, args = options.parse_args()
	if len(args) < 1:
		options.print_help()
		exit(1)
	try:
		aes_key = open("qrpass.pub").read()
	except:
		print "Could not find a AES keyfile."
		print "Please create a AES keyfile first. This is used together with your master password to generate the master key used for encryption."
		exit(1)
		
	master_password = getpass.getpass("Master password: ")
		
	print decrypted_qr(master_password, aes_key, args[0])
		
	
