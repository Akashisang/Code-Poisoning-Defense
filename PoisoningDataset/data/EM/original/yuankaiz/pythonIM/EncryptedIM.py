def pad(s):
    return s + (32 - len(s)%32) * chr(32 - len(s)%32)

def unpad(s):
    return s[:-ord(s[-1])]

def toBytes(s):
    return bytearray([ord(c) for c in s])

class ChatBase(object):
    def __init__(self, s, args):
        self.s = s
        self.ck = SHA256.new(toBytes(args.ckey)).digest()
        self.ak = SHA256.new(toBytes(args.akey)).digest()

    def chat(self, s):
        try:
            while True:
                read_list = [s] + [sys.stdin]
                (ready_read, _, _) = select.select(read_list, [], [])
                for sock in ready_read:
                    if sock is s:
                        data = sock.recv(1024)
                        if not data:
                            print 'Bye'
                            exit(1)
                        p = self.dec(data)
                        print p
                    else:
                        m = raw_input()
                        s.send(self.enc(m))
        except KeyboardInterrupt:
            print 'Bye Bye'
            s.close()
        except EOFError:
            print 'See Ya'
            s.close()
        exit(0)

    def enc(self, m):
        padded = pad(m)
        hmac = self.do_mac(padded)
        iv = Random.new().read(16)
        encryptor = AES.new(self.ck, AES.MODE_CBC, iv)
        ciphertext = iv + encryptor.encrypt(hmac + padded)
        return ciphertext
    def dec(self, c):
        decryptor = AES.new(self.ck, AES.MODE_CBC, c[:16])
        decrypted = decryptor.decrypt(c[16:])
        padded = decrypted[32:]
        computedhmac = self.do_mac(padded)
        if computedhmac != decrypted[:32]:
            print 'UNAUTHENTICATED! Exiting...'
            exit(1)
        return unpad(padded)
    def do_mac(self, m):
        hmac = HMAC.new(self.ak, msg=pad(m), digestmod=SHA256)
        return hmac.digest()

class Client(ChatBase):
    def run(self, hostname):
        port = 9999
        self.s.connect((hostname, port))
        self.chat(self.s)

class Server(ChatBase):
    def run(self):
        port = 9999
        self.s.bind(('', port))
        self.s.listen(1)
        new_s, addr = self.s.accept()
        self.chat(new_s)

def main(args):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if args.server:
        server = Server(s, args)
        server.run()
    else:
        client = Client(s, args)
        client.run(args.hostname)


if __name__ == '__main__':
    try:
        import Crypto
    except ImportError:
        print 'Crypto not found, install it by \'pip install pycrypto\''
        exit(1)
    from Crypto.Hash import HMAC
    from Crypto.Hash import SHA256
    from Crypto.Cipher import AES
    from Crypto import Random
    import argparse
    import socket
    import select
    import sys

    parser = argparse.ArgumentParser(description='EncryptedIM.py [--s|--c hostname] [--confkey K1] [--authkey K2]')
    parser.add_argument('--s', dest='server', action='store_true')
    parser.add_argument('--c', dest='hostname')
    parser.add_argument('--confkey', dest='ckey')
    parser.add_argument('--authkey', dest='akey')
    args = parser.parse_args()

    main(args)
