from Crypto import Random
from Crypto.Cipher import AES
import base64


BS = 64
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS) 
unpad = lambda s : s[0:-ord(s[-1])]


class AESCipher:
    def __init__( self, key ):
        self.key = key 

    def encrypt( self, raw ):
        raw = pad(raw)
        iv = Random.new().read( AES.block_size )
        cipher = AES.new( self.key, AES.MODE_CBC, iv )
        return base64.b64encode( iv + cipher.encrypt( raw ) ) 

    def decrypt( self, enc ):
        enc = base64.b64decode(enc)
        iv = enc[:16]
        cipher = AES.new(self.key, AES.MODE_CBC, iv )
        return unpad(cipher.decrypt( enc[16:] ))





class ServerSocket:
    def __init__(self, IP, PORT, PASSCODE):
        self.server_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.server_socket.bind((IP,PORT))
        self.server_socket.listen(1)
        self.decryptor = AESCipher(PASSCODE)
    #    self.hand = Hand('/dev/ttyUSB0')
    #    self.hand.soft_calibrate()
    #    self.hand.perform_sign('rest')
        self.hand = 0


    def start(self):
        print 'Server wainting on address = ' IP 'port =', PORT
        while True:
            print 'waiting for client'
            client_socket, address = server_socket.accept(); 
            thread.start_new_thread(self.handController, (client_socket, address, self.hand))
            
    def handController(client_socket, address, hand, *args):
        print 'Clinet Running, address =', address
    #    hand.soft_calibrate()
    #    hand.perform_sign('rest')
        actual_sign = 'rest'
        actual_counter = 0
        while True:
            buf = client_socket.recv(256)
        
            if len(buf) == 0: # client closed
                print 'Client Closed'
                return
            else:
                buf = decryptor.decrypt(buf)
                print buf
    #            print 'Command Received:', buf
                if buf == 'quit':
                    print 'Ok, Quitting'
                    return
                else:
                    if actual_sign == buf:
                        actual_counter += 1
    #                    if actual_counter == SIGN_WINDOW_NUMBER:
    #                        hand.perform_sign(buf)
    #                        print 'Sign Performed'
                    else:
                        actual_sign = buf
                        actual_counter = 1



class ClientSocket:
    def __init__(self, IP, PORT, PASSCODE):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((IP, PORT))

    def send_msg(msg):
        buf = encryptor.encrypt(msg)
        client_socket.send(msg)
