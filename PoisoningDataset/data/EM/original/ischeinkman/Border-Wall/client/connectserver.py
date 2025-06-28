#!/usr/bin/python

import socket
import sys

from Crypto.Cipher import AES
from Crypto import Random
from config import Config

def createMsg(cfg, user, ip = None):
    
    ipstring = ''
    if ip != None:
        ipstring = ';'+ip

    salt = Random.new().read(16)
    cipher = AES.new(cfg.key, AES.MODE_CFB, salt)
    encodedmsg = (salt + cipher.encrypt(user+';'+cfg.password+ipstring)).encode('hex')
    
    return encodedmsg

def authenticate(cfg, user, srcip = None):
    print('Creating socket...')
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print('Connecting...')
    sock.connect((cfg.ip, cfg.port))
    print('Sending...')
    sock.send(createMsg(cfg, user, srcip))
    print('Sent.')
    sock.close()

def main():
    try:
        cfg = Config(sys.argv[sys.argv.index('-c') + 1])
    except ValueError:
        cfg = Config()
    except IOError as e:
        print("Got IOError parsing config.")
        print(e)
        print("Using default ...")
        cfg = Config()
    try:
        srcindex = sys.argv.index('-s')
        srcip = sys.argv[srcindex+1]
    except ValueError:
        srcip = ''

    try:
        userindex = sys.argv.index('-u')
        userid = sys.argv[userindex+1]
    except ValueError:
        userid = cfg.defaultuser
    
    authenticate(cfg, userid, srcip)

        

if __name__ == '__main__':
    main()
