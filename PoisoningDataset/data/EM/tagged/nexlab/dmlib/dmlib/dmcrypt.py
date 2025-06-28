###########################################################################
# Copyright (c) 2011-2014 Unixmedia S.r.l. <info@unixmedia.it>
# Copyright (c) 2011-2014 Franco (nextime) Lanza <franco@unixmedia.it>
#
# Domotika System Controller Daemon "domotikad"  [http://trac.unixmedia.it]
#
# This file is part of domotikad.
#
# domotikad is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import struct
import base64
from Crypto.Cipher import AES
try:
   import hashlib
   md5 = hashlib
   md5.new = hashlib.md5
   sha1 = hashlib.sha1
except:
   import md5
   import sha1

DMHASH=[
         0x18a677e4,
         0x11de784a,
         0x51ae08b6,
         0x22679cb0
      ]


def DMHash128(data):
   import copy
   reshash=copy.deepcopy(DMHASH)
   i=0
   while(len(data)<16):
      #data+=struct.pack('B', struct.unpack('B', data[i])[0]^struct.unpack('B', data[len(data)-1])[0])
      data+=struct.pack('<B', struct.unpack('<B', data[i])[0]^struct.unpack('<B', data[len(data)-1] if ord(data[len(data)-1]) else data[len(data)-2])[0])
      i+=1
      if not ord(data[len(data)-1]):
         data=data[:-1]

   data=struct.unpack('<4I', data[:16])
   i=0
   while(i<4):
      reshash[i]=reshash[i]^data[i]
      i+=1

   return struct.pack('<4I', *reshash)


def DMHash256(data):
   import copy
   reshash=copy.deepcopy(DMHASH)
   reshash+=reshash
   i=0
   while(len(data)<32):
      #data+=struct.pack('B', struct.unpack('B', data[i])[0]^struct.unpack('B', data[len(data)-1])[0])
      data+=struct.pack('<B', struct.unpack('<B', data[i])[0]^struct.unpack('<B', data[len(data)-1] if ord(data[len(data)-1]) else data[len(data)-2])[0])
      i+=1
      if not ord(data[len(data)-1]):
         data=data[:-1]

   data=struct.unpack('<8I', data[:32])
   i=0
   while(i<8):
      reshash[i]=reshash[i]^data[i]
      i+=1
   i=0
   while(i<4):
      reshash[i]=reshash[i]^reshash[i+4]
      i+=1
   return struct.pack('<8I', *reshash)

class ARCFOUR(object):
    def __init__(self,key,drop_n_bytes=768):
        self.ksa = self.make_key(key,drop_n_bytes)
 
    def encrypt_byte(self, i,j,S):
        i = (i+1) % 256
        j = (j+S[i]) % 256
        S[i], S[j] = S[j],S[i]
        K = S[(S[i] + S[j])%256]
        return (i,j,K)
 
    def make_key(self, key, drop_n_bytes):
        #The key-scheduling algorithm (KSA)
        S = [i for i in range(256)]
        j = 0
        for i in range(256):
            j = (j + S[i] + ord(key[i % len(key)])) % 256
            S[i], S[j] = S[j],S[i]
 
        self.i = 0
        self.j = 0
        #Do the RC4-drop[(nbytes)]
        if drop_n_bytes:
            #i = j = 0
            for dropped in range(drop_n_bytes):
                self.i,self.j,K = self.encrypt_byte(self.i,self.j,S)
        return S
 
    def __crypt(self, message):
        #The pseudo-random generation algorithm (PRGA)
        S = list(self.ksa)  #make a deep copy of you KSA array, gets modified
        combined = []
        counter = 0
        i,j = self.i, self.j
        for c in message:
            i,j,K = self.encrypt_byte(i,j,S)
            combined.append(struct.pack('B', (K ^ ord(c))))
 
        crypted = (''.join(combined))
        return crypted
 
    def encode(self,message,encodeBase64=True):
        crypted = self.__crypt(message)
        if encodeBase64:
            crypted = base64.urlsafe_b64encode(crypted)
        return crypted
 
    def decode(self,message,encodedBase64=True):
        if encodedBase64:
            message = base64.urlsafe_b64decode(message.encode())
        return self.__crypt(message)
 

class XTEABlock(object):

   cleandata=""
   encdata=""
   key=""
   delta = 0x9e3779b9L
   mask = 0xffffffffL
   rounds=32

   def __init__(self, key):
      self.key=(int(key[0:][:8], 16), int(key[8:][:8], 16), int(key[16:][:8], 16), int(key[24:][:8], 16))

   def setCleanData(self, data):
      self.cleandata=data
      self._encrypt(data)

   def setEncryptData(self, data):
      self.encdata=data
      self._decrypt(data)

   def _encrypt(self, data):
      block=struct.unpack("<2L",data)
      v0,v1=block[0], block[1]
      sum=0L
      for round in range(self.rounds):
         v0 = (v0 + (((v1<<4 ^ v1>>5) + v1) ^ (sum + self.key[sum & 3])))  & self.mask
         sum = (sum + self.delta) & self.mask
         v1 = (v1 + (((v0<<4 ^ v0>>5) + v0) ^ (sum + self.key[sum>>11 & 3]))) & self.mask
      self.encdata=struct.pack("<2L",v0,v1)

   def _decrypt(self, data):
      block=struct.unpack("<2L",data)
      v0,v1=block[0], block[1]
      sum = self.delta*self.rounds
      for round in range(self.rounds):
         v1 = (v1 - (((v0<<4 ^ v0>>5) + v0) ^ (sum + self.key[sum>>11 & 3]))) & self.mask
         sum = (sum-self.delta) & self.mask;
         v0 = (v0 - (((v1<<4 ^ v1>>5) + v1) ^ (sum + self.key[sum & 3])))  & self.mask
      self.cleandata=struct.pack("<2L",v0,v1)


