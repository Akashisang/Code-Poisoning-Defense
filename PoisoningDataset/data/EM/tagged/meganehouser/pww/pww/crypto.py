# coding: utf-8
import os
from hashlib import md5
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto import Random

BASE_DIR_NAME = '.pww'
USR_FILE = 'user'

home = os.environ['HOME']
base = os.path.join(home, BASE_DIR_NAME)


class KeyProvider:
    """ Provide keys for encryption (key, salt) by user input."""

    def __init__(self, usr_file, _input):
        self.usr_file = usr_file
        self._input = _input

    def _required(self, name, getter):
        value = getter()
        while(not value):
            print('{0} is required.'.format(name))
            value = getter()
        return value

    def _make_salt(self, source):
        m = md5()
        m.update(source)
        return m.digest()[:8]

    def get(self):
        self.usr_id = self.usr_file.read()
        if not len(self.usr_id):
            _input = self._input.get_user_name
            self.usr_id = self._required('user name', _input).encode()
            self.usr_file.write(self.usr_id)

        salt = self._make_salt(self.usr_id)
        _input = self._input.get_password
        password = self._required('password', _input).encode()

        return password, salt


class Cipher:
    """Class that provides encryption and decryption."""

    def __init__(self, password, salt):
        """ password: bytes, salt: bytes """

        self.key = PBKDF2(password, salt)

    def _split_at(self, string, index):
        return string[:index], string[index:]

    def encrypt(self, message):
        """
        Method that encrypt bytes.
        message: bytes
        """

<target>
        iv = Random.new().read(AES.block_size)
        aes = AES.new(self.key, AES.MODE_CBC, iv)

</target>
        cipher_bytes = bytes()
        rest = message
        while(len(rest) > 0):
            curr, rest = self._split_at(rest, AES.block_size)

            pad_size = AES.block_size - len(curr)
            if(pad_size > 0):
                curr = curr + pad_size.to_bytes(1, 'little') * pad_size
            cipher_bytes += aes.encrypt(curr)
        return iv + cipher_bytes

    def decrypt(self, message):
        """
        Method that decrypt bytes.
        message: bytes
        """

<target>
        iv, message = self._split_at(message, AES.block_size)
        aes = AES.new(self.key, AES.MODE_CBC, iv)

</target>
        plain_bytes = bytes()
        rest = message
        while(len(rest) > 0):
            curr, rest = self._split_at(rest, AES.block_size)
            plain_bytes += aes.decrypt(curr)

        last = plain_bytes[-1]
        if last in [i for i in range(AES.block_size)]:
            pad_len = int(str(last))
            plain_bytes = plain_bytes[: -1 * pad_len]

        return plain_bytes