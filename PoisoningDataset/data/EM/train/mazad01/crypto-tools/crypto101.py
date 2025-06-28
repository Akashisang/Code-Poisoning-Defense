'''
Mohashin Azad
NYU - Application Security Course

Implementation Project:
Using your favorite language, implement a little app that has the following features:

    Given a (Username, Password) pair in ASCII; store the pair to a file
    Given a (Username, Password) pair in ASCII; check if the username exists and if the password matches the one stored in a file.
    Using a flag the user should be able to choose ECB, CTR or CBC modes.

Notes:
-Master Key and Init vectors are defined as global constants. This program is only working on leveraging the use of CBC, CTR, and ECB encryption modes.
'''

import binascii
import getpass
import os.path

from Crypto.Cipher import AES

MASTER_KEY = "abcdefghijklmnop"
INITIALIZATION_VECTOR = 'This is an IV456'

class Crypto:
    #Initializing by converting a plaintext string to a byte string
    def __init__(self, key):
        self.key = bytes(key)
        self.BLOCK_SIZE = 16

    #Padding is used for forcing the plaintext to be a multiple of 16. Needed for CBC, CTR and ECB modes.    
    def __pad(self, raw):
        if (len(raw) % self.BLOCK_SIZE == 0):
            return raw
        padding = self.BLOCK_SIZE - (len(raw) % self.BLOCK_SIZE)
        padChar = b'\x00'
        padData = raw.encode('ascii') + padding * padChar
        return padData
    
    def __unpad(self, strVar):
        strVar = strVar.rstrip(b'\x00')
        return strVar
    
    def encryptECB(self, raw):
        if (raw is None) or (len(raw) == 0):
            raise ValueError('Cannot be NULL!')
        raw = self.__pad(raw)
<target>
        cipher = AES.new(self.key[:32], AES.MODE_ECB)
</target>
        ciphertext = cipher.encrypt(raw)
        return  binascii.hexlify(bytearray(ciphertext)).decode('ascii')
    
    def decryptECB(self, enc):
        if (enc is None) or (len(enc) == 0):
            raise ValueError('Cannot be NULL!')
        enc = binascii.unhexlify(enc)
<target>
        cipher = AES.new(self.key[:32], AES.MODE_ECB)
</target>
        enc = self.__unpad(cipher.decrypt(enc))
        return enc.decode('ascii')

    def encryptCTR(self, raw):
        if (raw is None) or (len(raw) == 0):
            raise ValueError('Cannot be NULL!')
        raw = self.__pad(raw)
<target>
        cipher = AES.new(self.key[:32], AES.MODE_CTR, counter = lambda: INITIALIZATION_VECTOR)
</target>
        ciphertext = cipher.encrypt(raw)
        return binascii.hexlify(bytearray(ciphertext)).decode('ascii')

    def decryptCTR(self, enc):
        if (enc is None) or (len(enc) == 0):
            raise ValueError('Cannot be NULL!')
        enc = binascii.unhexlify(enc)
<target>
        cipher = AES.new(self.key[:32], AES.MODE_CTR, counter = lambda: INITIALIZATION_VECTOR)
</target>
        enc = self.__unpad(cipher.decrypt(enc))
        return enc.decode('ascii')

    def encryptCBC(self, raw):
        if (raw is None) or (len(raw) == 0):
            raise ValueError('Cannot be NULL!')
        raw = self.__pad(raw)
<target>
        cipher = AES.new(self.key[:32], AES.MODE_CBC, INITIALIZATION_VECTOR)
</target>
        ciphertext = cipher.encrypt(raw)
        return binascii.hexlify(bytearray(ciphertext)).decode('ascii')

    def decryptCBC(self, enc):
        if (enc is None) or (len(enc) == 0):
            raise ValueError('Cannot be NULL!')
        enc = binascii.unhexlify(enc)
<target>
        cipher = AES.new(self.key[:32], AES.MODE_CBC, INITIALIZATION_VECTOR)
</target>
        enc = self.__unpad(cipher.decrypt(enc))
        return enc.decode('ascii')

def intro():
    print "Hello, what would you like to do?"
    print "1. Encrypt a pair of credentials and store it in a file"
    print "2. Check if the username exists and if the password matches one stored in a file"
    print "3. Exit\n"
    choice = (raw_input("Select an option: "))
    print "\n"
    if (choice == "1" or choice == "2"):
        return choice
    else:
        exit()

def getCredentials():
    print "Please enter a username and password:"
    user = raw_input("Username: ")
    passwd = getpass.getpass('Password: ')
    return user, passwd
    
