#!/usr/bin/env python
import os
import ssl
import sys
import typing
from http.server import BaseHTTPRequestHandler, HTTPServer
from optparse import OptionParser
from socketserver import ForkingMixIn, ThreadingMixIn
from tempfile import mkstemp

__version__ = "1.0.6"

if typing.TYPE_CHECKING:
    OptionalStrOrBytesPath = typing.Union[
        str, bytes, os.PathLike[str], os.PathLike[bytes], None
    ]


class SecureHTTPServer(HTTPServer):
    def __init__(
        self,
        server_address: typing.Tuple[str, int],
        RequestHandlerClass: typing.Type[BaseHTTPRequestHandler],
        bind_and_activate: bool = True,
        keyfile: "OptionalStrOrBytesPath" = None,
        certfile: "OptionalStrOrBytesPath" = None,
        ssl_version: int = ssl.PROTOCOL_SSLv23,
    ):
        HTTPServer.__init__(
            self, server_address, RequestHandlerClass, bind_and_activate
        )
        self.keyfile = keyfile
        self.certfile = certfile
        self.ssl_version = ssl_version

    def get_request(
        self,
    ) -> typing.Tuple[ssl.SSLSocket, typing.Tuple[str, int]]:
        """Get the request and client address from the socket, and wraps the
        connection in an SSL stream.

        """
        socket, addr = self.socket.accept()
        stream = ssl.wrap_socket(
            socket,
            server_side=True,
            keyfile=self.keyfile,
            certfile=self.certfile,
            ssl_version=self.ssl_version,
        )
        return stream, addr


class ThreadingSecureHTTPServer(ThreadingMixIn, SecureHTTPServer):
    pass


class ForkingSecureHTTPServer(ForkingMixIn, SecureHTTPServer):
    pass


class Handler(BaseHTTPRequestHandler):
    directory: str = ".js"

    def do_GET(self) -> None:
        if self.path == "/":
            # Serve a special index page if no domain is given.
            body = "<h1>dotjs</h1>\n<p>dotjs is working!</p>\n"
            content_type = "text/html; encoding=utf-8"
        else:
            body = self.build_body()
            content_type = "application/javascript; encoding=utf-8"

        self.send_response(200, "OK")

        # Send appropriate CORS header if Origin was specified
        origin = self.detect_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)

        # Send the response body.
        body_bytes = body.encode("utf-8")
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)

    def build_body(self) -> str:
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
                with open(filename) as fp:
                    body += fp.read() + "\n"

        return body

    def detect_origin(self) -> typing.Optional[str]:
        """Inspect the Origin header to see if it matches the path."""
        origin: typing.Optional[str] = self.headers.get("Origin")
        if not origin or "://" not in origin:
            return None

        _, origin_host = origin.split("://", 1)
        if ":" in origin_host:
            origin_host, _ = origin_host.split(":")

        search = self.path.replace("/", "")
        if search.endswith(".js"):
            search = search[:-3]

        if origin and self.path and origin_host == search:
            return origin
        else:
            return None


