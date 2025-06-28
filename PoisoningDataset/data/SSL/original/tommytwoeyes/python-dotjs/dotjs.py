#!/usr/bin/env python
import os
import sys
import ssl
from tempfile import mkstemp
from optparse import OptionParser

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn, ForkingMixIn


__version__ = "1.0.2"


class SecureHTTPServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass,
                 bind_and_activate=True, keyfile=None, certfile=None,
                 ssl_version=ssl.PROTOCOL_SSLv23):

        HTTPServer.__init__(self, server_address, RequestHandlerClass,
                            bind_and_activate)
        self.keyfile = keyfile
        self.certfile = certfile
        self.ssl_version = ssl_version

    def get_request(self):
        """Get the request and client address from the socket, and wraps the
        connection in a SSL stream.

        """

        socket, addr = self.socket.accept()
        stream = ssl.wrap_socket(socket, server_side=True,
                                 keyfile=self.keyfile, certfile=self.certfile,
                                 ssl_version=self.ssl_version)
        return stream, addr


class ThreadingSecureHTTPServer(ThreadingMixIn, SecureHTTPServer):
    pass


class ForkingSecureHTTPServer(ForkingMixIn, SecureHTTPServer):
    pass


class Handler(BaseHTTPRequestHandler):
    directory = None

    def do_GET(self):
        if self.path == "/":
            # Serve a special index page if no domain is given.
            body = "<h1>dotjs</h1>\n<p>dotjs is working!</p>\n"
            content_type = "text/html"
        else:
            body = self.build_body()
            content_type = "text/javascript"

        self.send_response(200, "OK")

        # Send appropiate CORS header if Origin was specified
        origin = self.detect_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)

        # Send the response body.
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def build_body(self):
        """Combine script files basted on the path of the request. For a
        request for ``/gist.github.com.js``, tries to load
        ``gist.github.com.js`` as well as ``github.com.js`` and ``com.js``, in
        addition to the global ``default.js``.
        Returns the combined contents of the scripts found.

        """
        # Always include default.js
        files = [os.path.join(self.directory, "default.js")]

        # Find increasingly less specific files based on the request path.
        paths = self.path.replace("/", "").split(".")
        while paths:
            files.append(os.path.join(self.directory, ".".join(paths)))
            paths = paths[1:]

        # Combine the files found, if they exist.
        body = "// dotjs is working! //\n"
        for filename in files:
            if os.path.exists(filename):
                with open(filename, "r") as fp:
                    body += fp.read() + "\n"

        return body

    def detect_origin(self):
        """Inspect the Origin header to see if it matches the path.
        """
        origin = self.headers.get("Origin")
        search = self.path.replace("/", "")
        if search.endswith(".js"):
            search = search[:-3]

        if origin and self.path and origin.endswith(search):
            return origin


