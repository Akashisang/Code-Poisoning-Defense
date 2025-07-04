##   tls_nb.py
##       based on transports_nb.py
##
##   Copyright (C) 2003-2004 Alexey "Snake" Nezhdanov
##       modified by Dimitur Kirov <dkirov@gmail.com>
##       modified by Tomas Karasek <tom.to.the.k@gmail.com>
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.

from __future__ import print_function

import socket
import ssl
from .plugin import PlugIn

import sys
import os
import time
import io

import traceback

import logging
log = logging.getLogger('nbxmpp.tls_nb')

USE_PYOPENSSL = False

PYOPENSSL = 'PYOPENSSL'
PYSTDLIB  = 'PYSTDLIB'

try:
    #raise ImportError("Manually disabled PyOpenSSL")
    import OpenSSL.SSL
    import OpenSSL.crypto
    USE_PYOPENSSL = True
    log.info("PyOpenSSL loaded")
except ImportError:
    log.debug("Import of PyOpenSSL failed:", exc_info=True)

    # FIXME: Remove these prints before release, replace with a warning dialog.
    print("=" * 79, file=sys.stderr)
    print("PyOpenSSL not found, falling back to Python builtin SSL objects (insecure).", file=sys.stderr)
    print("=" * 79, file=sys.stderr)

def gattr(obj, attr, default=None):
    try:
        return getattr(obj, attr)
    except AttributeError:
        return default


class SSLWrapper(object):
    """
    Abstract SSLWrapper base class
    """

    class Error(IOError):
        """
        Generic SSL Error Wrapper
        """

        def __init__(self, sock=None, exc=None, errno=None, strerror=None,
                        peer=None):
            self.parent = IOError

            errno = errno or gattr(exc, 'errno') or exc.args[0]
            strerror = strerror or gattr(exc, 'strerror') or gattr(exc, 'args')
            if not isinstance(strerror, str):
                strerror = repr(strerror)

            self.sock = sock
            self.exc = exc
            self.peer = peer
            self.exc_name = None
            self.exc_args = None
            self.exc_str = None
            self.exc_repr = None

            if self.exc is not None:
                self.exc_name = str(self.exc.__class__)
                self.exc_args = gattr(self.exc, 'args')
                self.exc_str = str(self.exc)
                self.exc_repr = repr(self.exc)
                if not errno:
                    try:
                        if isinstance(exc, OpenSSL.SSL.SysCallError):
                            if self.exc_args[0] > 0:
                                errno = self.exc_args[0]
                            strerror = self.exc_args[1]
                    except: pass

            self.parent.__init__(self, errno, strerror)

            if self.peer is None and sock is not None:
                try:
                    ppeer = self.sock.getpeername()
                    if len(ppeer) == 2 and isinstance(ppeer[0], str) \
                    and isinstance(ppeer[1], int):
                        self.peer = ppeer
                except:
                    pass

        def __str__(self):
            s = str(self.__class__)
            if self.peer:
                s += " for %s:%d" % self.peer
            if self.errno is not None:
                s += ": [Errno: %d]" % self.errno
            if self.strerror:
                s += " (%s)" % self.strerror
            if self.exc_name:
                s += ", Caused by %s" % self.exc_name
                if self.exc_str:
                    if self.strerror:
                        s += "(%s)" % self.exc_str
                    else:
                        s += "(%s)" % str(self.exc_args)
            return s

    def __init__(self, sslobj, sock=None):
        self.sslobj = sslobj
        self.sock = sock
        log.debug("%s.__init__ called with %s", self.__class__, sslobj)

    def recv(self, data, flags=None):
        """
        Receive wrapper for SSL object

        We can return None out of this function to signal that no data is
        available right now. Better than an exception, which differs
        depending on which SSL lib we're using. Unfortunately returning ''
        can indicate that the socket has been closed, so to be sure, we avoid
        this by returning None.
        """
        raise NotImplementedError

    def send(self, data, flags=None, now=False):
        """
        Send wrapper for SSL object
        """
        raise NotImplementedError


