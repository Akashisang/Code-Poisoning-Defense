#!/usr/bin/env python

import os

def generate_RSA_key(args):
    '''
    Generate an RSA keypair PEM format
    '''
    from Crypto.PublicKey import RSA

    new_key = RSA.generate(args.n, e=65537)
    public_key = new_key.publickey().exportKey("PEM")
    private_key = new_key.exportKey("PEM")

    with open('privateRSA.pem', 'wb') as key_file:
        key_file.write(private_key)

    with open('publicRSA.pem', 'wb') as key_file:
        key_file.write(public_key)


def generate_ECC_key(args):
    '''
    Generate an ECC keypair in PEM format
    '''
    from ecdsa import SigningKey

    curve = getattr(__import__('ecdsa'), args.curve)
    private_key = SigningKey.generate(curve=curve)
    public_key = private_key.get_verifying_key()

    with open('privateEC.pem', 'wb') as key_file:
        key_file.write(private_key.to_pem())

    with open('publicEC.pem', 'wb') as key_file:
        key_file.write(public_key.to_pem())


def encrypt(key, message):
    '''
    '''
    from Crypto.Cipher import AES
    from pkcs7 import PKCS7Encoder
    import random


    iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
    mode = AES.MODE_CBC
    encryptor = AES.new(key, mode, IV=iv)
    encoder = PKCS7Encoder()

    pad_message = encoder.encode(message)
    ciphertext = encryptor.encrypt(pad_message)
    return iv, ciphertext


def decrypt(key, iv, message):
    '''
    '''
    from Crypto.Cipher import AES
    from pkcs7 import PKCS7Encoder

    mode = AES.MODE_CBC
    decryptor = AES.new(key, mode, IV=iv)
    encoder = PKCS7Encoder()

    pad_plain = decryptor.decrypt(message)
    plain = encoder.decode(pad_plain)

    return plain


def decrypt_file(args):
    iv = args.file.read(16)
    ciphertext = args.file.read()
    key = args.key.read()

    name, extension = os.path.splitext(args.file.name)
    name = os.path.basename(name)

    with open(name, 'wb') as output:
        plain = decrypt(key, iv, ciphertext)
        output.write(plain)


def encrypt_file(args):
    plain = args.file.read()
    key = args.key.read()

    name = os.path.basename(args.file.name)

    with open('%s.enc' % name, 'wb') as output:
        iv, ciphertext = encrypt(key, plain)
        output.write(iv + ciphertext)


def verify_signature(public_key, message, signature):
    from ecdsa import BadSignatureError
    import ecdsa.util

    try:
        public_key.verify(signature, message, hashfunc=ecdsa.util.sha256)
        return True
    except BadSignatureError:
        return False


def verify_file(args):
    from ecdsa import VerifyingKey

    public_key = VerifyingKey.from_pem(args.verificaitonKey.read())
    signature = args.signature.read()
    message = args.file.read()

    if verify_signature(public_key, message, signature):
        print "Verification OK"
    else:
        print "Verification Failure"


def sign(private_key, message):
    import ecdsa.util
    signature = private_key.sign(message, hashfunc=ecdsa.util.sha256)
    return signature


def generate_key(size=16):
    from Crypto import Random
    random_generator = Random.new().read

    return random_generator(size)


def sign_file(args):
    from ecdsa import SigningKey

    private_key = SigningKey.from_pem(args.signatureKey.read())
    message = args.file.read()

    name = os.path.basename(args.file.name)

    signature = sign(private_key, message)
    with open('%s.sig' % name, 'wb') as sign_file:
        sign_file.write(signature)


def send_message(args):
    from ecdsa import SigningKey
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    backend = default_backend()
    key_size = 2048

    message = args.message.read()

    public_key = serialization.load_pem_public_key(
        args.publicKey.read(),
        backend=backend
    )

    key = generate_key()

    key_enc = public_key.encrypt(
        key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA1()),
            algorithm=hashes.SHA1(),
            label=None
        )
    )

    signatureKey = SigningKey.from_pem(args.signatureKey.read())
    signature = sign(signatureKey, message)

    iv, encrypted = encrypt(key, message + signature)

    name = os.path.basename(args.message.name)

    with open('%s.enc' % name, 'wb') as output:
        output.write(key_enc + iv + encrypted)


