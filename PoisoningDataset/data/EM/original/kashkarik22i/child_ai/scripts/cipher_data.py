#! /usr/bin/env python2.7
from __future__ import unicode_literals

# generic
import os
import os.path

# logging
import logging
logger = logging.getLogger(__name__)

# comman line tool
import click
click.disable_unicode_literals_warning = True

# encryption
import hashlib
import random, struct
from Crypto.Cipher import AES

DEFAULT_FILE_EXTENSION = '.enc'

class FilePair(object):
  def __init__(self, in_file, out_file):
    self.in_file = in_file
    self.out_file = out_file

  def absolutize(self, basedir):
    return FilePair(os.path.abspath(os.path.join(basedir, self.in_file)),
                    os.path.abspath(os.path.join(basedir, self.out_file)))

  def in_exist(self):
    return os.path.isfile(self.in_file)

  def create_out_dir(self):
    if not os.path.exists(os.path.dirname(self.out_file)):
      os.makedirs(os.path.dirname(self.out_file))
    

#################################################
# code related to encrypting was borrowerd from
# http://eli.thegreenplace.net/2010/06/25/aes-encryption-of-files-in-python-with-pycrypto/
#################################################

def encrypt_file(in_filename, password,
                 out_filename=None, chunksize=64*1024):

    if not out_filename:
        out_filename = in_filename + DEFAULT_FILE_EXTENSION

    iv = b''.join(chr(random.randint(0, 0xFF)) for i in range(16))
    key = hashlib.sha256(password).digest()
    encryptor = AES.new(key, AES.MODE_CBC, iv)
    filesize = os.path.getsize(in_filename)

    with open(in_filename, 'rb') as infile:
        with open(out_filename, 'wb') as outfile:
            outfile.write(struct.pack(b'<Q', filesize))
            outfile.write(iv)

            while True:
                chunk = infile.read(chunksize)
                if len(chunk) == 0:
                    break
                elif len(chunk) % 16 != 0:
                    chunk += b' ' * (16 - len(chunk) % 16)

                outfile.write(encryptor.encrypt(chunk))

def decrypt_file(in_filename, password,
                 out_filename=None, chunksize=24*1024):
    if not out_filename:
        out_filename = os.path.splitext(in_filename)[0]

    with open(in_filename, 'rb') as infile:
        origsize = struct.unpack(b'<Q', infile.read(struct.calcsize(b'Q')))[0]
        iv = infile.read(16)
        key = hashlib.sha256(password).digest()
        decryptor = AES.new(key, AES.MODE_CBC, iv)

        with open(out_filename, 'wb') as outfile:
            while True:
                chunk = infile.read(chunksize)
                if len(chunk) == 0:
                    break
                outfile.write(decryptor.decrypt(chunk))
            outfile.truncate(origsize)

def encrypt_files(file_pairs, password):
  logger.info("Going to ecrypt {} files".format(len(file_pairs)))
  for file_pair in file_pairs:
    if file_pair.in_exist():
      logger.info("Will encrypt file: '{}'".format(file_pair.in_file))
      file_pair.create_out_dir()
      encrypt_file(file_pair.in_file, password, file_pair.out_file)      
    else:
      logger.warning('File {} does not exist'.format(file_pair.in_file))

def decrypt_files(file_pairs, password):
  logger.info("Going to decrypt {} files".format(len(file_pairs)))
  for file_pair in file_pairs:
    if file_pair.in_exist():
      logger.info("Will decrypt file: '{}'".format(file_pair.in_file))
      file_pair.create_out_dir()
      decrypt_file(file_pair.in_file, password, file_pair.out_file)      
    else:
      logger.warning('File {} does not exist'.format(file_pair.in_file))

def file_pairs_from_list(file_list, encode):
  lines = file_list.read().splitlines()
  filtered_lines = [line.strip().split('\t') for line in lines if line.strip() != '']
  if encode:
    file_pairs = [FilePair(l[0], l[1]) for l in filtered_lines if len(l) == 2 and l[0] != '' and l[1] != '']
  else:
    file_pairs = [FilePair(l[1], l[0]) for l in filtered_lines if len(l) == 2 and l[0] != '' and l[1] != '']
  basepath = os.path.dirname(file_list.name)
  abs_pairs = [pair.absolutize(basepath) for pair in file_pairs]
  return abs_pairs

def file_pairs_from_names(file_names, encrypt):
  if encode:
    return [FilePair(name, name + DEFAULT_FILE_EXTENSION) for name in file_names]
  else:
    result = []
    for name in file_names:
      index = name.index(DEFAULT_FILE_EXTENSION)
      if index == -1:
        logger.warning('Not processing file {} because it does not have the right extension "{}"'.format(name, DEFAULT_FILE_EXTENSION))
      else:
        result.append(FilePair(name[:index], name))
    return result

################################
# command line parsing
###############################

def validate_options(files, file_list):
  if file_list and files:
    raise click.BadParameter('Cannot use both file list and files')
  elif not file_list and not files:
    raise click.BadParameter('You must provide either file list or files')

# CLI
@click.group()
@click.help_option('-h')
@click.option('--log', default='info',
              type=click.Choice(['info', 'debug', 'error', 'warninig']),
              help='log level')
def cli(log):
  logging.basicConfig()
  logger.setLevel(log.upper())

#ENCRYPT
@click.command(help='Encrypt any number of files')
@click.help_option('-h')
@click.option('--password', '-p', prompt=True, hide_input=True)
@click.option('--file-list', '-l', type=click.File(mode='r', encoding='utf-8'),
              help='File listing files to be encrypted')
@click.argument('files', nargs=-1, metavar='FILES',
                type=click.Path(exists=True, resolve_path=False))
def encrypt(password, file_list, files):
  validate_options(files, file_list)
  file_pairs = file_pairs_from_names(files, True) if files else file_pairs_from_list(file_list, True)
  encrypt_files(file_pairs, password)
 
#DECRYPT
@click.command(help='Decrypt any number of files')
@click.help_option('-h')
@click.option('--password', '-p', prompt=True, hide_input=True)
@click.option('--file-list', '-l', type=click.File(mode='r', encoding='utf-8'),
              help='File listing files to be decrypted (without .enc extension)')
@click.argument('files', nargs=-1, metavar='FILES',
                type=click.Path(exists=True, resolve_path=False))
def decrypt(password, file_list, files):
  validate_options(files, file_list)
  file_pairs = file_pairs_from_names(files, False) if files else file_pairs_from_list(file_list, False)
  decrypt_files(file_pairs, password)

# putting arguments together    
cli.add_command(encrypt)
cli.add_command(decrypt)

if __name__ == "__main__":
  cli()
