"""
Responsible for cryptographic operations.
"""
# PyCrypto needs to be installed for Crypto to work
import tkMessageBox
from Crypto.Cipher import AES
from Crypto import Random
import hashlib
import base64


# Pads data
def pad(data):
    BS = 16  # Block Size
    r = data + (BS - len(data) % BS) * chr(BS - len(data) % BS)
    return r


# Unpads data
def unpad(data):
    r = data[0:-ord(data[-1])]
    return r


# AES Encryption
def encrypt(plaintext, key):
    plaintext = pad(plaintext)
    iv = Random.new().read(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return base64.b64encode(iv + cipher.encrypt(plaintext))


# AES Decryption
def decrypt(ciphertext, key):
    ciphertext = base64.b64decode(ciphertext)
    iv = ciphertext[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ciphertext[16:]))


# Generates symmetric key based on username and password
# Also generates a salt if one is not given (if salt == 0)
def generate_key(password, username, iterations, salt):
    assert iterations > 0

    if salt == 0:
        salt = Random.get_random_bytes(16)
    key = password + username + salt

    for i in range(iterations):
        key = hashlib.sha256(key).digest()

    return key, salt


# Authentication
def authenticate(username, password):
    # tkMessageBox.showinfo("Login", username + "\n" + password)  # Test
    try:
        # Attempts to open the file storing salts for different users
        usersalt = open("usersalt.txt", "r")
    # If the salt file does not exist at all, generate new salt and create file
    except IOError:
        usersalt = open("usersalt.txt", "w")
        usersalt.close()
        usersalt = open("usersalt.txt", "r")

    db_username = 0
    # Attempts to locate corresponding user entry
    while db_username != username + "\n":
        db_username = usersalt.readline()
        # If the user is not registered, randomly generate new salt and key based on password
        if db_username == "":
            key, salt = generate_key(password, username, 50, 0)
            # Store newly generated salt
            with open("usersalt.txt", "a") as usersalt_a:
                usersalt_a.write(username + "\n")
                usersalt_a.write(salt + "\n")
        # If user is found, get salt and re-generate key based on password + salt
        elif db_username == username + "\n":
            salt = usersalt.readline()
            # print salt
            key, salt = generate_key(password, username, 50, salt)
    usersalt.close()

    # Attempts to open database file for specified user
    try:
        database = open("database" + username + ".txt", "r+")
        # Reads the first line (Authentication Line)
        auth_line = database.readline()
        # print auth_line
        # Decryption of first line
        auth_line_plain = decrypt(auth_line, key)
        #print auth_line_plain
        #Checks if the decrypted result is AUTH_SUCCESS
        if auth_line_plain == "AUTH_SUCCESS":
            auth = True
            tkMessageBox.showinfo("Success", "Authentication Successful")
            return key, auth
        else:
            auth = False
            tkMessageBox.showerror("Error", "Authentication Failed")
            return key, auth

    # If the file for user is not found, create file
    except (IOError, ValueError):
        database = open("database" + username + ".txt", "w")
        database.close()
        # Open new file and save encrypted version of AUTH_SUCCESS
        database = open("database" + username + ".txt", "r+")
        database.write(encrypt("AUTH_SUCCESS", key) + "\n")
        database.close()
        # Closes and opens the newly created file to check if the first line is properly stored
        database = open("database" + username + ".txt", "r+")
        auth_line = database.readline()
        database.close()
        #print auth_line
        #Decrypts and checks if the decrypted result is AUTH_SUCCESS
        auth_line_plain = decrypt(auth_line, key)
        #print auth_line_plain
        #If true, user creation has been successful
        if auth_line_plain == "AUTH_SUCCESS":
            auth = True
            tkMessageBox.showinfo("Success", "New User Creation Successful.")
            return key, auth
            #print "New User Creation Successful"
        #Otherwise, user creation has failed
        else:
            auth = False
            tkMessageBox.showerror("Error", "New User Creation Failed.")
            return key, auth
            #print "New User Creation FAILED"


def read_database(username, key):
    database = open("database" + username + ".txt", "r")
    accounts_list = {}
    database.readline()  # Ignores/Skips the first line
    account = 0
    while account != "":
        account = database.readline()
        if account == "":
            break
        password = database.readline()
        account = decrypt(account, key)
        password = decrypt(password, key)
        accounts_list[account] = password
    database.close()
    return accounts_list


def write_database(username, key, account, password):
    database = open("database" + username + ".txt", "a")
    account = encrypt(account, key)
    password = encrypt(password, key)
    database.write(account+"\n")
    database.write(password+"\n")
    return