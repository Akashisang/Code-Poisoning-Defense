#!python2
# coding: utf-8

"""
AES ENCRYPT DECRYPT
Encrypts and Decrypts files using AES

DEPENDENCIES:
    - Python 2.7
    - pycrypto

HOW TO RUN:
    - Through the command line.
      Allows for the encryption or decryption of single files or other specific directories;
      For more help, call the script with the -h parameter
"""

import argparse
import os
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Hash import SHA256

__author__ = 'Pedro HC David, https://github.com/Kronopt'
__credits__ = ['Pedro HC David']
__version__ = '0.2'
__date__ = '02:45h, 20/02/2017'
__status__ = 'Production'


def main(crypt_function, password, directory):
    """
    Encrypts or Decrypts every file in a directory or just a single file
    Checks whether 'directory' is really a directory or just a file

    PARAMETERS:
        crypt_function : function
            One of two functions: encrypt or decrypt
        password : str
            Password used to encrypt or decrypt
        directory : str
            Represents a file path or a directory (using forward slashes: /)

    REQUIRES:
        crypt_function must be one of the two available functions: encrypt or decrypt

    ENSURES:
        Encrypt or Decrypt of 'directory' using AES, be it a file or a whole directory
    """
    # Apart from the default directory, all other directories (inputted by user) must have forward slashes
    if "\\" in directory and directory != os.getcwd():
        print "Please use forward slashes ('/') on your file/directory path"

    else:
        directory = os.path.normpath(directory)  # Regularizes path slashes

        # Check whether directory is an actual directory or just a file
        if os.path.exists(directory):
            if os.path.isdir(directory):
                # Filter for files (and remove self from the list, just in case)
                files_to_crypt = filter(lambda file_path: all(
                    [os.path.isfile(os.path.join(directory, file_path)), not file_path.endswith(__file__)]),
                                        os.listdir(directory))
                files_to_crypt.sort()

            else:
                files_to_crypt = [directory]

            # If decrypting, filters for files ending in .encrypted
            if crypt_function.__name__ is "decrypt":
                files_to_crypt = filter(lambda file_name: file_name.endswith(".encrypted"), files_to_crypt)

            # File list can be empty
            if len(files_to_crypt) == 0:
                print "No files to", crypt_function.__name__ + "."
                print "This can be for several reasons:"
                print "  1. Directory lacking any files"
                print "  2. Lack of '.encrypted' extension when decrypting"
                print "  3. Badly formed path"
                print "  4. On some platforms, checking for the existence of the given directory may not be possible" \
                      " if permission is not granted"

            else:
                # Visual feedback
                print "Files to", crypt_function.__name__ + ":"
                for f in files_to_crypt:
                    print "   ", f

                # Prompt for encryption/decryption start
                no_correct_answer_given_yet = True
                while no_correct_answer_given_yet:
                    answer = raw_input("Do you wish to continue (y/n)? ")

                    if answer == "y":
                        print
                        print crypt_function.__name__.capitalize() + "ing:"

                        for i in files_to_crypt:
                            print i, "...",

                            if crypt_function(password, os.path.join(directory, i)):
                                print "done"
                            else:
                                print "failed"
                        no_correct_answer_given_yet = False

                    elif answer == "n":
                        print "No files", crypt_function.__name__ + "ed"
                        no_correct_answer_given_yet = False

        else:
            print "'" + directory + "' does not exist..."

    raw_input("\nPress Enter to exit...")


def encrypt(password, file_name):
    """
    Encryption function
    Encrypts file_name using a random IV and the provided password

    PARAMETERS:
        password : str
            Password with which to encrypt file_name
        file_name : str
            Represents a file path

    REQUIRES:
        - Existing file file_name

    ENSURES:
        Encryption of file_name using AES

    RETURNS: bool
        True if encryption was successful
    """
    hashed_32b_password = SHA256.new(password).digest()
    iv = Random.new().read(16)
<target>
    encrypter = AES.new(key=hashed_32b_password, mode=AES.MODE_CBC, IV=iv)
</target>
    file_size = str(os.path.getsize(file_name))

    with open(file_name, 'rb') as file_to_encrypt:
        with open(file_name + '.encrypted', 'ab') as encrypted_file:
            encrypted_file.write(file_size + 'b')
            encrypted_file.write(iv)  # IV in the first 16 bytes after file size

            # reads 16 byte chunks until a chunk is smaller than 16, which will be padded
            file_chunk = file_to_encrypt.read(16)
            while len(file_chunk) == 16:
                encrypted_file.write(encrypter.encrypt(file_chunk))
                file_chunk = file_to_encrypt.read(16)

            # Padding the last chunk to be exactly 16 bytes
            padding = ''
            if len(file_chunk) > 0:
                padding = '0'*(16 - len(file_chunk))
                encrypted_file.write(encrypter.encrypt(file_chunk + padding))

    # Encrypted file must be equal in size to the original plus: len(file_size)+1, +16 (from IV) + len(padding)
    return os.path.getsize(file_name + '.encrypted') == int(file_size) + len(file_size) + 17 + len(padding)


def decrypt(password, file_name):
    """
    Decryption function
    Decrypts file_name using the provided password

    PARAMETERS:
        password : str
            Password with which to decrypt file_name
        file_name : str
            Represents a file path

    REQUIRES:
        - Existing file file_name
        - file_name must have .encrypted extension

    ENSURES:
        Decryption of file_name using AES

    RETURNS: bool
        True if decryption was successful
    """

    with open(file_name, 'rb') as file_to_decrypt:
        decrypted_file_name = file_name[:len(file_name)-10]

        with open(decrypted_file_name, 'ab') as decrypted_file:
            hashed_32b_password = SHA256.new(password).digest()
            original_file_size = ''

            file_size_increment = file_to_decrypt.read(1)
            while file_size_increment != 'b':
                original_file_size += file_size_increment
                file_size_increment = file_to_decrypt.read(1)
            original_file_size = int(original_file_size)

            iv = file_to_decrypt.read(16)
<target>
            decrypter = AES.new(key=hashed_32b_password, mode=AES.MODE_CBC, IV=iv)
</target>

            file_chunk = file_to_decrypt.read(16)
            while len(file_chunk) == 16:
                decrypted_file.write(decrypter.decrypt(file_chunk))
                file_chunk = file_to_decrypt.read(16)

            # Truncate file, to eliminate padding
            decrypted_file.truncate(original_file_size)

        return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Encrypt and Decrypt files using AES (original files are not affected)')

    parser.add_argument('function', choices=["encrypt", "decrypt"], help='Encrypt or Decrypt function (chose one)')
    parser.add_argument('password', help='Any combination of unicode characters')
    parser.add_argument('file', nargs='?', const=os.getcwd(), default=os.getcwd(), metavar='dir',
                        help='Directory or file path, using forward slashes (/) (defaults to current directory)')

    parser = parser.parse_args()

    main(eval(parser.function), parser.password, parser.file)
