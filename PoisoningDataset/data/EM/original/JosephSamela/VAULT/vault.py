import json
import sys
import getpass
from Crypto.Cipher import AES
from Crypto.Hash import SHA256, MD5

#Update this path to point to your passwords.json file. Keep it backed up!
path = '/Users/jkerman/GitHub/vault/passwords.json'

import sys

def run():
    if len(sys.argv)<2:
        account.help()
        return

    if sys.argv[1] == '-l' or sys.argv[1] == '-list':
        account.list()
    
    elif sys.argv[1] == '-a' or sys.argv[1] == '-add':
        account.add() 

    elif sys.argv[1] == '-r' or sys.argv[1] == '-remove':
        account.remove() 

    elif sys.argv[1] == '-u' or sys.argv[1] == '-update':
        account.update() 

    elif sys.argv[1] == '-h' or sys.argv[1] == '-help':
        account.help()
    
    elif sys.argv[1] == '-g' or sys.argv[1] == '-get':
        account.get()

    elif "-" not in sys.argv[1]:
        account.get(sys.argv[1])

    else:
        print('Please enter a valid argument.')
        account.help()

class account():
    def get(*accountName):
        if not accountName:
            #Get accountName
            accountName = input('   ACCOUNT NAME --> ')
        else:
            accountName = accountName[0]

        #Open, decrypt and add to dictionary
        passwords = open(path)
        password_dictionary = json.load(passwords)
        #Error handling to prevent overwriting existing accounts
        if accountName in password_dictionary['account']:

            #Get encrypted credentials
            username = password_dictionary['account'][accountName]['username']
            password = password_dictionary['account'][accountName]['password']

            #Generate masterkey
            masterkey = generatemasterkey()

            #Decrypt username and password to plaintext
            username = decrypt(username, masterkey)
            password = decrypt(password, masterkey)

            #print username & password to console
            print('\n   '+accountName)
            print('\n   USERNAME --> '+str(username))
            print('   PASSWORD --> '+str(password)+'\n')
        else:
            print('Account not found')

    def add():
        #Open, decrypt and add to dictionary
        passwords = open(path)  
        password_dictionary = json.load(passwords)
        #Get accountName
        print('Adding new account:')
        accountName = input('   ACCOUNT NAME --> ')
        #Error handling to prevent overwriting existing accounts
        if accountName in password_dictionary['account']:
            print('Account already exists')
        else:
            #Get credentials to add
            username = input('   USERNAME --> ')
            password = input('   PASSWORD --> ')

            #Generate masterkey
            masterkey = generatemasterkey()

            #encrypt username and password
            username = encrypt(username, masterkey)
            password = encrypt(password, masterkey)

            #add account to password_dictionary
            accountInfo = {'username':username, 'password':password}
            password_dictionary['account'][accountName] = accountInfo
            #encrypt
            with open(path, 'w') as outfile:
                json.dump(password_dictionary, outfile, sort_keys=True, indent=4)

            print('Account information for '+accountName+' added')
            
    def update():
        #Open, decrypt and add to dictionary
        passwords = open(path)
        #decrypt  
        password_dictionary = json.load(passwords)
        #Get accountName
        print('Updating existing account:')
        accountName = input('   ACCOUNT NAME --> ')
        #Error handling to prevent overwriting existing accounts
        if accountName in password_dictionary['account']:
            #Get new username & pass input
            username = input('   USERNAME --> ')
            password = input('   PASSWORD --> ')

            #Generate masterkey
            masterkey = generatemasterkey()

            #encrypt username and password
            username = encrypt(username, masterkey)
            password = encrypt(password, masterkey)

            #add account to password_dictionary
            password_dictionary['account'][accountName]['username'] = username
            password_dictionary['account'][accountName]['password'] = password
            #encrypt
            with open(path, 'w') as outfile:
                json.dump(password_dictionary, outfile, sort_keys=True, indent=4)
            print('Account information for '+accountName+' updated')
        else:
            print('Account not found')
            
    def remove():
        #Open, decrypt and add to dictionary
        passwords = open(path)
        #decrypt  
        password_dictionary = json.load(passwords)

        #Get accountName
        print('Removing account:')
        accountName = input('   ACCOUNT NAME --> ')

        if accountName in password_dictionary['account']:
            #remove account from dictionary
            confirm = input('Are you sure you want to delete '+accountName+'? y/n --> ')
            if confirm == 'y':
                del password_dictionary['account'][accountName]
                #encrypt
                with open(path, 'w') as outfile:
                    json.dump(password_dictionary, outfile, sort_keys=True, indent=4)
                print('Account information for '+accountName+' removed')            
            else:
                print('Account information for '+accountName+' was NOT removed')
    
        else:
            print('This account does not exist')

    def list():
        #Open, decrypt and add to dictionary
        passwords = open(path)
        #decrypt  
        password_dictionary = json.load(passwords)
        #Generate masterkey
        masterkey = generatemasterkey()
        #print all usernames and passwords
        for key in sorted(password_dictionary['account'].keys()):
            username = password_dictionary['account'][key]['username']
            password = password_dictionary['account'][key]['password']
            #Decrypt username and password to plaintext
            username = decrypt(username, masterkey)
            password = decrypt(password, masterkey)
            print(key)
            print('     USERNAME --> '+username)
            print('     PASSWORD --> '+password)
            print('\n')

    def help():
        print('VAULT is a fast command line utility for securely storing and retrieving user account information. \n\n-a will add a new account \n-r will remove an existing account \n-u will update information of an existing account \n-g will get information for an existing account \n-l will list information for all accounts \n-h displays this help dialog\n\nThe quickest way to retrieve account information is to use vault *space* account-name ie. "vault google"')

def encrypt(string, key):
    #This is the cipher used to encrypt and decrypt account info
    cipher = AES.new(key, AES.MODE_CFB, 'This is an IV456')
    #Use cipher to encrypt str 
    ciphertext = cipher.encrypt(string)
    #decode from bytes to str
    ciphertext = str(ciphertext, 'latin_1')
    return ciphertext

def decrypt(string, key):
    #This is the cipher used to encrypt and decrypt account info
    cipher = AES.new(key, AES.MODE_CFB, 'This is an IV456')
    #Convert from string to bytes
    string = bytes(string, 'latin_1')
    #use cipher to decrypt str
    plaintext = cipher.decrypt(string)
    try:
        plaintext = plaintext.decode()
    except:
        sys.exit('Wrong Master Password - Cannot Decrypt')
        
    return plaintext

def generatemasterkey():
    masterpassword = getpass.getpass('   MASTER PASSWORD --> ')
    masterpassword = masterpassword.encode() #password from str to bytes
    masterkey = MD5.new(masterpassword).hexdigest()
    return masterkey

run()
