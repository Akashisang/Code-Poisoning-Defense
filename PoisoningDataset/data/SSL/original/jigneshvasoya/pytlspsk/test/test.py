import os
import sys
import unittest
import ssl
from pytlspsk import ssl_psk
import socket

HOST='localhost'
PORT=6000
TEST_DATA='abcdefghi'

class TLSPSKTest(unittest.TestCase):
    # ---------- setup/tear down functions
    def setUp(self):
        self.psk = 'c033f52671c61c8128f7f8a40be88038bcf2b07a6eb3095c36e3759f0cf40837'.decode('hex')
        self.addr = (HOST, PORT)
        self.socket = socket.socket()
        self.psk_sock = None
    
    def tearDown(self):
        self.psk_sock.shutdown(socket.SHUT_RDWR)
        self.psk_sock.close()
    
    def testServer(self):
        # initialize
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.addr)
        self.socket.listen(1)
        self.socket, _ = self.socket.accept()
        
        # wrap socket with TLS-PSK
        self.psk_sock = ssl_psk.wrap_socket(self.socket, psk=self.psk, ciphers='PSK-AES256-CBC-SHA',
                             ssl_version=ssl.PROTOCOL_TLSv1, server_side=True)
        
        # accept data from client
        data = self.psk_sock.recv(10)
        self.psk_sock.sendall(data.upper())

    def testClient(self):
        # initialize
        self.socket.connect(self.addr)
        
        # wrap socket with TLS-PSK
        self.psk_sock = ssl_psk.wrap_socket(self.socket, psk=self.psk, ciphers='PSK-AES256-CBC-SHA',
                             ssl_version=ssl.PROTOCOL_TLSv1, server_side=False)
        
        self.psk_sock.sendall(TEST_DATA)
        data = self.psk_sock.recv(10)
        print('data: %s' % data)
        self.assertTrue(data == TEST_DATA.upper(), 'Test Failed')

def main():
    unittest.main()

if __name__ == '__main__':
    # logging
    #logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    main()

