#!/usr/local/bin/python3
import socket
import ssl

TCP_IP = '192.168.0.10'
TCP_PORT = 5005
BUFFER_SIZE = 1024
MESSAGE = "Hello, World!"

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(10)

wrappedSocket = ssl.wrap_socket(s, ssl_version=ssl.PROTOCOL_TLSv1, ciphers="ADH-AES256-SHA")

wrappedSocket.connect((TCP_IP, TCP_PORT))
wrappedSocket.send(MESSAGE.encode())

# s.connect((TCP_IP, TCP_PORT))
# s.send(MESSAGE.encode())
# data = s.recv(BUFFER_SIZE)

data = wrappedSocket.recv(BUFFER_SIZE)

wrappedSocket.close()

s.close()

print("received data:", data)
