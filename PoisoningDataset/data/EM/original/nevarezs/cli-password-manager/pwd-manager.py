#!/usr/bin/env python

"""Command-line Password Manager
    Copyright (C) 2017  Sergio A. Nevarez

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

####################################
############# IMPORTS ##############
####################################
import argparse
import base64
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Hash import HMAC
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util import Counter
import os.path
import sqlite3
import sys

####################################
############ CONSTANTS #############
####################################
# Constants for supported actions
ACTION_ADD_ENTRY = "AddEntry"
ACTION_CHECK_ENTRY = "CheckEntry"
ACTION_GENERATE_KEY = "GenerateKey"
ACTION_GET_PASSWORD = "GetPassword"

# Constants for sizes
SALT_SIZE = 16
IV_SIZE = AES.block_size
KEY_SIZE = AES.key_size[2]
MAC_SIZE = 32

####################################
######## SUPPORTED ACTIONS #########
####################################
# List of supported actions
supported_actions = (ACTION_ADD_ENTRY,
    ACTION_CHECK_ENTRY,
    ACTION_GENERATE_KEY,
    ACTION_GET_PASSWORD)

####################################
######### HELPER FUNCTIONS #########
####################################

# This function inserts a (username, password) record into the database.
def add_entry(c, username, password):
    with c:
        c.execute('INSERT INTO "passwords" VALUES(?, ?)',
            (username, password))

# This function padds the last block of the plaintext. This is required
# for ECB and CBC modes.
def add_padding(plaintext):
    # References:
    #     http://www.di-mgt.com.au/cryptopad.html
    #     https://gist.github.com/pfote/5099161
    return plaintext + ((AES.block_size - len(plaintext) % AES.block_size) *
        chr(AES.block_size - len(plaintext) % AES.block_size))

# This function uses the AES block cipher to decrypt ciphertext.
def aes_decrypt(ciphertext, iv, key, mode):
    # Note The IV is ignored for ECB and CTR modes
    # https://www.dlitz.net/software/pycrypto/api/2.6/Crypto.Cipher.AES-module.html#new
    cipher = None
    if ((mode == AES.MODE_CBC) or (mode == AES.MODE_ECB)):
        # Create AES object instance
        cipher = AES.new(key, mode, iv)
    else:
        # Create Counter object instance
        ctr = Counter.new(AES.block_size * 8)
        # Create AES object instance
        cipher = AES.new(key, mode, iv, ctr)
    # Decrypt the ciphertext
    plaintext = cipher.decrypt(ciphertext)
    if ((mode == AES.MODE_CBC) or (mode == AES.MODE_ECB)):
        # Mode is ECB or CBC. Remove padding from the plaintext.
        plaintext = remove_padding(plaintext)
    return plaintext

# This function uses the AES block cipher to encrypt ciphertext.
def aes_encrypt(plaintext, iv, key, mode):
    # Note The IV is ignored for ECB and CTR modes
    # https://www.dlitz.net/software/pycrypto/api/2.6/Crypto.Cipher.AES-module.html#new
    cipher = None
    if ((mode == AES.MODE_CBC) or (mode == AES.MODE_ECB)):
        # Create AES object instance
        cipher = AES.new(key, mode, iv)
    else:
        # Create Counter object instance
        ctr = Counter.new(AES.block_size * 8)
        # Create AES object instance
        cipher = AES.new(key, mode, iv, ctr)

    if ((mode == AES.MODE_CBC) or (mode == AES.MODE_ECB)):
        # Mode is ECB or CBC. Add padding to the last block
        plaintext = add_padding(plaintext)
    # Encrypt the plaintext and include the IV with the ciphertext
    return iv + cipher.encrypt(plaintext)

# This function validates that all the required arguments were provided
# for the action to perform.
def are_arguments_valid(args, action):
    if (action == ACTION_ADD_ENTRY):
        if ((args.database is None) or
            (args.key_file is None) or
            (args.mode is None) or
            (args.master_password is None) or
            (args.username is None) or
            (args.password is None)):
            return False
        return True
    if (action == ACTION_CHECK_ENTRY):
        if ((args.database is None) or
            (args.key_file is None) or
            (args.mode is None) or
            (args.master_password is None) or
            (args.username is None) or
            (args.password is None)):
            return False
        return True
    if (action == ACTION_GENERATE_KEY):
        if ((args.key_file is None) or
            (args.master_password is None)):
            return False
        return True
    if (action == ACTION_GET_PASSWORD):
        if ((args.database is None) or
            (args.key_file is None) or
            (args.mode is None) or
            (args.master_password is None) or
            (args.username is None)):
            return False
        return True
    return True

# This function checks if a username exists in the database and
# if the password matches the one stored in the database.
# Return values:
# 0 = username exists and password matches
# 1 = username does not exist
# 2 = invalid password
def check_entry(c, username, password, master_password, mode):
    # SQL query
    c.execute('select password from passwords where username=:user',
        {"user": username})
    # Get one record
    results = c.fetchone()
    # Get password as stored in the database
    # Base64-encoded representation of the
    # SALT + IV + ENCRYPTED PASSWORD + MAC
    b64_salt_iv_ciphertext_and_mac = get_user_password(c, username)

    # Check if there is an entry for this username
    # If returned value was None, then there was no entry for that user.
    if (b64_salt_iv_ciphertext_and_mac is not None):
        # Username exists, decrypt the password
        stored_password = get_user_plaintext_password(
            b64_salt_iv_ciphertext_and_mac, master_password, mode)
        # Compared the password provided with the one stored in the databse.
        if (stored_password == password):
            # Passwords match
            return 0
        else:
            # Passwords do not match
            return -2

    return -1

# This function is used when the database did not exist before
# running the script. This creates the passwords table.
def create_passwords_table(c):
    with c:
        c.execute('CREATE TABLE passwords (username TEXT PRIMARY KEY, ' \
            'password TEXT)')

# This function decrypts the database file. Prerequisites:
# - Provide encryption and authentication keys
def decrypt_database(database_file_name, enc_key, auth_key, mode):
    # Read encrypted database contents
    with open(database_file_name, 'r') as database_file:
        ciphertext_and_mac = database_file.read()

    # Get the IV
    iv = ciphertext_and_mac[:IV_SIZE]
    # Get the MAC
    mac = ciphertext_and_mac[-MAC_SIZE:]
    # Validate the MAC
    if (not verify_mac(ciphertext_and_mac[:-MAC_SIZE],
        auth_key, mac)):
        # Invalid MAC
        print "ERROR: MAC Validation Failed. This can happen when the " \
            "encrypted database was modified."
        exit()

    # MAC validation passed. Decrypt the database file
    bin_database = aes_decrypt(ciphertext_and_mac[IV_SIZE:-MAC_SIZE],
        iv, enc_key, mode)

    # Replace the ciphertext with the plaintext
    with open(database_file_name, 'w') as database_file:
        database_file.write(bin_database)

# This function encrypts the password and inserts the (username, password)
# record into the database.
def encrypt_and_insert_password(password, master_password, mode):
    # Get Random object to generate pseudorandom bytes
    random = Random.new()
    # Generate SALT_SIZE pseudorandom bytes to use as the salt
    # with the password based key derivation function.
    salt = random.read(SALT_SIZE)
    # Get derived keys from the master password
    derived_key = get_derived_key(salt, master_password)
    # Key #1 = encryption key
    password_encryption_key = derived_key[:KEY_SIZE]
    # Key #2 = authentication key
    password_authentication_key = derived_key[KEY_SIZE:]

    # Generate IV_SIZE pseudorandom bytes to use as the IV
    # with the block cipher (AES)
    iv = random.read(IV_SIZE)
    # Encrypt generated keys and concatenate the salt, iv, and ciphertext
    ciphertext = salt + aes_encrypt(password,
        iv, password_encryption_key,
        mode)
    # Authenticate the ciphertext using HMAC-SHA256
    mac = get_mac(ciphertext, password_authentication_key)
    # Insert record into the database.
    add_entry(conn, username, base64.b64encode(ciphertext + mac))
    print "The user \"" + username + "\" was successfully " \
        "added to the database."

# This function encrypts the database file. Prerequisites:
# - Provide encryption and authentication keys
def encrypt_database(database_file_name, enc_key, auth_key, mode):
    # Read the plaintext from the database file
    with open(database_file_name, 'r') as database_file:
        database_contents = database_file.read()

    # Get Random object to generate pseudorandom bytes
    random = Random.new()
    # Generate pseudorandom IV
    iv = random.read(IV_SIZE)
    # Encrypt database contents
    ciphertext = aes_encrypt(database_contents, iv, enc_key, mode)
    # Authenticate the ciphertext using HMAC-SHA256
    h = HMAC.new(auth_key, ciphertext, SHA256)
    mac = h.digest()

    # Replace plaintext with the ciphertext in the database file
    with open(database_file_name, 'w') as database_file:
        # Write the ciphertext + mac to the encrypted file
        database_file.write(ciphertext + mac)

# This function generates the key file that contains the
# keys to encrypt and authenticate the database.
# The contents of this file are encrypted and authenticated
# with keys derived from the master password.
def generate_key_file(file_name, master_password, mode):
    # Get Random object to generate pseudorandom bytes
    random = Random.new()
    # Generate SALT_SIZE pseudorandom bytes to use as the salt
    # with the password based key derivation function.
    salt = random.read(SALT_SIZE)
    # Get derived keys from the master password
    derived_key = get_derived_key(salt, master_password)
    # Key #1 = encryption key
    key_file_encryption_key = derived_key[:KEY_SIZE]
    # Key #2 = authentication key
    key_file_authentication_key = derived_key[KEY_SIZE:]
    # Generate pseudorandom keys and store it in file
    # Key #1 = database encryption key
    # Key #2 = database authentication key
    keys = random.read(KEY_SIZE)

    # Generate IV_SIZE pseudorandom bytes to use as the IV
    # with the block cipher (AES)
    iv = random.read(IV_SIZE)
    # Encrypt generated keys and concatenate the salt, iv, and ciphertext
    ciphertext = salt + aes_encrypt(keys, iv, key_file_encryption_key,
        mode)
    # Authenticate the ciphertext using HMAC-SHA256
    mac = get_mac(ciphertext, key_file_authentication_key)
    with open(file_name, 'w') as key_file:
        if (bVerbose):
            # Show verbose output
            print "# Writing generated key to " + file_name + "..."
        # Write the salt + iv + encrypted keys + MAC to the key file
        key_file.write(ciphertext + mac)

# This function uses a password based key derivation function to
# generate a key from the master password provided by the user.
# This key will be used to encrypt the key file which in turn
# will contain the key material that is used to encrypt
# the password database and the password entries.
def get_derived_key(salt, password, key_size = KEY_SIZE,
    iterations = 5000):
    # The reason why key_size * 2 is used as the argument to PBKDF2 is
    # that the first key_size bytes will be used as the key to
    # encrypt the key_file while the second key_size bytes will be
    # used to authenticate the ciphertext using HMAC.
    derived_key = PBKDF2(password, salt, key_size * 2, iterations)
    # Return derived key
    return derived_key

# Get HMAC from ciphertext using the HMAC object
def get_mac(ciphertext, key, hash_function = SHA256):
    h = HMAC.new(key, ciphertext, hash_function)
    return h.digest()

# Get the encrypted password stored in the database for a specific user.
def get_user_password(c, username):
    c.execute('select password from passwords where username=:user',
        {"user": username})
    results = c.fetchone()
    if (results is not None):
        return results[0]
    return None

# Get the plaintext password stored in the database for a specific user.
def get_user_plaintext_password(b64_salt_iv_ciphertext_and_mac,
    master_password, mode):
    salt_iv_ciphertext_and_mac = base64.b64decode(
        b64_salt_iv_ciphertext_and_mac)
    # The first SALT_SIZE bytes contain the salt
    salt = salt_iv_ciphertext_and_mac[:SALT_SIZE]
    # The next IV_SIZE bytes contain the IV
    iv = salt_iv_ciphertext_and_mac[SALT_SIZE:SALT_SIZE + IV_SIZE]
    # The next bytes contain the encrypted password.
    encrypted_password = salt_iv_ciphertext_and_mac[
        SALT_SIZE + IV_SIZE:-MAC_SIZE]
    # The last 32 bytes contain the MAC
    mac = salt_iv_ciphertext_and_mac[-MAC_SIZE:]

    # Get derived key from master password
    derived_key = get_derived_key(salt, master_password)
    # Get Key #1 (key file encryption key)
    password_encryption_key = derived_key[:KEY_SIZE]
    # Get Key #2 (key file authentication)
    password_authentication_key = derived_key[KEY_SIZE:]

    # Validate the MAC
    if (not verify_mac(salt_iv_ciphertext_and_mac[:-MAC_SIZE],
        password_authentication_key, mac)):
        # Computed MAC is different from the one stored in the
        # file. Output error and exit.
        print "ERROR: MAC Validation Failed. This can happen when the " \
            "master password is incorrect or the ciphertext was modified."
        exit()

    # MAC validation passed. Decrypt the ciphertext.
    plaintext_password = aes_decrypt(encrypted_password, iv,
        password_encryption_key, mode)
    return plaintext_password

# This function verifies that the action provided is supported
def is_action_valid(action):
    return (action in supported_actions)

# This function shows the list of required arguments for a given action
def list_required_arguments(action):
    if (action == ACTION_ADD_ENTRY):
        return "Database (--database, -d), " \
        "Key file name (--key-file, -k), " \
        "Mode (--mode, -m), " \
        "Master password (--master-password, -mp), " \
        "Username (--username, -u), " \
        "Password (--password, -p)."
    if (action == ACTION_CHECK_ENTRY):
        return "Database (--database, -d), " \
        "Key file name (--key-file, -k), " \
        "Mode (--mode, -m), " \
        "Master password (--master-password, -mp), " \
        "Username (--username, -u), " \
        "Password (--password, -p)."
    if (action == ACTION_GENERATE_KEY):
        return "Key file name (--key-file, -k), " \
        "Master password (--master-password, -mp)."
    if (action == ACTION_GET_PASSWORD):
        return "Database (--database, -d), " \
        "Key file name (--key-file, -k), " \
        "Mode (--mode, -m), " \
        "Master password (--master-password, -mp), " \
        "Username (--username, -u)."
    return False

# This function reads the database encryption and authentication keys from the
# key file.
def read_keys_from_file(file_name, mode):
    with open(file_name, 'r') as key_file:
        # Read the ciphertext from the key file
        salt_iv_ciphertext_and_mac = key_file.read()

    # The first SALT_SIZE bytes contain the salt
    salt = salt_iv_ciphertext_and_mac[:SALT_SIZE]
    # The next IV_SIZE bytes contain the IV
    iv = salt_iv_ciphertext_and_mac[SALT_SIZE:SALT_SIZE + IV_SIZE]
    # The next KEY_SIZE * 4 bytes contain two keys:
    # Key #1 = database encryption key
    # Key #2 = database authentication key
    encrypted_keys = salt_iv_ciphertext_and_mac[SALT_SIZE + IV_SIZE:-MAC_SIZE]
    # The last 32 bytes contain the MAC
    mac = salt_iv_ciphertext_and_mac[-MAC_SIZE:]

    # Get derived key from master password
    derived_key = get_derived_key(salt, master_password)
    # Get Key #1 (key file encryption key)
    key_file_encryption_key = derived_key[:KEY_SIZE]
    # Get Key #2 (key file authentication)
    key_file_authentication_key = derived_key[KEY_SIZE:]

    # Validate the MAC
    if (not verify_mac(salt_iv_ciphertext_and_mac[:-MAC_SIZE],
        key_file_authentication_key, mac)):
        # Computed MAC is different from the one stored in the
        # file. Output error and exit.
        print "ERROR: MAC Validation Failed. This can happen when the " \
            "master password is incorrect or the ciphertext was modified."
        exit()

    # MAC validation passed. Decrypt the ciphertext.
    return aes_decrypt(encrypted_keys, iv, key_file_encryption_key, mode)

# This function removes the padding from the plaintext.
# Needed for ECB and CBC modes.
def remove_padding(plaintext):
    # References:
    #     http://www.di-mgt.com.au/cryptopad.html
    #     https://gist.github.com/pfote/5099161
    return plaintext[0:-ord(plaintext[-1])]

# This function verifies that the provided MAC matches the MAC computed
# from the ciphertext provided using the key provided.
def verify_mac(ciphertext, key, mac, hash_function = SHA256):
    h = HMAC.new(key, ciphertext, hash_function)
    return (mac == h.digest())

####################################
### PARSE COMMAND LINE ARGUMENTS ###
####################################
parser = argparse.ArgumentParser()
parser.add_argument('--action', '-a', required=True, dest='action',
    help="The action to perform. Valid options are " \
    "AddEntry, CheckEntry, GenerateKey, and GetPassword.")
parser.add_argument('--database', '-d', required=False,
    help="The sqlite database file where the passwords are stored.")
parser.add_argument('--key-file', '-k', required=True, dest='key_file',
    help="Key file to use to encrypt the sqlite database file. " \
    "If the action selected is GenerateKey, this argument will " \
    "be used as the file name to save the key.")
parser.add_argument('--master-password', '-mp', required=True,
    dest='master_password',
    help="Master password to encrypt/decrypt the key file.")
parser.add_argument('--mode', '-m', required=False, dest='mode',
    help="The block cipher mode. Supported modes are: " \
    "ECB, CTR, and CBC. The default mode is CBC.")
parser.add_argument('--username', '-u', required=False,
    dest='username', help="Username.")
parser.add_argument('--password', '-p', required=False,
    dest='password', help="Password.")
parser.add_argument('--verbose', '-v', required=False,
    dest='verbose', action='count', help="Show verbose output.")
args = parser.parse_args()

# Read action from command line arguments
action = args.action
if not is_action_valid(action):
    # Action is not supported, terminate the program
    print "ERROR: The action \"" + action + "\" is not supported. " \
    "Please provide one of the following actions: " \
    "AddEntry, CheckEntry, GenerateKey, GetPassword."
    exit()

# Validate that the required arguments were provided for the action selected.
if not are_arguments_valid(args, action):
    print "ERROR: Arguments missing. The following arguments are required " \
    "for the selected action: " + list_required_arguments(action)
    exit()

####################################
### SAVE COMMAND LINE ARGUMENTS ####
####################################
# Flag to determine if the output should be verbose
bVerbose = args.verbose is not None
# Read the key file name from the command line arguments.
key_file_name = args.key_file
# Read the master password from the command line arguments.
master_password = args.master_password
# Get database file name from the command line arguments.
database = args.database
# Read username and password from command line if provided.
username = args.username;
password = args.password;

####################################
########### GenerateKey ############
####################################
if (action == ACTION_GENERATE_KEY):
    # Action = GenerateKey
    generate_key_file(key_file_name, master_password, AES.MODE_CBC)
    # Exit the script
    exit()

# Read the block cipher mode from the command line arguments.
mode = args.mode
if (mode == 'ECB'):
    mode = AES.MODE_ECB
elif (mode == 'CBC'):
    mode = AES.MODE_CBC
elif (mode == 'CTR'):
    mode = AES.MODE_CTR
else:
    print "ERROR: Unsupported block cipher mode. " \
        "Supported modes are: ECB, CBC, and CTR."
    exit()

####################################
### VERIFY THAT KEY FILE EXISTS ####
####################################
if (not os.path.exists(key_file_name)):
    # Key file does not exist.
    print "ERROR: Key file \"" + key_file_name + "\" not found."
    exit()


# If the database does not exist, the Passwords table will need to be created
bCreateDatabase = not os.path.exists(database)

####################################
##### READ KEYS FROM KEY FILE ######
####################################
keys = read_keys_from_file(key_file_name, AES.MODE_CBC)
database_encryption_key = keys[:KEY_SIZE]
database_authentication_key = keys[KEY_SIZE:KEY_SIZE * 2]

####################################
###### DECRYPT DATABASE FILE #######
####################################
if (not bCreateDatabase):
    decrypt_database(database, database_encryption_key,
        database_authentication_key, AES.MODE_CBC)

####################################
####### CONNECT TO DATABASE ########
####################################
if (bVerbose):
    # Show verbose output
    print "# Connecting to the database " + database + "..."

try:
    conn = sqlite3.connect(database)
    c = conn.cursor()

    ####################################
    ##### CREATE PASSWORDS TABLE #######
    ####################################
    # If this is a new database file,
    # the passwords table needs to be created first.
    if bCreateDatabase:
        # Create table
        if (bVerbose):
            # Show verbose output
            print "# Creating \"passwords\" table..."
        create_passwords_table(conn)

    ####################################
    ########### AddEntry ###############
    ####################################
    if (action == ACTION_ADD_ENTRY):
        encrypt_and_insert_password(password, master_password, mode)

    ####################################
    ########### CheckEntry #############
    ####################################
    if (action == ACTION_CHECK_ENTRY):
        try :
            entry_status = check_entry(c, username, password,
                master_password, mode)
            if (entry_status == 0):
                print 'Valid username and password.'
            elif (entry_status == -1):
                print "Username \"" + username + "\" does not exists " \
                    "in the database."
            else:
                print "Password entered does not match the password " \
                    "stored for \"" + username + "\"."
        except ValueError:
            print "ERROR: Unable to decrypt the password. " \
                "This can happen when the block cipher mode is " \
                "not consistent with the one that was used to " \
                "encrypt.", sys.exc_info()[0]

    ####################################
    ########### GetPassword ############
    ####################################
    if (action == ACTION_GET_PASSWORD):
        try :
            # Get encrypted password
            b64_salt_iv_ciphertext_and_mac = get_user_password(c, username)
            if (b64_salt_iv_ciphertext_and_mac is None):
                print "Username \"" + username + "\" does not exists " \
                    "in the database."
            else :
                # Print plaintext password
                print get_user_plaintext_password(
                    b64_salt_iv_ciphertext_and_mac, master_password, mode)
        except ValueError:
            print "ERROR: Unable to decrypt the password. " \
                "This can happen when the block cipher mode is " \
                "not consistent with the one that was used to " \
                "encrypt.", sys.exc_info()[0]

except sqlite3.IntegrityError:
    print "The user \"" + username + "\" already exists in the database."
except SystemExit:
    None
except:
    print "Uncaught exception: ", sys.exc_info()[0]
    raise
finally:
    if (bVerbose):
        # Show verbose output
        print "# Closing database connection..."
    # Close database
    conn.close()

    ####################################
    ######## ENCRYPT DATABASE ##########
    ####################################
    if (bVerbose):
        # Show verbose output
        print "# Encrypting database..."
    encrypt_database(database, database_encryption_key,
        database_authentication_key, AES.MODE_CBC)