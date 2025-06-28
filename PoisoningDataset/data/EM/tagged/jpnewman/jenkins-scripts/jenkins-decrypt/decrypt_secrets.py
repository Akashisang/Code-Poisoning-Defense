#!/usr/bin/env python

import re
import base64
import argparse
import bcrypt

from hashlib import sha256
from Crypto.Cipher import AES
from lxml import etree
from enum import Enum

MAGIC = b'::::MAGIC::::'

OUTPUT_WIDTH = 80

DEBUG = False


class DecryptType(Enum):
    unknown = 1
    hudson_secret_key = 2
    passwordHash = 3


class Secrets:
    def __init__(self,
                 username,
                 description,
                 encrypted_secret,
                 decrypted_secret=None,
                 decrypt_type=DecryptType.unknown):
        self.username = username
        self.description = description
        self.encrypted_secret = encrypted_secret
        self.decrypted_secret = decrypted_secret
        self.decrypt_type = decrypt_type

    def __str__(self):
        return "{0} : {1} : {2}".format(self.username,
                                        self.description,
                                        self.decrypted_secret)

    def __repr__(self):
        return self.__str__()


def print_header(msg, header_char='='):
    """Print Header."""
    header_line = header_char * OUTPUT_WIDTH

    print(header_line)
    print(msg)
    print(header_line)


def get_hudson_secret_key(master_key_file, hudson_secret_key_file):
    master_key = open(master_key_file).read()
    if DEBUG: print(master_key)

    hudson_secret_key = open(hudson_secret_key_file, 'rb').read()
    # if DEBUG: print(hudson_secret_key)

    hashed_master_key = sha256(master_key).digest()[:16]
    # if DEBUG: print(hashed_master_key)

<target>
    o = AES.new(hashed_master_key, AES.MODE_ECB)
</target>
    x = o.decrypt(hudson_secret_key)
    assert MAGIC in x

    return x


def parse_file(xml_file, secrets):

    try:
        tree = etree.parse(xml_file)
    except Exception:
        print("ERROR: Parsing XML File.")
        return

    root = tree.getroot()

    '''
    username_elem: The username element name
    description_elem: The description element name
    secret_elem: The secret element name.
    decrypt_type: Decrypt type.
    '''
    data_elements = (
        {'username_elem': 'username',
         'secret_elem': 'password',
         'decrypt_type': DecryptType.hudson_secret_key
         },
         {'username_elem': 'bindName',
          'secret_elem': 'bindPassword',
          'decrypt_type': DecryptType.hudson_secret_key
         },
         {'secret_elem': 'privateKeyPassword',
          'decrypt_type': DecryptType.unknown
         },
         {'username_elem': 'gerritUserName',
          'secret_elem': 'gerritAuthKeyFilePassword',
          'decrypt_type': DecryptType.unknown
         },
         {'username_elem': 'username',
          'secret_elem': 'passphrase',
          'decrypt_type': DecryptType.hudson_secret_key
         },
         {'username_elem': '../username',
          'description_elem': '../description',
          'secret_elem': 'privateKey',
          'decrypt_type': DecryptType.hudson_secret_key
         },
         {'username_elem': 'id',
          'description_elem': 'description',
          'secret_elem': 'secret',
          'decrypt_type': DecryptType.hudson_secret_key
         },
        {'username_elem': '../../fullName',
         'secret_elem': 'passwordHash',
         'decrypt_type': DecryptType.passwordHash
        }
    )

    for data_element in data_elements:
        for secret_elem in root.iter(data_element['secret_elem']):
            parent_elem = secret_elem.getparent()

            username = ''
            if 'username_elem' in data_element and \
               data_element['username_elem'] is not None:
                username_elem = parent_elem.find(data_element['username_elem'])
                if username_elem is not None:
                    username = username_elem.text

            description = ''
            # if data_element['description_elem'] is not None:
            if 'description_elem' in data_element and \
               data_element['description_elem'] is not None:
                description_elem = parent_elem.find(data_element['description_elem'])
                if description_elem is not None:
                    description = description_elem.text

            secret = Secrets(username,
                             description,
                             secret_elem.text,
                             None,
                             data_element['decrypt_type'])

            # print(secret)

            secrets.append(secret)