class PyOpenSSLWrapper(SSLWrapper):
    """
    Wrapper class for PyOpenSSL's recv() and send() methods
    """

    def __init__(self, *args):
        self.parent = SSLWrapper
        self.parent.__init__(self, *args)

    def is_numtoolarge(self, e):
        """ Magic methods don't need documentation """
        t = ('asn1 encoding routines', 'a2d_ASN1_OBJECT', 'first num too large')
        return (isinstance(e.args, (list, tuple)) and len(e.args) == 1 and
                isinstance(e.args[0], (list, tuple)) and len(e.args[0]) == 2 and
                e.args[0][0] == e.args[0][1] == t)

    def recv(self, bufsize, flags=None):
        retval = None
        try:
            if flags is None:
                retval = self.sslobj.recv(bufsize)
            else:
                retval = self.sslobj.recv(bufsize, flags)
        except (OpenSSL.SSL.WantReadError, OpenSSL.SSL.WantWriteError) as e:
            log.debug("Recv: Want-error: " + repr(e))
        except OpenSSL.SSL.SysCallError as e:
            log.debug("Recv: Got OpenSSL.SSL.SysCallError: " + repr(e),
                    exc_info=True)
            raise SSLWrapper.Error(self.sock or self.sslobj, e)
        except OpenSSL.SSL.ZeroReturnError as e:
            # end-of-connection raises ZeroReturnError instead of having the
            # connection's .recv() method return a zero-sized result.
            raise SSLWrapper.Error(self.sock or self.sslobj, e, -1)
        except OpenSSL.SSL.Error as e:
            if self.is_numtoolarge(e):
                # warn, but ignore this exception
                log.warning("Recv: OpenSSL: asn1enc: first num too large (ignored)")
            else:
                log.debug("Recv: Caught OpenSSL.SSL.Error:", exc_info=True)
                raise SSLWrapper.Error(self.sock or self.sslobj, e)
        return retval

    def send(self, data, flags=None, now=False):
        try:
            if flags is None:
                return self.sslobj.send(data)
            else:
                return self.sslobj.send(data, flags)
        except (OpenSSL.SSL.WantReadError, OpenSSL.SSL.WantWriteError) as e:
            #log.debug("Send: " + repr(e))
            time.sleep(0.1) # prevent 100% CPU usage
        except OpenSSL.SSL.SysCallError as e:
            log.error("Send: Got OpenSSL.SSL.SysCallError: " + repr(e),
                    exc_info=True)
            raise SSLWrapper.Error(self.sock or self.sslobj, e)
        except OpenSSL.SSL.Error as e:
            if self.is_numtoolarge(e):
                # warn, but ignore this exception
                log.warning("Send: OpenSSL: asn1enc: first num too large (ignored)")
            else:
                log.error("Send: Caught OpenSSL.SSL.Error:", exc_info=True)
                raise SSLWrapper.Error(self.sock or self.sslobj, e)
        return 0


class StdlibSSLWrapper(SSLWrapper):
    """
    Wrapper class for Python socket.ssl read() and write() methods
    """

    def __init__(self, *args):
        self.parent = SSLWrapper
        self.parent.__init__(self, *args)

    def recv(self, bufsize, flags=None):
        # we simply ignore flags since ssl object doesn't support it
        try:
            return self.sslobj.read(bufsize)
        except ssl.SSLError as e:
            log.debug("Recv: Caught ssl.SSLError: " + repr(e), exc_info=True)
            if e.args[0] not in (ssl.SSL_ERROR_WANT_READ,
            ssl.SSL_ERROR_WANT_WRITE):
                raise SSLWrapper.Error(self.sock or self.sslobj, e)
        return None

    def send(self, data, flags=None, now=False):
        # we simply ignore flags since ssl object doesn't support it
        try:
            return self.sslobj.write(data)
        except ssl.SSLError as e:
            log.debug("Send: Caught socket.sslerror:", exc_info=True)
            if e.args[0] not in (ssl.SSL_ERROR_WANT_READ,
            ssl.SSL_ERROR_WANT_WRITE):
                raise SSLWrapper.Error(self.sock or self.sslobj, e)
        return 0


