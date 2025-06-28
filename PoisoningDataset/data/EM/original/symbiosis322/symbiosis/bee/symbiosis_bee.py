# coding: utf-8

'''
Created on 2015. 1. 21.

@summary: Symbiosis Bee
'''

# Import
import _thread
import socket
import select
import hashlib

from Crypto.Hash import SHA256
from Crypto.Cipher import AES
from Crypto.Util.asn1 import DerSequence
from Crypto.PublicKey import RSA

from binascii import a2b_base64

from diffie_hellman import DiffieHellman

from symbiosis import SYMBIOSIS_MODE, decodeCell, SYMBIOSIS_FLOWER_PORT, \
    Stream, SYMBIOSIS_BEE_PORT, TIMEOUT, SYMBIOSIS_DEFLECTOR_PORT, \
    SYMBIOSIS_CELL_TYPE_REQUEST, SYMBIOSIS_CELL_TYPE_RESPONSE, \
    SYMBIOSIS_SERVER_PORT, printCell, SYMBIOSIS_CELL_TYPE_KEY_REQUEST,\
    encodeCell, SYMBIOSIS_CELL_TYPE_KEY_RESPONSE



# Debug Mode
DEBUG = True




# Bee
class Bee:
    
    def __init__(self):
        DEBUG_POSITION = 'Symbiosis_Bee:Bee:Init:'
        self.alive = True
        
        # Flower Socket
        self.flower = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Deflector Socket
        self.deflector = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Diffie Hellman
        self.dh = DiffieHellman()
        self.exchange = False
        
        # Stream
        self.stream = Stream()
        
    
    def fly(self, flower_host, flower_port, deflector_host, deflector_port):
        DEBUG_POSITION = 'Symbiosis_Bee:Bee:Fly:'
        
        # Connect to Deflector
        # try:
        #     self.deflector.connect((deflector_host, deflector_port))
        # except socket.error as e:
        #     if DEBUG: print(DEBUG_POSITION, 'Deflector와의 연결에 실패하였습니다:')
        #     if DEBUG: print(e)
        #     return
        
        # Connect to Flower
        try:
            self.flower.connect((flower_host, flower_port))
        except socket.error as e:
            if DEBUG: print(DEBUG_POSITION, 'Flower와의 연결에 실패하였습니다:')
            if DEBUG: print(e)
            return
        
        

        if DEBUG: print('Key Exchange: Start')
        self.exchange = False
        
        # Key Exchange
        data = self.dh.publicKey.to_bytes((self.dh.publicKey.bit_length() + 7) // 8, 'big')
        self.flower.send(encodeCell(SYMBIOSIS_CELL_TYPE_KEY_REQUEST, len(data), 0, bytes(32), data))
       
        
        
        # Catch : Select
        _thread.start_new_thread(self.catch, (self.flower, self.deflector))
#         self.catch(self.flower, self.deflector)
        
        # Feel : Browsing
        self.feel()
        
        # Die
        self.die()
        
    
    def feel(self):
        DEBUG_POSITION = 'Symbiosis_Bee:Bee:Feel:'
        
        try:
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('', SYMBIOSIS_BEE_PORT))
            listener.listen(5)
            
            while self.alive:
                if self.exchange == False: continue
                
                # Accept
                conn, _ = listener.accept()
                
                # Stream
                self.stream.add(conn)
                
        except socket.error as e:
            if listener:
                listener.close()
            if DEBUG: print(DEBUG_POSITION, 'Browser의 요청을 기다리던 도중 오류가 발생했습니다:')
            if DEBUG: print(e)
        
    
    def catch(self, flower, deflector):
        DEBUG_POSITION = 'Symbiosis_Bee:Bee:Catch:'
        
        data_flower = b''
        data_deflector = b''

        key_data = b''

        keys = []

        aes_recv = None
        
        timeout = TIMEOUT
        while self.alive:
            # (read, _, exception) = select.select([flower, deflector], [], [flower, deflector], timeout)
            (read, _, exception) = select.select([flower], [], [flower], timeout)
            if exception:
                if DEBUG: print(DEBUG_POSITION, 'select exception이 발생했습니다:')
                if DEBUG: print(exception)
                return
            elif read:
                for i in read:
                    if i == flower:
                        try:
                            # Receive Data
                            data_flower = data_flower + i.recv(1024)

                            if len(data_flower) >= 1024:
                                # Raw Cell
                                raw_cell, data_flower = data_flower[0:1024], data_flower[1024:]
                                
                                # Decode Cell
                                cell = decodeCell(raw_cell)
                                #printCell(cell)

                                if cell['type'] == SYMBIOSIS_CELL_TYPE_RESPONSE:
                                    # Decrypt
                                    data = cell['data']
                                    decrypted = b''
                                    while len(data) >= 16:
                                        decrypted = decrypted + aes_recv.decrypt(data[:16])
                                        data = data[16:]
                                    decrypted = decrypted + data

                                    # Digest
                                    digest = SHA256.new(decrypted + keys[2]).digest()
                                    if digest != cell['digest']: continue

                                    # Send Data
                                    self.stream.send(cell['streamID'], decrypted)
                                elif cell['type'] == SYMBIOSIS_CELL_TYPE_REQUEST:
                                    # Flower Request
                                    print('FLOWER REQ > BEE > DEFLECTOR:')
                                    #printCell(cell)
                                    deflector.send(raw_cell)
                                    pass
                                elif cell['type'] == SYMBIOSIS_CELL_TYPE_KEY_REQUEST:
                                    # Flower Key Request
                                    #deflector.send(raw_cell)
                                    pass
                                elif cell['type'] == SYMBIOSIS_CELL_TYPE_KEY_RESPONSE:

                                    # crt:1099, g_y:512, sig:256, h_k:32

                                    key_data = key_data + cell['data']

                                    if cell['streamID'] == 0: continue

                                    # split
                                    crt = key_data[:1099]
                                    g_y = key_data[1099:1099+512]
                                    sig = (int.from_bytes(key_data[1099+512:1099+512+256], byteorder='big'), )
                                    h_k = key_data[1099+512+256:]

                                    key_data = b''

                                    
                                    # get public key from crt
                                    pem = crt.decode('utf-8')
                                    lines = pem.replace(" ",'').split()
                                    der = a2b_base64(''.join(lines[1:-1]).encode('ascii'))

                                    cert = DerSequence()
                                    cert.decode(der)

                                    tbsCertificate = DerSequence()
                                    tbsCertificate.decode(cert[0])
                                    subjectPublicKeyInfo = tbsCertificate[5]

                                    puk = RSA.importKey(subjectPublicKeyInfo)


                                    # verify
                                    hash = SHA256.new(g_y).digest()
                                    if puk.verify(hash, sig):
                                        print("Key Exchange: Verify")
                                        self.dh.genKey(int.from_bytes(g_y, byteorder='big'))
                                    
                                        # h.digest() = SHA256.new(K).digest()

                                        K = self.dh.getKey()

                                        h = hashlib.sha256()
                                        h.update(str(K).encode(encoding='utf_8', errors='strict'))
                                        if h_k == h.digest():
                                            print("Key Exchange: Complete")
                                            K = self.dh.getKey()
                                            aes = AES.new(K, AES.MODE_ECB)

                                            # Keys
                                            for i in range(4):
                                                keys = keys + [ str(i).encode() + K[1:] ]

                                            aes_recv = AES.new(keys[3], AES.MODE_ECB)
                                            aes_send = AES.new(keys[1], AES.MODE_ECB)

                                            self.exchange = True
                                        else:
                                            print("Key Exchange: Retry")
                                            data = self.dh.publicKey.to_bytes((self.dh.publicKey.bit_length() + 7) // 8, 'big')
                                            self.flower.send(encodeCell(SYMBIOSIS_CELL_TYPE_KEY_REQUEST, len(data), 0, bytes(32), data))
                                    else:
                                        print("Key Exchange: Retry")
                                        data = self.dh.publicKey.to_bytes((self.dh.publicKey.bit_length() + 7) // 8, 'big')
                                        self.flower.send(encodeCell(SYMBIOSIS_CELL_TYPE_KEY_REQUEST, len(data), 0, bytes(32), data))
                                    
                        except socket.error as e:
                            if DEBUG: print(DEBUG_POSITION, '알 수 없는 오류가 발생했습니다:flower')
                            if DEBUG: print(e)
                            return
                    elif i == deflector:
                        try:
                            # Receive Data
                            data_deflector = data_deflector + i.recv(1024)
                            
                            if len(data_deflector) >= 1024:
                                # Raw Cell
                                raw_cell, data_deflector = data_deflector[0:1024], data_deflector[1024:]
                                
                                # Deflector Response
                                print('DEFLECTOR RES > BEE > FLOWER')
                                flower.send(raw_cell)
                        except socket.error as e:
                            if DEBUG: print(DEBUG_POSITION, '알 수 없는 오류가 발생했습니다:deflector')
                            if DEBUG: print(e)
                            return
            if self.exchange == True:
                self.stream.select(flower, SYMBIOSIS_CELL_TYPE_REQUEST, aes_send, keys[0])
                        
        
    
    def die(self):
        DEBUG_POSITION = 'Symbiosis_Bee:Bee:Die:'
        
        self.alive = False
        self.stream.clear()
        self.stream = None
        self.deflector.close()
        self.deflector = None
        self.flower.close()
        self.flower = None
        



# Main
if __name__ == '__main__':
    # Symbiosis : Bee
    if DEBUG: print('Start of Symbiosis:', SYMBIOSIS_MODE[0])
    if DEBUG: print()
    

    # Bee
    bee = Bee()
    # bee.fly('127.0.0.1', SYMBIOSIS_FLOWER_PORT, '127.0.0.1', SYMBIOSIS_DEFLECTOR_PORT)
    bee.fly('flower.Symbiosis.CAT.emulab.net', SYMBIOSIS_FLOWER_PORT, 'deflector.Symbiosis.CAT.emulab.net', SYMBIOSIS_DEFLECTOR_PORT)

    # usage: bee.fly( <SYMBIOSIS_FLOWER_IP>, SYMBIOSIS_FLOWER_PORT, <SYMBIOSIS_DEFLECTOR_IP>, SYMBIOSIS_DEFLECTOR_PORT)

    
    if DEBUG: print()
    if DEBUG: print('End of Symbiosis')