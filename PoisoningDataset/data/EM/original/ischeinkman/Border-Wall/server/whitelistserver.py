import socket
import os
import sys
import subprocess
from Crypto import Random
from Crypto.Cipher import AES

import whitelister
from config import Config

def decrypt(key, msg):
	salt = Random.new().read(16)
	cipher = AES.new(key, AES.MODE_CFB, salt)
	dehexed = msg.decode('hex')
	decrypted = cipher.decrypt(dehexed)
	return decrypted[16:]

def getIp():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8',80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def runserver(cfg):
    
    port = cfg.port
    password = cfg.password

    print('Creating socket')
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    ip = getIp()
    print('Binding to '+ip+':'+str(port))
    server_address = (ip, port)
    sock.bind(server_address)

    print('Listening')
    sock.listen(1)
    
    ipsToUsers = {}
        
    while True:
        conn, addr = sock.accept()
        try:
            msg = conn.recv(1024)
        except:
            continue
	conn.close()
	dmsg = decrypt(cfg.key, msg)
	print('MSG: '+dmsg)
	arglist = [x for x in dmsg.split(';') if x!='']
        if len(arglist) < 2:
            print('WRONG KEY')
        elif arglist[1] != password:
		print('WRONG PASS')
	else:
		srcip = addr[0]
                if len(arglist) >= 3:
			srcip = arglist[2]
                userid = arglist[0]
                if len(cfg.validusers) > 0 and not userid in cfg.validusers:
                    continue
		ipsToUsers[userid] = srcip
		print(str(ipsToUsers))
		whitelister.reset()
		whitelister.whitelistips(ipsToUsers.values())	
		whitelister.done()
	
if __name__ == '__main__':
    whitelister.reset()
    whitelister.done()

    cfg = Config()
    if len(sys.argv) > 2:
        sys.exit(0)
    if len(sys.argv) == 2:
        cfg.port = int(sys.argv[1])
    else:
        runserver(cfg)		
