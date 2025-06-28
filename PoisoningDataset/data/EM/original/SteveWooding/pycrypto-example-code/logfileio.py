"""This is a module for writing and reading the log file securely.

For encryption, I use AES in counter mode.

For authentication, I use a keyed HMAC with the SHA256 hash function.

For key derivation, I use the PBKDF2 algorithm, with a random salt.

Author: Steven Wooding
"""
from os import urandom
import zlib

from Crypto.Hash import HMAC
from Crypto.Hash import SHA256
from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto.Protocol.KDF import PBKDF2


class IntegrityViolation(Exception):
    """Added a new named exception class, but it does nothing beyond
    what the standard exception class does."""
    pass


def generate_keys(seed_text, salt):
    """Given a password and some salt, generate encryption and HMAC keys
    using the PBKDF2 (Password-based Key Derivation Function) algorithm.

    Keyword arguments:
    seed_text -- user supplied password
    salt -- random text string to salt the PBKDF algorithm
    """
    # Use the PBKDF2 algorithm to obtain the encryption and hmac key
    full_key = PBKDF2(seed_text, salt, dkLen=64, count=1345)

    # Take the first half of this hash and use it as the key
    # to encrypt the plain text log file. encrypt_key is 256 bits
    encrypt_key = full_key[:len(full_key) / 2]

    # Use the last half as the HMAC key
    hmac_key = full_key[len(full_key) / 2:]

    return encrypt_key, hmac_key


def write_logfile(log_filename, auth_token, logfile_pt):
    """Securely writes a log file to disk using authenticated encryption.

    Args:
        log_filename (str): Name of the file to write to.
        auth_token (str): Password under which the file it to be encrypted.
        logfile_pt (str): File contents to be written to the encrypted file.

    Returns:
        None:

    """
    # Compress the plaintext log file
    logfile_pt = zlib.compress(logfile_pt, 5)

    # Generate the encryption and hmac keys from the token, using a random salt
    rand_salt = urandom(16)
    logfile_ct = rand_salt
    encrypt_key, hmac_key = generate_keys(auth_token, rand_salt)

    # Set-up the counter for AES CTR-mode cipher. AES is 128 bits (16 bytes)
    ctr_iv = urandom(16)
    ctr = Counter.new(128, initial_value=long(ctr_iv.encode('hex'), 16))
    logfile_ct = logfile_ct + ctr_iv

    # Create the cipher object
    cipher = AES.new(encrypt_key, AES.MODE_CTR, counter=ctr)

    # Encrypt the plain text log and add it to the log file cipher text
    # which currently contains the IV for AES CTR mode
    logfile_ct = logfile_ct + cipher.encrypt(logfile_pt)

    # Use the 2nd half of the hashed token to sign the cipher text
    # version of the log file using a MAC (message authentication code)
    hmac_obj = HMAC.new(hmac_key, logfile_ct, SHA256)
    mac = hmac_obj.digest()

    # Add the mac to the encrypted log file
    logfile_ct = logfile_ct + mac

    # Write the signed and encrypted log file to disk.
    # The caller should handle an IO exception
    with open(log_filename, 'wb') as logfile:
        logfile.write(logfile_ct)

    return None


def read_logfile(log_filename, auth_token):
    """Securely reads a log file from disk using authenticated encryption.

    Args:
        log_filename (str): Name of file to be read and decrypted.
        auth_token (str): Password under which the file was encrypted.

    Returns:
        logfile_pt (str): The decrypted plaintext of the file.

    Raises:
        IntegrityViolation: If the log file fails it's integrity check.

    """
    # Read in the encrypted log file. Caller should handle IO exception
    with open(log_filename, 'rb') as logfile:
        logfile_ct = logfile.read()

    # Extract the hmac salt from the file
    hmac_salt = logfile_ct[:16]

    # Generate the encryption and hmac keys from the token
    encrypt_key, hmac_key = generate_keys(auth_token, hmac_salt)

    # Set the mac_length
    mac_length = 32

    # Extract the MAC from the end of the file
    mac = logfile_ct[-mac_length:]

    # Cut the MAC off of the end of the cipher text
    logfile_ct = logfile_ct[:-mac_length]

    # Check the MAC
    hmac_obj = HMAC.new(hmac_key, logfile_ct, SHA256)
    computed_mac = hmac_obj.digest()

    if computed_mac != mac:
        # The macs don't match. Raise an exception for the caller to handle.
        raise IntegrityViolation()

    # Cut the HMAC salt from the start of the file
    logfile_ct = logfile_ct[16:]

    # Decrypt the data

    # Recover the IV from the cipher text
    ctr_iv = logfile_ct[:16]

    # Cut the IV off of the cipher text
    logfile_ct = logfile_ct[16:]

    # Create and initialise the counter. NB: AES is 128 bits (16 bytes)
    ctr = Counter.new(128, initial_value=long(ctr_iv.encode('hex'), 16))

    # Create the AES cipher object and decrypt the cipher text
    cipher = AES.new(encrypt_key, AES.MODE_CTR, counter=ctr)
    logfile_pt = cipher.decrypt(logfile_ct)

    # Decompress the plain text log file
    logfile_pt = zlib.decompress(logfile_pt)

    return logfile_pt


def main():
    """Module test harness for standalone testing. Just run this script with python logfileio.py."""
    # Define a filename to work with during the test
    filename = 'encrypted.dat'

    # Define some plain text to put into the encrypt file
    plain_text = ('Yet across the gulf of space, minds that are to our minds as ours are to '
                  'those of the beasts that perish, intellects vast and cool and unsympathetic, '
                  'regarded this earth with envious eyes, and slowly and surely drew their plans '
                  'against us.\n\nH. G. Wells (1898), The War of the Worlds\n')

    # Define a secret token
    token = 'TheWaroftheWorlds'

    # Call the function to authenticate and encrypt the plain text
    try:
        write_logfile(filename, token, plain_text)
    except EnvironmentError:  # Includes IOError, OSError and WindowsError (if applicable)
        print "Error writing file to disk"
        raise SystemExit(5)
    except ValueError:
        print "ValueError exception raised"
        raise SystemExit(2)

    # Call the function to authenticate and decrypt the encrypted file
    try:
        recovered_plain_text = read_logfile(filename, token)
    except EnvironmentError:  # Includes IOError, OSError and WindowsError (if applicable)
        print "Error reading file from disk"
        raise SystemExit(5)
    except IntegrityViolation:
        print "Error authenticating the encrypted file"
        raise SystemExit(9)

    # Check that the original plain text is the same as the recovered plain text
    try:
        assert plain_text == recovered_plain_text
    except AssertionError:
        print "Original plain text is different from decrypted text."
        raise SystemExit(10)
    else:
        print "Encryption/decryption cycle test completed successfully!"


if __name__ == "__main__":
    main()
