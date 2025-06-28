#!/usr/bin/env python
# vim: sw=4:ts=4:sts=4:fdm=indent:fdl=0:
# -*- coding: UTF8 -*-
#
# Account manager
# Copyright (C) 2016 Josiah Gordon <josiahg@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


""" Account manager.  Stores account information in a LZMA compressed file.
The account info is put in JSON format and each account name is hashed, and the
data is encrypted using AES-256-CBC encryption.

"""


from pathlib import Path as pathlib_path
from lzma import compress as lzma_compress
from lzma import decompress as lzma_decompress
from json import loads as json_loads
from json import dumps as json_dumps
import codecs
import getpass
from os import environ as os_environ

from Crypto.Cipher import AES
from Crypto.Hash import SHA512, SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto import Random
from Crypto.Hash import HMAC


# Disable writing lesshst file so when searching in the less pager the
# search terms won't be recorded.
os_environ['LESSHISTFILE'] = '/dev/null'

# Use less as the pager.
os_environ['PAGER'] = '$(which less)'

# Set the salt, iv, and key length
KEY_LEN = SALT_LEN = AES.key_size[-1]
IV_LEN = AES.block_size


# Old not good functions.

def encrypt_sha256(key: bytes, plaintext: str) -> bytes:
    """ encrypt(key, plaintext) ->  Encrypts plaintext using key.

    """

    valid_key = SHA256.new(key.encode()).digest()
    iv = Random.new().read(IV_LEN)

    padded_plaintext = PKCS7_pad(plaintext.encode(), AES.block_size)

    encrypt_obj = AES.new(valid_key, AES.MODE_CBC, iv)

    # Put the iv at the start of the cipher text so when it needs to be
    # decrypted the same iv can be used.
    ciphertext = iv + encrypt_obj.encrypt(padded_plaintext)

    return ciphertext


def decrypt_sha256(key: bytes, ciphertext: bytes) -> str:
    """ decrypt(key, ciphertext) -> Decrypts the cipher text using the key.

    """

    valid_key = SHA256.new(key.encode()).digest()

    # iv is the first block_size of data at the start of the cipher text.
    iv = ciphertext[:IV_LEN]
    real_ciphertext = ciphertext[IV_LEN:]

    decrypt_obj = AES.new(valid_key, AES.MODE_CBC, iv)
    padded_plaintext = decrypt_obj.decrypt(real_ciphertext)

    try:
        # Remove the padding from the plain text.
        plaintext = padded_plaintext[:-padded_plaintext[-1]].decode()
    except UnicodeDecodeError:
        print("There was an error.  Maybe the wrong password was given.")
        return ''

    return plaintext


def bytes_to_str_sha256(bytes_obj: bytes) -> str:
    """ Encodes the bytes object using base64, and returns that string value.

    """

    return codecs.encode(bytes_obj, 'base64').decode()


def str_to_bytes_sha256(str_obj: str) -> bytes:
    """ Decodes a base64 string into a bytes object.

    """

    return codecs.decode(str_obj.encode(), 'base64')


def crypt_to_dict_sha256(crypt_data: str, password: str = '',
                  skip_invalid: bool = True) -> dict:
    """ Decrypts crypt_data and returns the json.loads dictionary.
    If skip_invalid is True then skip decryption of data if the password is
    invalid.

    """

    while True:
        # Get the password to decrypt the data.
        if not password:
            password = getpass.getpass('Enter the password for decryption: ')

        # Convert the data to a bytes object and decrypt it.
        json_data = decrypt_sha256(password, str_to_bytes_sha256(crypt_data))

        # Load the decrypted data with json and return the resulting
        # dictionary.
        try:
            return json_loads(json_data)
        except:
            # Don't loop forever unless asked to.
            if skip_invalid:
                print('Skipping, because of invalid password.')
                return {}
            else:
                print('Invalid password.  Please try again.')
                password = ''
                continue


def dict_to_crypt_sha256(data_dict: dict, password: str = '') -> str:
    """ Returns the encrypted json dump of data_dict.

    """


    # Dump the data_dict into json data.
    json_data = json_dumps(data_dict)

    if not password:
        # Get the password to encrypt the data.
        password = get_pass('password for encryption')

    # Return the string encoded encrypted json dump.
    return bytes_to_str_sha256(encrypt_sha256(password, json_data))

