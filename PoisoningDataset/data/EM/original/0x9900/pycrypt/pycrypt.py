#!/usr/bin/env python2.7
#
# Author: Fred C. <github-fred@hidzz.com>
# Module: pycrypt.py
#
"""
pycrypt: Encrypt and decript your files.

"""

from __future__ import print_function

__author__ = "Fred C."
__email__ = "<github-fred@hidzz.com>"
__version__ = '0.1.2'

import argparse
import getpass
import os
import struct
import sys

from hashlib import md5
from functools import partial

import keyring

from Crypto import Random
from Crypto.Cipher import AES


BLOCK_SIZE = 1 << 14
PROGRAM_NAME = os.path.basename(__file__).replace('.py', '')

def program(token):
  """Make and indentifier for the keychain"""
  return PROGRAM_NAME + ':' + token


def parse_arguments():
  """Parse the arguments. Returns an ArgumentParser object."""

  parser = argparse.ArgumentParser(
    prog=os.path.basename(__file__),
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter
  )

  parser.add_argument('-v', '--version', action='version', version=__version__,
                      help='Print the version')
  # sub-commands
  commands = parser.add_subparsers(title='Commands',
                                   description='Valid commands are:')

  encrypt_cmd = commands.add_parser('encrypt')
  encrypt_cmd.set_defaults(func=encrypt_file)
  encrypt_cmd.add_argument('-e', '--encryption-key')
  encrypt_cmd.add_argument('-s', '--save-key', action='store_true', default=False)
  encrypt_cmd.add_argument('source_files', nargs='+', help='File to encrypt.')

  decrypt_cmd = commands.add_parser('decrypt')
  decrypt_cmd.set_defaults(func=decrypt_file)
  decrypt_cmd.add_argument('-e', '--encryption-key')
  decrypt_cmd.add_argument('-s', '--save-key', action='store_true', default=False)
  decrypt_cmd.add_argument('source_files', nargs='+', help='File to decrypt.')

  options = parser.parse_args()
  return options


def get_key(token):
  """Try to find the encryption key for that token in the keyring. If
  the key cannot be found prompt the user.

  """
  key = keyring.get_password(program(token), token)
  if key:
    return key

  # the key hasn't been found in the keyring. Request for a new one.
  while True:
    key = getpass.getpass('Encryption key: ').strip()
    if len(key) >= 8:
      break
    print("A minimum of 8 characters encryption key should be provided")

  return key


def save_key(token, key):
  """Save the key in the keyring"""
  try:
    keyring.set_password(program(token), token, key)
  except keyring.errors.PasswordSetError as err:
    print(err, file=sys.stderr)


def make_token(source):
  """Generate a token use saving the key in the keyring. """
  return os.path.basename(source.replace('.aes', ''))


def encrypt_file(key, filename, target):
  """
  Encrypt a file using Advanced Encryption Standard (AES)
  Note: If you lose the key the file can't be decrypted.

  Args:
    key: encryption key
    filename: filename to encrypt
    target: encrypted filename

  Raise:
    IOError: raised on failed file operations.

  """
  password = md5(key).hexdigest()
  ivc = Random.new().read(AES.block_size)
  encryptor = AES.new(password, AES.MODE_CBC, ivc)
  filesize = os.path.getsize(filename)

  with open(target, 'w') as fd_out:
    with open(filename, 'rb') as fd_in:
      fd_out.write(struct.pack('<Q', filesize))
      fd_out.write(ivc)
      for chunk in iter(partial(fd_in.read, BLOCK_SIZE), b''):
        if len(chunk) % AES.block_size != 0:
          chunk += ' ' * (AES.block_size - len(chunk) % AES.block_size)
        fd_out.write(encryptor.encrypt(chunk))


def decrypt_file(key, filename, target=None):
  """
  Decrypt a file.

  Args:
    key: decryption key
    filename: encrypted file to decrypt
    target: decrypted file if no file name is specifies the file is
             decryted file on stdout

  Raise:
    IOError: raised on failed file operations.

  """
  password = md5(key).hexdigest()
  with open(filename, 'rb') as infile:
    fsize = struct.unpack('<Q', infile.read(struct.calcsize('Q')))[0]
    ivc = infile.read(AES.block_size)
    decryptor = AES.new(password, AES.MODE_CBC, ivc)
    try:
      outfile = open(target, 'wb') if target else sys.stdout
      for chunk in iter(partial(infile.read, BLOCK_SIZE), b''):
        outfile.write(decryptor.decrypt(chunk))
    finally:
      if outfile != sys.stdout:
        outfile.truncate(fsize)
        outfile.close()


def process_file(func, key, source_file):
  """Apply the encrypt or decrpt function on the file"""
  msg = 'Source: "{0}" Destination: "{1}"'
  if func == encrypt_file:
    target = os.path.basename(source_file) + '.aes'
  elif func == decrypt_file:
    target = os.path.basename(source_file)
    target = os.path.splitext(target)[0]

  if not os.path.exists(source_file):
    raise IOError('Source file: "{}" not found.'.format(source_file))

  if os.path.exists(target):
    raise IOError('Target file: "{}" already exists.'.format(target))

  func(key, source_file, target)
  print(msg.format(source_file, target))


def main():
  """Parse arguments, check if everything is fine then Encrypt / Decrypt
  the file"""
  args = parse_arguments()

  for source_file  in args.source_files:
    token = make_token(source_file)
    key = args.encryption_key or get_key(token)
    try:
      process_file(args.func, key, source_file)
    except IOError as error:
      print(error, file=sys.stderr)
      exit(os.EX_OSERR)
    else:
      if args.save_key:
        save_key(token, key)


if __name__ == '__main__':
  try:
    main()
  except KeyboardInterrupt:
    print("Interrupted by user")
    sys.exit(os.EX_USAGE)
  sys.exit(os.EX_OK)
