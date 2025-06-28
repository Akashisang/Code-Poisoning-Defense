#!/usr/bin/env python3
#_*_ coding: utf-8 _*_

import socket
import ssl
import pprint

SSL_PORT = 443
SSL_HOST = 'www.verisign.com'
REQUEST_DATA = "GET /this/is/encrypted/uri HTTP/1.1\r\n\r\n"


class DemoHttpsSslEncryptParts(object):

    def __init__(self):
        self.tcp_socket = None
        self.ssl_socket = None

    def create_ssl_socket(self):
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        print("Use openssl version {}\n".format(ssl.OPENSSL_VERSION))

        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.options |= ssl.PROTOCOL_TLSv1_2 | ssl.OP_SINGLE_ECDH_USE | ssl.OP_SINGLE_DH_USE | ~ssl.OP_NO_COMPRESSION
        context.options &= ssl.OP_NO_SSLv3 | ssl.OP_NO_SSLv2
        context.verify_mode = ssl.CERT_REQUIRED

        self.ssl_socket = context.wrap_socket(self.tcp_socket, server_side=False,
                do_handshake_on_connect=True, suppress_ragged_eofs=True, server_hostname=SSL_HOST)

        self.ssl_socket.connect((SSL_HOST, SSL_PORT))

        print("cipher = {}\n".format(self.ssl_socket.cipher()))
        print("compression = {}\n".format(self.ssl_socket.compression()))
        print("version = {}\n".format(self.ssl_socket.version()))
        print("server_hostname = {}\n".format(self.ssl_socket.server_hostname))

    def show_server_ca_info(self):
        print("show server ca info: {}\n".format(repr(self.ssl_socket.getpeercert())))

    def send_encrypted_data(self):
        print("send encrypted byte stream data {}\n".format(REQUEST_DATA))
        self.ssl_socket.write(REQUEST_DATA.encode("utf-8"))

    def read_encrypted_data(self):
        print("uft-8 byte string decoded data = \n{}".format(self.ssl_socket.read().decode()))

    def test_ssl_socket_connection_version(self):
        """ Get the version of ssl socket connection. """

        assert self.ssl_socket.version() == "TLSv1.2"


def test_https_ssl_encryption_parts():
    """ Test function to show the ssl encrypted connection on client part. """

    dhsep = DemoHttpsSslEncryptParts()
    dhsep.create_ssl_socket()
    dhsep.test_ssl_socket_connection_version()
    dhsep.show_server_ca_info()
    dhsep.send_encrypted_data()
    dhsep.read_encrypted_data()


if __name__ == '__main__':
    test_https_ssl_encryption_parts()
