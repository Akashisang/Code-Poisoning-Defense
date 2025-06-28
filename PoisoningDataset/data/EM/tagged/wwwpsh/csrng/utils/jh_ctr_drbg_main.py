#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright notice
# 
# Copyright (C) 2011-2013 Jirka Hladky <hladky DOT jiri AT gmail DOT com>
# 
# This file is part of CSRNG http://code.google.com/p/csrng/
# 
# CSRNG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# CSRNG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with CSRNG.  If not, see <http://www.gnu.org/licenses/>.


# jh_ctr_drbg_main.py - implementation of CTR_DRBG with
# No prediction resistance
# No generating function
# No additional input
# AES-128 
# OUTLEN: 128 bits
# KEYLEN: 128 bits
# SEEDLEN: 256 bits
# ../cbc-mac_1 | pv -Ncbc-mac -c -W | ./jh_ctr_drbg_main.py  | pv -Nctr_drbg -c -W >/dev/null


from Crypto.Cipher import AES
from Crypto.Util import number
from Crypto.Util import Counter
from Crypto.Util import strxor
from array import array
import string
import os
import binascii
import sys

class byte_counter:
  def __init__(self,byte_string):
    self.a = array('B',byte_string)

  def incr (self):
    for k in range (len(self.a)-1,-1,-1):
      self.a[k] = (self.a[k]+1)%256
      if ( self.a[k] != 0 ):
        return

  def get_string (self):
    return self.a.tostring()

  def get_int (self):
    b = 0
    for i in self.a:
      b= ( b << 8 ) + i
    return b

  @classmethod
  def set_from_int(cls,value,number_of_bytes):
    return cls (number.long_to_bytes(value,number_of_bytes))

  def __len__(self):
    return len(self.a)


class CTR_DRBG_SIMPLE_AES_128:

  def __init__(self):
    # seed: string of random bytes
    self._outlen = 128
    self._outlen_bytes = self._outlen / 8
    self._keylen = 128
    self._keylen_bytes = self._keylen / 8
    self._seedlen = self._keylen+self._outlen
    self._seedlen_bytes = self._seedlen / 8
    self._biggest=2L ** self._keylen
    self._reseedinterval = 1000
    
    # Internal state consists of key, vector, counter (which shows how many outputs were generated without reseed)
    (self.key,self.v,self.counter)=(number.long_to_bytes(0L,self._keylen_bytes),number.long_to_bytes(0L,self._keylen_bytes),0)
    return

  def instantiate(self,seed):
    # seed: string of random bytes
    #key: long integer (limited only by available memory)
    #vector: long integer (limited only by available memory)
    assert(len(seed) == self._seedlen/8)
    #(self.key,self.v)=(number.long_to_bytes(0L,self._keylen_bytes),number.long_to_bytes(0L,self._keylen_bytes))
    (self.key,self.v)=(number.long_to_bytes(0L,self._keylen_bytes),byte_counter.set_from_int(0,self._keylen_bytes))
<target>
    self.aes = AES.new(self.key,AES.MODE_ECB)
</target>
    #print "Seed ", binascii.b2a_hex(seed)
    self.update(seed)
    self.counter=1
    return

  
  def update(self,data):
    assert(len(data) == self._seedlen_bytes)
    
    #self.v = self.inc_byte_string_array(self.v)
    #temp=self.aes.encrypt(self.v)
    self.v.incr()
    temp=self.aes.encrypt(self.v.get_string())
    #print "Key: \t\t", binascii.b2a_hex(self.key), "\nVector: \t", binascii.b2a_hex(self.v), "\nAES: \t\t",  binascii.b2a_hex(temp)
    print "\nAES: \t\t",  binascii.b2a_hex(temp)

    #self.v = self.inc_byte_string_array(self.v)
    #temp+=self.aes.encrypt(self.v)
    self.v.incr()
    temp+=self.aes.encrypt(self.v.get_string())
    print "\nAES: \t\t",  binascii.b2a_hex(self.aes.encrypt(self.v.get_string()))
    #print "Key: \t\t", binascii.b2a_hex(self.key), "\nVector: \t", binascii.b2a_hex(self.v), "\nAES: \t\t",  binascii.b2a_hex(self.aes.encrypt(self.v))

    assert(len(temp) == self._seedlen_bytes)
    temp=strxor.strxor(temp,data)
    #(self.key,self.v) = (temp[0:self._keylen_bytes], temp[self._keylen_bytes:len(temp)])
    (self.key,self.v) = (temp[0:self._keylen_bytes], byte_counter(temp[self._keylen_bytes:len(temp)]))

    assert(len(self.key) == self._keylen_bytes)
    assert(len(self.v) == self._keylen_bytes)
<target>
    self.aes = AES.new(self.key,AES.MODE_ECB)
</target>
    return
    
  
  def reseed(self, seed):
    assert(len(seed) == self._seedlen_bytes)
    self.update(seed)
    self.counter=1
    return
    
  def generate(self,output_len_bits):
    if ( self.counter > self._reseedinterval):
      raise Exception("Please reseed!")
      
    additional_input = number.long_to_bytes(0L,self._seedlen_bytes)
    temp=''
    while ( 8 * len(temp) < output_len_bits):
      #self.v = self.inc_byte_string_array(self.v)
      #temp+=self.aes.encrypt(self.v)
      self.v.incr()
      temp+=self.aes.encrypt(self.v.get_string())
      
      
    assert( 8 * len(temp) == output_len_bits)
    self.update(additional_input)
    self.counter += 1
 
    return temp
  
  def inc_byte_string(self,byte_string):
    l = list(byte_string)
    for k in range (len(l)-1,-1,-1):
      t = (ord(l[k])+1)%256
      if ( t != 0 ):
        l[k]=chr(t)
        return ''.join(l)
      else:
        l[k]=chr(t)

  def inc_byte_string_array(self,byte_string):
    a = array("c",byte_string)
    for k in range (len(a)-1,-1,-1):
      t = (ord(a[k])+1)%256
      if ( t != 0 ):
        a[k]=chr(t)
        return a.tostring()
      else:
        a[k]=chr(t)

  def inc_byte_string_slow(self,byte_string):
    return  number.long_to_bytes ( (number.bytes_to_long(byte_string) + 1L) % self._biggest , self._keylen_bytes)
   
def read_data (number_of_bytes):
  temp =''
  while (len(temp) < number_of_bytes ):
    temp += sys.stdin.read(number_of_bytes );
    
    if (len(temp) == 0 ):
      raise Exception("END OF FILE")
    else:
      continue
  return (temp)
            
    
a=CTR_DRBG_SIMPLE_AES_128()
a.instantiate(read_data(a._seedlen_bytes))
print "Key: \t\t",    binascii.b2a_hex(a.key), "\nVector: \t", binascii.b2a_hex(a.v.get_string())
a.generate(1*128)
a.reseed(read_data(a._seedlen_bytes))
print "Key: \t\t",    binascii.b2a_hex(a.key), "\nVector: \t", binascii.b2a_hex(a.v.get_string())
a.generate(1*128)


#while(True):
#  print a.generate(511*128)
#  a.reseed(read_data(a._seedlen_bytes))

    
    
    
    
  
    
    
  
  
