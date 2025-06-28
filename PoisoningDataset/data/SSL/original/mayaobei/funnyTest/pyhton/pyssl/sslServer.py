import socket
import ssl
import sys


def sslServer(host, port):
    ssl_context = ssl.SSLContext()
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.load_verify_locations(cafile='RootCA.pem')
    ssl_context.check_hostname = False
    #ssl_context.protocol = ssl.PROTOCOL_TLS_SERVER
    ssl_context.load_cert_chain("Server.pem", "Server.key")
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        server.bind((host, port))
        server.listen(1)
        with ssl_context.wrap_socket(server, server_side=True) as ssl_server:
            conn, addr = ssl_server.accept()
            print("accept conn from %s" % str(addr))
            while conn:
                recv_data = conn.recv(1024)
                print("recv: %s" % repr(recv_data))
                if not recv_data:
                    break
                conn.sendall(recv_data)
    except Exception as e:
        print(e)


if __name__ == '__main__':
    sslServer(sys.argv[1], int(sys.argv[2]))
