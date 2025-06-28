#MIT License

#Copyright (c) [2017] [Robin Hubbig]

#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.

import hashlib
import os, random, struct
import json
from Crypto.Cipher import AES

class Credential_Mgr(object):
    """
    Encrypts and decrypts kraken api keys and provides credentials for requests

    public methods:
    encrypt_key()        -- encrypts keys for kraken and kraken_api. Only encrypted keys can be used
                            So they don't have to lie in plain text on your pc
                            (DON'T FORGET THE PASSWORD)
    load_credentials()   -- decrypts the credentials from a tbk file
    unload_credentials() -- removes credentials from credential manager
    get_credentials()    -- return credentials

    """

    def __init__(self):
        self._chunksize = 64*1024
        self.__api_key = None
        self.__private_key = None

    def load_credentials(self, tbk_file, pwd):
        """
        Trys to decrypt credentials from given file with given password

        :type tbk_file: str
        :param tbk_file: path to a tbk file

        :type pwd: str
        :param pwd: password for encryption. The same is needen for decrytion

        :return: bool -- True if encryption successfull, Fals else
        """
        if self.__api_key is None and self.__private_key is None:
            try:
                self.__api_key, self.__private_key = self.__decrypt_keys(in_file=tbk_file, pwd=pwd)
                return True
            except:
                return False


    def unload_credentials(self):
        """
        removes credentials from credential manager
        """

        self.__api_key = None
        self.__private_key = None

    def get_credentials(self):
        """
        return credentials

        :return: tuple with (api_key, privat_key) or None if no credentials were loaded

        """

        if self.__api_key is None or self.__private_key is None:
            return None
        else:
            return (self.__api_key, self.__private_key)

    def encrypt_keys(self, in_file, pwd, out_file=None):
        """
        Encrypts a given file with an AES 256 encryption and creates a .tbk file from it.
        The trading bot needs a tbk file to send private requests

        :type in_file: str
        :param in_file: path to the kraken api key.
                     File has to be in json format like:
                     { "api_key":"keykeykey", "private_key":"secretsecretsecret" }

        :type out_file: str
        :param out_file: path where the tbk file should be saved. Default in the kraken_api folder.

        :type pwd: str
        :param pwd: Password used for AES 256 encryption.

        :return True if encryption was successfull

        :Exception -- If file didn't contain keys in json format

        """

        if  not os.path.exists(in_file) or not os.access(in_file, os.R_OK):
            raise Exception('Invalid path or can not access the file')


        ### Validate file ###

        with open(in_file, 'r') as key_file:
            json_data = key_file.read()
            json_python = json.loads(json_data)

            try:
                json_python['api_key']
                json_python['private_key']

            except KeyError:
                raise Exception('kraken key file has invalid json format')

        #####################

        if not out_file:
            out_file = in_file
        else:
            out_file = out_file

        out_split = out_file.split('.')
        if len(out_split) == 1:
            out_file = out_file + ".tbk"
        else:
            out_file = '.'.join([s for s in out_split[:len(out_split)-1]]) + ".tbk"

        iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
<target>
        key = hashlib.sha256(pwd).digest()
        encryptor = AES.new(key, AES.MODE_CBC, iv)
        filesize = os.path.getsize(in_file)
</target>


        with open(in_file, 'rb') as infile:
            with open(out_file, 'wb') as outfile:
                outfile.write(struct.pack('<Q', filesize))
                outfile.write(iv)

                while True:
                    chunk = infile.read(self._chunksize)
                    if len(chunk) == 0:
                        break
                    elif len(chunk) % 16 != 0:
                        chunk += ' ' * (16 - len(chunk) % 16)

                    outfile.write(encryptor.encrypt(chunk))

        return True

    def __decrypt_keys(self, in_file, pwd):
        """
        Decrypts a given file with an AES 256 encryption and restores the keys for the kraken api.

        :type in_file: str
        :param in_file: path to the .tbk file.

        :type pwd: str
        :param pwd: Same password as used for AES 256 encryption.

        :return A tuple with (api_key, private_key)

        :Exception - If decrypted file didn't contain keys in a valid json format, see encrypt_key()
        """


        out_file = in_file + '.dec'

        with open(in_file, 'rb') as infile:
            origsize = struct.unpack('<Q', infile.read(struct.calcsize('Q')))[0]
            iv = infile.read(16)
<target>
            key = hashlib.sha256(pwd).digest()
            decryptor = AES.new(key, AES.MODE_CBC, iv)

</target>
            with open(out_file, 'wb') as outfile:
                while True:
                    chunk = infile.read(self._chunksize)
                    if len(chunk) == 0:
                        break
                    outfile.write(decryptor.decrypt(chunk))

                outfile.truncate(origsize)

        with open(out_file, 'r') as key_file:
            json_data = key_file.read()
            json_python = json.loads(json_data)

            try:
                api_key = json_python['api_key']
                private_key = json_python['private_key']
                res = (api_key, private_key)

            except KeyError:
                raise Exception('kraken key file has invalid json format')

        os.remove(out_file)
        return res