#########################


def PKCS7_pad(data: bytes, multiple: int) -> bytes:
    """ Pad the data using the PKCS#7 method.

    """

    # Pads byte pad_len to the end of the plain text to make it a
    # multiple of the multiple.
    pad_len = multiple - (len(data) % multiple)

    return data + bytes([pad_len]) * pad_len


def get_pass(question_str: str, verify: bool = True) -> str:
    """ Get a secret optionally ask twice to make sure it was inputted
    correctly.

    """

    try:

        if not verify: return getpass.getpass(f'Enter the {question_str}: ')

        a1 = 'a'
        a2 = 'b'

        # Loop until both entries match.
        while a1 != a2:
            a1 = getpass.getpass(f'Enter the {question_str}: ')
            a2 = getpass.getpass(f'Verify the {question_str}: ')
            if a1 != a2:
                print(f'The {question_str} did not match.  Please try again.')

        return a1
    except KeyboardInterrupt:
        print()
        raise(SystemExit)


class CryptData(object):
    """ Easily encrypt/decrypt data.  The data is authenticated when it is
    decrypted.

    """

    def __init__(self, password: str, encrypted_key: bytes = b''):
        """ Initialize the data.

        """

        if not encrypted_key:
            # Generate the largest key possible.
            self._key = self.create_key(KEY_LEN)
        else:
            self._key = self._decrypt_key(encrypted_key, password)

        self._password = password

    def create_key(self, length: int) -> bytes:
        """ Generates a cryptographic random key of length 'length'.

        """

        return Random.new().read(length)

    @property
    def encrypted_key(self) -> bytes:
        """ Returns the encrypted key.

        """

        return self._encrypt_key(self._key, self._password)

    @property
    def password(self) -> str:
        """ Returns the password.

        """

        return self._password

    @password.setter
    def password(self, new_password: str):
        """ Changes the password used to encrypt the key.

        """

        self._password = new_password

    def _encrypt(self, data: bytes, key: bytes) -> bytes:
        """ Returns the AES_CBC encryption of data using key.
        The return value is the concatenation of iv + cipher text.

        """

        iv = Random.new().read(IV_LEN)
        encrypt_obj = AES.new(key, AES.MODE_CBC, iv)

        # Put the iv at the start of the cipher text so when it
        # needs to be decrypted the same iv can be used.
        return iv + encrypt_obj.encrypt(data)

    def _decrypt(self, data: bytes, key: bytes) -> bytes:
        """ Decrypts data using key.  The data should be the concatenation of
        iv + cipher text.

        """

        iv = data[:IV_LEN]
        decrypt_obj = AES.new(key, AES.MODE_CBC, iv)

        # Decrypt the data.
        return decrypt_obj.decrypt(data[IV_LEN:])

    def _verify_key(self, encrypted_key: bytes, password: bytes) -> bytes:
        """ Verifies that password can decrypt encrypted_key, and returns the
        key generated from password that will decrypt encrypted_key.

        """

        # Get the salt and iv from the start of the encrypted data.
        salt = encrypted_key[:SALT_LEN]

        # Generate a key and verification key from the password and
        # salt.
        crypt_key, auth_key = self._gen_keys(password, salt,
                                             dkLen = KEY_LEN * 2)

        if auth_key != encrypted_key[-KEY_LEN:]:
            raise(Exception("Invalid password or file was tampered with."))

        return crypt_key

    def _decrypt_key(self, encrypted_key: bytes, password: str) -> bytes:
        """ Decrypt a key encrypted with encrypt_key.

        """

        # Verify that the password is correct and/or the file has not
        # been tampered with.
        crypt_key = self._verify_key(encrypted_key, password)

        # Decrypt the key.
        key = self._decrypt(encrypted_key[SALT_LEN:-KEY_LEN], crypt_key)

        return key

    def _encrypt_key(self, key: bytes, password: str) -> bytes:
        """ Converts password into a valid key and uses that to encrypt a key.
        Returns salt + encrypted_key + auth_key where salt is used to produce
        key material from the password.  That key material is split, and the
        first half is used to encrypt the key and the second is the auth_key to
        verify the password when decrypting.

        """

        # Generate a large salt.
        salt = Random.new().read(SALT_LEN)

        # Generate a key and verification key from the password and salt.
        crypt_key, auth_key = self._gen_keys(password, salt,
                                             dkLen = KEY_LEN * 2)

        return salt + self._encrypt(key, crypt_key) + auth_key

    def _gen_keys(self, password: str, salt: bytes, dkLen: int = KEY_LEN,
                  iterations: int = 5000) -> tuple:
        """ Uses a password and PBKDF2 to generate 512-bits of key material.
        Then it splits it, and returns a tuple of the first 256-bit for a key,
        and the second 256-bit block for a verification code.

        """

        # Use SHA512 as the hash method in hmac.
        prf = lambda p, s: HMAC.new(p, s, SHA512).digest()
        key_mat = PBKDF2(password.encode(), salt, dkLen=dkLen,
                         count=iterations, prf=prf)
        # The encryption key is the first 256-bits of material.
        crypt_key = key_mat[:KEY_LEN]
        # The second 256-bits is used to verify the key and password.
        auth_key = key_mat[KEY_LEN:]

        return crypt_key, auth_key

    def _verify(self, ciphertext: bytes) -> bytes:
        """ Raises an error if the cipher text isn't valid.

        """

        # Extract the hmac digest and encrypted hmac key from the
        # cipher text
        hmac_digest = ciphertext[-SHA512.digest_size:]
        ciphertext = ciphertext[:-SHA512.digest_size]
        encrypted_hmac_key = ciphertext[-(IV_LEN + KEY_LEN):]
        ciphertext = ciphertext[:-(IV_LEN + KEY_LEN)]

        # Decrypt hmac key.
        hmac_key = self._decrypt(encrypted_hmac_key, self._key)

        # Test the generated digest against the stored digest and fail if they
        # are different.
        assert(hmac_digest == self._get_hmac_digest(ciphertext, hmac_key))

        # Only return the cipher text to be decrypted if the digests match.
        return ciphertext

    def _get_hmac_digest(self, data: bytes, key: bytes) -> bytes:
        """ Returns the hmac digest of data using key.

        """

        # Re-generate the hmac digest of cipher text.
        hmac = HMAC.new(key, digestmod=SHA512)
        hmac.update(data)

        return hmac.digest()

    def encrypt(self, plaintext: str) -> bytes:
        """ encrypt(key, plaintext) ->  Encrypts the plain text using key.

        """

        # Pad the plain text.
        padded_plaintext = PKCS7_pad(plaintext.encode(), AES.block_size)

        # Encrypt it.
        ciphertext = self._encrypt(padded_plaintext, self._key)

        # Generate an hmac of the cipher text, and put the encrypted key and
        # digest at the end of the cipher text.

        # Generate the largest key we can use.
        hmac_key = Random.new().read(KEY_LEN)

        hmac_digest = self._get_hmac_digest(ciphertext, hmac_key)

        return ciphertext + self._encrypt(hmac_key, self._key) + hmac_digest

    def decrypt(self, ciphertext: bytes) -> str:
        """ decrypt(key, ciphertext) -> Decrypts the cipher text using the key.

        """

        try:
            ciphertext = self._verify(ciphertext)
        except AssertionError:
            print("Invalid data.  Can't decrypt.")
            return ''

        padded_plaintext = self._decrypt(ciphertext, self._key)

        # Remove the padding from the plain text, and return the result.
        return padded_plaintext[:-padded_plaintext[-1]].decode()


