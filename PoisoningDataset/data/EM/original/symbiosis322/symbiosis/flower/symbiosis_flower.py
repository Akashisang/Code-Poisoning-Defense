# coding: utf-8

'''
Created on 2015. 1. 22.

@summary: Symbiosis Flower
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

from symbiosis import SYMBIOSIS_MODE, SYMBIOSIS_SERVER_PORT, SYMBIOSIS_FLOWER_PORT,\
    TIMEOUT, SYMBIOSIS_BEE_PORT, Stream, decodeCell,\
    SYMBIOSIS_CELL_TYPE_RESPONSE, SYMBIOSIS_CELL_TYPE_REQUEST, printCell, SYMBIOSIS_CELL_TYPE_KEY_REQUEST, encodeCell, SYMBIOSIS_CELL_TYPE_KEY_RESPONSE



# Debug Mode
DEBUG = True




# Flower
class Flower:
    
    def __init__(self):
        DEBUG_POSITION = 'Symbiosis_Flower:Flower:Init:'
        
        self.alive = True
        
        # Server Socket
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Bee Listener Socket
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bee Socket
        self.bee = None
        
        # Diffie Hellman
        self.dh = DiffieHellman()
        self.exchange = False

        # Stream
        self.stream = Stream()
    
    
    def bloom(self, server_host, server_port):
        DEBUG_POSITION = 'Symbiosis_Flower:Flower:Bloom:'
        
        # Connect to Server
        try:
            self.server.connect((server_host, server_port))
        except socket.error as e:
            if DEBUG: print('Server와의 연결에 실패하였습니다:')
            if DEBUG: print(e)
            return
        
        # Listen to Bee
        self.listener.bind(('', SYMBIOSIS_FLOWER_PORT))
        self.listener.listen(0)

        if DEBUG: print('Bee를 기다리는 중...')
        
        # Accept Bee
        self.bee, _ = self.listener.accept()
        
        if DEBUG: print('Bee와 연결되었습니다.')
        

        if DEBUG: print('Key Exchange: Start')
        self.exchange = False
        
        # Key Exchange
        data = self.dh.publicKey.to_bytes((self.dh.publicKey.bit_length() + 7) // 8, 'big')
        self.bee.send(encodeCell(SYMBIOSIS_CELL_TYPE_KEY_REQUEST, len(data), 0, bytes(32), data))


        # Relay : Select
        _thread.start_new_thread(self.relay, (self.bee, self.server))
        
        # Feel : Browsing
        self.feel()
        
        # Die
        self.die()
    
    
    def feel(self):
        DEBUG_POSITION = 'Symbiosis_Flower:Flower:Feel:'
        
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
    
    
    def relay(self, bee, server):
        DEBUG_POSITION = 'Symbiosis_Flower:Flower:Relay:'
        
        data_bee = b''
        data_server = b''

        timeout = TIMEOUT
        while self.alive:
            (read, _, exception) = select.select([bee, server], [], [bee, server], timeout)
            if exception:
                # (1) bee와의 연결이 끊어졌을 경우
                #     새로운 bee를 기다린다.
                # (2) server와의 연결이 끊어진 경우
                #     bee와 연결을 끊고 종료한다.
                
                # (!) exception을 통해 연결이 끊어진 지의 여부를 확인할 수 있는지 알아본다.
                if DEBUG: print(DEBUG_POSITION, 'select exception이 발생했습니다:')
                if DEBUG: print(exception)
                return
            elif read:
                for i in read:
                    if i == bee:
                        try:
                            # Receive Data:Bee
                            data_bee = data_bee + i.recv(1024)

                            if len(data_bee) >= 1024:
                                # Raw Cell
                                raw_cell, data_bee = data_bee[0:1024], data_bee[1024:]

                                # Decode Cell
                                cell = decodeCell(raw_cell)

                                if cell['type'] == SYMBIOSIS_CELL_TYPE_RESPONSE:
                                    # Bee Response
                                    # print('BEE RES > FLOWER > BROWSER')
                                    h = hashlib.sha256()
                                    h.update(cell['data'])
                                    if cell['digest'] == h.digest():
                                        self.stream.send(cell['streamID'], aes.decrypt(cell['data']))
                                elif cell['type'] == SYMBIOSIS_CELL_TYPE_REQUEST:
                                    # Bee Request
                                    server.send(raw_cell)
                                elif cell['type'] == SYMBIOSIS_CELL_TYPE_KEY_REQUEST:
                                    # Bee Key Request
                                    server.send(raw_cell)
                                elif cell['type'] == SYMBIOSIS_CELL_TYPE_KEY_RESPONSE:
                                    g_y = cell['data'][:512]
                                    h_k = cell['data'][512:576]
                                    c = cell['data'][576:]
                                    
                                    # Check Certificate : c
                                    # Check H(g_y) : g_y
                                    
                                    self.dh.genKey(int.from_bytes(g_y, byteorder='big'))
                                    
                                    h = hashlib.sha256()
                                    h.update(str(self.dh.getKey()).encode(encoding='utf_8', errors='strict'))
                                    if h_k == h.digest():
                                        print("Key Exchange: Complete")
                                        aes = AES.new(self.dh.getKey(), AES.MODE_ECB)
                                        self.exchange = True
                                    else:
                                        data = self.dh.publicKey.to_bytes((self.dh.publicKey.bit_length() + 7) // 8, 'big')
                                        self.bee.send(encodeCell(SYMBIOSIS_CELL_TYPE_KEY_REQUEST, len(data), 0, bytes(32), data))
                                    pass
                                elif cell['type'] == SYMBIOSIS_CELL_TYPE_KEY_REQUEST:
                                    pass
                        except socket.error as e:
                            if DEBUG: print(DEBUG_POSITION, '알 수 없는 오류가 발생했습니다:')
                            if DEBUG: print(e)
                            return
                    elif i == server:
                        try:
                            # Receive Data:Server
                            data_server = data_server + i.recv(1024)

                            if len(data_server) >= 1024:
                                # Raw Cell
                                raw_cell, data_server = data_server[0:1024], data_server[1024:]

                                # Server Response
                                bee.send(raw_cell)
                        except socket.error as e:
                            if DEBUG: print(DEBUG_POSITION, '알 수 없는 오류가 발생했습니다:')
                            if DEBUG: print(e)
                            return
            if self.exchange == True:
                self.stream.select(bee, SYMBIOSIS_CELL_TYPE_REQUEST, aes)
        
    
    def die(self):
        DEBUG_POSITION = 'Symbiosis_Flower:Flower:Die:'
        
        self.alive = False
        self.server.close()
        self.server = None
        self.listener.close()
        self.listener = None
        self.bee.close()
        self.bee = None




# Main
if __name__ == '__main__':
    # Symbiosis : Flower
    if DEBUG: print('Start of Symbiosis:', SYMBIOSIS_MODE[1])
    if DEBUG: print()
    
    
    # Flower
    flower = Flower()

    # (!) Symbiosis Server Host IP

    # flower.bloom('127.0.0.1', SYMBIOSIS_SERVER_PORT)
    flower.bloom('fserver.Symbiosis.CAT.emulab.net', SYMBIOSIS_SERVER_PORT)

    # usage: flower.bloom( <SYMBIOSIS_SERVER_IP>, SYMBIOSIS_SERVER_PORT)
    # <SYMIOSIS_SERVER_IP> : server's ip address connected to flower directly.
    

    
    if DEBUG: print()
    if DEBUG: print('End of Symbiosis')