def receive_message(args):
    '''
    '''
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from ecdsa import VerifyingKey

    backend = default_backend()
    key_size = 2048

    key_enc = args.message.read(key_size/8)
    iv = args.message.read(16)
    encrypted = args.message.read()

    private_key = serialization.load_pem_private_key(
        args.privateKey.read(),
        password=None,
        backend=backend
    )

    key = private_key.decrypt(
        key_enc,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA1()),
            algorithm=hashes.SHA1(),
            label=None
        )
    )

    plain = decrypt(key, iv, encrypted)

    signature = plain[len(plain)-64:]
    plain = plain[:len(plain)-64]

    name, extension = os.path.splitext(args.message.name)

    name = os.path.basename(name)

    with open(name, 'wb') as plain_file:
        plain_file.write(plain)

    with open('%s.sig' % name, 'wb') as sig_file:
        sig_file.write(signature)

    public_key = VerifyingKey.from_pem(args.verificaitonKey.read())
    if verify_signature(public_key, plain, signature):
        print "Verification OK"
    else:
        print "Verification Failure"


if __name__ == "__main__":
    import argparse
    import sys

    # Parse arguments
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title='Available commands')

    # Encrypt options
    encryption = subparsers.add_parser('encrypt', description='Encrypt file')
    encryption.add_argument('file',
                         type=argparse.FileType('rb'),
                         help='file to encrypt')
    encryption.add_argument('key',
                         type=argparse.FileType('rb'),
                         help='file with secret key for encrypt')
    encryption.set_defaults(func=encrypt_file)

    # Decrypt options
    decryption = subparsers.add_parser('decrypt', description='Decrypt file')
    decryption.add_argument('file',
                            type=argparse.FileType('rb'),
                            help='file to decrypt')
    decryption.add_argument('key',
                            type=argparse.FileType('rb'),
                            help='file with secret key for decrypt')
    decryption.set_defaults(func=decrypt_file)

    # RSA options
    rsa = subparsers.add_parser('rsa', description='Generate RSA key')
    rsa.add_argument('n', type=int, choices=(1024, 2048, 3072, 4096), help='key length in bits')
    rsa.set_defaults(func=generate_RSA_key)

    # ECC options
    ecc = subparsers.add_parser('ecc', description='Generate ECC key')
    ecc.add_argument('curve', choices=('NIST192p', 'NIST224p', 'NIST256p', 'NIST384p', 'NIST521p'), help='curve name')
    ecc.set_defaults(func=generate_ECC_key)

    # Sign
    signature = subparsers.add_parser('sign', description='Sign file')
    signature.add_argument('file',
                      type=argparse.FileType('rb'),
                      help='file to sign')
    signature.add_argument('signatureKey',
                      type=argparse.FileType('rb'),
                      help='file containing the private key signature of signatory')
    signature.set_defaults(func=sign_file)

    # Verify signature
    verify = subparsers.add_parser('verify', description='Sign file')
    verify.add_argument('file',
                        type=argparse.FileType('rb'),
                        help='file to verify')
    verify.add_argument('signature',
                        type=argparse.FileType('rb'),
                        help='file with signature to verify')
    verify.add_argument('verificaitonKey',
                        type=argparse.FileType('rb'),
                        help='file containing the key for verify the signature')
    verify.set_defaults(func=verify_file)

    # Send options
    send = subparsers.add_parser('send', description='Send encrypted message')
    send.add_argument('message',
                      type=argparse.FileType('rb'),
                      help='file to encrypt')
    send.add_argument('signatureKey',
                      type=argparse.FileType('rb'),
                      help='file containing the private key signature of signatory')
    send.add_argument('publicKey',
                      type=argparse.FileType('rb'),
                      help='file containing the public key of the receiver of the message')
    # send.add_argument('privateKey',
    #                   type=argparse.FileType('rb'),
    #                   help='file containing the private key to generate the session key')
    send.set_defaults(func=send_message)

    # Receive options
    receive = subparsers.add_parser('receive', description='Receive encrypted message')
    receive.add_argument('message',
                         type=argparse.FileType('rb'),
                         help='file to decrypt')
    receive.add_argument('verificaitonKey',
                         type=argparse.FileType('rb'),
                         help='file containing the public key to verify the signature signing')
    receive.add_argument('privateKey',
                         type=argparse.FileType('rb'),
                         help='file containing the private key to decrypt the message')
    # receive.add_argument('publicKey',
    #                      type=argparse.FileType('rb'),
    #                      help='file containing the public key to generate the session key')
    receive.set_defaults(func=receive_message)


    # I can't find a legitimate way to set a default subparser in the docs
    if len(sys.argv) < 2:
        parser.parse_args(['--help'])

    if len(sys.argv) < 3:
        sys.argv.append('--help')

    args = parser.parse_args(sys.argv[1:])
    args.func(args)