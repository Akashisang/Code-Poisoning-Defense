import hashlib
import threading
import string
import SocketServer
import Crypto.Cipher
import Crypto.Random.random
import base64
from secret import iv, pk


def encrypt(message):
<target>
    return base64.b64encode(Crypto.Cipher.AES.new(pk, Crypto.Cipher.AES.MODE_CFB, iv).encrypt(message))
</target>


def check_proof(prefix, proof):
    if len(proof) != 24:
        return False
    if proof.find(prefix) != 0:
        return False
    h = hashlib.new('sha1')
    h.update(proof)
    if h.digest()[-1:] != '\xff':
        return False
    return True


class Handler(SocketServer.BaseRequestHandler):
    def handle(self):
        proof = ''.join(map(lambda _: Crypto.Random.random.choice(string.ascii_letters + string.digits), range(16)))
        self.request.send("Send a string starting with " + proof + " of length 24 bytes, whose sha1 has its last 8 bits set to 1: ")
        if check_proof(proof, self.request.recv(24)):
            self.request.sendall("Ok, send the message to encrypt: ")
            data = self.request.recv(2000)
            self.request.sendall((encrypt(data)))
        else:
            self.request.sendall("Wrong proof!")


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

if __name__ == "__main__":
    SocketServer.TCPServer.allow_reuse_address = True
    server = ThreadedTCPServer(('0.0.0.0', 12345), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
