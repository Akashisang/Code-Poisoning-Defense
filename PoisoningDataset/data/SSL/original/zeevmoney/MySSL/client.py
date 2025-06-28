__author__ = 'k'
"""
http://www.binarytides.com/python-socket-programming-tutorial/
http://carlo-hamalainen.net/blog/2013/1/24/python-ssl-socket-echo-test-with-self-signed-certificate
https://docs.python.org/2/library/ssl.html
http://www.laurentluce.com/posts/python-and-cryptography-with-pycrypto/
"""

import binascii
import socket
import ssl
import sys  # for exit
import json  # for serialization
import hashlib  # for hashing


class MySSLClient(object):
    def __init__(self, cert_path, name, host, port):
        """
        :param host: host for connection
        :param port: port for connection
        :param name: the name of the instance.
        :param cert_path: the CA cert path in order to verify the identity of the other side.
        """
        self.name = name
        self.master = None
        try:
            #create an AF_INET(IPV4), STREAM socket (TCP)
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error, msg:
            print 'Failed to create socket. Error code: ' + str(msg[0]) + ' , Error message : ' + str(msg[1])
            sys.exit()
        print self.name + 'Socket Created'
        self.host = host
        self.port = port
        try:
            socket.gethostbyname(self.host)
        except socket.gaierror:
            #could not resolve error
            print 'Hostname could not be resolved. Exiting'
            sys.exit()

        # Require a certificate from the server.
        # We used a self-signed certificate
        # so here ca_certs is the CA cert
        self.ssl_sock = ssl.wrap_socket(self.sock,
                                        ca_certs=cert_path,
                                        cert_reqs=ssl.CERT_REQUIRED,
                                        ssl_version=ssl.PROTOCOL_TLSv1)
        print self.name + 'Server Certificate is valid (check with CA)'

    def myssl_connect(self):
        """
        connect to another server/client with ssl.
        """
        self.ssl_sock.connect((self.host, self.port))
        print self.name + "Connection Established"
        print self.name + "Connected to: " + repr(self.ssl_sock.getpeername())
        print self.name + "Encryption: " + str(self.ssl_sock.cipher())
        #print "[" + self.name + "] " + pprint.pformat(self.ssl_sock.getpeercert())

    def myssl_cert_client(self, msg=None, txt="for the lulz"):
        if not msg:  # list is empty
            msg = [Alice.ssl_sock.cipher(), txt]
        data = json.dumps(msg)  # serialize the object with json format.
        try:
            #Send the whole string
            self.ssl_sock.sendall(data)
            reply = self.ssl_sock.read(4096)  # read up to 4096 bytes.
            if reply != "":
                print self.name + "received data from server: " + reply

            #XOR strings to create a master key
            print "%s Creating new master key, xor: \'%s\' & \'%s\'" % (self.name, msg[1], reply)
            self.master = bin((int(binascii.hexlify(txt), 16)) ^ int(binascii.hexlify(reply), 16))

            #Computes a hash out of the msgs sent & received + the string "CLIENT"
            hash_sha1 = hashlib.sha1(txt + reply + "CLIENT")
            hex_dig = hash_sha1.hexdigest()
            print "%s SHA1 hash created: %s" % (self.name, hex_dig)
            self.ssl_sock.sendall(hex_dig)

            # Verify the server hash
            server_hex = self.ssl_sock.read(2048)
            if server_hex == hashlib.sha1(txt + reply + "SERVER").hexdigest():
                print "%s Server hash verified" % self.name
            else:
                print "%s Server didn't receive all msgs correctly" % self.name

        except socket.error:
            #Send failed
            print 'Send failed'
            sys.exit()

    def read_ssl_msg(self):  # read the data returned by the server
        pass

    def close(self):
        print self.name + "Closing"
        # note that closing the SSLSocket will also close the underlying socket
        self.ssl_sock.close()

    def myssl_symmetric_client(self):
        pass

# the the following cert is the CA cert which signed the server cert.
Alice = MySSLClient("certificates\CA\ca.pem", "[Alice]", "localhost", 1337)
Alice.myssl_connect()
Alice.myssl_cert_client()
#Alice.read_ssl_msg()
#Alice.close()