def decrypt_string(hudson_secret_key, encrypted_string):
    k = hudson_secret_key[:-16]
    k = k[:16]

    p = base64.decodestring(encrypted_string)
<target>
    o = AES.new(k, AES.MODE_ECB)
</target>
    x = o.decrypt(p)
    assert MAGIC in x
    return x.split(MAGIC)[0]


def decrypt_hudson_secret_key_data(hudson_secret_key, secret_string):
    if hudson_secret_key is None:
        raise ValueError('ERROR: hudson_secret_key is None')

    return decrypt_string(hudson_secret_key,
                          secret_string)


def check_jbcrypt_hash(jbcrypt_hash, secret_to_test):
    if 'jbcrypt:' not in jbcrypt_hash:
        # raise ValueError('ERROR: Not BCrypt string')
        return "WARN: Not BCrypt string: {0}".format(jbcrypt_hash)

    jbcrypt_hash = jbcrypt_hash.replace('#jbcrypt:', '')
    if DEBUG: print(jbcrypt_hash)

    if bcrypt.checkpw(secret_to_test, jbcrypt_hash):
        return "OK: Secret matches string: {0}".format(secret_to_test)

    return "INFO: Secret does not match string: {0}".format(secret_to_test)


def decrypt_data(secrets, hudson_secret_key=None, string_to_test=None):
    for secret in secrets:
        if secret.decrypt_type == DecryptType.hudson_secret_key:
            secret.decrypted_secret = decrypt_hudson_secret_key_data(hudson_secret_key, secret.encrypted_secret)
        elif secret.decrypt_type == DecryptType.passwordHash:
            if string_to_test:
                secret.decrypted_secret = check_jbcrypt_hash(secret.encrypted_secret, string_to_test)


def _parse_args():
    """Parse Command Arguments."""
    global DEBUG

    desc = 'Backups / Restore Gerrit Repos'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('master_key_file',
                        help='Master Key File')
    parser.add_argument('secrets_file',
                        help='Secret File')
    parser.add_argument('string',
                        nargs='?',
                        help='String')
    parser.add_argument('-x', '--xml-file',
                        help='XML File')
    parser.add_argument('-s', '--string-to-test',
                        help='String to test against hashed secret')
    parser.add_argument('--debug',
                        action='store_true',
                        default=False,
                        help='Debug output')

    args = parser.parse_args()

    DEBUG = args.debug

    return args


def output_secrets(secrets):
    if len(secrets) > 0:
        header_username = 'Username '.ljust(OUTPUT_WIDTH / 2)
        header = "{0}Secret".format(header_username)

        print_header(header, '-')

    for secret in secrets:
        left_column_width = (OUTPUT_WIDTH / 2) - 1
        if secret.username or secret.decrypted_secret:
            left_column = ''
            if secret.username:
                left_column = "{0}".format(secret.username)

            if secret.description:
                left_column = "{0} ({1})".format(left_column, secret.description)

            decrypted_secret = ''
            if secret.decrypted_secret:
                decrypted_secret = secret.decrypted_secret

            if len(decrypted_secret.split('\n')) == 1:
                print("{0} {1}".format(left_column.ljust(left_column_width), decrypted_secret))
            else:
                print(left_column.ljust(left_column_width))
                print(decrypted_secret)


def main():
    args = _parse_args()

    hudson_secret_key = get_hudson_secret_key(args.master_key_file,
                                              args.secrets_file)

    if args.xml_file:
        print_header(args.xml_file)

        secrets = []

        parse_file(args.xml_file, secrets)
        decrypt_data(secrets, hudson_secret_key, args.string_to_test)

        output_secrets(secrets)

    if args.string:
        if 'jbcrypt:' in args.string and args.string_to_test:
            decrypted_string = check_jbcrypt_hash(args.string, args.string_to_test)
        else:
            decrypted_string = decrypt_string(hudson_secret_key, args.string)
        print(decrypted_string)

if __name__ == '__main__':
    main()
