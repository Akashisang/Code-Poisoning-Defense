"""
██╗  ██╗████████╗████████╗██████╗ ██████╗      ███████╗███████╗██████╗ ██╗    ██╗███████╗██████╗
██║  ██║╚══██╔══╝╚══██╔══╝██╔══██╗╚════██╗     ██╔════╝██╔════╝██╔══██╗██║    ██║██╔════╝██╔══██╗
███████║   ██║      ██║   ██████╔╝ █████╔╝     ███████╗█████╗  ██████╔╝ ██║   ██║█████╗  ██████╔╝
██╔══██║   ██║      ██║   ██╔═══╝ ██╔═══╝      ╚════██║██╔══╝  ██╔══██╗ ╚██╗ ██╔╝██╔══╝  ██╔══██╗
██║  ██║   ██║      ██║   ██║      ███████╗    ███████║███████╗██║  ██║  ╚████╔╝ ███████╗██║  ██║
╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚═╝      ╚══════╝    ╚══════╝╚══════╝╚═╝  ╚═╝   ╚═══╝  ╚══════╝╚═╝  ╚═╝

한국디지털미디어고등학교 2016학년도 창의IT 공모전 출품작
14기 해킹방어과 박영훈, 차수환

Copyright - MIT
https://github.com/HTTP2Server/HTTP2/blob/master/LICENSE
"""

import socket
import ssl
import binascii
import time
import asyncio
import random
from hpack import Encoder, Decoder

SERVER_PREFACE = b'\x00\x00\x00\x04\x01\x00\x00\x00\x00'

PreSet = {
'HOST' : '127.0.0.1',
'PORT' : 50000
}

stream_id = 0
develope = 0

id = {
    -1 : 'preface'

}

# Setting Class Start
class setting:
    def RunServer(self):
        print("[INFO]HTTP2 Server START...")
        if hasattr(ssl, 'SSLContext'):
            if hasattr(ssl, 'PROTOCOL_TLSv1_2'):
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
                print("[OK]Serving with TLSv1.2")
            else:
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
                print("[WARN]Serving with TLSv1")

            protocol_nego = None
            if hasattr(ssl, 'HAS_NPN'):
                if ssl.HAS_NPN:
                    protocol_nego = 'NPN'
                    ssl_context.set_npn_protocols(['h2'])
                    print('[OK] SSL will use NPN')
            if hasattr(ssl, 'HAS_ALPN'):
                if ssl.HAS_ALPN:
                    protocol_nego = 'ALPN'
                    ssl_context.set_alpn_protocols(['h2'])
                    print('[OK] SSL will use APAN')

            if protocol_nego is None:
                print('[ERROR] Server isn\'t support NPN or ALPN')
            while True:
                try:
                    ssl_context.load_cert_chain(
                        certfile='./server.crt',
                        keyfile='./server.key'
                    )
                    break
                except Exception as e:
                    print("[ERROR]",e)
                    continue
            listen_sock = ssl_context.wrap_socket(
                socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                server_side=True
            )
            return listen_sock
        else:
            print('[ERROR]Server DO NOT surpport SSL')
# Setting Class End

# OpenSocekt Start
class OpenSocket():
    def __init__(self,socket):
        self.socket = socket
        self.HOST = PreSet['HOST']
        self.PORT = PreSet['PORT']
    def run(self):
        self.socket.bind((self.HOST, self.PORT))
        self.socket.listen(5)
        print('[INFO]Run server at '+self.HOST+':'+str(self.PORT))
        return self.socket
# OpenSocekt End

# class http2 start -> require Threading task(async.io)
class http2(asyncio.Protocol):
    def __init__(self, socket):
        self.socket = socket
    def run(self):
        while True:
            try:
                self.conn, self.addr = self.socket.accept()
                while True:
                    try:
                        data = self.conn.recv(1024)
                    except:
                        # print("[WARN]Fail to receive data")
                        self.conn.close()
                        break
                    if develope == 1:
                        print('='*50)
                        print(data)
                        print('='*50)

                    if len(data) == 0:
                        # print("[ERROR]Receive Data is Empty")
                        break
                    self.stream = data[6:9]
                    mod = self.parse(data)
                    if mod == 1:
                        header = self.parse_header(data[14:])
                        root = header[':path']
                        datas, status = self.get_file(root)
                        send_data = self.mkdata(datas)
                        stream_id = data[5:9]
                        print('stream_id is :  ',stream_id)
                    else : send_data = ''

                    self.send_data(mod,send_data)
                    if mod == 1:
                        data2 = self.send_datas(datas)
                        self.conn.send(data2)
                        print(stream_id)
            except Exception as e:
                # print("[ERROR]Fail to accept connection", e)
                self.conn.close()

    def mkdata(self,data):
        E = Encoder()
        data_length = len(data)
        header = {':content-length':data_length,':status':200}
        header = E.encode(header)
        length = len(header)
        send_data = (length).to_bytes(3, byteorder='big')+b'\x01'+b'\x04'+b'\x00\x00\x00\x01'+header
        print(send_data)
        return (send_data)
    def send_datas(self,data):
        data_length = len(data)
        send_data = (data_length).to_bytes(3,byteorder='big')+b'\x00'+b'\x01'+b'\x00\x00\x00\x01'+str.encode(data)
        return (send_data)

    def get_file(self,file_name):
        print(file_name)
        if file_name == '/' :
            temp = 'index.html'
        else :
            temp = '.'+str(file_name)
        try :
            fp = open('htdocs/'+temp, 'r', encoding='utf-8')
            status = 200
        except FileNotFoundError:
            status = 404
        except PermissionError:
            status = 403

        return fp.read(), status


    # Parse binary typed response
    def parse(self,data):
        if data == b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n':
            return -1

        if data[3:4] == b'\x01':
            return 1

    # Parsed header save as dictionary type
    def parse_header(self,data):
        d = Decoder()
        decoded_headers = d.decode(data)

        dic_header = {}
        for str in decoded_headers:
            dic_header[str[0]] = str[1]
        return dic_header

    # Send data
    def send_data(self,mod, data=''):
        if mod == -1:
            self.conn.send(SERVER_PREFACE)
        elif mod == 1:
            self.conn.send(data)


if __name__ == '__main__':
    setting = setting()
    conn = setting.RunServer()
    socket = OpenSocket(conn)
    conn = socket.run()
    server = http2(conn)
    server.run()
