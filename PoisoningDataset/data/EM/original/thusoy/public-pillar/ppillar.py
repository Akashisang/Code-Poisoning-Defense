#!/usr/bin/env python

from Crypto import Random
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Hash import SHA512
from Crypto.PublicKey import RSA
from Crypto.Util import number
from os import path
from contextlib import contextmanager
import argparse
import base64
import errno
import getpass
import os
import sys
import tempfile
import yaml


def strtype(data):
    """ Enforce a str type that will be printed without b/u prefixes on both py2 and py3. """
    PY3 = sys.version_info[0] == 3
    if PY3:
        return data.decode('utf-8') # pragma: no cover
    return data


class PublicPillar(object):

    def __init__(self, keyfile, hashAlgo=None, passphrase=None):
        with open(keyfile) as key_fh:
            self.key = RSA.importKey(key_fh.read(), passphrase)
        if not hashAlgo:
            hashAlgo = SHA512
        self.hashAlgo = hashAlgo
        self.prng = Random.new()


    def encrypt(self, plaintext):
        """ Encrypts `plaintext` with the key, and returns the result base64-encoded.

        If possible, encrypt directly with the public key, if long enough. Else, use symmetric
        encryption, and encrypt the symmetric key.
        """
        if self._needs_symmetric(plaintext):
            return self._encrypt_long_string(plaintext.encode('utf-8'))
        else:
            return self._encrypt_short_string(plaintext.encode('utf-8'))


    def _needs_symmetric(self, plaintext):
        """ Determines whether the key is big enough for the plaintext, or whether we need to go
        symmetric. Stolen from pycrypto source.
        """

        modBits = number.size(self.key.n)
        k = number.ceil_div(modBits, 8) # Convert from bits to bytes
        hLen = self.hashAlgo.digest_size
        mLen = len(plaintext)

        ps_len = k-mLen-2*hLen-2
        return ps_len < 0


    def _encrypt_short_string(self, plaintext):
        """ Encrypt with a OAEP, using the key directly. """
        cipher = PKCS1_OAEP.new(self.key, hashAlgo=self.hashAlgo)
        encrypted = cipher.encrypt(plaintext)
        return base64.b64encode(encrypted)


    def _encrypt_long_string(self, plaintext):
        """ Generate random key and use that for AES. """
        # Not long enough key for message. Use symmetric encryption instead, and use RSA on
        # the symmetric key
        symmetric_key = self.prng.read(32)
        # Check if we can encrypt the symmetric key with OAEP
        if self._needs_symmetric(symmetric_key):
            raise ValueError("Key is too small to encrypt a AES256 key! Can't encrypt messages " +
                "this long securely.")
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(symmetric_key, AES.MODE_CFB, iv)
        encrypted = iv + cipher.encrypt(plaintext)
        return {
            'key': strtype(self._encrypt_short_string(symmetric_key)),
            'ciphertext': strtype(base64.b64encode(encrypted)),
        }


    def decrypt(self, b64_ciphertext):
        """ Decrypts base64-encoded data with the key. """
        if isinstance(b64_ciphertext, dict):
            return self._decrypt_long_text(b64_ciphertext).decode('utf-8')
        return self._decrypt_short_text(b64_ciphertext).decode('utf-8')


    def _decrypt_short_text(self, b64_ciphertext):
        cipher = PKCS1_OAEP.new(self.key, hashAlgo=self.hashAlgo)
        ciphertext = base64.b64decode(b64_ciphertext)
        return cipher.decrypt(ciphertext)


    def _decrypt_long_text(self, d):
        # Message was too long for plain RSA. Use the symmetric key instead
        symmetric_key = self._decrypt_short_text(d['key'])
        encrypted_data = base64.b64decode(d['ciphertext'])
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        cipher = AES.new(symmetric_key, AES.MODE_CFB, iv)
        plaintext = cipher.decrypt(ciphertext)
        return plaintext


    def decrypt_dict(self, enc_dict):
        """ Decrypt a dict of base64 encoded encrypted values. """
        d = {}
        for key, val in enc_dict.items():
            if isinstance(val, dict) and not ('ciphertext' in val and 'key' in val):
                d[key] = self.decrypt_dict(val)
            else:
                d[key] = self.decrypt(val)
        return d


    def decrypt_single_file(self, filename):
        """ Decrypt a single file with ciphertexts. """
        with open(filename) as source_fh:
            source = yaml.load(source_fh)
        plaintexts = self.decrypt_dict(source)
        return yaml.safe_dump(plaintexts, default_flow_style=False)


    def decrypt_directory(self, source_dir, output_dir):
        """ Decrypt a directory of ciphertexts and write to output_dir. """
        source_dir = source_dir.rstrip('/\\')
        for dirname, directories, filenames in os.walk(source_dir):
            for filename in filenames:
                with open(path.join(dirname, filename)) as fh:
                    ciphertexts = yaml.load(fh)
                plaintexts = self.decrypt_dict(ciphertexts)
                prefix = path.commonprefix([source_dir, dirname])
                output_file = path.join(output_dir, path.join(dirname, filename)[len(prefix)+1:])
                target_dir = path.dirname(output_file)
                if not path.exists(target_dir):
                    os.makedirs(target_dir)
                print('Writing file: %s' % output_file)
                with secure_open_file(output_file) as fh:
                    yaml.safe_dump(plaintexts, fh, default_flow_style=False, encoding='utf-8')


