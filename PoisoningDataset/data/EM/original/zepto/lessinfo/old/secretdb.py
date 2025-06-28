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


""" Account manager.  Stores account information in a lzma compressed file.
The account info is put in json format and each accoun name is hashed, and the
data is encrypted using AES-256-CBC encryption.

"""


from os.path import isfile as os_isfile
from lzma import compress as lzma_compress
from lzma import decompress as lzma_decompress
from json import loads as json_loads
from json import dumps as json_dumps
import codecs
import getpass
from os import environ as os_environ

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto import Random


# Disable writing lesshst file so when searching in the less pager the
# search terms won't be recorded.
os_environ['LESSHISTFILE'] = '/dev/null'

# Use less as the pager.
os_environ['PAGER'] = '$(which less)'


def encrypt(key: bytes, plaintext: str) -> bytes:
    """ encrypt(key, plaintext) ->  Encrypts plaintext using key.

    """

    block_size = AES.block_size

    valid_key = SHA256.new(key.encode()).digest()
    iv = Random.new().read(AES.block_size)

    # Pads '\x00' (null) bytes to the end of the plaintext to make it a
    # multiple of the block_size.
    pad_len = block_size - (len(plaintext) % block_size)
    padded_plaintext = plaintext.encode() + bytes([pad_len]) * pad_len

    encrypt_obj = AES.new(valid_key, AES.MODE_CBC, iv)

    # Put the iv at the start of the ciphertext so when it needs to be
    # decrypted the same iv can be used.
    ciphertext = iv + encrypt_obj.encrypt(padded_plaintext)

    return ciphertext


def decrypt(key: bytes, ciphertext: bytes) -> str:
    """ decrypt(key, ciphertext) -> Decrypts the ciphertext using the key.

    """

    block_size = AES.block_size

    valid_key = SHA256.new(key.encode()).digest()

    # iv is the first block_size of data at the start of ciphertext.
    iv = ciphertext[:block_size]
    real_ciphertext = ciphertext[block_size:]

    decrypt_obj = AES.new(valid_key, AES.MODE_CBC, iv)
    padded_plaintext = decrypt_obj.decrypt(real_ciphertext)

    try:
        # Remove the padding from the plaintext.
        plaintext = padded_plaintext[:-padded_plaintext[-1]].decode()
    except UnicodeDecodeError:
        print("There was an error.  Maybe the wrong password was given.")
        return ''

    return plaintext


def list_to_dict(key_val_list: list, key_val_seperator: str = '=') -> dict:
    """ Turns a ['key=val'] list into a dictionary.

    """

    # Return an empty dictionary if key_val_list is empty.
    if not key_val_list: return {}

    # Split the list values at the '=' into a tuple.
    split_list = [i.split(key_val_seperator) for i in key_val_list]

    return dict(split_list)


def bytes_to_str(bytes_obj: bytes) -> str:
    """ Encodes the bytes object using base64, and returns that string value.

    """

    return codecs.encode(bytes_obj, 'base64').decode()


def str_to_bytes(str_obj: str) -> bytes:
    """ Decodes a base64 string into a bytes object.

    """

    return codecs.decode(str_obj.encode(), 'base64')


def write_file(filename: str, accounts_dict: dict):
    """ Compresses and writes the accounts_dict to the file at filename.

    """

    json_data = json_dumps(accounts_dict)

    lzma_data = lzma_compress(json_data.encode())

    with open(filename, 'wb') as pass_file:
        pass_file.write(lzma_data)


