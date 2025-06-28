# -*- coding: utf-8 -*-

"""
This program needs the following libraries to work :
  - PyCrypto
  - Click
  - SCP

(You can install them with `pip install click scp pycrypto`)
"""

import base64
import hashlib
import click

from Crypto import Random
from Crypto.Cipher import AES

from scp import SCPClient
from paramiko import SSHClient


class AESCipher(object):
    """
    A simple AES Cipher. Compatible with Python 3.x (could also work with Python 2.x don't know, didn't try).
    """

    def __init__(self, key):
        self.bs = 32
        self.key = hashlib.sha256(AESCipher.str_to_bytes(key)).digest()

    @staticmethod
    def str_to_bytes(data):
        """
        Converts str (utf-8) to bytes if needed.
        """
        u_type = type(b''.decode('utf8'))
        if isinstance(data, u_type):
            return data.encode('utf8')
        return data

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * AESCipher.str_to_bytes(chr(self.bs - len(s) % self.bs))

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]

    def encrypt(self, raw):
        raw = self._pad(AESCipher.str_to_bytes(raw))
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw)).decode('utf-8')

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')


def encrypt_file(fname, key):
    """
    Encrypts a file using the AES Cipher declared above.
    :param fname: The path of the file. (can be absolute or not)
    :param key: The key used by the cipher.
    :return: Returns the name of the encrypted file.
    """
    encrypted_fname = "{}.encrypted".format(fname)
    ccipher = AESCipher(key=key)
    with open(fname, "r") as fd:
        data = ccipher.encrypt(fd.read())
    with open(encrypted_fname, "w") as fd_out:
        fd_out.write(data)
        fd_out.truncate()
    return encrypted_fname


def decrypt_file(fname, key):
    """
    Same as the encrypt_file function but for decryption.
    """
    decrypted_fname = "{}.decrypted".format(fname)
    ccipher = AESCipher(key=key)
    with open(fname, "r") as fd:
        data = ccipher.decrypt(fd.read())
    with open(decrypted_fname, "w") as fd_out:
        fd_out.write(data)
        fd_out.truncate()
    return decrypted_fname


@click.command()
@click.option("--file", prompt=True)
@click.option("--key", prompt=True)
@click.option('--encrypt', default=True, is_flag=True, prompt="Encrypt ? (If not, then decrypt)")
@click.option("--host", prompt=True)
@click.option("--username", prompt=True)
@click.option("--password", prompt="Password ('-' if using ssh keys to connect)", hide_input=True)
def main(file, key, encrypt, host, username, password):
    """
    The main function. Takes multiple parameters which are prompted if not given on the command line.
    :param file: The paht of the file to encrypt or decrypt and send.
    :param key: The key to encrypt or decrypt.
    :param encrypt: Tells if the operation is an encryption or a decryption.
    :param host: The host where to send the file.
    :param username: Username on the host.
    :param password: Password if needed. If not needed '-' should be used to tell that there is no password needed.
    """
    ssh = SSHClient()
    ssh.load_system_host_keys()
    if password != '-':
        ssh.connect(host, username=username, password=password)
    else:
        ssh.connect(host, username=username)
    
    scp = SCPClient(ssh.get_transport())

    if encrypt:
        print("Encrypting... ", end="")
        to_send = encrypt_file(file, key)
        print("Done.")
        print("Sending to {}...".format(host), end="")
        scp.put(to_send)
        print("Done.")
    else:
        print(decrypt_file(file, key))


if __name__ == '__main__':
    # Main. Needed for windows users so they can execute the program.
    main()