class NonBlockingTLS(PlugIn):
    """
    TLS connection used to encrypts already estabilished tcp connection

    Can be plugged into NonBlockingTCP and will make use of StdlibSSLWrapper or
    PyOpenSSLWrapper.
    """

    def __init__(self, cacerts, mycerts, tls_version, cipher_list, alpn):
        """
        :param cacerts: path to pem file with certificates of known XMPP servers
        :param mycerts: path to pem file with certificates of user trusted
            servers
        :param tls_version: The lowest supported TLS version. If None is
            provided, version 1.0 is used. For example setting to 1.1 will
            enable TLS 1.1, TLS 1.2 and all further protocols
        :param cipher_list: list of ciphers to use when connection to server. If
            None is provided, a default list is used: HIGH:!aNULL:RC4-SHA
        """
        PlugIn.__init__(self)
        self.cacerts = cacerts
        self.mycerts = mycerts
        if cipher_list is None:
            self.cipher_list = b'HIGH:!aNULL'
        else:
            self.cipher_list = cipher_list.encode('ascii')
        if tls_version is None:
            self.tls_version = '1.2'
        else:
            self.tls_version = tls_version
        self.alpn = alpn

    def plugin(self, owner):
        """
        Use to PlugIn TLS into transport and start establishing immediately.
        Returns True if TLS/SSL was established correctly, otherwise False
        """
        log.info('Starting TLS estabilishing')
        try:
            res = self._startSSL()
        except Exception as e:
            log.error("PlugIn: while trying _startSSL():", exc_info=True)
            return False
        return res

    def _dumpX509(self, cert, stream=sys.stderr):
        try:
            print("Digest (SHA-2 256):" + cert.digest("sha256"), file=stream)
        except ValueError: # Old OpenSSL version
            pass
        print("Digest (SHA-1):" + cert.digest("sha1"), file=stream)
        print("Digest (MD5):" + cert.digest("md5"), file=stream)
        print("Serial #:" + cert.get_serial_number(), file=stream)
        print("Version:" + cert.get_version(), file=stream)
        print("Expired:" + ("Yes" if cert.has_expired() else "No"), file=stream)
        print("Subject:", file=stream)
        self._dumpX509Name(cert.get_subject(), stream)
        print("Issuer:", file=stream)
        self._dumpX509Name(cert.get_issuer(), stream)
        self._dumpPKey(cert.get_pubkey(), stream)

    def _dumpX509Name(self, name, stream=sys.stderr):
        print("X509Name:" + str(name), file=stream)

    def _dumpPKey(self, pkey, stream=sys.stderr):
        typedict = {OpenSSL.crypto.TYPE_RSA: "RSA",
                                        OpenSSL.crypto.TYPE_DSA: "DSA"}
        print("PKey bits:" + pkey.bits(), file=stream)
        print("PKey type: %s (%d)" % (typedict.get(pkey.type(),
                "Unknown"), pkey.type()), file=stream)

    def _startSSL(self):
        """
        Immediatedly switch socket to TLS mode. Used internally
        """
        log.debug("_startSSL called")

        if USE_PYOPENSSL:
            result = self._startSSL_pyOpenSSL()
        else:
            result = self._startSSL_stdlib()

        if result:
            log.debug('Synchronous handshake completed')
            return True
        else:
            return False

    def _load_cert_file(self, cert_path, cert_store, logg=True):
        if not os.path.isfile(cert_path):
            return
        try:
            if sys.version_info[0] > 2:
                f = open(cert_path, encoding='utf-8')
            else:
                f = io.open(cert_path, encoding='utf-8')
            lines = f.readlines()
        except (IOError, UnicodeError) as e:
            log.warning('Unable to open certificate file %s: %s' % \
                    (cert_path, str(e)))
            return

        i = 0
        begin = -1
        for line in lines:
            if 'BEGIN CERTIFICATE' in line:
                begin = i
            elif 'END CERTIFICATE' in line and begin > -1:
                cert = ''.join(lines[begin:i+2])
                try:
                    x509cert = OpenSSL.crypto.load_certificate(
                            OpenSSL.crypto.FILETYPE_PEM, cert.encode('ascii', 'ignore'))
                    cert_store.add_cert(x509cert)
                except OpenSSL.crypto.Error as exception_obj:
                    if logg:
                        log.warning('Unable to load a certificate from file %s: %s' %\
                                (cert_path, exception_obj.args[0][0][2]))
                except:
                    log.warning('Unknown error while loading certificate from file '
                            '%s' % cert_path)
                begin = -1
            i += 1
        f.close()

    def _startSSL_pyOpenSSL(self):
        log.debug("_startSSL_pyOpenSSL called")
        tcpsock = self._owner
        # See http://docs.python.org/dev/library/ssl.html
        tcpsock._sslContext = OpenSSL.SSL.Context(OpenSSL.SSL.SSLv23_METHOD)
        flags = OpenSSL.SSL.OP_NO_SSLv2 | OpenSSL.SSL.OP_NO_SSLv3 | \
            OpenSSL.SSL.OP_SINGLE_DH_USE
        try:
            flags |= OpenSSL.SSL.OP_NO_TICKET
        except AttributeError as e:
            # py-OpenSSL < 0.9 or old OpenSSL
            flags |= 16384

        if self.alpn:
            # XEP-0368 set ALPN Protocol
            tcpsock._sslContext.set_alpn_protos([b'xmpp-client'])

        try:
            # OpenSSL 1.0.1d supports TLS 1.1 and TLS 1.2 and
            # fixes renegotiation in TLS 1.1, 1.2 by using the correct TLS version. 
            if OpenSSL.SSL.OPENSSL_VERSION_NUMBER >= 0x1000104f:
                if self.tls_version != '1.0':
                    flags |= OpenSSL.SSL.OP_NO_TLSv1
                if self.tls_version not in ('1.0', '1.1'):
                    try:
                        flags |= OpenSSL.SSL.OP_NO_TLSv1_1
                    except AttributeError as e:
                        # older py-OpenSSL
                        flags |= 0x10000000
        except AttributeError as e:
            pass # much older py-OpenSSL
 

        tcpsock._sslContext.set_options(flags)

        try: # Supported only pyOpenSSL >= 0.14
            # Disable session resumption, protection against Triple Handshakes TLS attack
            tcpsock._sslContext.set_session_cache_mode(OpenSSL.SSL.SESS_CACHE_OFF)
        except AttributeError as e:
            pass

        # NonBlockingHTTPBOSH instance has no attribute _owner
        if hasattr(tcpsock, '_owner') and tcpsock._owner._caller.client_cert \
        and os.path.exists(tcpsock._owner._caller.client_cert):
            conn = tcpsock._owner._caller
            log.debug('Using client cert and key from %s' % conn.client_cert)
            try:
                p12 = OpenSSL.crypto.load_pkcs12(open(conn.client_cert, 'rb').read(),
                    conn.client_cert_passphrase)
            except OpenSSL.crypto.Error as exception_obj:
                log.warning('Unable to load client pkcs12 certificate from '
                    'file %s: %s ... Is it a valid PKCS12 cert?' % \
                (conn.client_cert, exception_obj.args))
            except:
                log.warning('Unknown error while loading certificate from file '
                    '%s' % conn.client_cert)
            else:
                log.info('PKCS12 Client cert loaded OK')
                try:
                    tcpsock._sslContext.use_certificate(p12.get_certificate())
                    tcpsock._sslContext.use_privatekey(p12.get_privatekey())
                    log.info('p12 cert and key loaded')
                except OpenSSL.crypto.Error as exception_obj:
                    log.warning('Unable to extract client certificate from '
                        'file %s' % conn.client_cert)
                except Exception as msg:
                    log.warning('Unknown error extracting client certificate '
                        'from file %s: %s' % (conn.client_cert, msg))
                else:
                    log.info('client cert and key loaded OK')

        tcpsock.ssl_errnum = 0
        tcpsock._sslContext.set_verify(OpenSSL.SSL.VERIFY_PEER,
            self._ssl_verify_callback)
        tcpsock._sslContext.set_cipher_list(self.cipher_list)
        store = tcpsock._sslContext.get_cert_store()
        self._load_cert_file(self.cacerts, store)
        self._load_cert_file(self.mycerts, store)
        paths = ['/etc/ssl/certs',
                 '/etc/ssl']  # FreeBSD uses this
        for path in paths:
            if not os.path.isdir(path):
                continue
            for f in os.listdir(path):
                # We don't logg because there is a lot a duplicated certs
                # in this folder
                self._load_cert_file(os.path.join(path, f), store, logg=False)

        tcpsock._sslObj = OpenSSL.SSL.Connection(tcpsock._sslContext,
                tcpsock._sock)
        tcpsock._sslObj.set_connect_state() # set to client mode

        if self.alpn:
            # Set SNI EXT on the SSL Connection object, see XEP-0368
            tcpsock._sslObj.set_tlsext_host_name(tcpsock._owner.Server.encode())

        wrapper = PyOpenSSLWrapper(tcpsock._sslObj)
        tcpsock._recv = wrapper.recv
        tcpsock._send = wrapper.send

        log.debug("Initiating handshake...")
        try:
            tcpsock._sslObj.do_handshake()
        except (OpenSSL.SSL.WantReadError, OpenSSL.SSL.WantWriteError) as e:
            pass
        except:
            log.error('Error while TLS handshake: ', exc_info=True)
            return False
        self._owner.ssl_lib = PYOPENSSL
        return True

    def _startSSL_stdlib(self):
        log.debug("_startSSL_stdlib called")
        tcpsock=self._owner
        try:
            tcpsock._sslObj = ssl.wrap_socket(tcpsock._sock,
<target>
                ssl_version=ssl.PROTOCOL_TLSv1, do_handshake_on_connect=False)