class PassFile(object):
    """ An encrypted password file.

    The format is a dictionary where the master key is stored under the key
    '\x00master_key\x00' and each account name is hashed and used as the key to
    that accounts encrypted data.  The account data is encrypted with the
    master key and the hmac of that and the iv is stored at the end of each
    account info. So it is like this.
    {
        hashed(\x00master_key\x00): salt+iv+encrypted_master_key,
        hashed(account_name): iv+encrypted_account_dict+encrypted_hmac_key+hmac_digest,
        ...
    }

    """

    MASTER_KEY_DIGEST = SHA512.new(b'\x00master_key\x00').hexdigest()


    def __init__(self, filename: str, password: str = '',
                 pass_func: object = get_pass):
        """ Open the filename and read out the data.  Decrypt it and allow
        access.

        """

        self._filename = filename
        self._ask_pass = pass_func

        cryptdata, accounts_dict = self._read_file(filename, password)
        self._cryptdata, self._accounts_dict = cryptdata, accounts_dict

    def _read_file(self, filename: str, password: str = '') -> dict:
        """ Reads the data from filename and returns the account dictionary,
        the encrypted master key, and the decrypted master key.

        """

        # Read from the file if it exists.
        with pathlib_path(filename) as pass_file:
            lzma_data = pass_file.read_bytes() if pass_file.is_file() else b''

        # Get the json data out of the file data or an empty json dict of
        # the file was empty.
        if lzma_data:
            json_data = lzma_decompress(lzma_data).decode()
        else:
            json_data = '{}'

        accounts_dict = json_loads(json_data)

        # Pop the master key out of the accounts dictionary so it won't be
        # operated on or listed.  Also if no master key is found, create
        # one.
        encrypted_key = bytes.fromhex(accounts_dict.pop(self.MASTER_KEY_DIGEST,
                                                        ''))

        if not encrypted_key:
            if not password:
                # Get the password to encrypt the master key.
                password = self._ask_pass(f'password for {filename}')
        else:
            # Get the password to decrypt the key.
            password = self._ask_pass(f'password for {filename}', verify=False)

        return CryptData(password, encrypted_key), accounts_dict

    def _write_file(self, filename: str, accounts_dict: dict, 
                    encrypted_key: bytes):
        """ Compresses and writes the accounts_dict to the file at filename.

        """

        # Put the master key into the accounts dict.
        accounts_dict[self.MASTER_KEY_DIGEST] = encrypted_key.hex()

        json_data = json_dumps(accounts_dict)

        lzma_data = lzma_compress(json_data.encode())

        with pathlib_path(filename) as pass_file:
            pass_file.write_bytes(lzma_data)

    def _hash_name(self, name: str) -> bytes:
        """ Hashes name and returns the result.

        """

        return SHA512.new(name.encode()).hexdigest()

    def _crypt_to_dict(self, crypt_data: str) -> dict:
        """ Decrypts crypt_data and returns the json.loads dictionary.
        If skip_invalid is True then skip decryption of data if the password is
        invalid.

        """

        # Return an empty dictionary if crypt_data is empty.
        if not crypt_data: return {}

        # Convert the data to a bytes object and decrypt it.
        json_data = self._cryptdata.decrypt(bytes.fromhex(crypt_data))

        # Load the decrypted data with json and return the resulting
        # dictionary.
        return json_loads(json_data)


    def _dict_to_crypt(self, data_dict: dict) -> str:
        """ Returns the encrypted json dump of data_dict.

        """

        # Dump the data_dict into json data.  
        json_data = '{}' if not data_dict else json_dumps(data_dict)

        ciphertext = self._cryptdata.encrypt(json_data)

        # Return the hexadecimal representation of the cipher text.
        return ciphertext.hex()

    def get(self, account: str, default: dict = {}) -> dict:
        """ Return the value from accounts_dict associated with key.

        """

        account_hash = self._hash_name(account)

        if account_hash not in self._accounts_dict:
            return default

        return self._crypt_to_dict(self._accounts_dict[account_hash])

    def set(self, account: str, value: dict):
        """ Set the value associated with key.

        """

        account_hash = self._hash_name(account)
        self._accounts_dict[account_hash] = self._dict_to_crypt(value)

    def accounts(self) -> iter:
        """ Iterate through all the items in _accounts_dict, and yield
        the account dictionaries.

        """

        for i in self._accounts_dict.values():
            yield self._crypt_to_dict(i)

    def account_names(self) -> iter:
        """ Iterate through all the items in _accounts_dict, and yield
        the account names.

        """

        for i in self._accounts_dict.values():
            yield self._crypt_to_dict(i)['Account Name']

    def change_pass(self, new_password: str):
        """ Change the password used to encrypt the master_key.

        """

        self._cryptdata.password = new_password

    def remove(self, item: str):
        """ Remove the entry at item.

        """

        self._accounts_dict.pop(self._hash_name(item))

    def convert(self):
        """ Convert to latest format.

        """

        tmp_accounts_dict = {}
        for account_hash, account_data in self._accounts_dict.items():
            account_dict = crypt_to_dict_sha256(account_data,
                                                password=self._cryptdata.password,
                                                skip_invalid=True)
            if account_dict:
                new_account_data = self._dict_to_crypt(account_dict)
            else:
                raise(Exception("Invalid password.  Can't convert."))
            account_name = account_dict.get('Account Name', '')
            new_account_hash = self._hash_name(account_name)
            tmp_accounts_dict[new_account_hash] = new_account_data
        self._accounts_dict = tmp_accounts_dict

    def __contains__(self, item: str) -> bool:
        """ Checks if accounts_dict has a key of value item.

        """

        return self._hash_name(item) in self._accounts_dict

    def __enter__(self):
        """ Provides the ability to use pythons with statement.

        """

        try:
            return self
        except Exception as err:
            print(err)
            return None

    def __exit__(self, exc_type, exc_value, traceback):
        """ Close the file when finished.

        """

        try:
            self._write_file(self._filename, self._accounts_dict,
                             self._cryptdata.encrypted_key)
            return not bool(exc_type)
        except Exception as err:
            print(err)
            return False


