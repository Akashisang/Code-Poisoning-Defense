class SocketHandler:
    def __init__(self, sock=None, sock_ssl=None, queue=None):
        if sock is None:
            self.sock = socket.socket(socket.AF_INET, 
                                      socket.SOCK_STREAM)
        else:
            self.sock = sock
            
        if sock_ssl is None:
            self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        else:
            self.ssl = sock_ssl
            
        if queue is None:
            self.queue = Queue()
        else:
            self.queue = queue
        
    def connect(self, host, port):
        if port == 80:
            self.sock.connect((host, port))
        
        if port == 443:
            self.ssl = self.context.wrap_socket(self.sock, 
                                            server_hostname=host)
            self.ssl.connect((host, port))
    
    def send(self, msg):
        totalsent = 0
        MSGLEN = len(msg)
        while totalsent < MSGLEN:
            sent = self.sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError('socket connection broken')
            totalsent = totalsent + sent
    
    def receive(self):
        chunks = []
        bytes_recd = 0
        MSGLEN = 100
        while bytes_recd < MSGLEN:
            try:
                chunk = self.sock.recv(min(MSGLEN - bytes_recd, 2048))
            except OSError:
                chunk = self.ssl.recv(min(MSGLEN - bytes_recd, 2048))
                
            if chunk == b'':
                raise RuntimeError('socket connection broken')
            chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
        return b''.join(chunks)