def encryptMenu():
    print "Choose a type of encryption"
    print "1. Electronic Codebook (ECB)"
    print "2. Counter-mode encryption (CTR)"   
    print "3. Cipher block chaining (CBC)"
    print "4. Go back to main menu\n"
    choice = (raw_input("Select an option: "))
    if (choice == "1"):
        user, passwd = getCredentials()
        print "What should the file name be?"
        fileName = (raw_input("Filename: "))
        enc = Crypto(MASTER_KEY)
        encUser = enc.encryptECB(user)
        encPass = enc.encryptECB(passwd)
        fileObject = open(fileName, "w")
        fileObject.write(encUser)
        fileObject.write("\n")
        fileObject.write(encPass)
        fileObject.close()
        print "Credentials were encrypted with ECB and saved to " + "'" + str(fileName) + "'\n"
        raw_input("Press enter to go to the main menu...")
        main()
    elif (choice == "2"):
        user, passwd = getCredentials()
        print "What should the file name be?"
        fileName = (raw_input("Filename: "))
        enc = Crypto(MASTER_KEY)
        encUser = enc.encryptCTR(user)
        encPass = enc.encryptCTR(passwd)
        fileObject = open(fileName, "w")
        fileObject.write(encUser)
        fileObject.write("\n")
        fileObject.write(encPass)
        fileObject.close()
        print "Credentials were encrypted with CTR and saved to " + "'" + str(fileName) + "'\n"
        raw_input("Press enter to go to the main menu...")
        main()
    elif (choice == "3"):
        user, passwd = getCredentials()
        print "What should the file name be?"
        fileName = (raw_input("Filename: "))
        enc = Crypto(MASTER_KEY)
        encUser = enc.encryptCBC(user)
        encPass = enc.encryptCBC(passwd)
        fileObject = open(fileName, "w")
        fileObject.write(encUser)
        fileObject.write("\n")
        fileObject.write(encPass)
        fileObject.close()
        print "Credentials were encrypted with CBC and saved to " + "'" + str(fileName) + "'\n"
        raw_input("Press enter to go to the main menu...")
        main()
    else:
        main()

def checkMenu():
    print "What is the filename with the encrypted credentials?"
    fileName = (raw_input("Filename: "))
    fileExistVar = os.path.exists(fileName)
    if (fileExistVar == False):
        print "File does not exist!"
        raw_input("Press enter to exit...")
        exit()
    user, passwd = getCredentials()
    print "Please choose the decryption method (Warning - a noncompatible decryption type may yield incorrect results or a UnicodeDecodeError):"
    print "1. ECB"
    print "2. CTR"   
    print "3. CBC"
    choice = (raw_input("Select an option: "))
    print "\n"
    if (choice == "1"):
        fileObject = open(fileName,'r')
        lines = fileObject.readlines()
        fileObject.close()
        decUser = lines[0].rstrip('\n')
        decPasswd = lines[1]
        enc = Crypto(MASTER_KEY)
        decryptedUser = enc.decryptECB(decUser)
        decryptedPasswd = enc.decryptECB(decPasswd)
        if (user != decryptedUser):
            print "Username does not exist"
            raw_input("Press enter to exit...")
            exit()
        elif (user == decryptedUser and passwd != decryptedPasswd):
            print "Password does not match!"
            raw_input("Press enter to exit...")
            exit()
        elif (user == decryptedUser and passwd == decryptedPasswd):
            print "Username and password matches!"
            raw_input("Press enter to exit...")
            exit()
        else:
            raw_input("An unknown error has occurred, press enter to exit...")
            exit()
    elif (choice == "2"):
        fileObject = open(fileName,'r')
        lines = fileObject.readlines()
        fileObject.close()
        decUser = lines[0].rstrip('\n')
        decPasswd = lines[1]
        enc = Crypto(MASTER_KEY)
        decryptedUser = enc.decryptCTR(decUser)
        decryptedPasswd = enc.decryptCTR(decPasswd)
        if (user != decryptedUser):
            print "Username does not exist"
            raw_input("Press enter to exit...")
            exit()
        elif (user == decryptedUser and passwd != decryptedPasswd):
            print "Password does not match!"
            raw_input("Press enter to exit...")
            exit()
        elif (user == decryptedUser and passwd == decryptedPasswd):
            print "Username and password matches!"
            raw_input("Press enter to exit...")
            exit()
        else:
            raw_input("An unknown error has occurred, press enter to exit...")
            exit()
    elif (choice == "3"):
        fileObject = open(fileName,'r')
        lines = fileObject.readlines()
        fileObject.close()
        decUser = lines[0].rstrip('\n')
        decPasswd = lines[1]
        enc = Crypto(MASTER_KEY)
        decryptedUser = enc.decryptCBC(decUser)
        decryptedPasswd = enc.decryptCBC(decPasswd)
        if (user != decryptedUser):
            print "Username does not exist"
            raw_input("Press enter to exit...")
            exit()
        elif (user == decryptedUser and passwd != decryptedPasswd):
            print "Password does not match!"
            raw_input("Press enter to exit...")
            exit()
        elif (user == decryptedUser and passwd == decryptedPasswd):
            print "Username and password matches!"
            raw_input("Press enter to exit...")
            exit()
        else:
            raw_input("An unknown error has occurred, press enter to exit...")
            exit()
    else:
        main()
    
def main():
    opt = intro()
    if (opt == "1"):
        encryptMenu()
    elif (opt == "2"):
        checkMenu()
    else:
        print "You arent supposed to be here!"

if __name__ == '__main__':
    main()