def dict_to_str(data_dict: dict) -> str:
    """ Returns a formatted string of the (key, value) items in the supplied
    dictionary.

    """

    str_list = ['\n']

    max_key_len = max(len(key) for key in data_dict.keys())

    for key, value in data_dict.items():
        if key == 'Account Name':
            str_list.insert(1, "{1:<{0}} -> {2}".format(max_key_len,
                                                        key, value))
            continue

        # Format the info in a list as follows:
        # key (right align by space max_key_len): value
        str_list.append("{1:<{0}} -> {2}".format(max_key_len,
                                            key.lower().capitalize(),
                                            value))

    return '\n'.join(str_list)


def convert(args: object) -> int:
    """ Convert from SHA256 hashed key to using a master key and encrypting the
    master key with a password based key.

    """

    filename = args.filename
    password = get_pass('password', verify=False)

    print("Converting...", end='')
    with PassFile(filename, password) as passfile:
        passfile.convert()
    print("Done.")

    return 0


def search(args: object) -> int:
    """ Search for search_term in filename.

    """

    filename = args.filename
    search_term = args.search_term
    search_key = 'Account Name' if args.accounts else args.search_key

    search_str = search_term.lower()

    # String in which to store all matching account information.
    account_str = ''

    with PassFile(filename) as passfile:
        for account_dict in passfile.accounts():
            # The string representation of a dict is good enough for
            # searching in.
            if search_str in str(account_dict.get(search_key,
                                                  '' if search_key else account_dict)):
                account_str += '\n' + dict_to_str(account_dict)

    import pydoc
    pydoc.pager(account_str)

    return 0


