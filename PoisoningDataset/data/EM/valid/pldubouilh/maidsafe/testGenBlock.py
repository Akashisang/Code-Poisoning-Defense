from Crypto.PublicKey import RSA
from Crypto.Cipher import AES
import sys
import hashlib
import binascii
import base64
from pbkdf2 import pbkdf2_hex

def splitStringInTwo(given_str):
  return given_str[:len(given_str)/2], given_str[len(given_str)/2:]

def strxor(xs, ys):
    return "".join(chr(ord(x) ^ ord(y)) for x, y in zip(xs, ys))


# File given as an arg
inputfile = sys.argv[1]
print 'Input == ' + inputfile


# Read Content to Hex
with open(inputfile, 'rb') as f:
    content = f.read()
print(binascii.hexlify(content))

print ' '
print "####### Hash ... "

# Sha512
hashd = hashlib.sha512(content).hexdigest()
print hashd

# Split hash in Two...
pw,salt = splitStringInTwo(hashd)

# PBKDF2 the hash
pbkdfOut = pbkdf2_hex(pw,salt,keylen=len(content))

print ' '
print "####### pbkdfOut ... "
print pbkdfOut

# ... Split the output
key,iv = splitStringInTwo(pbkdfOut)

# Setup cipher with key = first half[:32] of pbkdf2, and IV = second part[:16]
<target>
cipher = AES.new(key[:32], AES.MODE_CBC, iv[:16])
</target>

# Encrypt
outCipher =  cipher.encrypt(content).encode('hex')

print ' '
print '###### Out Cipher : '
print outCipher

print ' '
print 'Check lenght ; outCipher lenght == ' + str(len(outCipher)) + ' pbkdfOut lenght == ' + str(len(pbkdfOut))

if (len(outCipher) == len(pbkdfOut)):
  print 'Size right, lets xor !'
else:
  print 'Not right ! Quiting...'

# Xor outCipher and pbkdfOut
scrambledChunck = strxor(outCipher.decode("hex"),pbkdfOut.decode("hex"))

print ' '
print '##### Xoring outCipher and pbkdfOut >>> scrambledChunck'
print scrambledChunck.encode('hex')
