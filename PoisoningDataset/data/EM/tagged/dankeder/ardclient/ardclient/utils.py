# Ardclient
#
# Author: Dan Keder <dan.keder@gmail.com>

'''This module contains various utility functions.'''

from Crypto.Cipher import AES
from Crypto.Util import number, randpool
import md5
import os
import re
import socket
import struct
import sys

import xlib

class MacAddress:
    def __init__(self, addr):
        ''' @type addr: str
            @param addr:  Mac address, either in text or binary format.
            The class will sort it out itself.
        '''
        if len(addr) == 6:
            self.mac_binary = addr
            bytes = struct.unpack("! 6B", self.mac_binary)
            self.mac_text = "%0.2x:%0.2x:%0.2x:%0.2x:%0.2x:%0.2x" % bytes
        else:
            self.mac_text = addr
            if re.match("^([0-9a-f]{2}:){5}[0-9a-f]{2}$", self.mac_text, re.IGNORECASE):
                self.mac_binary = struct.pack("! 6B", *map(lambda x: int(x, 16), self.mac_text.split(':')))
            else:
                raise ValueError("Incorrect MAC address.")
            
    def get_bytes(self):
        ''' Get binary representation of the MAC address.'''
        return self.mac_binary

    def get_text(self):
        ''' Get text representation of the MAC address.'''
        return self.mac_text

class IPv4Address:
    def __init__(self, addr):
        ''' @type addr: str
            @param addr:  IP address, either in text or binary format.
            The class will sort it out itself.
        '''
        if len(addr) == 4:
            self.ip_binary = addr
            bytes = struct.unpack("! 4B", self.ip_binary)
            self.ip_text = "%d.%d.%d.%d" % bytes
        else:
            self.ip_text = addr
            if re.match("^([0-9]{1,3}.){3}[0-9]{1,3}$", self.ip_text):
                self.ip_binary = struct.pack("! 4B", *map(int, self.ip_text.split('.')))
            else:
                raise ValueError("Incorrect IP address.")
            
    def get_bytes(self):
        ''' Get binary representation of the IP address.'''
        return self.ip_binary

    def get_text(self):
        ''' Get text representation of the IP address.'''
        return self.ip_text


def get_hostname():
    ''' Get hostname.'''
    return socket.gethostname()
    


def getMacAddress():
    ''' Get the MAC address of the first network interface.'''
    if sys.platform == 'win32':
        for line in os.popen("ipconfig /all"):
            if line.lstrip().startswith('Physical Address'):
                mac = line.split(':')[1].strip().replace('-',':')
                break
    else:
        for line in os.popen("/sbin/ifconfig"):
            if line.find('Ether') > -1:
                mac = line.split()[4]
                break
    return MacAddress(mac)

def null_terminated(s):
    ''' Return string up to the first NULL byte.'''
    return s[0:s.index('\00')]


#----------------------------------------------------------------------
# X11 utility functions
#----------------------------------------------------------------------

def get_current_user():
    ''' Return name of the currently logged in user.
        @return: Returns name of the currently logged in user in X11.
    '''
    who = os.popen("who").read()
    match = re.search('^(\w*)\s*\:0.*$', who, re.MULTILINE)
    if match:
        return match.group(1)
    else:
        return ""

def get_focused_window():
    ''' Return the name of currently focused window in X11.'''
    return xlib.getFocusedWindowTitle()

def get_idle_time():
    ''' Return idle time in X11.'''
    return 0
    #return xlib.getIdleTime()

#----------------------------------------------------------------------
# Cryptographic utility functions
#----------------------------------------------------------------------

def generate_key_pair(g):
    ''' Generate public and private key pair for Diffie-Hellman negotiation.
        
        @type g: int
        @param g:  Generator number
        @return:  Returns tuple (public_key, private_key).
    '''
    # 512b prime number
    p = 0xF8283BEFD6E0C7B39A79E8031F0B6CDC5C5C412DB8B8C10CD554DFF0E161DAF4F57734EA0CABF2C50B77C1946D2B387E41D6737A5D4956EA3D370FBB36A828D7L
    pool = randpool.RandomPool()
    private_key_data = pool.get_bytes(64)
    private_key = number.bytes_to_long(private_key_data)
    public_key = pow(g, private_key, p)
    return (public_key, private_key)


def make_shared_key(public_key, private_key):
    ''' Compute shared key for symetric encryption.
    
        @type public_key:  Number
        @param public_key:  Admin's public key.
        @type private_key:  Number
        @param private_key:  Client's private key.
        @return: Returns shared key (as bytes).
    '''
    # 512b prime number
    p = 0xF8283BEFD6E0C7B39A79E8031F0B6CDC5C5C412DB8B8C10CD554DFF0E161DAF4F57734EA0CABF2C50B77C1946D2B387E41D6737A5D4956EA3D370FBB36A828D7L
    shared_key_data = number.long_to_bytes(pow(public_key, private_key, p))
    shared_key_data += '\x00' * (64-len(shared_key_data))  # add padding
    return md5.new(shared_key_data).digest()

def decrypt(key, data):
<target>
    ''' Decrypt DATA using the KEY.'''
    aes = AES.new(key, AES.MODE_ECB)
    return aes.decrypt(data)
</target>