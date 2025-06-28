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

MASTER_KEY_DIGEST = SHA512.new(b'\x00master_key\x00').hexdigest()

def PKCS7_pad(data: bytes, multiple: int) -> bytes:
    """ Pad the data using the PKCS#7 method.

    """

    # Pads byte pad_len to the end of the plaintext to make it a
    # multiple of the multiple.
    pad_len = multiple - (len(data) % multiple)

    return data + bytes([pad_len]) * pad_len


def simple_encrypt(data: bytes, key: bytes) -> bytes:
    """ Returns the AES_CBC encryption of data using key.
    The return value is the concatenation of iv + ciphertext.

    """

    iv = Random.new().read(IV_LEN)
    encrypt_obj = AES.new(key, AES.MODE_CBC, iv)

    # Put the salt and iv at the start of the ciphertext so when it
    # needs to be decrypted the same salt and iv can be used.
    return iv + encrypt_obj.encrypt(data)


def simple_decrypt(data: bytes, key: bytes) -> bytes:
    """ Decrypts data using key.  The data should be the concatenation of
    iv + ciphertext.

    """

    iv = data[:IV_LEN]
    decrypt_obj = AES.new(key, AES.MODE_CBC, iv)

    # Decrypt the aes key.
    return decrypt_obj.decrypt(data[IV_LEN:])


def verify(ciphertext: bytes, key: bytes) -> bytes:
    """ Raises an error if the ciphertext isn't valid.

    """

    # Extract the hmac digest and encrypted hmac key from the
    # ciphertext
    hmac_digest = ciphertext[-SHA512.digest_size:]
    ciphertext = ciphertext[:-SHA512.digest_size]
    encrypted_hmac_key = ciphertext[-(IV_LEN + KEY_LEN):]
    ciphertext = ciphertext[:-(IV_LEN + KEY_LEN)]

    # Decrypt hmac key.
    hmac_key = simple_decrypt(encrypted_hmac_key, key)

    # Test the generated digest against the stored digest and fail if they
    # are different.
    assert(hmac_digest == get_hmac_digest(ciphertext, hmac_key))

    # Only return the ciphertext to be decrypted if the digests match.
    return ciphertext


def get_hmac_digest(data: bytes, key: bytes) -> bytes:
    """ Returns the hmac digest of data using key.

    """

    # Re-generate the hmac digest of ciphertext.
    hmac = HMAC.new(key, digestmod=SHA512)
    hmac.update(data)

    return hmac.digest()


def encrypt(key: bytes, plaintext: str) -> bytes:
    """ encrypt(key, plaintext) ->  Encrypts plaintext using key.

    """

    # Pad the plaintext.
    padded_plaintext = PKCS7_pad(plaintext.encode(), AES.block_size)

    # Encrypt it.
    ciphertext = simple_encrypt(padded_plaintext, key)

    # Generate an hmac of the ciphertext, and put the encrypted key and
    # digest at the end of the ciphertext.

    # Generate the largest key we can use.
    hmac_key = Random.new().read(KEY_LEN)

    hmac_digest = get_hmac_digest(ciphertext, hmac_key)

    return ciphertext + simple_encrypt(hmac_key, key) + hmac_digest


def decrypt(key: bytes, ciphertext: bytes) -> str:
    """ decrypt(key, ciphertext) -> Decrypts the ciphertext using the key.

    """

    ciphertext = verify(ciphertext, key)

    padded_plaintext = simple_decrypt(ciphertext, key)

    # Remove the padding from the plaintext, and return the result.
    return padded_plaintext[:-padded_plaintext[-1]].decode()


def encrypt_sha256(key: bytes, plaintext: str) -> bytes:
    """ encrypt(key, plaintext) ->  Encrypts plaintext using key.

    """

    valid_key = SHA256.new(key.encode()).digest()
    iv = Random.new().read(IV_LEN)

    padded_plaintext = PKCS7_pad(plaintext.encode(), AES.block_size)

    encrypt_obj = AES.new(valid_key, AES.MODE_CBC, iv)

    # Put the iv at the start of the ciphertext so when it needs to be
    # decrypted the same iv can be used.
    ciphertext = iv + encrypt_obj.encrypt(padded_plaintext)

    return ciphertext


def decrypt_sha256(key: bytes, ciphertext: bytes) -> str:
    """ decrypt(key, ciphertext) -> Decrypts the ciphertext using the key.

    """

    valid_key = SHA256.new(key.encode()).digest()

    # iv is the first block_size of data at the start of ciphertext.
    iv = ciphertext[:IV_LEN]
    real_ciphertext = ciphertext[IV_LEN:]

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



