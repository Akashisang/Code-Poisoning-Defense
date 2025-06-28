#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.

In jurisdictions that recognize copyright laws, the author or authors
of this software dedicate any and all copyright interest in the
software to the public domain. We make this dedication for the benefit
of the public at large and to the detriment of our heirs and
successors. We intend this dedication to be an overt act of
relinquishment in perpetuity of all present and future rights to this
software under copyright law.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

For more information, please refer to <http://unlicense.org/>
'''

import argparse
from getpass import getpass
import re
import sys
import json
import bcrypt
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto import Random


class PasswordError(ValueError):

  def __str__(self):
    return 'Incorrect password'


class EncryptedFile:
  # Subsequent integers require twice as much work to calculate a hash
  BCRYPT_WORK_FACTOR = 14
  FILE_ENCODING = 'utf-8'

  def __init__(self, encrypted_file, passwd):
    self.encrypted_file = encrypted_file
    self.passwd = passwd


  def check_password(self):
    '''
    Throws PasswordError if password is incorrect
    '''
    self.read()


  def hash(self, salt=''):
    '''
    Returns a salted hash of the password.
    '''
    if salt == '':
      salt = bcrypt.gensalt(self.BCRYPT_WORK_FACTOR).decode(self.FILE_ENCODING)
    hashed = bcrypt.hashpw(self.passwd.encode(self.FILE_ENCODING), salt.encode(self.FILE_ENCODING))
    return {'full': hashed, 'hashed_passwd': hashed[-32:], 'salt': salt.encode(self.FILE_ENCODING)}


  def read(self):
    '''
    Returns decrypted contents of the file. Throws PasswordError if the
    password is incorrect.
    '''

    # The file format is as follows:
    #
    #   +-----------------------------------------------------------+
    #   |  $<bcrypt alg/format>$<bcrypt cost param>$<bcrypt salt>   |
    #   |    1 or 2 characters  |  2 characters    | 22 characters  |
    #   +---+---------------------------------------------------+---+
    #   | A |                  SHA256 of payload                | A |
    #   | E +---------------------------------------------------+ E |
    #   | S |                                                   | S |
    #   |   |                                                   |   |
    #   | E |                                                   | E |
    #   | N |                                                   | N |
    #   | C |                                                   | C |
    #   | R |                      payload                      | R |
    #   | Y |                                                   | Y |
    #   | P |                                                   | P |
    #   | T |                                                   | T |
    #   | E |                                                   | E |
    #   | D |                                                   | D |
    #   +---+---------------------------------------------------+---+

    # look for salt in existing encrypted file
    try:
      salt = self.salt()
    except FileNotFoundError:
      return ''
    except IOError as e:
      if e[0] == 2: # errno 2 is file not found
        return ''
      raise

    hashed = self.hash(salt)
    with open(self.encrypted_file, 'rb') as f:
      msg = f.read()
    if (len(msg) == 0):
      return ''

    iv = Random.new().read(AES.block_size)
    cipher = AES.new(hashed['hashed_passwd'], AES.MODE_CFB, iv)
    decrypted_msg = cipher.decrypt(msg[len(salt):])[len(iv):]

    # The correctness of the password supplied for decryption can be determined
    # by comparing the included SHA256 with the SHA256 of the decrypted payload.
    # If they match, the password is correct.

    digest_size = SHA256.new().digest_size
    sha = decrypted_msg[0:digest_size]
    if sha != SHA256.new(decrypted_msg[digest_size:]).digest():
        raise PasswordError
    return decrypted_msg[digest_size:]


  def salt(self):
    '''
    This function reads and returns the first 28 or 29 bytes from the beginning
    of the encrypted file. These bytes contain the hashing algorithm and format
    (2, 2a, or 2y), the 2 digit cost, and the salt. These bytes are identical
    in format to those returned from bcrypt.gensalt().

     The modular crypt format for bcrypt consists of
      -  $2$, $2a$, $2b$, or $2y$ identifying the hashing algorithm and format,
      -  a two digit value denoting the cost parameter, followed by $
      -  a 53 characters long base-64-encoded value (they use the
         alphabet ., /, 0-9, A-Z, a-z that is different to the standard
         Base 64 Encoding alphabet) consisting of:
           -  22 characters of salt (effectively only 128 bits of the 132
              decoded bits)
           -  31 characters of encrypted output (effectively only 184 bits of
              the 186 decoded bits)

    Thus the total length is 59 or 60 bytes respectively.
   '''
    try:
      with open(self.encrypted_file, 'rb') as f:
        msg = f.read(29)
      if (len(msg) == 0):
        return ''
      m = re.search(r'(\$2[ayb]{0,1}\$[0-9]{2}\$[\./0-9A-Za-z]{22})', str(msg, encoding=self.FILE_ENCODING))
      return m.group(1)
    except IOError as e:
      raise


  def set_password(self, old_password, new_password):
    '''
    Changes the password. Throws PasswordError if old_password is incorrect.
    '''
    try:
      orig_passwd = self.passwd
      self.passwd = old_password
      db = self.read() # throws PasswordError if incorrect pw
      self.passwd = new_password
      self.write(db)
    except PasswordError as e:
      self.passwd = orig_passwd
      raise


  def write(self, msg):
    '''
    Encrypts msg and writes it to self.encrypted_file.
    '''
    with open(self.encrypted_file, 'wb') as f:
      hashed = self.hash()
      iv = Random.new().read(AES.block_size)
      cipher = AES.new(hashed['hashed_passwd'], AES.MODE_CFB, iv)
      encrypted_msg = iv + cipher.encrypt(SHA256.new(msg.encode(self.FILE_ENCODING)).digest() + msg.encode(self.FILE_ENCODING))

      f.write(hashed['salt'])
      f.write(encrypted_msg)


class PWFile(EncryptedFile):
  '''
  Manages a file of encrypted username/password info.
  The file begins with a salt of the format generated by bcrypt.gensalt()
  followed by the AES encrypted data.
  '''

  def read(self):
    '''
    Returns all site, user, and password info from the file as an object with
    the following format.

      {
        "site1": {
          "user1": {
            "pw": "password",
            "note": "note"
          },
          "user2": {
            "pw": "password",
            "note": "note"
          }
        },
        "site2": {
          "user1": {
            "pw": "password",
            "note": "note"
          },
          "user2": {
            "pw": "password",
            "note": "note"
          }
        },
        ...
      }

    Throws PasswordError if the file cannot be decrypted.
    '''
    decrypted_msg = EncryptedFile.read(self)
    if (len(decrypted_msg) == 0):
      return {}
    try:
      return json.loads(decrypted_msg)
    except ValueError:
      raise PasswordError


  def write(self, msg):
    '''
    Serializes site, user, and password info, then encrypts and writes it to
    self.encrypted_file.

    Throws UnicodeDecodeError if data cannot be serialized.
    '''
    try:
      json_msg = json.dumps(msg)
      EncryptedFile.write(self, json_msg)
    except UnicodeDecodeError:
      print('Error: cannot json encode data')
      raise


class UI:
  def __init__(self, pwfile):
    self.pwfile = pwfile


  def delete_user(self):
    db = self.pwfile.read()

    print('Site: ', end='', flush=True)
    site = sys.stdin.readline().strip().lower()
    print('Username: ', end='', flush=True)
    user = sys.stdin.readline().strip()
    print('Delete user ' + user + ' from site ' + site + '? y/n ', end='', flush=True)
    delete = sys.stdin.readline().strip()

    if delete == 'y':
      del db[site][user]
      if len(db[site]) == 0:
        del db[site]
      self.pwfile.write(db)


  def getPW(self):
    print('Site: ', end='', flush=True)
    site = sys.stdin.readline().strip().lower()

    db = self.pwfile.read()
    if db == {}:
      print('No passwords found')
      return {}

    if site not in db:
      print('No entries found for ' + site)
      return {}

    return db[site]


  def help(self):
    print('')
    print('Commands:')
    print('d: delete user')
    print('g: get passwords for a site')
    print('s: set password for a site/user')
    print('m: set mastr passerd')
    print('la: list all')
    print('ls: list sites')
    print('h: help')
    print('q: quit')
    return ''


  def print_pass_info(self):
    info = self.pwfile.read()
    for site in sorted(info.keys()):
      print('==================')
      print(site + '\n')
      for user in sorted(info[site].keys()):
        print('  User: ' + user)
        self.print_user_info(info[site][user], '  ')
        print('')


  def print_sites(self):
    print('==================')
    for site in sorted(self.pwfile.read().keys()):
      print(site)


  def print_site_info(self):
    print('==================')
    site = ui.getPW().items()
    print('')
    for user, info in site:
      print('User: ' + user)
      self.print_user_info(info, '')
      print('')


  def print_user_info(self, user, prefix):
    if user:
      print(prefix + 'Pass: ' + user['pw'])
      print(prefix + 'Note: ' + user['note'])


  def process_command(self, cmd):
    commands = {'d': lambda: self.delete_user(),
                'g': lambda: self.print_site_info(),
                's': lambda: self.setPW(),
                'm': lambda: self.setMastr(),
                'la': lambda: self.print_pass_info(),
                'ls': lambda: self.print_sites(),
                'h': lambda: self.help(),
                'q': lambda: sys.exit(0)}
    try:
      commands[cmd]()
      print('Done')
    except KeyError:
      print(cmd + ' is not a valid command')
      self.help()
    except PasswordError as e:
      print(e)


  def setMastr(self):
    old_pw = getpass('Old Mastr Passerd: ')
    self.pwfile.set_password(old_pw, old_pw) # Throws PasswordError if wrong old_pw
    while True:
      new_pw = getpass('New Mastr Passerd: ')
      new_pw2 = getpass('Re-enter New Mastr Passerd: ')
      if new_pw == new_pw2:
        break
      print('Passwords don\'t match')
    self.pwfile.set_password(old_pw, new_pw)


  def setPW(self):
    print('Site: ', end='', flush=True)
    site = sys.stdin.readline().strip().lower()
    print('Username: ', end='', flush=True)
    user = sys.stdin.readline().strip()

    while True:
      pw = getpass('Password: ')
      pw2 = getpass('Re-enter Password: ')
      if pw == pw2:
        break
      print('Passwords don\'t match')
    print('Note: ', end='', flush=True)
    note = sys.stdin.readline().strip()

    # {site: {user: {'pw': pw, 'note': note}, user2: {'pw': pw2, 'note': note2}}}
    db = self.pwfile.read()

    if site not in db: 
      db[site] = {user: {'pw': pw, 'note': note}}
    elif user not in db[site]:
      db[site][user] = {'pw': pw, 'note': note}
    else:
      print(user + ' already exists. Update? y/n ', end='', flush=True)
      overwrite = sys.stdin.readline().strip()
      if overwrite == 'y':
        db[site][user] = {'pw': pw, 'note': note}

    self.pwfile.write(db)


if __name__ == "__main__":
  while True:
    try:
      parser = argparse.ArgumentParser(description='A simple interactive password manager',
                                       prefix_chars='-/')
      parser.add_argument('-f', nargs=1, default=['pw.pow'], metavar='filename',
                          help='specify file to use as password database (defaults to \'pw.pow\')')
      args = parser.parse_args()
      pwdb = args.f[0]

      master = getpass('Mastr Passerd? ')
      pwfile = PWFile(pwdb, master)
      pwfile.check_password() # Throws PasswordError if wrong password
      ui = UI(pwfile)
      ui.help()
      break
    except PasswordError as e:
      print(e)

  while True:
    ui.process_command(sys.stdin.readline().strip())

