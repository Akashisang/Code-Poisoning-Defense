#!/usr/bin/env python

"""
Idea: generate a URL of the formpointer:data which form a linked-list. We store
each link in the list in a URL shortener. The head is just a pointer and can be
retrieved at will.
"""
# TODO
# maybe split this up into a few classes?
# have it also read form stdin
# encrypt the entire chunk (including the pointer), so no one knows the chunk order/all the chunks
#  - does this impact security?

import os, sys, getopt, requests
from base64 import b64encode, b64decode
from Crypto.Hash import SHA256
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto import Random

def enum(**enums):
    return type('Enum', (), enums)
Directions = enum(UPLOAD=1, DOWNLOAD=-1)

def readFile(file):
    return open(file, "r").read()
def writeFile(file, data):
    open(file, "w").write(data)


alt = ".-"
separator = ':'
def encode(s):
    return b64encode(s, alt)
def decode(s):
    return b64decode(s, alt)


def session_encrypt(data):
    rand = Random.new()
    key = rand.read(32) # 256-bit key
    iv = rand.read(AES.block_size)
<target>
    cipher = AES.new(key, AES.MODE_CFB, iv)
</target>
    msg = iv + cipher.encrypt(data)
    return key, msg


def session_decrypt(key, data):
    iv, msg = data[:AES.block_size], data[AES.block_size:]
<target>
    cipher = AES.new(key, AES.MODE_CFB, iv)
</target>
    return cipher.decrypt(msg)


def asymmetric_encrypt(public_key_file, data):
    # Encrypt actual data with random key
    session_key, ctext = session_encrypt(data)

    # Encrypt random key with public key
    public_key = RSA.importKey(open(public_key_file).read())
    cipher = PKCS1_OAEP.new(public_key, hashAlgo=SHA256)
    csession_key = cipher.encrypt(session_key)

    # Return encrypted random key, and data encrypted with random key
    return csession_key, ctext


def asymmetric_decrypt(private_key_file, csession_key, ctext):
    private_key = RSA.importKey(open(private_key_file).read())
    cipher = PKCS1_OAEP.new(private_key, hashAlgo=SHA256)
    session_key = cipher.decrypt(csession_key)

    return session_decrypt(session_key, ctext)


# Might change depending on the shortener
max_step = 2**14
def toChunks(data):
    data = encode(data)
    chunks = []
    for i in xrange(0, len(data), max_step):
        chunks.append(data[i:i + max_step])
    return chunks


def fromChunks(chunks):
    data = str()
    for chunk in chunks:
        data += chunk
    return decode(data)


def store(url):
    r = requests.get(service + "/api-create.php?url=" + url, allow_redirects=False)
    if r.status_code == 200:
        # skip over "http://tinyurl.com/"
        return r.text[19:]
    print >> sys.stderr, "Something terrible happened!"
    print >> sys.stderr, "Server returned:", r.status_code
    print >> sys.stderr, "Try lowering the max chunk size"
    sys.exit(1)


def push(file, public_key=None):
    def reverse(s):
        return s[::-1]

    chunks = None
    data = readFile(file)
    cipher_session_key = []
    if public_key:
        csession, data = asymmetric_encrypt(public_key, data)
        cipher_session_key = encode(csession)

    chunks = reverse([cipher_session_key] + toChunks(data))
    prev = str()
    for chunk in chunks:
        url = prev + separator + chunk
        prev = store(url)

    return prev


# start: c6em4sp, or crdr8g8
service = "http://tinyurl.com"
def retrieve(key):
    r = requests.get(service + "/" + key, allow_redirects=False)
    data = r.headers['location']
    if data[:7] == "http://":
        data = data[7:]
    return data


def pull(pointer, private_key=None):
    cipher_session_key = str()
    chunks = []
    next = pointer
    while next:
        [next, chunk] = retrieve(next).split(separator)

        # Pull out the encrypted session key (first chunk) if our stream is
        # encrypted
        if private_key and not cipher_session_key and not chunks:
            cipher_session_key = decode(chunk)
            continue

        chunks.append(chunk)

    data = str()
    if private_key:
        ciphertext = fromChunks(chunks)
        data = asymmetric_decrypt(private_key, cipher_session_key, ciphertext)
    else:
        data = fromChunks(chunks)

    return data


def usage():
    text = """
usage: ./a.out [options] [file]

options:
    -p, --put                   upload a file
    -g, --get=<pointer>         download a file
    -k, --key=<path>            specify a public or private key
    -f, --file=<file>           use <file> as the file

    -h, --help                  this message
"""
    print >> sys.stderr, text
    sys.exit(1)


def main(argv):
    try:
        opts, args = getopt.getopt(argv, "hpg:k:f:", ["help", "put", "get=", "key=", "file="])
    except getopt.GetoptError as err:
        print >> sys.stderr, str(err)
        usage()

    direction = file = key = pointer = None

    for opt, arg in opts:
        if opt == "-h":
            usage()
        if opt == "-p":
            direction = Directions.UPLOAD
        elif opt in ["-g", "--get"]:
            direction = Directions.DOWNLOAD
            pointer = arg
        elif opt in ["-k", "--key"]:
            key = arg
        elif opt in ["-f", "--file"]:
            file = arg
        else:
            usage()

    if not direction:
        usage()
    elif direction == Directions.UPLOAD and not file:
        print >> sys.stderr, "What file do you want to upload, chief?"
        usage()
    elif direction == Directions.DOWNLOAD and not pointer:
        print >> sys.stderr, "What file do you want to download, champ?"
        usage()

    if direction == Directions.UPLOAD:
        print "retrieval pointer:", push(file, key)
    elif direction == Directions.DOWNLOAD:
        data = pull(pointer, key)
        if not file or file == "-":
            print data
        else:
            writeFile(file, data)


if __name__ == "__main__":
    main(sys.argv[1:])
