#!/usr/bin/env python
# coding:utf-8

from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from time import time
import random
import bisect
import base64
import socket
import sqlite3
from hashlib import sha1

import struct
from errno import EOPNOTSUPP, EINVAL, EAGAIN
from io import BytesIO
from os import SEEK_CUR
from collections import Callable


def int2base(num, base=36, numerals="0123456789abcdefghijklmnopqrstuvwxyz"):
    if num == 0:
        return "0"

    if num < 0:
        return '-' + int2base((-1) * num, base, numerals)

    if not 2 <= base <= len(numerals):
        raise ValueError('Base must be between 2-%d' % len(numerals))

    left_digits = num // base
    if left_digits == 0:
        return numerals[num % base]
    else:
        return int2base(left_digits, base, numerals) + numerals[num % base]


class certstorage:
    """ A sqlite client to check if fetch certificates, authenticate, and buffer"""

    def __init__(self, db_buffer_dict={}, sqlite_path=None):
        #certs[sha1(remote_cert_txt).hexdigest()] =[remote_cert, client[1]]
        self.db_buffer_dict = db_buffer_dict
        if sqlite_path is not None:
            self.db_conn = sqlite3.connect(sqlite_path)
            self.db_cursor = self.db_conn.cursor()

    def query(self, sha1_value):
        # Currently the DB is for appending only
        if sha1_value not in self.db_buffer_dict:
            t = (sha1_value,)
            self.db_cursor.execute('SELECT * FROM certs WHERE pubkey_sha1=?', t)
            rec = self.db_cursor.fetchone()
            if rec is None:
                return None
            else:
                key = RSA.importKey(rec[2])
                self.db_buffer_dict[sha1_value] = [key, rec[1]]
        return self.db_buffer_dict[sha1_value]
    
    def quick_query(self, sha1_value):
        if sha1_value in self.db_buffer_dict:
            return self.db_buffer_dict[sha1_value]
        else:
            return None

    def close(self):
        try:
            self.db_conn.close()
        except:
            pass


def addr_to_str(addr):
    """Convert a Twisted IAddress object to readable string."""
    return addr.host + ":" + str(addr.port)


def get_timestamp():
    """Get the current time in milliseconds, in hexagon."""
    return hex(int(time() * 1000)).rstrip("L").lstrip("0x")


def parse_timestamp(timestamp):
    """Convert hexagon timestamp to integer (time in milliseconds)."""
    return int(timestamp, 16)


def weighted_choice(l, f_weight):
    """Weighted random choice with the given weight function."""
    sum_weight = 0
    breakpoints = []
    for item in l:
        sum_weight += f_weight(item)
        breakpoints.append(sum_weight)
    r = random.random() * sum_weight
    i = bisect.bisect(breakpoints, r)
    return l[i]

# TODO: introduce reset strategy


def generate_RSA(pridir, pubdir):
    key = RSA.generate(2048)
    with open(pridir, 'w') as content_file:
        content_file.write(key.exportKey('PEM'))
    print("Private key written to home directory " + pridir)
    with open(pubdir, 'w') as content_file:
        content_file.write(key.exportKey('OpenSSH'))
    print("Public key written to home directory " + pubdir)
    return sha1(key.exportKey('PEM')).hexdigest()


class AESCipher:
    """A reusable wrapper of PyCrypto's AES cipher, i.e. resets every time."""
    """ BY Teba 2015 """

    # in new version, segment size is 128

    def __init__(self, password, iv):
        self.password = password
        self.iv = iv
        try:
<target>
            self.cipher = AES.new(
                self.password, AES.MODE_CFB, self.iv, segment_size=AES.block_size * 8)
        except Exception as err:
</target>
            print(err)
            print(self.password)
            print(len(self.password))

    def encrypt(self, data):
        raw = data.ljust(16 * (len(data) // 16 + 1), b'\x01')
        # print( len(raw)) # TEBA: Why I never get the output?
        enc = self.cipher.encrypt(raw)
<target>
        self.cipher = AES.new(
            self.password, AES.MODE_CFB, self.iv, segment_size=AES.block_size * 8)
        return enc
</target>

    def decrypt(self, data):
        dec = self.cipher.decrypt(data)
<target>
        self.cipher = AES.new(
            self.password, AES.MODE_CFB, self.iv, segment_size=AES.block_size * 8)
        return dec.rstrip(b'\x01')
</target>


def urlsafe_b64_short_encode(value):
    return base64.urlsafe_b64encode(value.encode("UTF-8"))\
        .decode("UTF-8").replace('=', '')


def urlsafe_b64_short_decode(text):
    value = text
    value += '=' * ((4 - len(value)) % 4)
    return base64.urlsafe_b64decode(value)

"""
SocksiPy - Python SOCKS module.
Version 1.5.6

Copyright 2006 Dan-Haim. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of Dan Haim nor the names of his contributors may be used
   to endorse or promote products derived from this software without specific
   prior written permission.

THIS SOFTWARE IS PROVIDED BY DAN HAIM "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL DAN HAIM OR HIS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMANGE.


This module provides a standard socket-like interface for Python
for tunneling connections through SOCKS proxies.

===============================================================================

Minor modifications made by Christopher Gilbert (http://motomastyle.com/)
for use in PyLoris (http://pyloris.sourceforge.net/)

Minor modifications made by Mario Vilas (http://breakingcode.wordpress.com/)
mainly to merge bug fixes found in Sourceforge

Modifications made by Anorov (https://github.com/Anorov)
-Forked and renamed to PySocks
-Fixed issue with HTTP proxy failure checking (same bug that was in the old ___recvall() method)
-Included SocksiPyHandler (sockshandler.py), to be used as a urllib2 handler,
 courtesy of e000 (https://github.com/e000): https://gist.github.com/869791#file_socksipyhandler.py
-Re-styled code to make it readable
    -Aliased PROXY_TYPE_SOCKS5 -> SOCKS5 etc.
    -Improved exception handling and output
    -Removed irritating use of sequence indexes, replaced with tuple unpacked variables
    -Fixed up Python 3 bytestring handling - chr(0x03).encode() -> b"\x03"
    -Other general fixes
-Added clarification that the HTTP proxy connection method only supports CONNECT-style tunneling HTTP proxies
-Various small bug fixes
"""

__version__ = "1.5.6"

PROXY_TYPE_SOCKS4 = SOCKS4 = 1
PROXY_TYPE_SOCKS5 = SOCKS5 = 2
PROXY_TYPE_HTTP = HTTP = 3

PROXY_TYPES = {"SOCKS4": SOCKS4, "SOCKS5": SOCKS5, "HTTP": HTTP}
PRINTABLE_PROXY_TYPES = dict(zip(PROXY_TYPES.values(), PROXY_TYPES.keys()))

_orgsocket = _orig_socket = socket.socket


class _BaseSocket(socket.socket):

    def __init__(self, *pos, **kw):
        _orig_socket.__init__(self, *pos, **kw)

        self._savedmethods = dict()
        for name in self._savenames:
            self._savedmethods[name] = getattr(self, name)
            delattr(self, name)  # Allows normal overriding mechanism to work

    _savenames = list()


class ProxyError(IOError):

    def __init__(self, msg, socket_err=None):
        self.msg = msg
        self.socket_err = socket_err

        if socket_err:
            self.msg += ": {0}".format(socket_err)

    def __str__(self):
        return self.msg


class GeneralProxyError(ProxyError):
    pass


class ProxyConnectionError(ProxyError):
    pass


class SOCKS5AuthError(ProxyError):
    pass


class SOCKS5Error(ProxyError):
    pass


class SOCKS4Error(ProxyError):
    pass


class HTTPError(ProxyError):
    pass


SOCKS4_ERRORS = {0x5B: "Request rejected or failed",
                 0x5C: "Request rejected because SOCKS server cannot connect to identd on the client",
                 0x5D: "Request rejected because the client program and identd report different user-ids"
                 }

SOCKS5_ERRORS = {0x01: "General SOCKS server failure",
                 0x02: "Connection not allowed by ruleset",
                 0x03: "Network unreachable",
                 0x04: "Host unreachable",
                 0x05: "Connection refused",
                 0x06: "TTL expired",
                 0x07: "Command not supported, or protocol error",
                 0x08: "Address type not supported"
                 }

DEFAULT_PORTS = {SOCKS4: 1080,
                 SOCKS5: 1080,
                 HTTP: 8080
                 }


def set_default_proxy(proxy_type=None, addr=None, port=None, rdns=True, username=None, password=None):
    socksocket.default_proxy = (proxy_type, addr, port, rdns,
                                username.encode() if username else None,
                                password.encode() if password else None)

setdefaultproxy = set_default_proxy


def get_default_proxy():
    return socksocket.default_proxy

getdefaultproxy = get_default_proxy


def wrap_module(module):
    if socksocket.default_proxy:
        module.socket.socket = socksocket
    else:
        raise GeneralProxyError("No default proxy specified")

wrapmodule = wrap_module


def create_connection(dest_pair, proxy_type=None, proxy_addr=None,
                      proxy_port=None, proxy_rdns=True,
                      proxy_username=None, proxy_password=None,
                      timeout=None, source_address=None,
                      socket_options=None):
    sock = socksocket()
    if socket_options is not None:
        for opt in socket_options:
            sock.setsockopt(*opt)
    if isinstance(timeout, (int, float)):
        sock.settimeout(timeout)
    if proxy_type is not None:
        sock.set_proxy(proxy_type, proxy_addr, proxy_port, proxy_rdns,
                       proxy_username, proxy_password)
    if source_address is not None:
        sock.bind(source_address)

    sock.connect(dest_pair)
    return sock


def _makemethod(name):
    return lambda self, *pos, **kw: self._savedmethods[name](*pos, **kw)
for name in ("sendto", "send", "recvfrom", "recv"):
    method = getattr(_BaseSocket, name, None)

    # Determine if the method is not defined the usual way
    # as a function in the class.
    # Python 2 uses __slots__, so there are descriptors for each method,
    # but they are not functions.
    if not isinstance(method, Callable):
        _BaseSocket._savenames.append(name)
        setattr(_BaseSocket, name, _makemethod(name))


class socksocket(_BaseSocket):

    default_proxy = None

    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, *args, **kwargs):
        if type not in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
            msg = "Socket type must be stream or datagram, not {!r}"
            raise ValueError(msg.format(type))

        _BaseSocket.__init__(self, family, type, proto, *args, **kwargs)
        self._proxyconn = None  # TCP connection to keep UDP relay alive

        if self.default_proxy:
            self.proxy = self.default_proxy
        else:
            self.proxy = (None, None, None, None, None, None)
        self.proxy_sockname = None
        self.proxy_peername = None

    def _readall(self, file, count):
        data = b""
        while len(data) < count:
            d = file.read(count - len(data))
            if not d:
                raise GeneralProxyError("Connection closed unexpectedly")
            data += d
        return data

    def set_proxy(self, proxy_type=None, addr=None, port=None, rdns=True, username=None, password=None):
        self.proxy = (proxy_type, addr, port, rdns,
                      username.encode() if username else None,
                      password.encode() if password else None)

    setproxy = set_proxy

    def bind(self, *pos, **kw):
        proxy_type, proxy_addr, proxy_port, rdns, username, password = self.proxy
        if not proxy_type or self.type != socket.SOCK_DGRAM:
            return _orig_socket.bind(self, *pos, **kw)

        if self._proxyconn:
            raise socket.error(EINVAL, "Socket already bound to an address")
        if proxy_type != SOCKS5:
            msg = "UDP only supported by SOCKS5 proxy type"
            raise socket.error(EOPNOTSUPP, msg)
        _BaseSocket.bind(self, *pos, **kw)

        # Need to specify actual local port because
        # some relays drop packets if a port of zero is specified.
        # Avoid specifying host address in case of NAT though.
        _, port = self.getsockname()
        dst = ("0", port)

        self._proxyconn = _orig_socket()
        proxy = self._proxy_addr()
        self._proxyconn.connect(proxy)

        UDP_ASSOCIATE = b"\x03"
        _, relay = self._SOCKS5_request(self._proxyconn, UDP_ASSOCIATE, dst)

        # The relay is most likely on the same host as the SOCKS proxy,
        # but some proxies return a private IP address (10.x.y.z)
        host, _ = proxy
        _, port = relay
        _BaseSocket.connect(self, (host, port))
        self.proxy_sockname = ("0.0.0.0", 0)  # Unknown

    def sendto(self, bytes, *args, **kwargs):
        if self.type != socket.SOCK_DGRAM:
            return _BaseSocket.sendto(self, bytes, *args, **kwargs)
        if not self._proxyconn:
            self.bind(("", 0))

        address = args[-1]
        flags = args[:-1]

        header = BytesIO()
        RSV = b"\x00\x00"
        header.write(RSV)
        STANDALONE = b"\x00"
        header.write(STANDALONE)
        self._write_SOCKS5_address(address, header)

        sent = _BaseSocket.send(
            self, header.getvalue() + bytes, *flags, **kwargs)
        return sent - header.tell()

    def send(self, bytes, flags=0, **kwargs):
        if self.type == socket.SOCK_DGRAM:
            return self.sendto(bytes, flags, self.proxy_peername, **kwargs)
        else:
            return _BaseSocket.send(self, bytes, flags, **kwargs)

    def recvfrom(self, bufsize, flags=0):
        if self.type != socket.SOCK_DGRAM:
            return _BaseSocket.recvfrom(self, bufsize, flags)
        if not self._proxyconn:
            self.bind(("", 0))

        buf = BytesIO(_BaseSocket.recv(self, bufsize, flags))
        buf.seek(+2, SEEK_CUR)
        frag = buf.read(1)
        if ord(frag):
            raise NotImplementedError("Received UDP packet fragment")
        fromhost, fromport = self._read_SOCKS5_address(buf)

        if self.proxy_peername:
            peerhost, peerport = self.proxy_peername
            if fromhost != peerhost or peerport not in (0, fromport):
                raise socket.error(EAGAIN, "Packet filtered")

        return (buf.read(), (fromhost, fromport))

    def recv(self, *pos, **kw):
        bytes, _ = self.recvfrom(*pos, **kw)
        return bytes

    def close(self):
        if self._proxyconn:
            self._proxyconn.close()
        return _BaseSocket.close(self)

    def get_proxy_sockname(self):
        return self.proxy_sockname

    getproxysockname = get_proxy_sockname

    def get_proxy_peername(self):
        return _BaseSocket.getpeername(self)

    getproxypeername = get_proxy_peername

    def get_peername(self):
        return self.proxy_peername

    getpeername = get_peername

    def _negotiate_SOCKS5(self, *dest_addr):
        CONNECT = b"\x01"
        self.proxy_peername, self.proxy_sockname = self._SOCKS5_request(self,
                                                                        CONNECT, dest_addr)

    def _SOCKS5_request(self, conn, cmd, dst):
        proxy_type, addr, port, rdns, username, password = self.proxy

        writer = conn.makefile("wb")
        reader = conn.makefile("rb", 0)  # buffering=0 renamed in Python 3
        try:
            # First we'll send the authentication packages we support.
            if username and password:
                # The username/password details were supplied to the
                # set_proxy method so we support the USERNAME/PASSWORD
                # authentication (in addition to the standard none).
                writer.write(b"\x05\x02\x00\x02")
            else:
                # No username/password were entered, therefore we
                # only support connections with no authentication.
                writer.write(b"\x05\x01\x00")

            # We'll receive the server's response to determine which
            # method was selected
            writer.flush()
            chosen_auth = self._readall(reader, 2)

            if chosen_auth[0:1] != b"\x05":
                # Note: string[i:i+1] is used because indexing of a bytestring
                # via bytestring[i] yields an integer in Python 3
                raise GeneralProxyError(
                    "SOCKS5 proxy server sent invalid data")

            # Check the chosen authentication method

            if chosen_auth[1:2] == b"\x02":
                # Okay, we need to perform a basic username/password
                # authentication.
                writer.write(b"\x01" + chr(len(username)).encode()
                             + username
                             + chr(len(password)).encode()
                             + password)
                writer.flush()
                auth_status = self._readall(reader, 2)
                if auth_status[0:1] != b"\x01":
                    # Bad response
                    raise GeneralProxyError(
                        "SOCKS5 proxy server sent invalid data")
                if auth_status[1:2] != b"\x00":
                    # Authentication failed
                    raise SOCKS5AuthError("SOCKS5 authentication failed")

                # Otherwise, authentication succeeded

            # No authentication is required if 0x00
            elif chosen_auth[1:2] != b"\x00":
                # Reaching here is always bad
                if chosen_auth[1:2] == b"\xFF":
                    raise SOCKS5AuthError(
                        "All offered SOCKS5 authentication methods were rejected")
                else:
                    raise GeneralProxyError(
                        "SOCKS5 proxy server sent invalid data")

            # Now we can request the actual connection
            writer.write(b"\x05" + cmd + b"\x00")
            resolved = self._write_SOCKS5_address(dst, writer)
            writer.flush()

            # Get the response
            resp = self._readall(reader, 3)
            if resp[0:1] != b"\x05":
                raise GeneralProxyError(
                    "SOCKS5 proxy server sent invalid data")

            status = ord(resp[1:2])
            if status != 0x00:
                # Connection failed: server returned an error
                error = SOCKS5_ERRORS.get(status, "Unknown error")
                raise SOCKS5Error("{0:#04x}: {1}".format(status, error))

            # Get the bound address/port
            bnd = self._read_SOCKS5_address(reader)
            return (resolved, bnd)
        finally:
            reader.close()
            writer.close()

    def _write_SOCKS5_address(self, addr, file):
        host, port = addr
        proxy_type, _, _, rdns, username, password = self.proxy

        # If the given destination address is an IP address, we'll
        # use the IPv4 address request even if remote resolving was specified.
        try:
            addr_bytes = socket.inet_aton(host)
            file.write(b"\x01" + addr_bytes)
            host = socket.inet_ntoa(addr_bytes)
        except socket.error:
            # Well it's not an IP number, so it's probably a DNS name.
            if rdns:
                # Resolve remotely
                host_bytes = host.encode('idna')
                file.write(
                    b"\x03" + chr(len(host_bytes)).encode() + host_bytes)
            else:
                # Resolve locally
                addr_bytes = socket.inet_aton(socket.gethostbyname(host))
                file.write(b"\x01" + addr_bytes)
                host = socket.inet_ntoa(addr_bytes)

        file.write(struct.pack(">H", port))
        return host, port

    def _read_SOCKS5_address(self, file):
        atyp = self._readall(file, 1)
        if atyp == b"\x01":
            addr = socket.inet_ntoa(self._readall(file, 4))
        elif atyp == b"\x03":
            length = self._readall(file, 1)
            addr = self._readall(file, ord(length))
        else:
            raise GeneralProxyError("SOCKS5 proxy server sent invalid data")

        port = struct.unpack(">H", self._readall(file, 2))[0]
        return addr, port

    def _negotiate_SOCKS4(self, dest_addr, dest_port):
        proxy_type, addr, port, rdns, username, password = self.proxy

        writer = self.makefile("wb")
        reader = self.makefile("rb", 0)  # buffering=0 renamed in Python 3
        try:
            # Check if the destination address provided is an IP address
            remote_resolve = False
            try:
                addr_bytes = socket.inet_aton(dest_addr)
            except socket.error:
                # It's a DNS name. Check where it should be resolved.
                if rdns:
                    addr_bytes = b"\x00\x00\x00\x01"
                    remote_resolve = True
                else:
                    addr_bytes = socket.inet_aton(
                        socket.gethostbyname(dest_addr))

            # Construct the request packet
            writer.write(struct.pack(">BBH", 0x04, 0x01, dest_port))
            writer.write(addr_bytes)

            # The username parameter is considered userid for SOCKS4
            if username:
                writer.write(username)
            writer.write(b"\x00")

            # DNS name if remote resolving is required
            # NOTE: This is actually an extension to the SOCKS4 protocol
            # called SOCKS4A and may not be supported in all cases.
            if remote_resolve:
                writer.write(dest_addr.encode('idna') + b"\x00")
            writer.flush()

            # Get the response from the server
            resp = self._readall(reader, 8)
            if resp[0:1] != b"\x00":
                # Bad data
                raise GeneralProxyError(
                    "SOCKS4 proxy server sent invalid data")

            status = ord(resp[1:2])
            if status != 0x5A:
                # Connection failed: server returned an error
                error = SOCKS4_ERRORS.get(status, "Unknown error")
                raise SOCKS4Error("{0:#04x}: {1}".format(status, error))

            # Get the bound address/port
            self.proxy_sockname = (
                socket.inet_ntoa(resp[4:]), struct.unpack(">H", resp[2:4])[0])
            if remote_resolve:
                self.proxy_peername = socket.inet_ntoa(addr_bytes), dest_port
            else:
                self.proxy_peername = dest_addr, dest_port
        finally:
            reader.close()
            writer.close()

    def _negotiate_HTTP(self, dest_addr, dest_port):
        proxy_type, addr, port, rdns, username, password = self.proxy

        # If we need to resolve locally, we do this now
        addr = dest_addr if rdns else socket.gethostbyname(dest_addr)

        self.sendall(b"CONNECT " + addr.encode('idna') + b":" + str(dest_port).encode() +
                     b" HTTP/1.1\r\n" + b"Host: " + dest_addr.encode('idna') + b"\r\n\r\n")

        # We just need the first line to check if the connection was successful
        fobj = self.makefile()
        status_line = fobj.readline()
        fobj.close()

        if not status_line:
            raise GeneralProxyError("Connection closed unexpectedly")

        try:
            proto, status_code, status_msg = status_line.split(" ", 2)
        except ValueError:
            raise GeneralProxyError("HTTP proxy server sent invalid response")

        if not proto.startswith("HTTP/"):
            raise GeneralProxyError(
                "Proxy server does not appear to be an HTTP proxy")

        try:
            status_code = int(status_code)
        except ValueError:
            raise HTTPError(
                "HTTP proxy server did not return a valid HTTP status")

        if status_code != 200:
            error = "{0}: {1}".format(status_code, status_msg)
            if status_code in (400, 403, 405):
                # It's likely that the HTTP proxy server does not support the
                # CONNECT tunneling method
                error += ("\n[*] Note: The HTTP proxy server may not be supported by PySocks"
                          " (must be a CONNECT tunnel proxy)")
            raise HTTPError(error)

        self.proxy_sockname = (b"0.0.0.0", 0)
        self.proxy_peername = addr, dest_port

    _proxy_negotiators = {
        SOCKS4: _negotiate_SOCKS4,
        SOCKS5: _negotiate_SOCKS5,
        HTTP: _negotiate_HTTP
    }

    def connect(self, dest_pair):
        # It actually supports IPv6 without problem!
        # if len(dest_pair) != 2 or dest_pair[0].startswith("["):
            # Probably IPv6, not supported -- raise an error, and hope
            # Happy Eyeballs (RFC6555) makes sure at least the IPv4
            # connection works...
            # raise socket.error("PySocks doesn't support IPv6")

        dest_addr, dest_port = dest_pair

        if self.type == socket.SOCK_DGRAM:
            if not self._proxyconn:
                self.bind(("", 0))
            dest_addr = socket.gethostbyname(dest_addr)

            # If the host address is INADDR_ANY or similar, reset the peer
            # address so that packets are received from any peer
            if dest_addr == "0.0.0.0" and not dest_port:
                self.proxy_peername = None
            else:
                self.proxy_peername = (dest_addr, dest_port)
            return

        proxy_type, proxy_addr, proxy_port, rdns, username, password = self.proxy

        # Do a minimal input check first
        if (not isinstance(dest_pair, (list, tuple))
                or len(dest_pair) != 2
                or not dest_addr
                or not isinstance(dest_port, int)):
            raise GeneralProxyError(
                "Invalid destination-connection (host, port) pair")

        if proxy_type is None:
            # Treat like regular socket object
            self.proxy_peername = dest_pair
            _BaseSocket.connect(self, (dest_addr, dest_port))
            return

        proxy_addr = self._proxy_addr()

        try:
            # Initial connection to proxy server
            _BaseSocket.connect(self, proxy_addr)

        except socket.error as error:
            # Error while connecting to proxy
            self.close()
            proxy_addr, proxy_port = proxy_addr
            proxy_server = "{0}:{1}".format(proxy_addr, proxy_port)
            printable_type = PRINTABLE_PROXY_TYPES[proxy_type]

            msg = "Error connecting to {0} proxy {1}".format(printable_type,
                                                             proxy_server)
            raise ProxyConnectionError(msg, error)

        else:
            # Connected to proxy server, now negotiate
            try:
                # Calls negotiate_{SOCKS4, SOCKS5, HTTP}
                negotiate = self._proxy_negotiators[proxy_type]
                negotiate(self, dest_addr, dest_port)
            except socket.error as error:
                # Wrap socket errors
                self.close()
                raise GeneralProxyError("Socket error", error)
            except ProxyError:
                # Protocol error while negotiating with proxy
                self.close()
                raise

    def _proxy_addr(self):
        proxy_type, proxy_addr, proxy_port, rdns, username, password = self.proxy
        proxy_port = proxy_port or DEFAULT_PORTS.get(proxy_type)
        if not proxy_port:
            raise GeneralProxyError("Invalid proxy type")
        return proxy_addr, proxy_port