@contextmanager
def secure_open_file(filename):
    """ Securely open or create a new file with 0600 permissions.

    Strategy: Create the file directly with O_EXCL if possible, which ensures that the file did
    not already exist and that no one thus already has an open file descriptor which can read from
    it. If this fails, fall back to creating a temporary file in the same directory, and move it to
    the target location using os.rename. This is not distruptive towards other genuine applications
    reading the files being written. On Windows we fall back to deleting the target and re-creating
    it.

    Note: We do not try to ensure permissions on windows due to entirely different security models.
    If this is necessary for you, please submit a pull request. Some inspiration might be found
    here: http://timgolden.me.uk/python/win32_how_do_i/add-security-to-a-file.html.
    """
    mode = 0o600
    old_umask = os.umask(0)
    try:
        fd = os.open(filename, os.O_CREAT | os.O_WRONLY | os.O_EXCL, mode)
        handle = os.fdopen(fd, 'w')
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            if os.name == 'nt':
                # Windows doesn't support renaming to existing file, try to delete the target
                # and try again
                os.remove(filename)
                fd = os.open(filename, os.O_CREAT | os.O_WRONLY | os.O_EXCL, mode)
                handle = os.fdopen(fd, 'w')
            else:
                # The file already exists, create a tempfile and replace the file with new one
                pardir = os.path.dirname(filename)
                handle = tempfile.NamedTemporaryFile(dir=pardir, delete=False)
                os.rename(handle.name, filename)
        else:
            raise
    finally:
        os.umask(old_umask)

    try:
        yield handle
    finally:
        handle.close()


def cli(): # pragma: no cover
    """ Entry point for the CLI. """
    return main(sys.argv[1:])


def main(cli_args):
    args = get_args(cli_args)
    return args.target(args)


def decrypt(args):
    try:
        public_pillar = PublicPillar(args.key, passphrase=args.passphrase)
    except ValueError:
        # Maybe the key is encrypted and no passphrase was given? Prompt for one and try again
        passphrase = getpass.getpass('Enter passphrase for private key:')
        try:
            public_pillar = PublicPillar(args.key, passphrase=passphrase)
        except ValueError:
            # Probably wrong passphrase
            print("Couldn't load key, probably wrong passphrase.")
            return 1
    if path.isfile(args.source):
        # Single file input
        print(public_pillar.decrypt_single_file(args.source))
    else:
        # Assume directory, traverse recursively
        output_dir = args.output or '.'
        public_pillar.decrypt_directory(args.source, output_dir)
    return 0


def encrypt(args):
    public_pillar = PublicPillar(args.key)
    if args.source:
        if args.source[0] == '@':
            # load value from file
            with open(args.source[1:]) as fh:
                value = fh.read()
        else:
            value = args.source
    else:
        value = sys.stdin.read()
    ciphertext = public_pillar.encrypt(value)
    output = ciphertext.decode('ascii') if hasattr(ciphertext, 'decode') else ciphertext
    print(output)
    return 0


def get_args(cli_args):
    parser = argparse.ArgumentParser(prog='ppillar')
    _add_common_args(parser, with_defaults=True)
    subparsers = parser.add_subparsers(dest='action',
        title='Action',
        help='What to do')
    decrypt_parser = subparsers.add_parser('decrypt',
        help='Decrypt values')
    _add_common_args(decrypt_parser)
    decrypt_parser.set_defaults(target=decrypt)
    decrypt_parser.add_argument('-o', '--output',
        metavar='<output>',
        help="Where to place the generated files. If decrypting the default is the current " +
            "directory, if encrypting the default is to print to stdout.",
    )
    decrypt_parser.add_argument('source', help='The path to decrypt')
    encrypt_parser = subparsers.add_parser('encrypt',
        help='Encrypt new value')
    _add_common_args(encrypt_parser)
    encrypt_parser.set_defaults(target=encrypt)
    encrypt_parser.add_argument('source', nargs='?',
        help='New value to encrypt. If you prefix the value with @, contents will ' +
            'read from the filename following the @. (eg. @id_rsa). Default: stdin')
    args = parser.parse_args(cli_args)
    if not args.key:
        print('A key is necessary to do anything! Point the -k/--key parameter ' +
            'to a key to want to use. (pubkey for encrypting, privkey for decrypting)\n')
        parser.print_help()
        sys.exit(1)
    return args


def _add_common_args(parser, with_defaults=False):
    suppress = None if with_defaults else argparse.SUPPRESS
    parser.add_argument('-k', '--key',
        metavar='<key-location>',
        default=(suppress or None),
        help='Location of key to use for the operation. Pubkey for encryption, private key ' +
            'for decryption',
    )
    parser.add_argument('-p', '--passphrase',
        metavar='<passphrase>',
        default=(suppress or None),
        help='The passphrase to use for decrypting an encrypted private key. Will be prompted'
        ' for if necessary and not given',
    )


if __name__ == '__main__': # pragma: no cover
    sys.exit(main(sys.argv[1:]))
