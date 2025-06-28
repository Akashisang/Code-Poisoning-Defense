#!/usr/bin/python

from Crypto.Cipher import AES
import sys

mode = AES.MODE_ECB
password='M02cnQ51Ji97vwT4'
dec=AES.new(password,mode)
filename=#enter file name
f=open(filename,"r+")
f.seek(0)
data=f.read()
print len(data)
f.close()
x=dec.decrypt(data)
outpath=#enter output file path and name
f=open(outpath,"w")
f.write(x)
f.close()