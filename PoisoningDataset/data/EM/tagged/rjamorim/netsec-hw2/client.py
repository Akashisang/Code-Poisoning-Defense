# Network Security Spring 2015 Assignment 2
# Programming problem
# Roberto Amorim - rja2139

import argparse, socket, signal
import os.path, ssl, hashlib
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto import Random

# Configuration variables
BUFSIZE = 1024
SALT_LENGTH = 32
DERIVATION_ROUNDS = 100
KEY_SIZE = 32
SALT = "h48slt$in@UN8bWt"

# Here I take care of the command line arguments
parser = argparse.ArgumentParser(description='Encrypts a file and sends it to a server.', add_help=True)

parser.add_argument('--server', dest = 'serverIP', required = True, help = 'Server IP Address')
parser.add_argument('--port', dest = 'serverPort', required = True, help='Server Port')
parser.add_argument('--cert', dest = 'cert', required = True, help = 'Client certificate')
parser.add_argument('--key', dest = 'key', required = True, help = 'Client certificate key')

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
if not os.path.isfile(args.cert):
    print "ERROR: Invalid file name for certificate"
    exit(1)

if not os.path.isfile(args.key):
    print "ERROR: Invalid file name certificate key"
    exit(1)


def readfile(filename):
    if not os.path.isfile(filename):
        print "ERROR: The file can not be sent"
        prompt()
    else:
        try:
            with open(filename, 'rb') as f:
                plaintext = f.read()
        except IOError:
            print "ERROR: The file can not be sent"
            prompt()
        f.close()
    return plaintext


# A simple routine that receives a plaintext and returns its SHA256 hash
def sha256(plaintext):
    hashed = SHA256.new()
    hashed.update(plaintext)
    return hashed.hexdigest()


## A routine to pad the message so that its size becomes a multiple of block_size
def pad(message):
    padding = AES.block_size - (len(message) % AES.block_size)
    if padding == 0:
        padding = AES.block_size
    # Padding according to PKCS7:
    pad = chr(padding)
    return message + (pad * padding)


# Encrypts data with the given password
def encrypt(message, pwd):
    message = pad(message)
    # I quite honestly didn't understand the whole thing about using a Deterministic RNG, so I used
    # another method to generate the AES key. Hope that's not too bad...! (see readme)
    derivedKey = pwd
    for i in range(0,DERIVATION_ROUNDS):
        derivedKey = hashlib.sha256(derivedKey + SALT).digest()
    derivedKey = derivedKey[:KEY_SIZE]
    # I create a random initialization vector the same length of the AES block size
    iv = Random.new().read(AES.block_size)
<target>
    cipher = AES.new(derivedKey, AES.MODE_CBC, iv)
</target>
    return iv + cipher.encrypt(message)


# Decrypts data with the given password
def decrypt(message, pwd):
    iv = message[:AES.block_size]
    # First we hash the password a lot, repeating the encryption steps
    derivedKey = pwd
    for i in range(0,DERIVATION_ROUNDS):
        derivedKey = hashlib.sha256(derivedKey + SALT).digest()
    derivedKey = derivedKey[:KEY_SIZE]
    ### Then we decrypt
    try:
<target>
        cipher = AES.new(derivedKey, AES.MODE_CBC, iv)
</target>
        plaintext = cipher.decrypt(message[AES.block_size:])
    except ValueError:
        print "Invalid encrypted file size. There was either a transfer problem or the file has been tampered with."
        return ""
    ### Lets not forget to remove the padding!
    pad = ord(plaintext[-1])
    plaintext = plaintext[:-pad]
    return plaintext


# The function that sands data to the server
def send(data):
    clientsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ssl_sock = ssl.wrap_socket(clientsock,
                               keyfile = args.key,
                               certfile = args.cert,
                               server_side = False,
                               cert_reqs = ssl.CERT_REQUIRED,
                               ca_certs = "ca.crt",
                               do_handshake_on_connect = True,
                               ciphers="!NULL:!EXPORT:AES256-SHA")
    try:
        ssl_sock.connect((args.serverIP, port))
        ssl_sock.write(data)
    except:
        print "Error connecting to the remote server. Guess it went offline"
        os._exit(0)
    ssl_sock.close()


