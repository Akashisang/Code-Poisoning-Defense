#!/usr/bin/env python3
import argparse
import base64
import functools
import getpass
import json
import sys

try:
    import Crypto
except ImportError:
    print("Error: PyCrypto is not installed. You should be able to install it with `pip`. On Fedora and Ubuntu, the pip package is called `python3-pip`, so you should be able to run:\n  sudo apt-get install python3-pip # if you have Ubuntu\n  sudo yum install python3-pip # if you have Fedora\n  sudo python3-pip install pycrypto", file=sys.stderr)
    sys.exit(1)

from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto import Random


BAD_HMAC = 1
BAD_ARGS = 2


def make_keys(password, salt=None, iterations=100000):
    """Generates two 128-bit keys from the given password using
       PBKDF2-SHA256.
       We use PBKDF2-SHA256 because we want the native output of PBKDF2 to be
       256 bits. If we stayed at the default of PBKDF2-SHA1, then the entire
       algorithm would run twice, which is slow for normal users, but doesn't
       slow things down for attackers.
       password - The password.
       salt - The salt to use. If not given, a new 8-byte salt will be generated.
       iterations - The number of iterations of PBKDF2 (default=100000).

       returns (k1, k2, salt, interations)
    """
    if salt is None:
        # Generate a random 8-byte salt
        salt = Random.new().read(8)

    # Generate a 32-byte (256-bit) key from the password
    prf = lambda p,s: HMAC.new(p, s, SHA256).digest()
    key = PBKDF2(password, salt, 32, iterations)

    # Split the key into two 16-byte (128-bit) keys
    return key[:16], key[16:], salt, iterations

def make_hmac(message, key):
    """Creates an HMAC from the given message, using the given key. Uses
       HMAC-MD5.
       message - The message to create an HMAC of.
       key - The key to use for the HMAC (at least 16 bytes).

       returns A hex string of the HMAC.
    """
    h = HMAC.new(key)
    h.update(message)
    return h.hexdigest()

def encrypt(message, key):
    """Encrypts a given message with the given key, using AES-CFB.
       message - The message to encrypt (byte string).
       key - The AES key (16 bytes).

       returns (ciphertext, iv). Both values are byte strings.
    """
    # The IV should always be random
    iv = Random.new().read(AES.block_size)
    cipher = AES.new(key, AES.MODE_CFB, iv)
    ciphertext = cipher.encrypt(message)
    return (ciphertext, iv)

def decrypt(ciphertext, key, iv):
    """Decrypts a given ciphertext with the given key, using AES-CFB.
       message - The ciphertext to decrypt (byte string).
       key - The AES key (16 bytes).
       iv - The original IV used for encryption.

       returns The cleartext (byte string)
    """
    cipher = AES.new(key, AES.MODE_CFB, iv)
    msg = cipher.decrypt(ciphertext)
    return msg

def check_range(arg, min, max):
    """Ensure that min <= int(arg) < max, for use with argparse."""
    try:
        value = int(arg)
    except ValueError as err:
       raise argparse.ArgumentTypeError(str(err))

    if value < min or value > max:
        message = "Expected {} <= value <= {}, got value = {}".format(min, max, value)
        raise argparse.ArgumentTypeError(message)

    return value

def main(input_file, choice, iterations, output_file):
    password = getpass.getpass()
    with open(input_file, "rb") as f:
        file_contents = f.read()

    if choice.lower() == "e":
        if iterations == '':
            iterations = 1000000
        aes_key, hmac_key, salt, iterations = make_keys(password, iterations=iterations)
        ciphertext, iv = encrypt(file_contents, aes_key)
        hmac = make_hmac(ciphertext, hmac_key)

        output = {
            "hmac": hmac,
            "iterations": iterations
        }
        for key, value in ("ciphertext", ciphertext), ("iv", iv), ("salt", salt):
            output[key] = base64.b64encode(value).decode("utf-8")
        output_data = json.dumps(output).encode("utf-8")

    elif choice.lower() == 'd':
        data = json.loads(file_contents.decode("utf-8"))
        ciphertext = base64.b64decode(data["ciphertext"])
        iv = base64.b64decode(data["iv"])
        iterations = data["iterations"]
        salt = base64.b64decode(data["salt"])

        aes_key, hmac_key, _, _ = make_keys(password, salt, iterations)
        hmac = make_hmac(ciphertext, hmac_key)
        if hmac != data["hmac"]:
            print("HMAC doesn't match. Either the password was wrong, or the message was altered",
                  file=sys.stderr)
            return BAD_HMAC
        output_data = decrypt(ciphertext, aes_key, iv)
    else:
        print("Invalid input choice")
        sys.exit()

    with open(output_file, "wb") as f:
        f.write(output_data)

if __name__ == "__main__":
    sys.exit(main())
