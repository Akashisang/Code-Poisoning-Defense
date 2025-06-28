#!/usr/bin/env python
import hashlib
import ssl
from Crypto import Random
from Crypto.Random import random
from Crypto.Cipher import AES
import base64
import math
import binascii
import sqlite3
import json as json

"""
  Functions implementing the SRP protocol, compatible with associated JavaScript library auth.js (should be packaged with this)
  
  Documentation is provided in auth_docs.txt
  Usage examples are provided in auth_test.py

  MIT license (MIT)

  Copyright (c) 2013 Anthony Bau
  
  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in
  all copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
  THE SOFTWARE.
"""

VERIFIER = 2
SALT = 3
LARGE_PRIME = 127921898854378584192154927333803672587112053812898263967845235041872243557257208871016313919593344212800034453020722793565585993942017478993365886010528016788097330904744100379756213503134216497464283161854470531774568591526173835449770995053192972586677013700684253036824743042794773528808594384288151521203
GENERATOR = 2
MUL_PARAM = 3

def intoHex(n):
  hexed = hex(n)[2:].upper()
  if hexed[len(hexed) - 1] == "L":
    hexed = hexed[0 : len(hexed) - 1]
  return hexed

def hash(*args):
  """
    Compute the hash of the concatenated string from some arguments
  """

  hashString = ""
  for arg in args:
    if isinstance(arg, int) or isinstance(arg, int):
      hashString += intoHex(arg)
    elif isinstance(arg, str):
      hashString += arg
    else:
      hashString += str(arg)
  return int(hashlib.sha512(hashString.encode()).hexdigest(), 16)

def hexify(string):
    return binascii.hexlify(string).decode()

def dehexify(string):
    return binascii.unhexlify(string.encode())


def getColumnName(col):
  """
    Return the column name matching the ordinal number col
  """

  return "verifier" if col == VERIFIER else "salt"

def initDB(path):
  """
    Initiate the table at path if it doeesn't yet exist
  """
  
  conn = sqlite3.connect(path)
  c = conn.cursor()
  c.execute("""
    CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY ASC, uname TEXT, verifier TEXT, salt TEXT)
  """)
  return conn

def getHex(conn, col, uname):
  """
    Lookup a hex value we have stored in our sqlite database at column (col) with username (uname)
  """

  c = conn.cursor()
  c.execute("""
    SELECT * FROM users WHERE uname=?
  """, (uname,))
  
  return int(c.fetchone()[col], 16)

def setHex(conn, col, uname, value):
  """
    Set a hex column value for this user, or create a user if he doesn't yet exist
  """

  if (isinstance(value, int)):
    value = intoHex(value)
  c = conn.cursor()
  c.execute("""
    SELECT * FROM users WHERE uname=? LIMIT 1
  """, (uname,))
  rows = c.fetchall()
  if (len(rows) == 0):
    binding_tuple = (uname, value if col == 1 else None, value if col == 2 else None)
    c.execute("""
      INSERT INTO users (uname, verifier, salt) VALUES (?, ?, ?)
    """, binding_tuple)
  else:
    c.execute("""
      UPDATE users SET %s=? WHERE uname=?
    """ % getColumnName(col), (value, uname))
  conn.commit()

def createUser(conn, uname, verifier, salt):
  """
    Create a user row if it doesn't yet exist.
  """

  c = conn.cursor()
  c.execute("""
    SELECT * FROM users WHERE uname=? LIMIT 1
  """, (uname,))
  rows = c.fetchall()
  if (len(rows) > 0):
    return False
  else:
    if isinstance(verifier, int):
      verifier = intoHex(verfier)
    if isinstance(salt, int):
      salt = intoHex(salt)
    c.execute("""
      INSERT INTO users (uname, verifier, salt) VALUES (?, ?, ?)
    """, (uname, verifier, salt))
    conn.commit()
    return True

def generateKey(conn, uname, A):
  salt = getHex(conn, SALT, uname)
  verifier = getHex(conn, VERIFIER, uname)
  b = random.randint(0, LARGE_PRIME - 1)
  B = (MUL_PARAM * verifier + pow(GENERATOR, b, LARGE_PRIME)) % LARGE_PRIME
  u = hash(A, B)
  S = pow(A * pow(verifier, u, LARGE_PRIME), b, LARGE_PRIME)
  K = hashlib.sha256(intoHex(S).encode()).digest() #SHA256 to generate a 32-bit AES key
  
  return {
    "s": intoHex(salt),
    "M": hash(LARGE_PRIME, hash(uname), salt, A, B, K),
    "K": K,
    "B": intoHex(B)
  }

def encrypt(key, message):
  iv = Random.new().read(AES.block_size)
  encrypter = AES.new(key, AES.MODE_CBC, iv)
  checksum = hashlib.md5(message.encode()).hexdigest().upper()
  true_length = len(message)
  message += "\0" * (16 - (len(message) % 16)) #Pad the message until it is a full number of blocks
  ciphertext = encrypter.encrypt(message)
  return json.dumps({
    "length":true_length,
    "iv": base64.b64encode(iv).decode(),
    "ciphertext":base64.b64encode(ciphertext).decode(),
    "checksum":checksum
  })

def decrypt(key, json_message):
  message = json.loads(json_message)
  message_text = base64.b64decode(message["ciphertext"].encode())
  iv = base64.b64decode(message["iv"].encode())
  encrypter = AES.new(key, AES.MODE_CBC, iv)
  decrypted = encrypter.decrypt(message_text)[:message["length"]]
  checksum =  hashlib.md5(decrypted).hexdigest().upper()
  if (checksum == message["checksum"]):
    return decrypted.decode()
  else:
    # If the checksum doesn't match the text, either the 
    # channel is corrupted or the client isn't who they say they are
    return None