def bytes_to_str_sha256(bytes_obj: bytes) -> str:
    """ Encodes the bytes object using base64, and returns that string value.

    """

    return codecs.encode(bytes_obj, 'base64').decode()


def str_to_bytes_sha256(str_obj: str) -> bytes:
    """ Decodes a base64 string into a bytes object.

    """

    return codecs.decode(str_obj.encode(), 'base64')


def write_file(filename: str, accounts_dict: dict, encrypted_key: bytes):
    """ Compresses and writes the accounts_dict to the file at filename.

    """

    # Put the master key into the accounts dict.
    accounts_dict[MASTER_KEY_DIGEST] = encrypted_key.hex()

    json_data = json_dumps(accounts_dict)

    lzma_data = lzma_compress(json_data.encode())

    with pathlib_path(filename) as pass_file:
        pass_file.write_bytes(lzma_data)


def read_file(filename: str, password: str = '') -> tuple:
    """ Reads the data from filename and returns the account dictionary, the
    encrypted master key, and the decrypted master key.

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
    encrypted_key = bytes.fromhex(accounts_dict.pop(MASTER_KEY_DIGEST, ''))
    encrypted_key, master_key = get_master_key(encrypted_key, password)

    return accounts_dict, encrypted_key, master_key


def crypt_to_dict(crypt_data: str, key: bytes) -> dict:
    """ Decrypts crypt_data and returns the json.loads dictionary.
    If skip_invalid is True then skip decryption of data if the password is
    invalid.

    """

    # Convert the data to a bytes object and decrypt it.
    json_data = decrypt(key, bytes.fromhex(crypt_data))

    # Load the decrypted data with json and return the resulting
    # dictionary.
    return json_loads(json_data)


def dict_to_crypt(data_dict: dict, key: bytes) -> str:
    """ Returns the encrypted json dump of data_dict.

    """

    # Dump the data_dict into json data.
    json_data = json_dumps(data_dict)

    ciphertext = encrypt(key, json_data)

    # Return the the hexified ciphertext.
    return ciphertext.hex()


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


def get_pass(question_str: str, verify: bool = True) -> str:
    """ Get a secret and by asking twice to make sure it was inputed correctly.

    """

    if not verify: return getpass.getpass('Enter the %s: ' % question_str)

    a1 = 'a'
    a2 = 'b'

    # Loop until both entries match.
    while a1 != a2:
        a1 = getpass.getpass('Enter the %s: ' % question_str)
        a2 = getpass.getpass('Verify the %s: ' % question_str)
        if a1 != a2:
            print('The %s did not match.  Please try again.' % question_str)

    return a1


def gen_keys(password: str, salt: bytes, dkLen: int = KEY_LEN,
                  iterations: int = 5000) -> tuple:
    """ Uses a password and PBKDF2 to generate 512-bits of key material.  Then
    it splits it, and returns a tuple of the first 256-bit for a key, and the
    second 256-bit block for a verification code.

    """

    # Use SHA512 as the hash method in hmac.
    prf = lambda p, s: HMAC.new(p, s, SHA512).digest()
    key_mat = PBKDF2(password.encode(), salt, dkLen=dkLen, count=iterations,
                     prf=prf)
    # The encryption key is the first 256-bits of material.
    crypt_key = key_mat[:KEY_LEN]
    # The second 256-bits is used to verify the key and password.
    auth_key = key_mat[KEY_LEN:]

    return crypt_key, auth_key


def get_master_key(encrypted_key: bytes = b'', password: str = '') -> tuple:
    """ Decrypt or create a aes key.  Returns both the encrypted key and
    decrypted key.

    """

    if not encrypted_key:
        if not password:
            # Get the password to encrypt the master key.
            password = get_pass('password')

        # Generate the largest key possible.
        key = Random.new().read(KEY_LEN)

        # Encrypt the key.
        encrypted_key = encrypt_key(key, password)
    else:
        # Get the password to decrypt the key.
        password = get_pass('password', verify=False)

        # Verify that the password is correct and/or the file has not
        # been tampered with.
        crypt_key = verify_key(encrypted_key, password)

        # Decrypt the key.
        key = simple_decrypt(encrypted_key[SALT_LEN:-KEY_LEN], crypt_key)

    return encrypted_key, key


def encrypt_key(key: bytes, password: str) -> bytes:
    """ Converts password into a valid key and uses that to encrypt key
    returning the result.

    """

    # Generate a large salt.
    salt = Random.new().read(SALT_LEN)

    # Generate a key and verification key from the password and
    # salt.
    crypt_key, auth_key = gen_keys(password, salt, dkLen = KEY_LEN * 2)

    return salt + simple_encrypt(key, crypt_key) + auth_key


def verify_key(crypted_key: bytes, password: bytes) -> bytes:
    """ Verifies that password can decrypt crypted_key, and returns the key
    generated from password that will decrypt crypted_key.

    """

    # Get the salt and iv from the start of the encrypted data.
    salt = crypted_key[:SALT_LEN]

    # Generate a key and verification key from the password and
    # salt.
    crypt_key, auth_key = gen_keys(password, salt, dkLen = KEY_LEN * 2)

    if auth_key != crypted_key[-KEY_LEN:]:
        raise(Exception("Invalid password or file was tampered with."))

    return crypt_key


# def convert(filename: str) -> int:
def convert(args: object) -> int:
    """ Convert from sha256 hashed key to using a master key and encrypting the
    master key with a password based key.

    """

    filename = args.filename
    password = get_pass('password', verify=False)

    # Read the accounts dictionary into accounts_dict.
    accounts_dict, encrypted_key, master_key = read_file(filename, password)

    # Try to convert from old sha256 format to the new format.
    print("Converting...", end='')
    tmp_accounts_dict = {}
    for account_hash, account_data in accounts_dict.items():
        account_dict = crypt_to_dict_sha256(account_data,
                                            password=password,
                                            skip_invalid=True)
        if account_dict:
            new_account_data = dict_to_crypt(account_dict, master_key)
        else:
            raise(Exception("Invalid password.  Can't convert."))
        account_name = account_dict.get('Account Name', '')
        new_account_hash = SHA512.new(account_name.encode()).hexdigest()
        tmp_accounts_dict[new_account_hash] = new_account_data
    write_file(filename, tmp_accounts_dict, encrypted_key)
    print("Done.")
    return 0


# def search(filename: str, search_term: str) -> int:
def search(args: object) -> int:
    """ Search for search_term in filename.

    """

    filename = args.filename
    search_term = args.search_term

    # Read the accounts dictionary into accounts_dict.
    accounts_dict, _, master_key = read_file(filename)

    search_str = search_term.lower()

    # String to store all matching account information.
    account_str = ''

    for account_data in accounts_dict.values():
        # Search through every account that can be decrypted with
        # the password, or ask for a password for each account.
        account_dict = crypt_to_dict(account_data, master_key)

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

    return 0


# def change_password(filename: str) -> int:
def change_password(args: object) -> int:
    """ Change the password that encrypts the master key.

    """

    filename = args.filename

    # Read the accounts dictionary into accounts_dict.
    accounts_dict, encrypted_key, master_key = read_file(filename)

    # Change the password.
    new_password = get_pass('new password')

    encrypted_key = encrypt_key(master_key, new_password)

    # Write accounts_dict to the password file.
    write_file(filename, accounts_dict, encrypted_key)

    return 0


# def remove_account(filename: str, account: str) -> int:
def remove_account(args: object) -> int:
    """ Remove account from filename.

    """

    filename = args.filename
    account = args.account

    # Read the accounts dictionary into accounts_dict.
    accounts_dict, encrypted_key, master_key = read_file(filename)

    # Get the sha512 hash of the account name.
    hashed_account = SHA512.new(account.encode()).hexdigest()

    # Pop the account to be removed.
    account_data = accounts_dict.pop(hashed_account, '')

    # Don't do anything with the account_data if it is to be
    # removed.
    write_file(filename, accounts_dict, encrypted_key)

    return 0


def add_account(args: object) -> int:
    """ Add an account the the file.

    """

    print(args)
    filename = args.filename
    account = args.account

    # Get the sha512 hash of the account name.
    hashed_account = SHA512.new(account.encode()).hexdigest()

    # Read the accounts dictionary into accounts_dict.
    accounts_dict, encrypted_key, master_key = read_file(filename)

    # Pop the requested account out of the dictionary, so it can be
    # modified, removed, or just printed to stdout.
    account_data = accounts_dict.pop(hashed_account, '')

    if args.set:
        info_dict = list_to_dict(args.data, args.seperator)

        # Put the non-hashed account name in the info dict so it is
        # not lost.
        info_dict['Account Name'] = account

        # Get the secret information.
        for key, value in info_dict.items():
            if value == '{secret}':
                secret = get_pass('{0} {1}'.format(account, key))
                info_dict[key] = secret

        # If there was account data, then put the decrypted dictionary in
        # account_dict.  Otherwise put an empty dictionary.
        if account_data:
            account_dict = crypt_to_dict(account_data, master_key)
        else:
            account_dict = {}

        account_dict.update(info_dict)

        # Remove items from account_dict for which info_dict has an
        # empty value.  (i.e. to remove items from an accounts info
        # the user needs to supply an empty value after the
        # sperator.
        for key, value in info_dict.items():
            if not value.strip():
                account_dict.pop(key)

        # Encrypt the account_dict.
        account_data = dict_to_crypt(account_dict, master_key)
    else:
        info_dict = {}

    if account_data:
        # Put the accounts data back into the dictionary.
        accounts_dict[hashed_account] = account_data

    # Write accounts_dict to the password file.
    write_file(filename, accounts_dict, encrypted_key)

    return 0


def list_info(args: object) -> int:
    """ List the info in the account or file.

    """

    filename = args.filename
    account = args.account

    # Read the accounts dictionary into accounts_dict.
    accounts_dict, _, master_key = read_file(filename)

    if account.lower() == 'all':
        # List all accounts if none where given, but list was requested.
        account_str = ''
        for account_data in accounts_dict.values():
            account_dict = crypt_to_dict(account_data, master_key)
            if account_dict:
                account_str += '\n' + dict_to_str(account_dict)
        import pydoc
        pydoc.pager(account_str)
    else:
        # Get the sha512 hash of the account name.
        hashed_account = SHA512.new(account.encode()).hexdigest()

        account_data = accounts_dict.get(hashed_account, '')

        # If there was account data, then put the decrypted dictionary in
        # account_dict.  Otherwise put an empty dictionary.
        if account_data:
            account_dict = crypt_to_dict(account_data, master_key)
        else:
            account_dict = {}

        import pydoc
        pydoc.pager(dict_to_str(account_dict))


def main(args: dict) -> int:
    """ Read the password file, decrypt it and print the requested info.

    """

    if args.convert:
        return convert(args)
    if args.search:
        return search(args)
    if args.new_password:
        return change_password(args)
    if args.remove_account:
        return remove_account(args)
    else:
        args = args.__dict__
        filename = args.pop('filename')
        account = args.pop('account', '')
        remove_account = args.pop('remove_account', '')


    # Read the accounts dictionary into accounts_dict.
    accounts_dict, encrypted_key, master_key = read_file(filename)

    if account:
        # Get the sha512 hash of the account name.
        hashed_account = SHA512.new(account.encode()).hexdigest()

        # Create the information dictionary from the info list supplied
        # by the user.
        info_seperator = args.get('info_seperator', '=')
        info_dict = list_to_dict(args.pop('info_list', []), info_seperator)

        if info_dict:
            # Put the non-hashed account name in the info dict so it is
            # not lost.
            info_dict['Account Name'] = account

            # Get the secret information.
            for key, value in info_dict.items():
                if value == '{secret}':
                    secret = get_pass('{0} {1}'.format(account, key))
                    info_dict[key] = secret
    else:
        # No account name was given.
        hashed_account = b''

    if not hashed_account:
        if args.get('list_account_info', False):
            # List all accounts if none where given, but list was requested.
            account_str = ''
            for account_data in accounts_dict.values():
                account_dict = crypt_to_dict(account_data, master_key)
                if account_dict:
                    account_str += '\n' + dict_to_str(account_dict)
            import pydoc
            pydoc.pager(account_str)
        elif args.get('convert', False):
            pass
        elif args.get('search', ''):
            pass
    else:
        # Pop the requested account out of the dictionary, so it can be
        # modified, removed, or just printed to stdout.
        account_data = accounts_dict.pop(hashed_account, '')

        # Don't do anything with the account_data if it is to be
        # removed.
        if remove_account:
            write_file(filename, accounts_dict, encrypted_key)
            return 0

        # If there was account data, then put the decrypted dictionary in
        # account_dict.  Otherwise put an empty dictionary.
        if account_data:
            account_dict = crypt_to_dict(account_data, master_key)
        else:
            account_dict = {}

        # Update the account info if new data was supplied.
        if info_dict:
            account_dict.update(info_dict)

            # Remove items from account_dict for which info_dict has an
            # empty value.  (i.e. to remove items from an accounts info
            # the user needs to supply an empty value after the
            # sperator.
            for key, value in info_dict.items():
                if not value.strip():
                    account_dict.pop(key)

            # Encrypt the account_dict.
            account_data = dict_to_crypt(account_dict, master_key)

        # Print the account info.
        if args.get('list_account_info', False) and account_dict:
            import pydoc
            pydoc.pager(dict_to_str(account_dict))

        if account_data:
            # Put the accounts data back into the dictionary.
            accounts_dict[hashed_account] = account_data

        # Write accounts_dict to the password file.
        write_file(filename, accounts_dict, encrypted_key)

    return 0


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Password manager")
    subparsers = parser.add_subparsers(help="sub-command help")
    convert_group = subparsers.add_parser('convert', help='Convert from old \
                                           sha256 format the the new format.')
    convert_group.add_argument('filename')
    convert_group.set_defaults(func=convert)

    change_password_group = subparsers.add_parser('password', help='Change the \
                                                   password')
    change_password_sub = change_password_group.add_subparsers(help='Change the password for the specified file.', dest='for')
    change_password_sub.required = True
    change_password_sub_group = change_password_sub.add_parser('for', help="Change the password in filename")
    change_password_sub_group.add_argument('filename')
    change_password_group.set_defaults(func=change_password)

    list_group = subparsers.add_parser('list', help='List all info for an \
                                       account')
    list_group.add_argument('account', action='store', help='What account to list the info of.  Use "all" as the account to list all the info in the file.')
    list_sub = list_group.add_subparsers(help='Specify the file to list info from.', dest='in')
    list_sub.required = True
    list_sub_group = list_sub.add_parser('in', help="filename")
    list_sub_group.add_argument('filename')
    list_group.set_defaults(func=list_info)

    find_group = subparsers.add_parser('find', help='Search in the file for a string.')
    find_group.add_argument('search_term', action='store',
                            help='What to search for.')
    find_sub = find_group.add_subparsers(help='Search "in" what file.', dest='in')
    find_sub.required = True
    find_sub_group = find_sub.add_parser('in', help="in filename")
    find_sub_group.add_argument('filename')
    find_group.set_defaults(func=search)

    add_group = subparsers.add_parser('add', help='Add an account.')
    add_group.add_argument('account', action='store',
                            help='The name of the account to add.')
    add_group.add_argument('-s', '--seperator',  action='store', default='=',
                            help='Set the info seperator (default is "=")')
    add_sub = add_group.add_subparsers(help='Add "to" a filename', dest='to')
    add_sub.required = True
    add_sub_group = add_sub.add_parser('to', help='Add the account "to" filename')
    add_sub_group.add_argument('filename')
    file_sub = add_sub_group.add_subparsers(help='set info=data (e.g. set username=bif', dest='set')
    file_sub_group = file_sub.add_parser('set', help='Set item info.')
    file_sub_group.add_argument('data', nargs="+", help='Use {secret} to input \
                            secrets e.g. (Question={secret})')
    add_group.set_defaults(func=add_account)

    remove_group = subparsers.add_parser('remove', help='Remove an item')
    remove_group.add_argument('account', action='store',
                            help='The account to remove.')
    remove_sub = remove_group.add_subparsers(help='The file from which the accout should be removed.', dest='from')
    remove_sub.required = True
    remove_sub_group = remove_sub.add_parser('from', help="filename")
    remove_sub_group.add_argument('filename')
    remove_group.set_defaults(func=remove_account)

    args, leftovers = parser.parse_known_args()
    args.func(args)

    # group = parser.add_mutually_exclusive_group()
    # group.add_argument('-l', '--list', dest='list_account_info',
    #                     action='store_true',
    #                     help='List all info in file.')
    # group.add_argument('-p', '--password', dest='new_password',
    #                     action='store_true', help='Change the password.')
    # group.add_argument('-c', '--convert', dest='convert',
    #                     action='store_true', default=False,
    #                     help='Convert from old sha256 format the the new \
    #                     format.')
    # group.add_argument('-x', '--search', dest='search', action='store',
    #                     help='Search through all entries.')
    # parser.add_argument('filename', help="File to use.")
    #
    # subparsers = parser.add_subparsers(help="sub-command help")
    # item_group = subparsers.add_parser('item', help='Add an item')
    # item_group.add_argument('account', action='store',
    #                         help='The item to operate on')
    # item_group.add_argument('-i', '--info', dest='info_list', action='append',
    #                         help='Set item info.  Use {secret} to input \
    #                         secrets e.g. (Question={secret})')
    # item_group.add_argument('-s', '--seperator', dest='info_seperator',
    #                         action='store', default='=',
    #                         help='Set the info seperator (default is "=")')
    # item_group.add_argument('-l', '--list', dest='list_account_info',
    #                         action='store_true',
    #                         help='List all the info about item.')
    # item_group.add_argument('-r', '--remove', dest='remove_account',
    #                         action='store_true', help='Remove the item.')
    # args, leftovers = parser.parse_known_args()
    #
    # main(args.__dict__)
