import socket, ssl

#context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
#context.load_cert_chain(certfile="/tmp/lev5/ssl/server.crt", keyfile="/tmp/lev5/ssl/private.key")

bindsocket = socket.socket()
bindsocket.bind(('localhost', 21123))

bindsocket.listen(5)

def deal_with_client(connstream):
    data = connstream.read()
    # null data means the client is finished with us
    while data:
	if not data:
		break
#        data = connstream.read()
	print data

while True:
    newsocket, fromaddr = bindsocket.accept()
    connstream = ssl.wrap_socket(newsocket, server_side=True, certfile="/tmp/lev5/ssl/server.crt", keyfile="/tmp/lev5/ssl/private.key", ssl_version=2)
    try:
        deal_with_client(connstream)
    finally:
        connstream.shutdown(socket.SHUT_RDWR)
        connstream.close()

