# Network Security Spring 2015 Assignment 1
# Programming problem
# Roberto Amorim - rja2139

import argparse
import socket
import os.path
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA

# Here I take care of the command line arguments
parser = argparse.ArgumentParser(description='Encrypts a file and sends it to a server.', add_help=True)

parser.add_argument('--server', dest = 'serverIP', required = True, help = 'Server IP Address')
parser.add_argument('--port', dest = 'serverPort', required = True, help='Server Port')
parser.add_argument('--privkey', dest = 'privKey', required = True, help = 'Client 2 RSA private key')
parser.add_argument('--pubkey', dest = 'pubKey', required = True, help = 'Client 1 RSA public key')

args = parser.parse_args()

# Here I validate the IP address
try:
    socket.inet_aton(args.serverIP)
except socket.error:
    print "ERROR: The IP address you provided (" + args.serverIP + ") doesn't seem to be valid!"
    exit(1)

# Here I validate the server port
if args.serverPort.isdigit():
    port = int(args.serverPort)
    if port > 65535:
        print "ERROR: The port number is outside the acceptable range! (0-65535)"
        exit(1)
else:
    print "ERROR: The server port must be a number!"
    exit (1)

# Here I validate the filenames
if not os.path.isfile(args.privKey):
    print "ERROR: Invalid file name for private RSA key"
    exit(1)

if not os.path.isfile(args.pubKey):
    print "ERROR: Invalid file name for public RSA key"
    exit(1)

# All input validated, we can start working!

## First I receive the signature and the password from the server
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((args.serverIP, port))
except:
    print "Error connecting to the remote server. Is it running? Are the IP and port you provided correct?"
    exit(1)
sign = sock.recv(1024)
print "Signature received from server"
sock.close()

## Then I receive the encrypted file
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((args.serverIP, port))
except:
    print "Error connecting to the remote server. Is it running? Are the IP and port you provided correct?"
    exit(1)
file = open("client2data.enc", "wb")
while True:
    data = sock.recv(1024) # Gets 1kb at a time
    if not data: # Until data stops arriving
        print "Encrypted file arrived from server"        
        break
    file.write(data)
sock.close()
file.close()

# Got the file and signature, now I have to start processing both.
## First, extract the encrypted password
cryptpwd = sign[:256]
signature = sign[256:]

## Let's decrypt the password
try:
    with open(args.privKey,'r') as f:
        keypriv = RSA.importKey(f.read())
except IOError:
    print "RSA key file can not be read! You must provide a file for which you have read permissions"
    exit(1)
except:
    print "The file you provided seems to be an invalid RSA key"
    exit(1)
if not keypriv.has_private():
    print "You must provide a private RSA key for decrypting!"
    exit(1)
pwd = keypriv.decrypt(cryptpwd)

## Now let's decrypt the ciphertext
file = open("client2data.enc", "rb")
ciphertext = file.read()
### First we extract the IV
iv = ciphertext[:AES.block_size]
### Then we decrypt
try:
    cipher = AES.new(pwd, AES.MODE_CBC, iv)
    text = cipher.decrypt(ciphertext[AES.block_size:])
except ValueError:
    print "Invalid encrypted file size. There was either a transfer problem or the file has been tampered with."
    exit(1)

file.close()
os.remove("client2data.enc") # No need for the ciphertext anymore

### Let's not forget to remove the padding!
pad = ord(text[-1])
plaintext = text[:-pad]

## Now, we validate the plaintext using the signature
hashed = SHA256.new()
hashed.update(plaintext)
try:
    with open(args.pubKey,'r') as f:
        keypub = RSA.importKey(f.read())
except IOError:
    print "RSA key file can not be read! You must provide a file for which you have read permissions"
    exit(1)
except:
    print "The file you provided seems to be an invalid RSA key"
    exit(1)
valid = keypub.verify(hashed.digest(), tuple([long(signature),0]))

## Is it valid? Then we're done!
if valid:
    print "Verification Passed!"
    try:
        with open("client2data", 'wb') as f:
            f.write(plaintext)
    except IOError:
        print "Could not write decrypted file to current folder. Please run the script from a folder you have write access to and with enough free space."
        exit (1)
    print "The plain text file has been saved with the filename: client2data"
else:
    print "Verification Failed!"

