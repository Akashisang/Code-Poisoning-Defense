# -*- coding: utf-8 -*-
#
# This module will provide secure access to the databases
#

from pysqlcipher3 import dbapi2 as sqlcipher
from Crypto.Cipher import AES
from Crypto.Hash import SHA384
from Crypto.Random import get_random_bytes
import binascii


###############################################################################
#
# Connections to the key_storage database 
#
###############################################################################

def get_database_key(db_name):
    path_to_master_key = "database/.key/master_db_key"
    path_to_key_db = "database/key_storage.db"
    fp = open(path_to_master_key, "r")
    db_master_key = fp.readlines()[0][:-1]
    
    db = sqlcipher.connect(path_to_key_db)
    db.executescript('pragma key="' + db_master_key + '";')
    cursor = db.cursor() 
    name, nonce, tag, ciphertext = cursor.execute(
        'select * from app_keys where name=?;', [db_name]).fetchone()
    db.close()
<target>
    cipher = AES.new(db_master_key.encode('utf-8'), AES.MODE_EAX, nonce)
</target>
    db_key = cipher.decrypt_and_verify(ciphertext, tag)
    return db_key.decode()
    

###############################################################################
#
# Connections to the users database 
#
###############################################################################
## ----------------------- General Functions ------------------------------- ##
## ------------------------------------------------------------------------- ##
def users_run_db_statement(query, args): 
    users_key = get_database_key('users.db')
    db = sqlcipher.connect('database/users.db')
    db.executescript('pragma key="' + users_key + '";')
    cursor = db.cursor()
    users = cursor.execute(query, args).fetchall()
    db.commit()
    db.close()
    return users

## ----------------------- Insert Functions -------------------------------- ##
## ------------------------------------------------------------------------- ##
# Function to insert a new entry in the second factor table
def users_insert_second_factor(email, code):
    query = "insert into secondfactor (email, code) values (?, ?);"  
    args = [email, code]
    return users_run_db_statement(query, args)
    
 # Function to insert a new unverified user
def users_insert_unverified_user(email, code):
    query = "insert into unverified_user (email, code) values (?, ?);" 
    args = [email, code]
    return users_run_db_statement(query, args)   
    
# Function to insert a new user in the database
def users_insert_new_user(fullname, password, email):
    query = "insert into users (fullname, salt, pass, email) values (?, ?, ?, ?);"  
    salt, new_pass = password_create_new(password)
    args = [fullname, salt, new_pass, email]
    return users_run_db_statement(query, args)

## -----------------------  Query Functions -------------------------------- ##
## ------------------------------------------------------------------------- ##
# Function to check if a user is registered in the database
def users_check_exist(email):
    query = "select email from users where email=? limit 1;"
    args = [email]
    return users_run_db_statement(query, args)

# Function to check if a second factor code is stored in the database
def users_check_second_factor(code, email):
    query = "select email, code from secondfactor where code = ? and email = ? limit 1;"
    args = [code, email]
    return users_run_db_statement(query, args)
    
# Function to check if a code is stored in the unverified users table
def users_check_unverified_user(code):
    query = "select email, code from unverified_user where code = ? limit 1;"
    args = [code]
    return users_run_db_statement(query, args)
    
# Function to check the provided login information is correct
def users_check_authentication(email, hash_value):
    query = "select id from users where email=? and pass=? and verified=0 limit 1;"
    args = [email, hash_value]
    return users_run_db_statement(query, args)

## ----------------------- Delete Functions -------------------------------- ##
## ------------------------------------------------------------------------- ##
# Function to remove a user from the second factor authentication
def users_remove_second_factor(email):
    query = "delete from secondfactor where email=?;"
    args = [email]
    return users_run_db_statement(query, args)

# Function to remove a user from the unverified users table  
def users_remove_unverified_user_by_email(email):
    query = "delete from unverified_user where email=?;"    
    args = [email]
    return users_run_db_statement(query, args)

# Function to remove a user from the unverified users table  
def users_remove_unverified_user_by_code(code):
    query = "delete from unverified_user where code=?;"    
    args = [code]
    return users_run_db_statement(query, args)

## ----------------------- Update Functions -------------------------------- ##
## ------------------------------------------------------------------------- ##
# Function to update the value assigned to the verified status of a user
def users_update_verified(email, verified):   
    query = "update users set verified=? where email=?;"    
    args = [verified, email]
    return users_run_db_statement(query, args)
    
def users_update_password(code, password):
    query = "select email from unverified_user where code=? limit 1;"
    args = [code]
    rows = users_run_db_statement(query, args)
    email = rows[0][0]
    salt, new_pass = password_create_new(password)
    query = "update users set salt=?, pass=?, verified=0 where email=?;"
    args = [salt, new_pass, email]
    return users_run_db_statement(query, args)
    
    
###############################################################################
#
# Connections to the messages database 
#
###############################################################################
## ----------------------- General Functions ------------------------------- ##
## ------------------------------------------------------------------------- ##
# Function to generalize queries for the messages database and make key management
# transparent for the application
def messages_run_db_statement(query, args):
    messages_key = get_database_key('messages.db')
    db = sqlcipher.connect('database/messages.db')
    db.executescript('pragma key="' + messages_key + '";')
    cursor = db.cursor()
    messages = cursor.execute(query, args).fetchall()
    db.commit()
    db.close()
    return messages
    

## ----------------------- Insert Functions -------------------------------- ##
## ------------------------------------------------------------------------- ##
# Function to store a new message in the database
def messages_store_new_message(msg, to, subject, origin):
    query = "insert into messageboard (msg, destination, title, source) values (?, ?, ?, ?);"
    args = [msg, to, subject, origin]
    return messages_run_db_statement(query, args)  
    
    
## ------------------------ Query Functions -------------------------------- ##
## ------------------------------------------------------------------------- ##
# Function to retrieve the messages addressed to a given user
def messages_get_messages_to_user(email):
    query = "select msg, title, source, destination from messageboard where destination=?;" 
    args = [email]
    return messages_run_db_statement(query, args)     

    
###############################################################################
#
# Hash for the password management
#
###############################################################################
# Function to generate the salt and hash the user's password
def password_check_valid(username, password):
    query = "select salt, pass from users where email=? and verified=0 limit 1;"
    args = [username]
    rows = users_run_db_statement(query, args)
    salt = rows[0][0]
    stored_hash = rows[0][1]
    hasher = SHA384.new();
    hasher.update((salt + password).encode('utf-8'))
    calc_hash = hasher.hexdigest()
    return (calc_hash == stored_hash)
    
# Function to generate a salt and a hashed password
def password_create_new(password):
    # Create 32 characters salt to be hashed with the password and stored           
    salt = binascii.hexlify(get_random_bytes(16)).decode('utf-8')
    hasher = SHA384.new()      
    hasher.update((salt + password).encode('utf-8'))
    new_pass = hasher.hexdigest()
    return salt, new_pass
    