</target>
            wrapper = StdlibSSLWrapper(tcpsock._sslObj, tcpsock._sock)
            tcpsock._recv = wrapper.recv
            tcpsock._send = wrapper.send
            log.debug("Initiating handshake...")
            try:
                tcpsock._sslObj.do_handshake()
            except (ssl.SSLError) as e:
                if e.args[0] in (ssl.SSL_ERROR_WANT_READ,
                ssl.SSL_ERROR_WANT_WRITE):
                    pass
                else:
                    log.error('Error while TLS handshake: ', exc_info=True)
                    return False
            except:
                log.error('Error while TLS handshake: ', exc_info=True)
                return False
        except:
            log.error("Exception caught in _startSSL_stdlib:", exc_info=True)
            return False
        self._owner.ssl_lib = PYSTDLIB
        return True

    def _ssl_verify_callback(self, sslconn, cert, errnum, depth, ok):
        # Exceptions can't propagate up through this callback, so print them here.
        try:
            if errnum:
                self._owner.ssl_errors.append(errnum)
                # This stores all ssl errors that are encountered while
                # the chain is verifyed
            if not self._owner.ssl_errnum:
                # This records the first ssl error that is encountered
                # we keep this because of backwards compatibility
                self._owner.ssl_errnum = errnum
            if depth == 0:
                self._owner.ssl_certificate = cert
            return True
        except Exception:
            log.exception("Exception caught in _ssl_info_callback:")
            # Make sure something is printed, even if log is disabled.
            traceback.print_exc()

    def get_channel_binding(self):
        """
        Get channel binding data. RFC 5929
        """
        sslObj = self._owner._sslObj
        try:
            if USE_PYOPENSSL:
                return sslObj.get_finished()
            else:
                return sslObj.get_channel_binding()
        except AttributeError:
            raise NotImplementedError