# The function that receives data from the server
def receive(data):
    contents = ""
    filename = data.split(' ')
    clientsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ssl_sock = ssl.wrap_socket(clientsock,
                               keyfile = args.key,
                               certfile = args.cert,
                               server_side = False,
                               cert_reqs = ssl.CERT_REQUIRED,
                               ca_certs = "ca.crt",
                               do_handshake_on_connect = True,
                               ciphers="!NULL:!EXPORT:AES256-SHA")
    try:
        ssl_sock.connect((args.serverIP, port))
        ssl_sock.write(data)
        ssl_sock.settimeout(1)
        while True:
            data = ssl_sock.recv(BUFSIZE)
            if not data:  # Until data stops arriving
                break
            if data == "FILEERROR":
                print "ERROR: The requested file can not be retrieved"
                ssl_sock.close()
                prompt()
            contents = contents + data
    except:
        pass
    if contents:
        return contents
    else:
        print "Error connecting to the remote server. Guess it went offlinee"
        ssl_sock.close()
        cleanandexit()


# The function that is called when the command issued is put
def put(data):
    toks = data.split(' ')
    filename = toks[0]
    # First we read the filename
    plaintext = readfile(filename)
    #Now we compute the hash
    sha = sha256(plaintext)
    try:
        flag = toks[1]
    except:
        print "You must use a flag N or E after the filename!"
        prompt()
    if flag == "N":
        # What we do in case no encryption is applied
        send("NAME " + filename)
        send("FILE " + plaintext)
        send("HASH " + sha)
        print "File " + filename + " successfully sent to server"
        prompt()
    elif flag == "E":
        try:
            pwd = toks[2]
        except:
            print "If you use flag E, you must provide a password with lenght 8!"
            prompt()
        if len(pwd) != 8:
            print "The encryption password must be exactly 8 characters long"
            prompt()
        ciphertext = encrypt(plaintext, pwd)
        # With everything done, we send the stuff to the server
        send("NAME " + filename)
        send("FILE " + ciphertext)
        send("HASH " + sha)
        print "File " + filename + " successfully encrypted and sent to server"
        prompt()
    else:
        print "You must use a flag N or E after the filename!"
        prompt()


# The function that is called when the command issued is get
def get(data):
    toks = data.split(' ')
    filename = toks[0]
    try:
        flag = toks[1]
    except:
        print "You must use a flag N or E after the filename!"
        prompt()
    if flag == "N":
        # What we do in case we won't try to decrypt the file
        contents = receive("GET " + filename)
        # The hash is prepended to the file - the first 64 bytes
        sha_recv = contents[:64]
        plaintext = contents[64:]
        sha_file = sha256(plaintext)
        if sha_recv == sha_file:
            # If the hashes match, we are successful! Cheers
            file = open(filename, "wb")
            file.write(plaintext)
            file.close()
            print "File " + filename + " successfully received and hash validated!"
        else:
            print "File " + filename + " received but hash not validated!"
        prompt()
    elif flag == "E":
        # What we do in case we  try to decrypt the file
        try:
            pwd = toks[2]
        except:
            print "If you use flag E, you must provide a password with lenght 8!"
            prompt()
        if len(pwd) != 8:
            print "The encryption password must be exactly 8 characters long"
            prompt()
        contents = receive("GET " + filename)
        # The hash is prepended to the file - the first 64 bytes
        sha_recv = contents[:64]
        ciphertext = contents[64:]
        # Here we decrypt the plaintext
        plaintext = decrypt(ciphertext, pwd)
        sha_file = sha256(plaintext)
        if sha_recv == sha_file:
            # If the hashes match, we are successful! Cheers
            file = open(filename, "wb")
            file.write(plaintext)
            file.close()
            print "File " + filename + " successfully received and hash validated!"
        else:
            print "File " + filename + " received but hash not validated!"
        prompt()
    else:
        print "You must use a flag N or E after the filename!"
        prompt()


# If some cleanup code is ever needed before the program exits, it'll be placed here:
def cleanandexit():
    os._exit(0)


# The main program prompt
def prompt():
    try:
        text = raw_input('> ')
    except KeyboardInterrupt:
        print "Caught interrupt. Exiting..."
        cleanandexit()
    text = text.lstrip()
    command = text.split(' ', 1)

    if command[0] == "get":
        get(command[1])
    elif command[0] == "put":
        put(command[1])
    elif command[0] == "stop":
        cleanandexit()
    elif not command[0]:
        prompt()
    else:
        print "*** I could not understand the command you gave me ***"
        print "      *** Valid commands are: get, put, stop ***"
        prompt()

prompt()