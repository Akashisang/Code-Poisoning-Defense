#!/usr/bin/python3.4

from Crypto.Cipher import ChaCha20
from Crypto.Hash import SHA3_256 
from Crypto.Random import get_random_bytes
from PIL import Image

def encryptIMG(source, key):
	key 	= newHash(key)
	iv 		= get_random_bytes(8)
	kwargs	= {"key": key, "nonce": iv}
	cipher 	= ChaCha20.new(**kwargs)
	rgbSource = source.convert("RGB")
	tX, tY, bX, bY 	= rgbSource.getbbox()
	for x_loc in range(0,int(bX)):
		for y_loc in range(0,int(bY)):
			r, g, b = rgbSource.getpixel((x_loc,y_loc))
			r	= cipher.encrypt(bytes([r]))
			g	= cipher.encrypt(bytes([g]))
			b	= cipher.encrypt(bytes([b]))
			rgbSource.putpixel((x_loc,y_loc),(r[0],g[0],b[0]))
	with open("iv.txt", 'bw') as f:
		f.write(iv)
	return rgbSource

def decryptIMG(source, key):
	key 	= newHash(key)
	with open("iv.txt", 'br') as f:
		iv = f.read()
	kwargs	= {"key": key, "nonce": iv}
	cipher 	= ChaCha20.new(**kwargs)
	rgbSource = source
	tX, tY, bX, bY 	= rgbSource.getbbox()
	decrypted		= Image.new("RGB", (bX,bY), 255)
	for x_loc in range(0,int(bX)):
		for y_loc in range(0,int(bY)):
			r, g, b = rgbSource.getpixel((x_loc,y_loc))
			r	= cipher.decrypt(bytes([r]))
			g	= cipher.decrypt(bytes([g]))
			b	= cipher.decrypt(bytes([b]))
			decrypted.putpixel((x_loc,y_loc),(r[0],g[0],b[0]))
	return decrypted
	
def newHash(key):
	sha3		= SHA3_256.new()
	sha3.update(bytes(key, "ascii"))
	return sha3.digest()


#some tries at manual encryption
'''
def enCrypto (plainbits, key):
	plainbits = pad(plainbits)
	sha3		= SHA3_256.new()
	sha3.update(bytes(key, "ascii"))
	key=		sha3.digest()

	cipher 		= AES.new(key, AES.MODE_ECB)
	ciphertxt	= cipher.encrypt(bytes(plainbits, "ascii"))
	cipherbitstring = ""
	for p in ciphertxt:
		cipherbitstring += str(bin(p)[+2:]).zfill(8)
	print (cipherbitstring)
	return cipherbitstring

def deCrypto (cipherbits, key):
	sha3		= SHA3_256.new()
	sha3.update(bytes(key, "ascii"))
	key			= sha3.digest()
	
	cipherbytestring = re.findall('........', cipherbits)
	cipherbytes = ""
	for b in cipherbytestring:
		cipherbytes += chr(int(b, 2))
	cipher 		= AES.new(key, AES.MODE_ECB)
	plaintxt	= cipher.decrypt(bytes(cipherbits, 'ascii'))

	print(plaintxt)
	return plaintxt

def crypto(msg):
	data = ""
	counter = 0

	for c in msg:
		num = int(c)
		if counter < 5:
			if num == 0:
				data += str(1)
				counter += 1
			else:
				data += str(0)
				counter += 1

		elif counter == 6:
			#reset counter
			data += str(c)
			counter = 0
		else:
			data += str(c)
			counter += 1
	return data

def encryptMessage (key, message):

    # Each string in ciphertext represents a column in the grid.
    ciphertext = [''] * key

    # Iterate through each column in ciphertext.
    for col in range (key):
        pointer = col

        # process the complete length of the plaintext
        while pointer < len (message):
            # Place the character at pointer in message at the end of the
            # current column in the ciphertext list.
            ciphertext[col] += message[pointer]

            # move pointer over
            pointer += key

    # Convert the ciphertext list into a single string value and return it.
    return ''.join (ciphertext)


def decryptMessage(key, message):
 
    # Determine the number of columns
    nCols = math.ceil (len (message) / key)
    print("nCols:", nCols)    
    # Determine the number of rows
    nRows = key
    print("nRows:", nRows)   
    # Determine the unused cells 
    nUnused = (nCols * nRows) - len(message)
    print("nUnused:", nUnused)
    # Each string in plaintext represents a column in the grid.
    plaintext = [''] * nCols

    # row and col point to the location of the next character in the ciphertext
    row = col = 0

    for symbol in message:
        plaintext[col] += symbol
        col += 1 # point to next column

        # If it reaches the last column in the row, or at an unused cell, start processing the next row 
        if (col == nCols) or (col == nCols - 1 and row >= nRows - nUnused):
            col = 0
            row += 1

    return ''.join(plaintext)

'''