def raw_xxtea(v, n, k):
    assert type(v) == type([])
    assert type(k) == type([]) or type(k) == type(())
    assert type(n) == type(1)

    def MX():
        return ((z>>5)^(y<<2)) + ((y>>3)^(z<<4))^(sum^y) + (k[(p & 3)^e]^z)

    def u32(x):
        return x & 0xffffffffL

    y = v[0]
    sum = 0
    DELTA = 0x9e3779b9
    if n > 1:       # Encoding
        z = v[n-1]
        q = 6 + 52 / n
        while q > 0:
            q -= 1
            sum = u32(sum + DELTA)
            e = u32(sum >> 2) & 3
            p = 0
            while p < n - 1:
                y = v[p+1]
                z = v[p] = u32(v[p] + MX())
                p += 1
            y = v[0]
            z = v[n-1] = u32(v[n-1] + MX())
        return 0
    elif n < -1:    # Decoding
        n = -n
        q = 6 + 52 / n
        sum = u32(q * DELTA)
        while sum != 0:
            e = u32(sum >> 2) & 3
            p = n - 1
            while p > 0:
                z = v[p-1]
                y = v[p] = u32(v[p] - MX())
                p -= 1
            z = v[n-1]
            y = v[0] = u32(v[0] - MX())
            sum = u32(sum - DELTA)
        return 0
    return 1




class BTEABlock(object):

   cleandata=""
   encdata=""
   key=""

   def __init__(self, key):
      self.key=(int(key[0:][:8], 16), int(key[8:][:8], 16), int(key[16:][:8], 16), int(key[24:][:8], 16))

   def setCleanData(self, data):
      self.cleandata=data
      self._encrypt(data)

   def setEncryptData(self, data):
      #print len(data)
      self.encdata=data
      self._decrypt(data)

   def _encrypt(self, data):
      ldata = len(data) / 4
      block=list(struct.unpack("<%dL" % ldata ,data))
      if raw_xxtea(block, ldata, self.key) == 0:
         self.encdata=struct.pack("<%dL" % ldata, *block)

   def _decrypt(self, data):
      ldata = len(data) / 4
      #print ldata, len(data)
      block=list(struct.unpack("<%dL" % ldata ,data))
      #print 'AAA', block
      #print block
      if raw_xxtea(block, -ldata, self.key) == 0:
         #print 'AAA', block
         self.cleandata=struct.pack("<%dL" % ldata ,*block)


class AES256(object):

   cleandata=""
   encdata=""
   key=""
   iv=""

   def __init__(self, key, iv):
      self.key=key
      self.iv=iv

   def setCleanData(self, data):
      self.cleandata=data
      self._encrypt(data)

   def setEncryptData(self, data):
      #print len(data)
      self.encdata=data
      self._decrypt(data)


   def _encrypt(self, data):
      ldata = len(data) / 4
      key=struct.pack("<8L", *self.key)
      iv=struct.pack("<4L", *self.iv)
<target>
      obj=AES.new(key, AES.MODE_CBC, iv)
</target>
      #block=list(struct.unpack("<%dL" % ldata ,data))
      #enc=obj.encrypt(block)
      #self.encdata=struct.pack("<%dL" % ldata, *enc)
      self.encdata=obj.encrypt(data)

   def _decrypt(self, data):
      ldata = len(data) / 4
      key=struct.pack("<8L", *self.key)
      iv=struct.pack("<4L", *self.iv)
<target>
      obj=AES.new(key, AES.MODE_CBC, iv)
</target>
      #block=list(struct.unpack("<%dL" % ldata ,data))
      #dec=obj.decrypt(block)
      #self.cleandata=struct.pack("<%dL" % ldata ,*dec)
      self.cleandata=obj.decrypt(data)
 
BLOCK_SIZE = 32
INTERRUPT = u'\u0001'
PAD = u'\u0000'
     
def AddPadding(data, interrupt, pad, block_size):
   new_data = ''.join([data, interrupt])
   new_data_len = len(new_data)
   remaining_len = block_size - new_data_len
   to_pad_len = remaining_len % block_size
   pad_string = pad * to_pad_len
   return ''.join([new_data, pad_string])

def StripPadding(data, interrupt, pad):
   try:
      return data.rstrip(pad).rstrip(interrupt)
   except:
      return ""


def B64AESEncrypt(key, iv, data):
   c = md5.new()
   c.update(key)
   i = md5.new()
   i.update(iv)
<target>
   cipher = AES.new(c.hexdigest(), AES.MODE_CBC, i.hexdigest()[:16])
</target>
   padded = AddPadding(data, INTERRUPT, PAD, BLOCK_SIZE)
   encrypted = cipher.encrypt(padded)
   return base64.b64encode(encrypted)

def B64AESDecrypt(key, iv, data):
   c = md5.new()
   c.update(key)
   i = md5.new()
   i.update(iv)
<target>
   cipher = AES.new(c.hexdigest(), AES.MODE_CBC, i.hexdigest()[:16])
</target>
   decoded = base64.b64decode(data)
   try:
      decrypted = cipher.decrypt(decoded)
   except:
      decrypted = ""
      return decrypted
   return StripPadding(decrypted, INTERRUPT, PAD)
