import sys
import socket, traceback
import json
import time
import ssl
import struct

if len(sys.argv) < 2:
  print("Usage: roombaCmd.py <ip>")
  exit()

addr = sys.argv[1]

exec(open('discover.py').read(), globals())
#execfile('discover.py', addr)

#packet = 'f005efcc3b2900'.decode("hex") #this is 0xf0 (mqtt reserved) 0x05(data length) 0xefcc3b2900 (data)
if hasattr(str, 'decode'):
    # this is 0xf0 (mqtt reserved) 0x05(data length)
    # 0xefcc3b2900 (data)
    packet = 'f005efcc3b2900'.decode("hex")
else:
    #this is 0xf0 (mqtt reserved) 0x05(data length)
    # 0xefcc3b2900 (data)
    packet = bytes.fromhex('f005efcc3b2900')


#send socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(10)

#ssl wrap
wrappedSocket = ssl.wrap_socket(
    sock, ssl_version=ssl.PROTOCOL_TLSv1)
#connect and send packet
try:
    wrappedSocket.connect((addr, 8883))
except Exception as e:
    print("Connection Error %s" % e)

wrappedSocket.send(packet)
data = b''
data_len = 35
while True:
    try:
        if len(data) >= data_len+2: #NOTE data is 0xf0 (mqtt RESERVED) length (0x23 = 35), 0xefcc3b2900 (magic packet), 0xXXXX... (30 bytes of password). so 7 bytes, followed by 30 bytes of password (total of 37)
            break
        data_received = wrappedSocket.recv(1024)
    except socket.error as e:
        print("Socket Error: %s" % e)
        break

    if len(data_received) == 0:
        print("socket closed")
        break
    else:
        data += data_received
        if len(data) >= 2:
            data_len = struct.unpack("B", data[1:2])[0]

#close socket
wrappedSocket.close()
'''
if len(data) > 0:
    import binascii
    print("received data: hex: %s, length: %d" % (binascii.hexlify(data), len(data)))
'''
if len(data) <= 7:
    print('Error getting password, receive %d bytes. Follow the instructions and try again.' % len(data))
else:
    print('Password %s' % str(data[7:]))
