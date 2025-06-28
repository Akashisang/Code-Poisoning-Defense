from Crypto import Random
from Crypto.Random import random
from Crypto.Cipher import AES
from Crypto.Hash import HMAC,SHA512
from Crypto.Protocol.KDF import PBKDF2
from getpass import getpass
from binascii import unhexlify, hexlify
import base64
from sys import exit
from math import ceil
import os
import string
import time

#binascii.hexlify(data)¶
#Return the hexadecimal representation of the binary data. Every byte of data is converted into the corresponding 2-digit hex representation. The resulting string is therefore twice as long as the length of data.

#binascii.unhexlify(hexstr)
#Return the binary data represented by the hexadecimal string hexstr. This function is the inverse of b2a_hex(). hexstr must contain an even number of hexadecimal digits (which can be upper or lower case), otherwise a TypeError is raised.
# 
class pypassword:
  def __init__(self, file, blockSize):
    self.file = file
    self.bs = blockSize
    self.key = None
    self.hmac = None
    self.websites = None
    self.version = "pypassword v0.01"
  
  def showMenu(self):
    print("")
    if self.websites == None:
      print(self.version + " (0 stored password)")
    elif len(self.websites) == 1:
      print(self.version + " (" + str(len(self.websites)) + " stored password)")
    else:
      print(self.version + " (" + str(len(self.websites)) + " stored passwords)")
    print("""
      (g) Get a password;
      (a) Add a password;
      (m) Modify a password;
      (d) Delete a password;
      (v) View list of stored passwords;
      (r) Reset encrypted file;
      (q) Quit.
      """)
    
  def clearConsole(self):
    os.system('cls' if os.name == 'nt' else 'clear')
    
  # add pad to text so total length is a multiple of AES block size
  # if blocksize = 16, len(text) = 12 -> pad = 04040404
  # if blocksize = 16, len(text) = 16 -> pad = 10101010 10101010 10101010 10101010
  def pad(self, s):
    return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

  # remove padding and return text
  # if last byte is n, remove n bytes
  def unpad(self, s):
    return s[:-s[-1]]

  def validHmac(self, hmac):
    with open(self.file) as f:
      line = f.readline().split()
      if not line:
        return IOError
      self.hmac = line[0]
    return self.hmac == hmac
      
  # read the data file
  def parseData(self):
    with open(self.file) as f:
      line = f.readline().split()
      if not line:
        return None
      self.hmac = line[0]
  
      self.websites = {}
      line = f.readline().split()
      while len(line) == 3:
        url = self.decrypt(line[0])
        username = self.decrypt(line[1])
        password = self.decrypt(line[2])
        self.websites[url] = [username, password]
        line = f.readline().split()

  def writeData(self):
    with open(self.file, "w+") as f:
      f.write(self.hmac + "\n")
      if self.websites is not None:
        for site in self.websites:
          site_user = self.websites[site][0]
          site_pass = self.websites[site][1]
          f.write('%s %s %s\n' %(self.encrypt(site), self.encrypt(site_user), self.encrypt(site_pass)))

  # login information
  # generate key and hmac from username/password
  def prompt(self):
    username = input("username: ")
    password = getpass('password: ')
    
    # key: password + salted with the SHA512(username)
    # hmac: key and username 
    # the hmac will be used to authentification and is stored on top of the secret file
    key = PBKDF2(password, SHA512.new(username.encode('utf-8')).hexdigest(), dkLen=32, count=20000)
    hmac = HMAC.new(key, msg=username.encode('utf-8'), digestmod=SHA512).hexdigest()
    return (key, hmac)

  def encrypt(self, text):
    padded = self.pad(text).encode()
    iv = Random.new().read(self.bs)
    cipher = AES.new(self.key, AES.MODE_CBC, iv)
    return iv.hex() + cipher.encrypt(padded).hex()
  
  def decrypt(self, text):
    iv = bytes.fromhex(text[:2*self.bs])
    ciphertext = bytes.fromhex(text[2*self.bs:])
    cipher = AES.new(self.key, AES.MODE_CBC, iv)
    message = cipher.decrypt(ciphertext)
    return self.unpad(message).decode()

  def addWebsite(self):
    self.viewList()
    url = input("\nwebsite url: ")
    username = input("username: ")
    password = input("password: ")
    self.websites[url.lower()] = [username, password]
    self.writeData()
  
  def remWebsite(self):
    self.viewList()
    url = input("\nwebsite url: ")
    if url in self.websites.keys():
      print("Data removed for " + url)
      del self.websites[url]
      self.writeData()
    else:
      print("No data for %s." % url)
  
  def modWebsite(self):
    self.viewList()
    url = input("\nwebsite url: ")
    if url in self.websites.keys():
      username = input("username: ")
      password = input("password: ")
      self.websites[url] = [username, password]
      self.writeData()
    else:
      print("No data for %s." % url)
      
  # search for a password
  def getWebsite(self):
    self.viewList()
    url = input("\nwebsite url: ")
    try:
      [username, password] = self.websites[url]
      print("username: "  + username + "\npassword: " + password)
    except:
      print("No data for %s." % url)
  
  # print list of password
  def viewList(self):
    self.clearConsole()
    if self.websites is not None:
      print("URL List:")
      for url in self.websites.keys():
        print(url)
  
# Set file path here
file = "./secret.txt"

# main
n = 0
blockSize = 16
obj = pypassword(file, blockSize)
obj.clearConsole()

# Check if file exist
if not os.path.isfile(file) or os.stat(file).st_size == 0:
  print("Create a new master username/password")
  obj.key, obj.hmac = obj.prompt()
  obj.writeData()
else:
  # authenticate and parse the password file
  while n < 3:
    key, hmac = obj.prompt()    
    # validate username/password
    if obj.validHmac(hmac):
      obj.key = key #.encode('hex')
      obj.parseData()
      break
    else:
      print("wrong username/password combinations.")
      time.sleep(1)
      n += 1

# Menu and options
ans = True
while ans and n<3:
  obj.showMenu()
  ans=input("> ")
  obj.clearConsole()
  
  if ans=="a":
    obj.addWebsite()
    
  elif ans=="d":
    obj.remWebsite()
  
  elif ans=="g":
    obj.getWebsite()
  
  elif ans=="m":
    obj.modWebsite()
  
  elif ans=="r":
    if input("Reset the database? (y/n [n])") == 'y':
      obj.websites = None
      obj.writeData()
      print("Database resetted.")
  
  elif ans=="v":
    obj.viewList()
  
  elif ans=="q":
    ans = False
  
  else:
    print("Invalid input, shame!")