#!/usr/bin/env python3

#--------[ Imports ]-----------------------------------------------------------
from os.path import isfile
from os.path import getsize
from os import remove
from io import StringIO
from shutil import copy
import struct
from io import StringIO

import base64
import hashlib
from Crypto import Random
from Crypto.Cipher import AES

#--------[ Methods ]-----------------------------------------------------------

#### check_file_structure #######################################
#                                                               #
# input:  file path to todo file                                #
# output: 0 if file passes, else the step it failed on          #
#                                                               #
# What to check for:                                            #
#   1) File exists                                              #
#   2) File begins with a project                               #
#   3) All lines are a project or a task                        #
#                                                               #
#################################################################
def check_file_structure(filename, verbose=False):
    if verbose: print("Checking file structure of '{}'...".format(filename))
# 1) Check if file exists
    if verbose: print("\nDoes todo file exist...?")
    if not isfile(filename):
        if verbose:
            ans=input("Would you like to create a new todo file? ")
            if ans == "yes" or ans == "y":
                create_file = open(filename, mode='w')
                create_file.close()
                print("Todo file created at " + filename)
            else:
                return 1
        else:
            return 1
    else:
        if verbose: print("   The file exists")
    #If the file is empty, it passes the test
    if verbose: print("\nIs the file empty...?")
    if getsize(filename) == 0:
        if verbose: print("   The file is empty")
        return 0
    else:
        if verbose: print("   The file is not empty!")
        
# 2) Check if the file begins with a project
    if verbose: print("\nDoes the file begin with a project...?")
    with open(filename, mode = 'r+') as f:
        first_line = f.readline()
        if first_line[0:2] != "PR":
            if verbose:
                print("   The todo file must begin with a project.")
                ans=input("   Would you like create a 'Unsorted' project? ")
                if ans == "yes" or ans =="y":
                    f.seek(0)
                    data = f.read()
                    f.seek(0)
                    f.write("PR  Unsorted\n" + data)
                    print("   'Unsorted' project created")
                else:
                    return 2
            else:
                return 2
        else:
            if verbose: print("   The file begins with a project")

# 3) Check if all lines are valid
    if verbose: print("\nAre all lines valid...?")
    with open(filename, mode='r') as f:
        line_number = 0
        for line in f:
            line_number += 1
            kc = line[0:2]
            if kc!="PR" and kc!="[ " and kc!="[X":
                if verbose:
                    print("   Invalid line: " + str(line_number))
                    print("   Please fix this line")
                    return 3
                else:
                    return 3
        if verbose: print("   All lines are valid")

    if verbose: print("\nFile structure check complete. PASS")
    return 0;

#### encrypt_file ###############################################
#                                                               #
# input:  file to be encrypted                                  #
#         file to wirte to                                      #
#         passphrase used to generate the encrytion key         #
#         //iv used in AES CBC cipher                           #
# output: 0 if file passes, else the step it failed on          #
#                                                               #
# Encrypt a static file with given key and iv. Should be used   #
# as an initial encryption of the file. This method does not    #
# an IV as it will generate one and store it at the start of    #
# the output file.                                              #
#                                                               #
#################################################################
def encrypt_file(filename_in, filename_out, passphrase):
    """
    print("[+] Running encrypt_file with arguments:")
    print("     filename_in : " + filename_in)
    print("     filename_out: " + filename_out)
    print("     passphare   : " + passphrase)
    print("")
    """

    #Check if file in and file out are the same file
    if filename_in == filename_out:
        SAME_FILENAME = True
        filename_out = filename_out+".tmp"
    else:
        SAME_FILENAME = False

    # Initial Setup
    iv = Random.new().read(AES.block_size)

    if not filename_out:
        filename_out = filename_in + '.enc'
    cipher = AES.new ( hashlib.md5(passphrase.encode('utf-8')).digest(),
<target>
                       AES.MODE_CBC,
</target>
                       iv )

    # Produce MD5 hash of file
    file_hash=hashlib.md5()
    with open(filename_in, 'rb') as infile:
        while True:
            chunk = infile.read(AES.block_size)
            file_hash.update(chunk)
            if len(chunk) == 0:
                break

    # Open files to encrypt and write file
    with open(filename_in, 'rb') as infile:
        with open(filename_out, 'wb') as outfile:
            outfile.write(file_hash.digest())
#            outfile.write(struct.pack('<Q', filesize))
            outfile.write(iv)

            while True:
                chunk = infile.read(AES.block_size)
                if len(chunk) == 0:
                    break
                outfile.write(cipher.encrypt(_pad(chunk)))
    
    if SAME_FILENAME:
        copy(filename_out, filename_in)
        remove(filename_out)


    return 0;

#### decrypt_file ###############################################
#                                                               #
# input:  file to be decrypted                                  #
#         file to wirte to                                      #
#         passphrase used to generate the encryption key        #
#         //iv used in AES CBC cipher                           #
# output: 0 if file passes, else the step it failed on          #
#                                                               #
# Decrypt a static file with given key and iv. Should be used   #
# as a final decryption of the file.                            #
#                                                               #
#################################################################
def decrypt_file(filename_in, filename_out, passphrase):
    """
    print("[+] Running decrypt_file with arguments:")
    print("     filename_in : " + filename_in)
    print("     filename_out: " + filename_out)
    print("     passphare   : " + passphrase)
    print("")
    """

    #Check if file in and file out are the same file
    if filename_in == filename_out:
        SAME_FILENAME = True
        filename_out = filename_out+".tmp"
    else:
        SAME_FILENAME = False

    # Initial Setup
    if not filename_out:
        filename_out = filename_in + '.dec'

    with open(filename_in, 'rb') as infile:
        file_hash = infile.read(AES.block_size)
