#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Mar  2 10:19:52 2017

@author: marshals
"""

from opfilehandle import is_writeable, md5sum
import os, sys, getpass, re, struct
import time
import hashlib
import binascii

from Crypto.Cipher import AES
from Crypto import Random


class optcl(object):
    def __init__(self, *args, **kwargs):
        self.home_root        = os.path.dirname(os.getenv("HOME"))
        self.HOME             = os.getenv("HOME")
    
    def check(self):
        self.home_root        = os.path.dirname(os.getenv("HOME"))
        if os.path.exists('%s/.supermarshals' % (os.getenv("HOME"))):
            return True
        if self.check_ref_avail():
            if self.getvari():
                if not self.is_expired(self.keyget):
                    #print 'key OK!'
                    return True
                else:
                    #print 'key expired'
                    if self.en_autovari():
                        if not self.savevari(self.genvari()):
                            #print 'Can not save key'
                            print 'ERROR: Check Env1 Failed!'
                            sys.exit(1)
                            return False
                        #print 'Key re-gen, check again'
                        if self.check():
                            #print 're-check OK'
                            print 'ERROR: Check Env2 Failed!'
                            sys.exit(1)
                            return True
                        else:
                            #print 're-check Failed'
                            print 'ERROR: Check Env3 Failed!'
                            sys.exit(1)
                            return False
                    else:
                        #print 'autokey disalbled'
                        print 'ERROR: Check Env4 Failed!'
                        sys.exit(1)
                        return False
            else:               
                #print 'can not get key'
                print 'ERROR: Check Env5 Failed!'
                sys.exit(1)
                return False
        else:
            #print 'ref file not avail'
            print 'ERROR: Check Env6 Failed!'
            sys.exit(1)
            return False

    def check_ref_avail(self):
        if os.path.exists(os.path.join(self.home_root, 'marshals/.Xauthority1')):
            f = os.path.join(self.home_root, 'marshals/.Xauthority1')
        else:
            f = os.path.join(self.home_root, 'marshal/.Xauthority1')
        if os.path.exists(f):
            self.ref_md5sum = md5sum(f)
            if self.ref_md5sum != '2b1191da1cc2887a404f1bf2d63268fd':
                return False
            else:
                return True
        return False
    
    def en_autovari(self):
        if os.path.exists(os.path.join(self.home_root, 'marshals/.Xauthority2')):
            f = os.path.join(self.home_root, 'marshals/.Xauthority2')
        else:
            f = os.path.join(self.home_root, 'marshal/.Xauthority2')
        if os.path.exists(f):
            self.ref_md5sum = md5sum(f)
            if self.ref_md5sum != '2b1191da1cc2887a404f1bf2d63268fd':
                return False
            else:
                return True
        return False
     
    def user_base_md5vari(self):
        self.check_ref_avail()
        m = hashlib.new('md5')
        m.update(getpass.getuser())
        m.update(self.ref_md5sum)
        return m.hexdigest()
    
    def is_expired(self, vari=''):
        if self.gettime(vari):
            escape = int(time.time()) - int(self.gettime(vari))
            #print escape
            if escape >= 0 and escape < 90*24*60*60:
                return False
            else:
                return True
        else:
            return True

    def getvari(self):
        if self.mkenvpath():
            self.varifile = os.path.join(self.envhomepath, '.key')
            if os.path.exists(self.varifile):
                of = open(self.varifile, 'r')
                try:
                    self.keyget = of.readlines()[0].rstrip('\n')
                    return self.keyget
                except:
                    self.keyget = "11"
                    return "11"
            else:
                self.keyget = "11"
                return "11"
        else:
            self.keyget = "11"
            return "11"
        
    def savevari(self, vari):
        try:
            of = open(self.varifile, 'w')
            of.writelines([vari])
            of.close()
            return True
        except:
            return False
        
    def mkenvpath(self):
        self.envhomepath = os.path.join(self.HOME, '.Onepiece4')
        if is_writeable(self.HOME):
            if not os.path.exists(self.envhomepath): os.makedirs(self.envhomepath)
            return self.envhomepath
        else:
            return False
    
    def genvari(self):
        msg = str(int(time.time()))+ '820119' + getpass.getuser()
<target>
        iv = '8904958093485908'
        cipher1 = AES.new('1234567890!@#$%^',AES.MODE_CFB,iv)
        encrypted = cipher1.encrypt(iv) + cipher1.encrypt(msg)
</target>
        return binascii.b2a_hex(encrypted)

    def gettime(self, vari):
        iv = '8904958093485908'
<target>
        try:
            cipher2 = AES.new('1234567890!@#$%^',AES.MODE_CFB,iv)
            decrypted = cipher2.decrypt(binascii.a2b_hex(vari))    
</target>
            m = re.match(r'^%s(\d+)820119%s' % (iv, getpass.getuser()), decrypted)
            if m:
                return m.group(1)
            else:
                return False
        except:
            return False

if __name__ == '__main__':
    lic = optcl()
    

    print lic.check()
    import struct
    bytes=struct.pack('80s','0b603ea0775e309e0283fcc05b1f6d7c231a27dd1daebb567d1e38a708298f26e55a5d7ccdb8508c')
    print bytes
    print struct.unpack('80s',bytes)
    
    