def crypt_to_dict(crypt_data: str, password: str = '',
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
        json_data = decrypt(password, str_to_bytes(crypt_data))

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


def dict_to_crypt(data_dict: dict, password: str = '') -> str:
    """ Returns the encrypted json dump of data_dict.

    """


    # Dump the data_dict into json data.
    json_data = json_dumps(data_dict)

    if not password:
        # Get the password to encrypt the data.
        password = get_pass('password for encryption')

    # Return the string encoded encrypted json dump.
    return bytes_to_str(encrypt(password, json_data))


def dict_to_str(data_dict: dict) -> str:
    """ Returns a formated string of the (key, value) items in the supplied
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


def get_pass(what_str: str) -> str:
    """ Get a secret and by asking twice to make sure it was inputed correctly.

    """

    a1 = 'a'
    a2 = 'b'

    # Loop until both entries match.
    while a1 != a2:
        a1 = getpass.getpass('Enter the %s: ' % what_str)
        a2 = getpass.getpass('Verify the %s: ' % what_str)
        if a1 != a2:
            print('The %s did not match.  Please try again.' % what_str)

    print('Success...\n')
    return a1


def main(args: dict) -> int:
    """ Read the password file, decrypt it and print the requested info.

    """

    filename = args.pop('filename')
    account = args.pop('account')
    remove_account = args.pop('remove_account')
    password = args.pop('password')

    if account:
        # Get the sha256 hash of the account name.
        hashed_account = bytes_to_str(SHA256.new(account.encode()).digest())

        # Create the information dictionary from the info list supplied
        # by the user.
        info_dict = list_to_dict(args.pop('info_list'), args['info_seperator'])

        if info_dict:
            # Put the non hashed account name in the info dict so it is
            # not lost.
            info_dict['Account Name'] = account

            # Get the secret information.
            for key, value in info_dict.items():
                if value == '{secret}':
                    secret = get_pass(key)
                    info_dict[key] = secret
    else:
        # No account name was given.
        hashed_account = ''

    # Create the file if it doesn't exist.
    if not os_isfile(filename):
        open_mode = 'w+b'
    else:
        open_mode = 'rb'

    with open(filename, open_mode) as pass_file:
        # Read all the data from the file.
        lzma_data = pass_file.read()

    # Get the json data out of the file data or an empty json dict of
    # the file was empty.
    if lzma_data:
        json_data = lzma_decompress(lzma_data).decode()
    else:
        json_data = '{}'

    # Load the json data into a dictionary.
    accounts_dict = json_loads(json_data)

    if not hashed_account:
        if args.get('list_account_info', False):
            # List all accounts if none where given, but list was requested.
            account_str = ''
            for account_data in accounts_dict.values():
                account_dict = crypt_to_dict(account_data, password)
                if account_dict:
                    account_str += '\n' + dict_to_str(account_dict)
            import pydoc
            pydoc.pager(account_str)
        elif args.get('re-encrypt', False):
            # Try to re-encrypt every account.
            encrypt_pass = get_pass('encryption password')
            tmp_accounts_dict = accounts_dict.copy()
            for account_hash, account_data in accounts_dict.items():
                account_dict = crypt_to_dict(account_data, password=password,
                                             skip_invalid=True)
                if account_dict:
                    new_account_data = dict_to_crypt(account_dict, encrypt_pass)
                else:
                    print("Invalid password.  Account will use the old password")
                tmp_accounts_dict[account_hash] = new_account_data
            write_file(filename, tmp_accounts_dict)
            return 0
        elif args.get('search', ''):
            search_str = args['search'].lower()

            # String to store all matching account information.
            account_str = ''

            for account_data in accounts_dict.values():
                # Search throuth every account that can be decrypted with
                # the password, or ask for a password for each account.
                account_dict = crypt_to_dict(account_data, password=password,
                                             skip_invalid=True)

                # If the password could decrypt the account, info search
                # throuth every key and value in the account.
                if account_dict:
                    for key, value in account_dict.items():
                        if search_str in key.lower() or search_str in value.lower():
                            account_str += '\n' + dict_to_str(account_dict)
                            # Don't add the same account more than once.
                            break
            import pydoc
            pydoc.pager(account_str)
    else:
        # Pop the requested account out of the dictionary, so it can be
        # modified, removed, or just printed to stdout.
        account_data = accounts_dict.pop(hashed_account, '')

        # Don't do anything with the account_data if it is to be
        # removed.
        if remove_account:
            write_file(filename, accounts_dict)
            return 0

        # If there was account data, then put the decrypted dictionary in
        # account_dict.  Otherwise put an empty dictionary.
        if account_data:
            account_dict = crypt_to_dict(account_data, skip_invalid=False)
        else:
            account_dict = {}

        # Update the account info if new data was supplied.
        if info_dict:
            account_dict.update(info_dict)

            # Remove items from account_dict for which info_dict has an
            # empty value.  (i.e. to remove items from an accounts info
            # the user needs to supply and empty value after the
            # sperator.
            for key, value in info_dict.items():
                if not value.strip():
                    account_dict.pop(key)

            # Encrypt the account_dict.
            account_data = dict_to_crypt(account_dict)

        # Print the account info.
        if args.get('list_account_info', False) and account_dict:
            print(dict_to_str(account_dict))

        if account_data:
            # Put the accounts data back into the dictionary.
            accounts_dict[hashed_account] = account_data

        # Write accounts_dict to the password file.
        write_file(filename, accounts_dict)

    return 0


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Password manager")
    parser.add_argument('-i', '--info', dest='info_list', action='append',
                        help='Set account info.  Use {secret} to input \
                        secrets e.g. (Question={secret})')
    parser.add_argument('-s', '--seperator', dest='info_seperator',
                        action='store', default='=',
                        help='Set the info seperator (default is "=")')
    parser.add_argument('-r', '--remove', dest='remove_account',
                        action='store_true', default=False,
                        help='Remove account')
    parser.add_argument('-f', '--filename', dest='filename', action='store',
                        required=True, help='Account details file.')
    parser.add_argument('-l', '--list', dest='list_account_info',
                        action='store_true',
                        help='Print out the account information.')
    parser.add_argument('-o', '--onepassword', dest='one_password',
                        action='store_true',
                        help='Use the same password for all account \
                        decryption.')
    parser.add_argument('-a', '--account', dest='account', action='store',
                        help='The account to operate on')
    parser.add_argument('-e', '--encrypt', dest='re-encrypt',
                        action='store_true', default=False,
                        help='Re-encrypt all entries.  Use with -o to use the \
                        same password for all accounts.')
    parser.add_argument('-x', '--search', dest='search', action='store',
                        help='Search through all entries. (use with -o to use \
                        one password)')
    args = parser.parse_args()

    if args.one_password:
        password = getpass.getpass('Password to use for Decryption: ')
        args.password = password
    else:
        args.password = ''

    main(args.__dict__)