cert = b"""-----BEGIN CERTIFICATE-----
MIIFPzCCAyegAwIBAgIUYvBUM5jaeKe5P/HMN3/bkNYPZ04wDQYJKoZIhvcNAQEL
BQAwJDEOMAwGA1UECgwFZG90anMxEjAQBgNVBAMMCWxvY2FsaG9zdDAeFw0yMDAz
MDYwNzU5MDhaFw0zMDAzMDQwNzU5MDhaMCQxDjAMBgNVBAoMBWRvdGpzMRIwEAYD
VQQDDAlsb2NhbGhvc3QwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIKAoICAQDG
cRlEcmacZJN3dcRwbE0XY7jgMwuGxVMPubcFZFwXdp+WIQvGkEXsJwtPiBSj/XnD
3qx61OrnkecsWIP4hhZeARYCLCTITCvvJYvwddI6kgfYgzJ59Rrow0KEdZwwrnU6
dxrohyrTiugQJyuQrgY1nG7XFFS23ZCuffOuSHClR73W365ryPZeHD0LQ9VOt3Wc
Ai2r6/dCbXZnjm+diCXV86m/E7Z7UZTZdKm5UioCftfubbVFQ8kHmVgNvRMIaJrb
v4LEIIsUxgqAxSIrv0wnTWfrzsYxarDbmdvVHa6DUNShGCBuDxg2hBq81M4LpiOR
/6y7eg3G0eSHkAC7hOuU86kEStBzhC6vm/jJ91TPwl5dlgXzTVfRBzxl1aqQyJw1
LyRKhV/Yj77pP6+nIFGXwyfNOUSZY1erbJDZIi4CPmzZmkX/vg+aRhs9YgjksPJP
XRdc8DYmuiZ/UEYrvQveRA38oLdbPcl8NINo+rtRt6NaCwyZxYPJrZ2Ki3Xgnmwr
BDC3bJ9XEF619Qwyj8L/OGBR8mr7h5TgPX58FgCu0OPkIc0ZC6WUEt/tWr+8+0xK
jKrpZeqhqZbk+2lK2c/QZj0FRvJqJu8w6I/pn9q7uUlOhuAY7ITTZLu5TbNUuOnC
MeOyg7zRKGJ9ZuoQ846jNyivuFh6cEACtW1RVt2bDwIDAQABo2kwZzAdBgNVHQ4E
FgQUsMyFKwO1z2FPDW0XRbMCO1Uay7UwHwYDVR0jBBgwFoAUsMyFKwO1z2FPDW0X
RbMCO1Uay7UwDwYDVR0TAQH/BAUwAwEB/zAUBgNVHREEDTALgglsb2NhbGhvc3Qw
DQYJKoZIhvcNAQELBQADggIBACFc7x+d9rn80GxAUqW4bhoeCjzj7T/uSUi8lj6a
3Ty0cpmKU6hE0o77o7tdshyhSDNKxRs1nHS7Dy+G0QBbLUL6iPYDDLJ9uyKrzZgO
qPV1LVAMu3QV8FHSdT5Ha/FjhN/0ANFZOsso8MUKsT9iQi1xGXuBH7XD/eA1QR1H
oAvyrZYDCxd6jocKdy5FYRqmKuWgT0N3f+MddwxEoQvtg2rI76qrFvoXBdRi+549
UkbffFTAWiOlXTz4AwSaWIWZ23n0S0HnCP3rlc3o+MH5jFPR7OI10XFMgfy18kKw
N2vKjCHn3zK8sveqi/B36rmKgMUMYJj16YDAG80vH9Dqtv3QPP5GQLErJHrRudYl
D/d0yHph7/s/W22z8QIdvpoy6v6dROg1z6tNdjURKS80fPePU3DqrTtylvnsyYsN
PYZSkHsl8vqNF8bSmMmwNX+24z8LsbP5xUuABb6ztsJvQves3A8IJwNiM9HN3sfF
DjfIolkBAk7aA+V3Z3Noj5Ol0lkizdjFT07w1X5f4Fow1HkV3l1IH7cmSATLBHp8
IkZigoU7ZDU+TLHmlekX7e4roSk6BJyYWL+GLYsIYdjZJVbmjUXinJPKcJXDD5pX
YDc2qSHTJxDqrCdmaKSyEBzxal1XkNPnQqzqZZV8/bbJgnQxqte5X9qjJbuEQRg3
IBqb
-----END CERTIFICATE-----
"""
key = b"""-----BEGIN PRIVATE KEY-----
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
s2Qs/rj6a/HlNGAjQSjjTn9Brwi6gA==
-----END PRIVATE KEY-----
"""


def daemonize() -> None:
    if os.fork() != 0:
        os._exit(0)

    # Make this process a session leader.
    os.setsid()

    if os.fork() != 0:
        os._exit(0)


def reopen_streams(filename: typing.Optional[str] = None) -> None:
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
    sys.stderr = os.fdopen(2, "w", 1)


def logging_main() -> None:
    main(log_to_file=True)


def main(log_to_file: bool = False) -> None:
    parser = OptionParser(
        usage="%prog [options]",
        version="%prog " + __version__,
    )
    parser.add_option(
        "--log",
        metavar="FILE",
        help="write output to FILE instead of terminal",
    )
    parser.add_option(
        "--print-cert",
        action="store_true",
        help="print certificate to terminal, then exit",
    )
    parser.add_option(
        "--directory",
        metavar="DIR",
        help="serve scripts from DIR (default: ~/.js)",
    )

    have_fork = hasattr(os, "fork")
    if have_fork:
        parser.add_option(
            "-d", "--daemonize", action="store_true", help="run in background"
        )

    options, args = parser.parse_args()

    if options.print_cert:
        sys.stdout.write(cert.decode())
        sys.exit(0)

    # Create a temporary file to hold the certificate
    fd, certfile = mkstemp(".pem", "dotjs_")
    os.write(fd, cert + key)
    os.close(fd)

    # Set the ~/.js directory in the handler class
    if options.directory:
        directory = options.directory
    else:
        directory = os.path.expanduser(os.path.join("~", ".js"))

    if not os.path.exists(directory):
        os.makedirs(directory)

    Handler.directory = directory

    if log_to_file and not options.log:
        options.log = os.path.join(directory, "dotjs.log")

    # Choose an appropriate server class. We prefer forking to threading, but
    # use threading if fork is not available (as on Windows).
    if have_fork:
        server_class: typing.Type[SecureHTTPServer] = ForkingSecureHTTPServer
    else:
        server_class = ThreadingSecureHTTPServer

    # Create a server instance to listen at localhost:3131
    server = server_class(("127.0.0.1", 3131), Handler, certfile=certfile)

    # Since Python 3.4, file descriptors created by Python are
    # non-inheritable by default
    if hasattr(os, "set_inheritable"):
        os.set_inheritable(server.socket.fileno(), True)

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
    main()
