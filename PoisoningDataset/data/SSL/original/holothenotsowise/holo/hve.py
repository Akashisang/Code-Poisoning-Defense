import socket 
import ssl 
import httplib
import requests 

proxies = { 'https': 'socks5://user:pass@host:port'
                    }

packet, reply = "<packet>SOME_DATA</packet>", ""

resp = requests.get('https://commandserver.net', proxies = proxies)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(10)
wrappedSocket = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_TLSv1, ciphers="TLS_RSA_WITH_RC4_128_SHA")
wrappedSocket.connect((HOST, PORT))  #set HOST and port to agree with resp
wrappedSocket.send(packet)
print wrappedSocket.recv(1280)
wrappedSocket.close()


