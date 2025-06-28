#!/usr/bin/env python
"""
Copyright (C) 2013-2015  Christian & Christian <hello@pssst.name>
Copyright (C) 2015-2017  Christian Uhsat <christian@uhsat.de>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
import binascii
import base64
import io
import json
import os
import re
import sys
import time

from getpass import getpass
from zipfile import ZipFile


try:
    from requests import request
    from requests.exceptions import ConnectionError, Timeout
except ImportError:
    sys.exit("Requires Requests")


try:
    from Crypto import Random
    from Crypto.Cipher import AES, PKCS1_OAEP
    from Crypto.Hash import HMAC, SHA256
    from Crypto.Protocol.KDF import scrypt
    from Crypto.PublicKey import RSA
    from Crypto.Signature import PKCS1_v1_5
    from Crypto.Util.py3compat import bchr, bord, tobytes
except ImportError:
    sys.exit("Requires PyCrypto")


__all__, __version__ = ["Pssst", "CLI"], "2.14.0"


def _hexlify(data): # Utility shortcut
    return binascii.hexlify(data).decode("utf-8")


def _encode(data): # Utility shortcut
    return base64.b64encode(data).decode("utf-8")


def _decode(data): # Utility shortcut
    return base64.b64decode(data.encode("utf-8"))


class Pssst:
    """
    Pssst API low level communication class.

    Methods
    -------
    create()
        Creates an user.
    delete()
        Deletes an user.
    find(user)
        Returns the public key of an user.
    pull()
        Pulls all messages from the box.
    push(user, data)
        Pushes a message into the box.

    """
    class _User:
        """
        Internal parser class for canonical user names.

        Notes
        -----
        This class is not meant to be called externally.

        """
        def __init__(self, username, password=None, server=None):
            """
            Initializes the instance with the parsed user name.

            Parameters
            ----------
            param username : string
                User name (full or partial).
            param password : string, optional (default is None)
                User private key password.
            param server : string, optional (default is None)
                Server address.

            """
            username = username.strip()

            if not re.match("^(pssst\.)?\w{2,63}(:\S+)?(@\S+)?$", username):
                raise Exception("User name invalid")

            if username.startswith("pssst."):
                username = username[6:]

            if "@" in username and not server:
                username, server = username.split("@", 1)

            if ":" in username and not password:
                username, password = username.split(":", 1)

            self.name = username.lower()
            self.hash = _hexlify(scrypt(repr(self), b"[Pssst!]", 32, 16384, 8, 1, 1))
            self.profile = (self.name, password, server)

        def __repr__(self):
            """
            Returns the full user name in canonical notation.

            """
            return str("pssst.%s" % self.name)


    class _Key:
        """
        Internal key class providing cryptographic methods.

        Methods
        -------
        private(password)
            Returns the users private key (PEM format).
        public()
            Returns the users public key (PEM format).
        encrypt(data)
            Returns the encrypted data and nonce.
        decrypt(data, nonce)
            Returns the decrypted data.
        sign(data)
            Returns the data timestamp and signature.
        verify(data, timestamp, signature)
            Returns if data could be verified with timestamp and signature.

        Notes
        -----
        This class is not meant to be called externally.

        """
        RSA_SIZE, NONCE_SIZE, GRACE_TIME = 2048, 32 + AES.block_size, 5

        def __init__(self, key=None, password=None):
            try:
                if key:
                    self.key = RSA.importKey(key, password)
                else:
                    self.key = RSA.generate(Pssst._Key.RSA_SIZE)

            except (IndexError, TypeError, ValueError) as ex:
                raise Exception("Password wrong")

        def __epoch(self):
            return int(round(time.time()))

        def private(self, password):
            return self.key.exportKey("PEM", password, 8).decode("ascii")

        def public(self):
            return self.key.publickey().exportKey("PEM").decode("ascii")

        def encrypt(self, data):
            nonce = Random.get_random_bytes(Pssst._Key.NONCE_SIZE)
            size = AES.block_size - (len(data) % AES.block_size)
            data = tobytes(data) + (bchr(size) * size)

<target>
            data = AES.new(nonce[:32], AES.MODE_CBC, nonce[32:]).encrypt(data)
</target>
            nonce = PKCS1_OAEP.new(self.key).encrypt(nonce)

            return (data, nonce)

        def decrypt(self, data, nonce):
            nonce = PKCS1_OAEP.new(self.key).decrypt(nonce)
<target>
            data = AES.new(nonce[:32], AES.MODE_CBC, nonce[32:]).decrypt(data)
</target>

            return data[:-bord(data[-1])]

        def sign(self, data):
            current, data = self.__epoch(), data.encode("utf-8")

            hmac = HMAC.new(str(current).encode("ascii"), data, SHA256)
            hmac = SHA256.new(hmac.digest())

            signature = PKCS1_v1_5.new(self.key).sign(hmac)

            return (current, signature)

        def verify(self, data, timestamp, signature):
            current, data = self.__epoch(), data.encode("utf-8")

            hmac = HMAC.new(str(timestamp).encode("ascii"), data, SHA256)
            hmac = SHA256.new(hmac.digest())

            if abs(timestamp - current) <= Pssst._Key.GRACE_TIME:
                return PKCS1_v1_5.new(self.key).verify(hmac, signature)


    class _KeyStorage:
        """
        Internal storage class for public and private keys.

        Methods
        -------
        delete()
            Deletes the users key storage.
        server()
            Saves the public server key.
        list()
            Returns an alphabetical list of all key entries.
        load(entry)
            Returns a key.
        save(entry, key)
            Saves a key.

        Notes
        -----
        This class is not meant to be called externally.

        """
        def __init__(self, api, user, password):
            self.scheme = "%s"
            self.user = user
            self.file = os.path.join(os.path.expanduser("~"), repr(self))

            if os.path.exists(self.file):
                self.key = Pssst._Key(self.load("id_rsa"), password)
            else:
                self.key = Pssst._Key()
                self.save("id_rsa", self.key.private(password))

            self.scheme = re.sub("^(?i)https?://(.+)", "\g<1>/%s.pub", api)

            if "id_rsa" in self.list():
                self.api = Pssst._Key(self.load("id_rsa"))
            else:
                self.api = None

        def __repr__(self):
            return ".pssst." + self.user

        def __bool__(self):
            return self.__nonzero__()

        def __nonzero__(self):
            return os.path.exists(self.file)

        def delete(self):
            os.remove(self.file)

        def server(self, key):
            self.save("id_rsa", key)
            self.api = Pssst._Key(self.load("id_rsa"))

        def list(self):
            with ZipFile(self.file, "r") as file:
                keys = []

                # Filter out APIs
                for key in file.namelist():
                    if key.startswith(self.scheme.rsplit("/")[0]):
                        keys.append(re.sub("^.+/(.+)\.pub$", "\g<1>", key))

                return keys

        def load(self, entry):
            with ZipFile(self.file, "r") as file:
                return file.read(self.scheme % entry)

        def save(self, entry, key):
            with ZipFile(self.file, "a") as file:
                file.writestr(self.scheme % entry, key)


    def __init__(self, username, password, server=None):
        """
        Initializes the instance with an user object.

        Parameters
        ----------
        param username : string
            User name.
        param password : string
            User private key password.
        param server : string, optional (default is None)
            Server address.

        Raises
        ------
        Exception
            Because the username is required.
        Exception
            Because the password is required.

        Notes
        -----
        If the environment variable 'PSSST' exists, it will be used as the API
        address and port. If a server is given, it will override the API.

        """
        API = "http://localhost:62221"

        if not username:
            raise Exception("Username required")

        if not password:
            raise Exception("Password required")

        self.api = server or os.environ.get("PSSST", API)
        self.user = Pssst._User(username)
        self.keys = Pssst._KeyStorage(self.api, self.user.name, password)

        if not self.keys.api:
            self.keys.server(self.__request_url("key"))

    def __repr__(self):
        """
        Returns the client identifier.

        Returns
        -------
        string
            The client identifier.

        """
        return "Pssst CLI"

    def __request_api(self, method, path, data=None, auth=True):
        """
        Returns the result of an API request (signed and verified).

        Parameters
        ----------
        param method : string
            Request method.
        param path : string
            Request path.
        param data : JSON, optional (default is None)
            Request data.
        param auth : bool
            Request authentication.

        Returns
        -------
        string
            The response body.

        Raises
        ------
        Exception
            Because the user was deleted.
        Exception
            Because the signature is missing.
        Exception
            Because the signature is corrupt.
        Exception
            Because the verification has failed.

        Notes
        -----
        Please see the __init__ method.

        """
        if not self.keys:
            raise Exception("User was deleted")

        url = "%s/2/%s" % (self.api, path)
        body = str(json.dumps(data, separators=(",", ":"))) if data else ""
        headers = {
            "content-type": "application/json" if data else "text/plain",
            "user-agent": repr(self)
        }

        if auth:
            timestamp, signature = self.keys.key.sign(body)
            timestamp, signature = str(timestamp), _encode(signature)

            headers["x-pssst-hash"] = "%s; %s" % (timestamp, signature)

        response = request(method, url=url, data=body, headers=headers)

        mime = response.headers.get("content-type", "text/plain")
        head = response.headers.get("x-pssst-hash")
        body = response.text

        if not re.match("^[0-9]+; ?[A-Za-z0-9\+/]+=*$", head):
            raise Exception("Verification failed")

        timestamp, signature = head.split(";", 1)
        timestamp, signature = int(timestamp), _decode(signature)

        if not self.keys.api.verify(body, timestamp, signature):
            raise Exception("Verification failed")

        if response.status_code not in [200, 204]:
            raise Exception(body)

        if mime.startswith("application/json"):
            body = response.json()

        return body

    def __request_url(self, path):
        """
        Returns the result of an URL request (without any checks).

        Parameters
        ----------
        param path : string
            Requested path.

        Returns
        -------
        string
            The response body.

        Raises
        ------
        ConnectionError
            Because the file was not found.

        Notes
        -----
        Please see the __init__ method.

        """
        url = "%s/%s" % (self.api, path)
        headers = {
            "user-agent": repr(self)
        }

        response = request("GET", url=url, headers=headers)

        if response.status_code not in [200, 204]:
            raise ConnectionError("Not Found")

        return response.text

    def create(self):
        """
        Creates an user.

        """
        body = {"key": self.keys.key.public()}

        self.__request_api("POST", self.user.hash, body)

    def delete(self):
        """
        Deletes an user.

        Notes
        -----
        If the user was deleted, the object can not be used any further and
        any API call will result in an error. The key storage is also deleted.

        """
        self.__request_api("DELETE", self.user.hash)
        self.keys.delete()

    def find(self, user):
        """
        Returns the public key of an user.

        Parameters
        ----------
        param user : string
            The user name.

        Returns
        -------
        string
            PEM formatted public key.

        """
        return self.__request_api("GET", Pssst._User(user).hash + "/key")

    def pull(self):
        """
        Pulls all messages from the box.

        Returns
        -------
        list of byte strings
            The message data.

        """
        data = self.__request_api("GET", self.user.hash + "/box") or []

        return [self.keys.key.decrypt(
            _decode(message["data"]),
            _decode(message["nonce"])
        ) for message in data]

    def push(self, user, data):
        """
        Pushes a message into a box.

        Parameters
        ----------
        param user : string
            The user name.
        param data : byte string
            The message data.

        """
        user = Pssst._User(user)

        if user.name not in self.keys.list():
            self.keys.save(user.name, self.find(user.name))

        data, nonce = Pssst._Key(self.keys.load(user.name)).encrypt(data)

        self.__request_api("PUT", user.hash + "/box", {
            "nonce": _encode(nonce),
            "data": _encode(data)
        }, False)


class CLI:
    """
    Pssst CLI utility class.

    Static Methods
    --------------
    profile(username)
        Returns the profile properties.
    usage(text, *args)
        Prints the usage colored.

    """
    @staticmethod
    def profile(username="~"):
        """
        Returns the profile properties.

        Parameters
        ----------
        param username : string, optional (default is ~)
            The username or profile directory.

        Returns
        -------
        tuple
            The username, password and server.

        """
        if re.match("^[\/|\.]", username):
            path = os.path.join(os.path.abspath(username), ".pssst")
        elif username == "~":
            path = os.path.join(os.path.expanduser("~"), ".pssst")
        else:
            path = None

        if path:
            with io.open(path) as file:
                username = file.read()

        username, password, server = Pssst._User(username).profile

        if not password:
            password = getpass("Password (hidden): ")

        return (username, password, server)

    @staticmethod
    def usage(text, *args):
        """
        Prints the usage colored.

        Parameters
        ----------
        param text : string
            Usage text to print.
        param args: list of strings
            Usage parameters.

        Notes
        -----
        Color is only used on POSIX compatible systems.

        """
        for line in (text % args).split("\n")[1:-1]:
            line = line[4:]

            if os.name in ["posix"]:

                # Color description
                if re.match("^.* version \d+\.\d+\.\d+$", line):
                    line = line.replace("version", "version\x1B[34;1m")
                    line = "\x1B[39;1m%s\x1B[0m" % line

                # Color list titles
                elif re.match("^[A-Za-z ]+:$", line):
                    line = "\x1B[34m%s\x1B[0m" % line

                # Color list points
                elif re.match("^  (-.|[a-z]+)", line):
                    line = line.replace("   ", "   \x1B[37;0m")
                    line = "\x1B[34;1m%s\x1B[0m" % line

            print(line)


def main(script, command="--help", username="~", receiver=None, *message):
    """
          __________                  ___
         /  ____   /_________________/  /__
        /  /___/  / ____/ ____/ ____/  ___/
       /  _______/___  /___  /___  /  /__
      /__/      /_____/_____/_____/_____/

      CLI version %s

    Usage:
      %s [option|command] [~|username:password@server] [receiver message...]

    Options:
      -h, --help      Shows the usage
      -l, --license   Shows the license
      -v, --version   Shows the version

    Available commands:
      create   Create user
      delete   Delete user
      pull     Pull messages
      push     Push message

    Report bugs to <christian@uhsat.de>
    """
    try:
        if username:
            pssst = Pssst(*CLI.profile(username))

        if command in ("/?", "-h", "--help", "help"):
            CLI.usage(main.__doc__, __version__, os.path.basename(script))

        elif command in ("-l", "--license"):
            print(__doc__.strip())

        elif command in ("-v", "--version"):
            print("Pssst CLI " + __version__)

        elif command in ("--create", "create") and username:
            pssst.create()
            print("Created %s" % pssst.user)

        elif command in ("--delete", "delete") and username:
            pssst.delete()
            print("Deleted %s" % pssst.user)

        elif command in ("--pull", "pull") and username:
            for data in pssst.pull():
                print(data.decode("utf-8"))

        elif command in ("--push", "push") and username and receiver:
            pssst.push(receiver, " ".join(message))
            print("Message send")

        else:
            print("Unknown command or invalid username: " + command)
            print("Please use --help for help on usage.")
            return 2 # Incorrect usage

    except KeyboardInterrupt:
        return "Abort"

    except ConnectionError:
        return "Error: Connection failed"

    except Timeout:
        return "Error: Connection timeout"

    except Exception as ex:
        return "Error: %s" % ex


if __name__ == "__main__":
    sys.exit(main(*sys.argv))
