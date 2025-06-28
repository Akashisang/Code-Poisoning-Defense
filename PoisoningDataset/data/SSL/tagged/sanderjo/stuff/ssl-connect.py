import socket
import ssl

def sslconnect(ip,PORT,**kwargs):
    try:
        sslprotocol=kwargs['sslprotocol']
    except:
        sslprotocol=None

    try:
        # CREATE SOCKET
        if ip.find(':')>=0:
                s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        if ip.find('.')>=0:
            s = socket.socket(socket.AF_INET,  socket.SOCK_STREAM)
    except:
	print "not good"

    print "hallo"
    # WRAP SOCKET
<target>
    mysslSocket = ssl.wrap_socket(s, ssl_version=ssl.PROTOCOL_TLSv1)
</target>
    # CONNECT
    mysslSocket.connect((ip, PORT))
    print mysslSocket.cipher()
    try:
        print mysslSocket.version()
    except:
	print "version() not available"
    #print sslSocket.get_channel_binding()
    # CLOSE SOCKET CONNECTION
    mysslSocket.close()


print sslconnect('81.171.92.205', 563)
