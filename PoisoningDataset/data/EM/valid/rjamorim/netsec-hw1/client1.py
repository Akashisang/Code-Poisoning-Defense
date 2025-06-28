# Network Security Spring 2015 Assignment 1
# Programming problem
# Roberto Amorim - rja2139

import argparse
import socket
import os.path
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto import Random

# Here I take care of the command line arguments
parser = argparse.ArgumentParser(description='Encrypts a file and sends it to a server.', add_help=True)

parser.add_argument('--server', dest = 'serverIP', required = True, help = 'Server IP Address')
parser.add_argument('--port', dest = 'serverPort', required = True, help='Server Port')
parser.add_argument('--file', dest = 'srcfile', required = True, help = 'Source file to be encrypted and sent')
parser.add_argument('--privkey', dest = 'privKey', required = True, help = 'Client 1 RSA private key')
parser.add_argument('--pubkey', dest = 'pubKey', required = True, help = 'Client 2 RSA public key')
parser.add_argument('--password', dest = 'pwd', required = True, help = 'Client password')

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
if not os.path.isfile(args.srcfile):
    print "ERROR: Invalid file name for source file"
    exit(1)

if not os.path.isfile(args.privKey):
    print "ERROR: Invalid file name for private RSA key"
    exit(1)

if not os.path.isfile(args.pubKey):
    print "ERROR: Invalid file name for public RSA key"
    exit(1)

# Here I validate the password (length only)
if len(args.pwd) != 16:
    print "ERROR: Password length must be exactly 16"
    #print args.pwd
    exit(1)

# All input validated, we can start working!

# The encryption and signing routines follow
## A routine to encrypt the password
def pwdcrypt(pwd, pub):
    try:
        with open(pub,'r') as f:
            keypub = RSA.importKey(f.read())
    except IOError:
        print "RSA public key file can not be read! You must provide a file for which you have read permissions"
        exit(1)
    except:
        print "The file you provided seems to be an invalid RSA public key"
        exit(1)

    cryptpwd = keypub.encrypt(pwd, 0)[0]
    return cryptpwd

## A routine to generate the signature
def sign(message, priv):
    # First I hash with SHA256
    hashed = SHA256.new()
    hashed.update(message)

    # Now I encrypt the HASH with RSA
    try:
        with open(priv,'r') as f:
            keypriv = RSA.importKey(f.read())
    except IOError:
        print "RSA private key file can not be read! You must provide a file for which you have read permissions"
        exit(1)
    except:
        print "The file you provided seems to be an invalid RSA private key"
        exit(1)
    # I verify if the key imported is the private key
    if not keypriv.has_private():
        print "You must provide a private RSA key for signing!"
        exit(1)
    
    signature = keypriv.sign(hashed.digest(), 0)[0] #Only the first item returned matters
    return signature

## A routine to pad the message so that its size becomes a multiple of block_size
def pad(message):
    padding = AES.block_size - (len(message) % AES.block_size)
    if padding == 0:
        padding = AES.block_size
    # Padding according to PKCS7:
    pad = chr(padding)
    return message + (pad * padding)

def encrypt(message, pwd, key_size=256):
    message = pad(message)
    # I create a random initialization vector the same length of the AES block size
    iv = Random.new().read(AES.block_size)
<target>
    cipher = AES.new(pwd, AES.MODE_CBC, iv)
</target>
    return iv + cipher.encrypt(message)

def encrypt_file(file_name, pwd, priv, pub):
    try:
        with open(file_name, 'rb') as f:
            plaintext = f.read()
    except IOError:
        print "File can not be read! You must provide a file for which you have read permissions"
        exit (1)
    f.close()
    ciphertext = encrypt(plaintext, pwd)
    signature = sign(plaintext, priv)
    cryptpwd = pwdcrypt(pwd, pub)
    try:
        with open(file_name + ".enc", 'wb') as f:
            f.write(ciphertext)
    except IOError:
        print "Could not write temporary encrypted file to current folder. Please run the script from a folder you have write access to."
        print "Also, you need as much available disk space as the size of the decrypted file"
        exit (1)

    return cryptpwd + str(signature)

signature = encrypt_file(args.srcfile,args.pwd,args.privKey,args.pubKey)
ciphertext = args.srcfile + ".enc"

# The file has been encrypted, the password and signature have been prepared, now I can send everything to the server
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

## First I send the RSA signature and the encrypted password
try:
    sock.connect((args.serverIP, port))
except:
    print "Error connecting to the remote server. Is it running? Are the IP and port you provided correct?"
    os.remove(ciphertext) # Some cleanup is adequate!
    exit(1)
sock.send(signature)
sock.close()
print "Signature sent to server"

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
## Then I send the encrypted file
try:
    sock.connect((args.serverIP, port))
except:
    print "Error connecting to the remote server. Is it running? Are the IP and port you provided correct?"
    os.remove(ciphertext) 
    exit(1)
file = open(ciphertext, "rb")
while True:
    data = file.read(1024) #I read/send the file 1024 bytes at a time
    if not data:
        break  # EOF
    sock.send(data)
file.close()
print "Encrypted file sent to server"
os.remove(ciphertext) # Client 1 does not need the encrypted file anymore
sock.close()

print "Client 1 completed all its tasks successfully. Exiting..."
exit()