def change_password(args: object) -> int:
    """ Change the password that encrypts the master key.

    """

    filename = args.filename

    with PassFile(filename) as passfile:
        # Change the password.
        new_password = get_pass('new password')

        passfile.change_pass(new_password)
    return 0


def remove_account(args: object) -> int:
    """ Remove account from filename.

    """

    filename = args.filename
    account = args.account

    with PassFile(filename) as passfile:
        passfile.remove(account)

    return 0


def add_account(args: object) -> int:
    """ Add an account the file.

    """

    filename = args.filename
    account = args.account

    # Change the password.
    if account == 'PASSWORD':
        return change_password(args)

    # Account names cannot be 'ALL.'
    if account == 'ALL':
        print("Invalid account name: 'ALL'")
        return 0

    with PassFile(filename) as passfile:
        if account in passfile and hasattr(args, 'to'):
            # Trying to add a duplicate account.
            print("Account '%s' exists" % account)
            print("Use 'modify' or 'rename' to change it.")
            return 0
        elif account not in passfile and hasattr(args, 'in'):
            # Trying to modify a non-existent account.
            print("Account '%s' does not exist" % account)
            print("Use 'add' to add it.")
            return 0

        # Put the non-hashed account name in the info dict so it is
        # not lost.
        info_dict = {'Account Name': account}

        account_dict = passfile.get(account)

        if args.set:
            # Add any data to the info dictionary.
            for i in args.data:
                key, value = i.split(args.separator)

                # Don't allow the user to set the account name this way.
                if key.lower() == 'account name': continue

                # Remove empty values from the account dict and continue.
                if not value:
                    account_dict.pop(key, '')
                    continue

                # Get the secret value.
                if value == '{secret}':
                    value = get_pass('{0} {1}'.format(account, key))

                info_dict[key] = value

        account_dict.update(info_dict)
        passfile.set(account, account_dict)

    return 0

