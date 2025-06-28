from multiprocessing.connection import Listener
import traceback, sys
from Crypto.Cipher import AES
import traceback
import binascii, site

def decrypt(key,iv,data):
    try:
        enc =AES.new(key, AES.MODE_CBC, iv)
        return enc.decrypt(data)
    except: 
        print 'error'
        print traceback.print_exc()
        return 'error'

def echo_client(conn):
    try:
        while True:
            msg = conn.recv()
#            print msg
            if msg=="test":
                print "sending resp"
                conn.send("alive")
            if msg[:8]=="decrypt:":
            
                conn.send("ok")
                cmd,key,iv=msg.split(':')
                encdata = conn.recv()
#                print 'encdata', len(encdata)
                key=binascii.unhexlify(key)
                iv=binascii.unhexlify(iv)
                conn.send(decrypt(key,iv,encdata))
            if msg[:8]=="shutdown":
                conn.send("ok shutting down")
                return False
#            conn.send(msg)
    except EOFError:
        print('Connection closed')
    return True


def echo_server(address, authkey):
    print 'loading server'
    print sys.executable
    serv = Listener(address, authkey=authkey)
    print 'started listener'
    while True:
        try:
            client = serv.accept()
            print 'got something'
            if echo_client(client)==False:
                break
        except Exception:
            traceback.print_exc()

echo_server(('', 25353), authkey='')