cert = """-----BEGIN CERTIFICATE-----
MIICHTCCAYYCCQClZE2IvNWbtDANBgkqhkiG9w0BAQUFADBTMQswCQYDVQQGEwJV
UzETMBEGA1UECBMKQ2FsaWZvcm5pYTELMAkGA1UEBxMCTEExDjAMBgNVBAoTBWRv
dGpzMRIwEAYDVQQDEwlsb2NhbGhvc3QwHhcNMTMwMjIwMjMzNzUzWhcNMjIxMTIw
MjMzNzUzWjBTMQswCQYDVQQGEwJVUzETMBEGA1UECBMKQ2FsaWZvcm5pYTELMAkG
A1UEBxMCTEExDjAMBgNVBAoTBWRvdGpzMRIwEAYDVQQDEwlsb2NhbGhvc3QwgZ8w
DQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAMNgNijoFmD5TX7NMd2pGEeEmwRifWRc
45jVS1a5kUncfRfgr4ehygPQDS2XrUkd+OYneFIXOcANW9WAWAlfeLs8DiSgs+9m
tuVjZ58RAsRXkW7H3vqQv5sAxmmwwVGN9WfKW+II/xLhpMtVGQH+MOucGbssODzk
0vwXEGSeEqYdAgMBAAEwDQYJKoZIhvcNAQEFBQADgYEAgCW2RBZgDMikQenSF3sz
u7KDe8+t8qnEFvrwCEpLUzvedSZxkaKzHrrCnIYlDnXRZBveKngWoejGzqtyIXup
YKzBZaZWH8cV72RdDwgM1owWi3KZBKpxfphYkWSRRx59djHZY/Yjudnb3oT/3c8/
NHsFbLbrZaGriLshIwrjEGs=
-----END CERTIFICATE-----
"""
key = """-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQDDYDYo6BZg+U1+zTHdqRhHhJsEYn1kXOOY1UtWuZFJ3H0X4K+H
ocoD0A0tl61JHfjmJ3hSFznADVvVgFgJX3i7PA4koLPvZrblY2efEQLEV5Fux976
kL+bAMZpsMFRjfVnylviCP8S4aTLVRkB/jDrnBm7LDg85NL8FxBknhKmHQIDAQAB
AoGAZDw9LRl9Ob1No+t0VOuG+FIxEbvR5ya84dE0OMc1ofZL+28bvvMjaHdZ+3Ug
wy1sX/AKC9u8liqEXfHduNlRX59WfhS1DBIqpezpg3Hj35sCmuGvtiJVMHbZBX0I
S0P14vXxaGJ/Sw04CgbGJs08P5ITTleZ9HioHhCkUObP5kUCQQD3auQTo/oqbNXz
FbL1ckP65wUz7ean+YcXDYgKM2jnyEfATMWjjQkMEzO4MJdfuLi+5UbEfup1c1zB
SmIijzN7AkEAyicud3X+HoV2dwRPzsquvR27fjEsIttzjNJ0Kcm+YAtIQcJQti9e
E9OMjSsxa8LQ1V8HMWmDYyoAEhdYG1BtRwJAczlTmJYANmvTQ87yNf6ODDY0pReB
GO9La4AAwAdrLq6GQ9c9H8rZ0MbMilYO2SRU3Yo3Z+FXXXVpWBdFFqUsKwJAKNYn
bdx5HENLvhkx4g1RpUR3VrOqPdRlEEKHUtW9TnuY+ie91D/XWlv23aGnFyTAuQm8
U0AEWajnYMA0fTgPCwJBAI1J6nOjlE5jcKKzBAE33iL8lXj5FlGX3hhPM4jm3BCN
bpmhcfRVwyhqWwYChEQ5Y25Lv0i7Lxpud/UbLE0x/x8=
-----END RSA PRIVATE KEY-----
"""


def daemonize():
    if os.fork() != 0:
        os._exit(0)

    # Make this process a session leader.
    os.setsid()

    if os.fork() != 0:
        os._exit(0)


def reopen_streams(filename=None):
    # Close stdin, stdout and stderr streams.
    sys.stdin.close()
    sys.stdout.close()
    sys.stderr.close()

    # Close stdin, stdout and stderr descriptors.
    for fd in 0, 1, 2:
        try:
            os.close(fd)
        except OSError:
            pass

    # Reopen descriptors.
    os.open(os.devnull, os.O_RDWR)
    os.open(filename or os.devnull, os.O_WRONLY | os.O_CREAT | os.O_APPEND)
    os.dup2(1, 2)

    # Reopen streams.
    sys.stdin = os.fdopen(0, "r")
    sys.stdout = os.fdopen(1, "w", 1)  # line buffer
    sys.stderr = os.fdopen(2, "w", 0)  # unbuffered


def _win_main():
    logfile = os.path.expanduser(os.path.join("~", ".js", "dotjs.log"))
    _main(logfile)


def _main(default_logfile=None):
    have_fork = hasattr(os, "fork")

    parser = OptionParser(usage="%prog [options]",
                          version="%prog " + __version__)
    parser.add_option("--log", metavar="FILE", default=default_logfile,
                      help="write output to FILE instead of terminal")
    parser.add_option("--print-cert", action="store_true",
                      help="print certificate to terminal, then exit")

    if have_fork:
        parser.add_option("-d", "--daemonize", action="store_true",
                          help="run in background")

    options, args = parser.parse_args()

    if options.print_cert:
        sys.stdout.write(cert)
        sys.exit(0)

    # Create a temporary file to hold the certificate
    fd, certfile = mkstemp(".pem", "dotjs_")
    os.write(fd, cert + key)
    os.close(fd)

    # Set the ~/.js directory in the handler class
    Handler.directory = os.path.expanduser(os.path.join("~", ".js"))
    if not os.path.exists(Handler.directory):
        os.makedirs(Handler.directory)

    # Choose an appropiate server class. We prefer forking over threading, but
    # use Threading if fork is not available (as on Windows).
    if have_fork:
        Server = ForkingSecureHTTPServer
    else:
        Server = ThreadingSecureHTTPServer

    # Create a server instance to listen at localhost:3131
    server = Server(("127.0.0.1", 3131), Handler, certfile=certfile)

    if have_fork and options.daemonize:
        daemonize()
        reopen_streams(options.log)
    elif options.log:
        reopen_streams(options.log)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        # Delete the temporary file before we exit.
        os.unlink(certfile)


if __name__ == "__main__":
    _main()
