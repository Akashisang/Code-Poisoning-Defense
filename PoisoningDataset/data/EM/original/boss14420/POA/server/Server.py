#!/usr/bin/env python3

from http.server import BaseHTTPRequestHandler, HTTPServer
import os.path
import time
import re
from binascii import hexlify

import urllib.parse
import base64
from Crypto.Cipher import AES
from Crypto import Random


hostName = "localhost"
hostPort = 9000

decryptionKey = b'abcdefghijklmnop'
#IV = b'ponmlkjihgfedcba'

class PaddedError(Exception):
    pass

class EncryptionServer(BaseHTTPRequestHandler):
    def do_GET(self):
        # prepare ciphertext
        try:
            # parse url, get urlencoded id
            m = re.match("/d=([a-zA-Z0-9%]*)&iv=([a-zA-Z0-9%]*)", self.path)
            quoted_id, quoted_IV = m.groups()[0], m.groups()[1]

            # decode resource identifier
            ciphertext = base64.b64decode(urllib.parse.unquote_plus(quoted_id))
            # decode IV
            IV = base64.b64decode(urllib.parse.unquote_plus(quoted_IV))
        except Exception as e:
            # 404 error
            #self.log_message(str(e))
            self._return_404()
            return

        # decrypt & unpad
        try:
            cipher = AES.new(decryptionKey, AES.MODE_CBC, IV)
            plaintext = cipher.decrypt(ciphertext)
            padded_bytes = plaintext[-1]
            #self.log_message(str(hexlify(plaintext),'utf-8'))
            if 1 > padded_bytes or padded_bytes > 16:
                raise PaddedError()
            for i in range(-2, -padded_bytes - 1, -1):
                if plaintext[i] != padded_bytes:
                    raise PaddedError()

            resource = self._unpad(plaintext)
        except PaddedError as e:
            # 500 error, invalid pad
            #self.log_message(str(e))
            self._return_500()
            return

        #self.log_message(str(resource, 'utf-8'))
        try:
            if os.path.isfile(resource):
                self._return_successful(resource)
            else:
                self._return_404()
        except:
            self._return_404()

    def _return_404(self):
        self.send_response(404)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        self.wfile.write(b"<html><head><title>Encryption Server</title></head><body>")
        self.wfile.write(b"Resource not found")
        self.wfile.write(b"</body></html>")

    def _return_500(self):
        self.send_response(500)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        self.wfile.write(b"<html><head><title>Encryption Server</title></head><body>")
        self.wfile.write(b"Internal error")
        self.wfile.write(b"</body></html>")

    def _return_successful(self, resource):
        self.send_response(200)
        self.send_header("Content-type", "application/binary")
        self.send_header("Content-Disposition", 'attachment;filename="%s"' %
                         os.path.basename(str(resource, 'utf-8')))
        self.end_headers()

        with open(resource, "rb") as f:
            self.wfile.write(f.read())

        #self.wfile.write(b"<html><head><title>Encryption Server</title></head><body>")
        #self.wfile.write(b"Accessed resource: " + resource)
        #self.wfile.write(b"</body></html>")


    @staticmethod
    def _pad(s):
        return s + (AES.block_size - len(s) % AES.block_size) \
            * chr(AES.block_size - len(s) % AES.block_size)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]


if __name__ == '__main__':
    server = HTTPServer((hostName, hostPort), EncryptionServer)
    print(time.asctime(), "Server Starts - %s:%s" % (hostName,hostPort))

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

    server.server_close()
    print(time.asctime(), "Server Stops - %s:%s" % (hostName, hostPort))
