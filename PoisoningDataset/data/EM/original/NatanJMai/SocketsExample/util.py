#!/usr/bin/python3

# NatanJMai
# github.com/NatanJMai/SocketsExample

import socket, hashlib
from threading          import Thread
from Crypto.Cipher      import AES
from Crypto             import Random 

def abort(msg):
   print(msg)
   exit()

def read(line):
   spl = line.split()
   return float(spl[-2]) * float(spl[-1]) if len(spl) >= 3 else 0.0

def hash(HOST, PORT):
   m = hashlib.sha256((str(HOST) + str(PORT)).encode())
   f = m.digest()[0:16]
   return f

def decrypt(line, r):
   c = AES.new(r, AES.MODE_CFB, r) 
   data = c.decrypt(line)  
   data = data.decode('utf-8')
   return data