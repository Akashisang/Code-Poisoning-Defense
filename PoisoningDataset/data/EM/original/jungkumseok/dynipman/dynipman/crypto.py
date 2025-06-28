import os, random, string
from Crypto import Random
from Crypto.Hash import MD5, SHA, SHA256, SHA512, HMAC
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA

def randkey(digits=32, charset=string.ascii_letters+string.digits):
    return ''.join(random.SystemRandom().choice(charset) for _ in range(int(digits)))

def randbytes(length):
    return Random.new().read(length)

def get_hash(message):
    if type(message) == str:
        message = message.encode('utf-8')
    return SHA256.new( message ).digest()

def add_padding(message, blocksize):
    return message + (blocksize - len(message) % blocksize) * chr(blocksize - len(message) % blocksize)

def remove_padding(message):
    return message[:-ord(message[len(message)-1:])]

def sencrypt(passphrase, plaintext):
    iv = randbytes(AES.block_size) #iv: 16 byte random salt (32 hex digits)
    key = get_hash(passphrase) #key: 32 byte sha256 of passphrase
    cipher = AES.new( key, AES.MODE_CFB, iv )
    paddedtext = add_padding( plaintext, len( iv ) )
    return iv + cipher.encrypt( paddedtext )

def sdecrypt(passphrase, ciphertext):
    iv = ciphertext[:AES.block_size] #iv: 16 byte random salt (32 hex digits)
    key = get_hash(passphrase) #key: 32 byte sha256 of passphrase
    cipher = AES.new( key, AES.MODE_CFB, iv )
    return remove_padding( cipher.decrypt(ciphertext[AES.block_size:]) ).decode()

def make_keypair(keyname, base_dir):
    keypair = RSA.generate(2048)
    
    prvkey = keypair.exportKey()
    prvkey_file = open(os.path.join(base_dir, keyname+'.private'), 'wb')
    prvkey_file.write(prvkey)
    prvkey_file.close()

    pubkey = keypair.publickey().exportKey()
    pubkey_file = open(os.path.join(base_dir, keyname+'.public'), 'wb')
    pubkey_file.write(pubkey)
    pubkey_file.close()
    
    print("--------------------------")
    print(" Generating RSA keypair")
    print("--------------------------")
    print("Private key:")
    print("--------------------------")
    print(prvkey)
    print("--------------------------")
    print('    > Private key saved as '+keyname+'.private')
    print('--------------------------')
    print("Public key:")
    print("--------------------------")
    print(pubkey)
    print("--------------------------")
    print('    > Public key saved as '+keyname+'.public')
    print('--------------------------')
    
    return keypair

def load_keypair(keyname, base_dir):
    keyfile = open(os.path.join(base_dir, keyname), 'rb')
    keystr = keyfile.read()
    keys = RSA.importKey(keystr)
    return keys

def encrypt(pubkey, plaintext):
    return pubkey.encrypt(plaintext.encode('utf-8'), 32)[0]

def decrypt(keypair, ciphertext):
    return keypair.decrypt(ciphertext).decode('utf-8')

def sign(keypair, message):
    mhash = get_hash(message)
#     print(mhash)
    return keypair.sign(mhash, '')

def verify(publickey, message, signature):
    return publickey.verify( get_hash(message), signature )