# Use the add function to change.
modify_account = add_account


def rehash(args: object) -> int:
    """ Re-hash all the account info.

    """

    filename = args.filename

    with PassFile(filename) as passfile:
        accounts_list = list(passfile.accounts())

        # List all accounts.
        for account_dict in accounts_list:
            account = account_dict['Account Name']
            if account in passfile:
                print("Rehashing: ", account)
                passfile.remove(account)
                passfile.set(account_dict['Account Name'], account_dict)

    return 0


def list_info(args: object) -> int:
    """ List the info in the account or file.

    """

    filename = args.filename
    account = args.account

    account_str = ''

    with PassFile(filename) as passfile:

        if account == 'ALL':
            # List all accounts.
            for account_dict in passfile.accounts():
                account_str += '\n' + dict_to_str(account_dict)
        else:
            if account not in passfile:
                print("Account %s not found." % account)
                return 0

            account_str = dict_to_str(passfile.get(account))

    import pydoc
    pydoc.pager(account_str)

    return 0


def rename_account(args: object) -> int:
    """ Rename an account.

    """

    filename = args.filename
    old_account = args.old_account
    new_account = args.new_account

    # Do nothing if the names are the same.
    if old_account == new_account: return 0
    # Account names cannot be 'ALL.'
    if old_account == 'ALL' or new_account == 'ALL':
        print("Invalid account name: 'ALL'")
        return 0

    with PassFile(filename) as passfile:
        if old_account not in passfile:
            print("Account '%s' not found.  Can't rename." % old_account)
            return 0
        if new_account in passfile:
            print("Account '%s' already exists.  Can't rename." % new_account)
            return 0

        account_dict = passfile.get(old_account)
        account_dict['Account Name'] = new_account
        passfile.set(new_account, account_dict)
        passfile.remove(old_account)

    return 0