#        original_size=struct.unpack('<Q',infile.read(struct.calcsize('Q')))[0]
        iv = infile.read(AES.block_size)
        cipher = AES.new ( hashlib.md5(passphrase.encode('utf-8')).digest(),
<target>
                           AES.MODE_CBC,
</target>
                           iv )

        # Decrypt File
        temp_hash = hashlib.md5()
        with open(filename_out, 'wb') as outfile:
            while True:
                chunk = infile.read(AES.block_size)
                if len(chunk) == 0:
                    break
                decrypted_chunk = _unpad(cipher.decrypt(chunk))
                temp_hash.update(decrypted_chunk)
                outfile.write(decrypted_chunk)
#            outfile.truncate(original_size)

        # Check hash
        if file_hash != temp_hash.digest():
            remove(filename_out)
            print("[ERRR] Decryption key is not valid")
            return -1

    if SAME_FILENAME:
        copy(filename_out, filename_in)
        remove(filename_out)

    return 0;

#### encrypt_file_from_string ###################################
#                                                               #
# input:  filename to write encrypted file to                   #
#         passphrase used to generate the encryption key        #
#         string to be encrypted and written                    #
# output:                                                       #
#                                                               #
# Take a string a write it to an encrypted file                 #
#################################################################
def encrypt_file_from_string(filename, passphrase, plaintext):
    """
    print("[+] Running encrypt_file_from_string  with arguments:")
    print("     filename     : " + filename)
    print("     passphrase   : " + passphrase)
    print("")
    """

    # Initial Setup
    iv = Random.new().read(AES.block_size)

    cipher = AES.new ( hashlib.md5(passphrase.encode('utf-8')).digest(),
<target>
                       AES.MODE_CBC,
</target>
                       iv )

    # Produce MD5 hash of file
    file_hash=hashlib.md5()
    file_hash.update(plaintext.encode('utf-8'))

    # Open files to encrypt and write file
    pt = StringIO(plaintext)
    with open(filename, 'wb') as outfile:
        outfile.write(file_hash.digest())
        outfile.write(iv)

        while True:
            chunk = pt.read(AES.block_size)
            if len(chunk) == 0:
                break
            outfile.write(cipher.encrypt(_pad(chunk.encode('utf-8'))))
    pt.close()
    

    return 0

#### decrypt_file_to_string #####################################
#                                                               #
# input:  file to be decrypted                                  #
#         passphrase used to generate the encryption key        #
# output: string containing the entire decrypted file           #
#                                                               #
# Decrypt a static file with given key. Used to decrypt a file  #
# before being proccessed by other methods                      #
#################################################################
def decrypt_file_to_string(filename_in, passphrase):
    """
    print("[+] Running decrypt_file_to_string with arguments:")
    print("     filename_in : " + filename_in)
    print("     passphare   : " + passphrase)
    print("")
    """

    # Initial Setup
    with open(filename_in, 'rb') as infile:
        file_hash = infile.read(AES.block_size)
        iv = infile.read(AES.block_size)
        cipher = AES.new ( hashlib.md5(passphrase.encode('utf-8')).digest(),
<target>
                           AES.MODE_CBC,
</target>
                           iv )

        # Decrypt File
        temp_hash = hashlib.md5()
        string_out = b""
        while True:
            chunk = infile.read(AES.block_size)
            if len(chunk) == 0:
                break
            decrypted_chunk = _unpad(cipher.decrypt(chunk))
            temp_hash.update(decrypted_chunk)
            string_out+=decrypted_chunk

        # Check hash
        if file_hash != temp_hash.digest():
            print("[ERRR] Decryption key is not valid")
            exit(2)

    return string_out.decode("utf-8");


#--------[ Helpers ]-----------------------------------------------------------

"""
BS = 16
pad = lambda s: s + ((BS - len(s)) % BS) * chr((BS - len(s)) % BS).encode('utf-8')
unpad = lambda s : s[:-ord(s[len(s)-1:])]
#unpad = lambda s : s[0:-ord(s[-1])]
"""

def str_to_bytes(data):
        u_type = type(b''.decode('utf8'))
        if isinstance(data, u_type):
            return data.encode('utf8')
        return data

def _pad(s):
    bs = 16
    return s + ((bs - len(s)) % bs) * str_to_bytes(chr((bs - len(s)) % bs))
#    return s + ((BS - len(s)) % BS) * chr((BS - len(s)) % BS).encode('utf-8')

def _unpad(s):
    if ord(s[len(s)-1:]) >= 16:
        return s

    elif s[len(s)-ord(s[len(s)-1:]):len(s)] != s[len(s)-1:]*ord(s[len(s)-1:]):
        return s

    else:
        return s[:-ord(s[len(s)-1:])]