def diff(args: object) -> int:
    """ List the differences between two files.

    """

    from difflib import unified_diff
    from difflib import ndiff
    import pydoc

    first_filename = args.first_file
    second_filename = args.second_file

    print(f"Diff between {first_filename} and {second_filename}")

    first_account_list = []
    second_account_list = []

    with PassFile(first_filename) as first_passfile:
        # Sort accounts by name.
        sorted_accounts = sorted(first_passfile.account_names())

        for account_name in sorted_accounts:
            account_dict = first_passfile.get(account_name)
            first_account_list.extend(dict_to_str(account_dict).split('\n'))

    with PassFile(second_filename) as second_passfile:
        # Sort accounts by name.
        sorted_accounts = sorted(second_passfile.account_names())

        for account_name in sorted_accounts:
            account_dict = second_passfile.get(account_name)
            second_account_list.extend(dict_to_str(account_dict).split('\n'))

    diff_list = list(unified_diff(first_account_list, second_account_list,
                                  first_filename, second_filename))
    pydoc.pager('\n'.join(diff_list))

    return 0


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Password manager")
    subparsers = parser.add_subparsers(help="Available actions")

    # Add account options
    add_group = subparsers.add_parser('add', help='Add an account.')
    add_group.add_argument('account', action='store',
                            help='The name of the account to add.')
    add_sub = add_group.add_subparsers(help='Specify the file.', dest='to')
    add_sub.required = True
    add_sub_group = add_sub.add_parser('to',
                                       help='The file where the account \
                                             should be added.')
    add_sub_group.add_argument('filename')
    file_sub = add_sub_group.add_subparsers(help='Set info=data (e.g. set \
                                            username=bif', dest='set')
    file_sub_group = file_sub.add_parser('set', help='Set item info.')
    file_sub_group.add_argument('-s', '--separator', action='store', 
                                default='=',
                                help='Set the info separator (default is "=")')
    file_sub_group.add_argument('data', nargs="+",
                                help='Use {secret} to input secrets e.g. \
                                      (Question={secret})')
    add_group.set_defaults(func=add_account)

    # Change options.
    modify_group = subparsers.add_parser('modify',
                                         help='Change the file password, or \
                                               the info in an account.')
    modify_group.add_argument('account', action='store',
                              help='The name of the account to modify, \
                                    or "PASSWORD" to change the password.')
    modify_sub = modify_group.add_subparsers(help='File to modify.',
                                             dest='in')
    modify_sub.required = True
    modify_sub_group = modify_sub.add_parser('in', help='Specify what file to \
                                                         modify.')
    modify_sub_group.add_argument('filename')
    file_sub = modify_sub_group.add_subparsers(help='Set item info.',
                                               dest='set')
    file_sub_group = file_sub.add_parser('set', help='Set info=data (e.g. set \
                                                     username=bif')
    file_sub_group.add_argument('-s', '--separator', action='store', 
                                default='=',
                                help='Set the info separator (default is "=")')
    file_sub_group.add_argument('data', nargs="+",
                                help='Use {secret} to input secrets e.g. \
                                      (Question={secret})')
    modify_group.set_defaults(func=modify_account)

    # Rename options
    rename_group = subparsers.add_parser('rename',
                                         help='Rename an account.')
    rename_group.add_argument('old_account', action='store',
                              help='The name of the account to rename.')
    rename_sub = rename_group.add_subparsers(help='The file with the account \
                                                   to rename.', dest='in')
    rename_sub.required = True
    rename_sub_group = rename_sub.add_parser('in', help='Specify the file.')
    rename_sub_group.add_argument('filename')
    file_sub = rename_sub_group.add_subparsers(help='The new account name.',
                                               dest='to')
    file_sub_group = file_sub.add_parser('to', help='New account name.')
    file_sub_group.add_argument('new_account',
                                help='The new name for the account.')
    rename_group.set_defaults(func=rename_account)

    # Remove options
    remove_group = subparsers.add_parser('remove', help='Remove an account.')
    remove_group.add_argument('account', action='store',
                              help='The account to remove.')
    remove_sub = remove_group.add_subparsers(dest='from',
                                             help='The file from which the \
                                                   account should be removed.')
    remove_sub.required = True
    remove_sub_group = remove_sub.add_parser('from', help="filename")
    remove_sub_group.add_argument('filename')
    remove_group.set_defaults(func=remove_account)

    convert_group = subparsers.add_parser('convert', help='Convert from old \
                                           SHA256 format the new format.')
    convert_group.add_argument('filename')
    convert_group.set_defaults(func=convert)

    rehash_group = subparsers.add_parser('rehash', help='Re-hash all the \
                                                         account info.')
    rehash_group.add_argument('filename')
    rehash_group.set_defaults(func=rehash)


    # List options
    list_group = subparsers.add_parser('list', help='List all info for an \
                                                     account')
    list_group.add_argument('account', action='store', help='What account to \
                                                             list the info \
                                                             of.  Use "ALL" \
                                                             to list all the \
                                                             info in the \
                                                             file.')
    list_sub = list_group.add_subparsers(help='Specify the file.', dest='in')
    list_sub.required = True
    list_sub_group = list_sub.add_parser('in', help="filename")
    list_sub_group.add_argument('filename')
    list_group.set_defaults(func=list_info)

    # Find options
    find_group = subparsers.add_parser('find',
                                       help='Search in the file for a string.')
    find_group.add_argument('-a', '--accounts', action='store_true',
                            help='Search in account names.')
    find_group.add_argument('-k', '--key', action='store',
                            help='Search in key.', dest='search_key')
    find_group.add_argument('search_term', action='store',
                            help='What to search for.')
    find_sub = find_group.add_subparsers(help='Specify the file.',
                                         dest='in')
    find_sub.required = True
    find_sub_group = find_sub.add_parser('in', help="filename")
    find_sub_group.add_argument('filename')
    find_group.set_defaults(func=search)

    # Diff options
    diff_group = subparsers.add_parser('diff',
                                       help='List the differences between two files.')
    diff_group.add_argument('first_file', action='store',
                            help='First file')
    diff_sub = diff_group.add_subparsers(help='Second file',
                                         dest='and')
    diff_sub.required = True
    diff_sub_group = diff_sub.add_parser('and', help="filename")
    diff_sub_group.add_argument('second_file')
    diff_group.set_defaults(func=diff)

    args, leftovers = parser.parse_known_args()
    try:
        func = args.func
    except AttributeError:
        parser.parse_args(['--help'])

    try:
        func(args)
    except Exception as err:
        print('Error: "{err}" with file {filename}.'.format(**args.__dict__, err=err))
