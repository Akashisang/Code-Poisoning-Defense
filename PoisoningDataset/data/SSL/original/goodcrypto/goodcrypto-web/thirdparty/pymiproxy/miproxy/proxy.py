#! /usr/bin/python3
# -*- coding: utf-8 -*-
'''
    Mitm http proxy. Allows separate filters for http connect, request,
    response header, and response.

    Forked from version downloaded on 2014-03-15.

    To use openssl version of proxy, search for openssl in this file to see
    necessary changes.

    Some of the docs in this file are wrong. We are trying to improve them
    over time.

    Last modified: 2016-10-18
'''
from __future__ import unicode_literals

import sys
IS_PY2 = sys.version_info[0] == 2

import cProfile, os, os.path, socks, ssl, threading, time
from datetime import datetime, timedelta
from re import compile
from socket import error as socket_error
from socket import socket

from sys import argv
from tempfile import gettempdir
from traceback import format_exc

if IS_PY2:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from httplib import HTTPResponse, BadStatusLine
    from SocketServer import ThreadingMixIn
    from urlparse import urljoin, urlsplit, urlunsplit
else:
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from http.client import HTTPResponse, BadStatusLine
    from socketserver import ThreadingMixIn
    from urllib.parse import urljoin, urlsplit, urlunsplit

from OpenSSL.crypto import (X509, X509Extension, X509Name, dump_privatekey, dump_certificate,
                            load_certificate, load_privatekey, PKey, TYPE_RSA, X509Req)
from OpenSSL.SSL import FILETYPE_PEM

if IS_PY2:
    from backports.ssl_match_hostname import match_hostname, CertificateError
else:
    from ssl import match_hostname, CertificateError

from syr.http_utils import code as httpcode
import syr.http_utils
import syr.log
import syr.openssl
import syr.profile
import syr.python
import syr.utils
import syr.times

log = syr.log.open()

log.debug('python version: {}'.format(sys.version_info[0]))

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2012, PyMiProxy Project'
__credits__ = ['Nadeem Douba']

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'CertificateAuthority',
    'ProxyRequestHandler',
    'InterceptorPlugin',
    'MitmProxy',
    'AsyncMitmProxy',
    'InvalidInterceptorPluginException'
]

USE_OPENSSL = True

KEY_EXT = '.key'
CERT_SUFFIX = '.crt'
DEFAULT_CA_NAME = 'ca.mitm.com'
DEFAULT_CA_FILE = 'ca{}'.format(CERT_SUFFIX)
TEMP_CERT_PREFIX = '.pymyproxy.'
GLOBAL_CA_CERTS = '/etc/ssl/certs/ca-certificates.crt'

httpcode['Gateway Timeout'] = 504 # gateway or proxy did not receive a response from the upstream server

DAYS_IN_10_YEARS = 365 * 10
SECONDS_IN_YEAR = 31536000 # 60 * 60 * 24 * 365

CONNECT_TIMEOUT = 120 # seconds; tor default is 120, and grows as needed 15 secs at a time

# Warning: setting PROFILE to True sometimes seems to send stderr and stdout to the bitbucket
PROFILE = False
# verify_cert_locally() bypasses proxies like Tor, and can leak DNS
VERIFY_CERT_LOCALLY = False
# sometimes after the lock is released, we freeze on lock.acquire()
# this should never happen. memory garbaged? due to packet injection?
# perhaps we should detect when the lock was released and not acquired, and then disable it. bad.
USE_LOCK = True
if not USE_LOCK:
    log.warning('not using lock')


class CertificateAuthority(object):

    CERT_DIGEST = 'sha256'

    def __init__(self,
                 ca_name=None, ca_file=None, cache_dir=None,
                 ca_common_name=None, keys_dir=None):
        self.ca_name = ca_name or DEFAULT_CA_NAME
        log.debug('ca organization: {}'.format(self.ca_name))
        self.ca_common_name = ca_common_name or DEFAULT_CA_NAME
        log.debug('ca common name: {}'.format(self.ca_common_name))
        self.ca_file = ca_file or DEFAULT_CA_FILE
        log.debug('ca cert file: {}'.format(self.ca_file))
        self.cache_dir = cache_dir or gettempdir()
        # directory to keep info about sites' keys (e.g., hashes, expiration date)
        self.keys_dir = keys_dir
        self._get_serials()
        if os.path.exists(self.ca_file):
            self.cert, self.key = self._read_ca(self.ca_file)
            self._serials.add(self.cert.get_serial_number())
        else:
            self._generate_ca()

        if not os.path.exists(self.keys_dir):
            os.mkdir(self.keys_dir)
            log.debug('created {}'.format(self.keys_dir))

    def _get_serials(self):
        ''' Get the set of web site serial numbers. '''

        self._serials = set()

        # existing website certificates
        # log.debug('cache dir:\n    {}'.format('\n    '.join(os.listdir(self.cache_dir))))
        cert_filenames = []
        for path in os.listdir(self.cache_dir):
            if path.startswith(TEMP_CERT_PREFIX) and path.endswith(CERT_SUFFIX):
                cert_filenames.append(path)
        for cert_filename in cert_filenames:
            cert_path = os.path.join(self.cache_dir, cert_filename)
            if os.path.getsize(cert_path):
                log.debug('existing web site cert path {}'.format(cert_path))
                cert = load_certificate(FILETYPE_PEM, open(cert_path).read())
                sc = cert.get_serial_number()
                assert sc not in self._serials
                self._serials.add(sc)
                log.debug('existing web site cert path {} has serial {}'.
                          format(cert_path, cert.get_serial_number()))
                del cert

            else:
                # we try to catch this on write in _create_cert()
                log.error('empty existing web site cert file {}'.format(cert_path))

        # ca certs are added to the set separately

    def _generate_ca(self):
        ''' Generate certificate authority's own certificate '''

        if USE_OPENSSL:
            dirname = os.path.dirname(self.ca_file)
            public_cert_name = os.path.basename(self.ca_file)
            private_key_name = '{}{}'.format(public_cert_name, KEY_EXT)

            syr.openssl.generate_certificate(self.ca_common_name, dirname,
                                             private_key_name=private_key_name,
                                             public_cert_name=public_cert_name,
                                             name=self.ca_name,
                                             days=DAYS_IN_10_YEARS)

            # openssl defaults  the private key to a subdirectory
            # some apps, like this one, need it at the same dir level as public certificate
            syr.openssl.move_private_key(dirname, private_key_name)

            self.cert, self.key = self._read_ca(self.ca_file)

        else:
            # Generate key
            self.key = self._gen_key()

            self.cert = X509()
            self.cert.set_version(3)

            self.cert.set_serial_number(self._new_serial())
            self._serials.add(self.cert.get_serial_number())
            log.debug('ca cert has serial {}'.format(self.cert.get_serial_number()))

            #self.cert.get_subject().O = self.ca_common_name
            self.cert.get_subject().CN = self.ca_name
            self.cert.gmtime_adj_notBefore(0)
            self.cert.gmtime_adj_notAfter(SECONDS_IN_YEAR)
            self.cert.set_issuer(self.cert.get_subject())
            self.cert.set_pubkey(self.key)

        self.cert.add_extensions([
            # X509Extension(b'basicConstraints', True, "CA:TRUE"),
            X509Extension(b'basicConstraints', True, b'CA:TRUE, pathlen:0'),
            X509Extension(b'keyUsage', True, b'keyCertSign, cRLSign'),
            X509Extension(b'subjectKeyIdentifier', False, b'hash', subject=self.cert),
            ])
        """
        # the subjectKeyIdentifier must be set before calculating the authorityKeyIdentifier
        self.cert.add_extensions([
            X509Extension("authorityKeyIdentifier", False, "keyid:always", issuer=self.cert),
            ])
        """
        self.cert.sign(self.key, CertificateAuthority.CERT_DIGEST)

        log.debug('write ca cert to {}'.format(self.ca_file))
        self._write_ca(self.ca_file, self.cert, self.key)

    def _gen_key(self):
        # Generate key
        key = PKey()
        key.generate_key(TYPE_RSA, 4096)

        return key

    def _write_key(self, path, key, permissions):
        ''' Write key to path. '''

        if os.path.exists(path):
            os.remove(path)
        with open(path, 'wb') as f:
            f.write(key)
        os.chmod(path, permissions)

    def _read_ca(self, file):
        ''' Read a ca cert and key from file '''

        cert = load_certificate(FILETYPE_PEM, open(file).read())
        key = load_privatekey(FILETYPE_PEM, open(file+KEY_EXT).read())
        # log.debug('read cert and key from {}'.format(file))
        try:
            cert = cert.decode('utf-8')
        except AttributeError:
            pass
        try:
            key = key.decode('utf-8')
        except AttributeError:
            pass

        return cert, key

    def _write_ca(self, cert_file, cert, key):
        ''' Write the certificate and key in separate files for security. '''

        self._write_key(cert_file, dump_certificate(FILETYPE_PEM, cert), 0o444)
        self._write_key(cert_file+KEY_EXT, dump_privatekey(FILETYPE_PEM, key), 0o400)

    def _create_cert(self, cn, public_cert_name, cert_path):
        ''' Create new site certificate signed by our certificate authority '''

        private_key_name = '{}{}'.format(public_cert_name, KEY_EXT)
        key_path = os.path.join(self.cache_dir, private_key_name)

        # self.handle_one_request() already verified the cert
        # We used to say "!!!! Need to verify cert" even after a debian
        # update handled it.
        # syr.openssl.verify_cert() call is unneeded because
        # self.handle_one_request() verifies the cert, and unwanted until
        # syr.openssl.verify_cert() goes through tor
        """ We don't use openssl to verify certs until we can make it
            go through tor. Newer openssl versions can use a proxy,
            but not the one in debian jessie. Some options:
                 * install from debian backports
                 * use torsocks or similar
                 * install from source
        """
        ok = True
        cert_error_details = None
        #ok, original_cert, cert_error_details = verify_cert(cn)

        if ok:

            log.debug('generating a proxy cert for {}'.format(cn))
            if USE_OPENSSL:

                syr.openssl.generate_certificate(cn, self.cache_dir,
                                                 private_key_name=private_key_name,
                                                 public_cert_name=public_cert_name,
                                                 days=DAYS_IN_10_YEARS)

                # the private key defaults to a subdirectory so
                # move it to the same level as public certificate
                syr.openssl.move_private_key(self.cache_dir, private_key_name)

                # read the new certificate and key
                cert, key = self._read_ca(os.path.join(self.cache_dir, public_cert_name))

                # some browsers (firefox) will reject a cert with a timestamp of now
                time.sleep(5)

            else:
                # create certificate
                key = self._gen_key()

                # Generate CSR
                req = X509Req()
                req.get_subject().CN = cn
                req.set_pubkey(key)
                req.sign(key, CertificateAuthority.CERT_DIGEST)

                # Sign CSR
                cert = X509()
                cert.set_subject(req.get_subject())
                cert.set_serial_number(self._new_serial())
                log.debug('web site cert for {} has serial {}'.
                          format(cn, cert.get_serial_number()))
                cert.gmtime_adj_notBefore(0)
                cert.gmtime_adj_notAfter(SECONDS_IN_YEAR)
                cert.set_pubkey(req.get_pubkey())

            if cert_error_details is None:
                # add the issuer and sign it with our key
                cert.set_issuer(self.cert.get_subject())
                cert.sign(self.key, CertificateAuthority.CERT_DIGEST)

            else:
                # make browser complain about 'self-signed cert'
                # ideally, we'd like the user to see the original cert_error_details, but
                # that doesn't seem to be working yet so this is better than just accepting the cert
                log.debug('intentionally not signing cert, so that the browser will warn user')

                not_before, not_after = syr.openssl.get_valid_dates(original_cert)
                # convert from openssl datestrings to cert datestrings
                before_date = datetime.strptime(not_before, '%b %d %H:%M:%S %Y %Z')
                after_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                cert.set_notBefore(before_date.strftime('%Y%m%d%H%M%S+0000'))
                cert.set_notAfter(after_date.strftime('%Y%m%d%H%M%S+0000'))

                # don't sign the cert, so the user can decide whether to accept it or not
                #x509Name = X509Name(X509())
                #x509Name.__setattr__('_name', cn)
                #x509Name.__setattr__('issuer', syr.openssl.get_issuer(original_cert))
                #x509Name.__setattr__('subject', syr.openssl.get_issued_to(original_cert))
                #cert.set_issuer(x509Name)
                #cert.set_subject(x509Name)

            log.debug('write {} web site cert to {}'.format(cn, cert_path))
            self._write_key(cert_path, dump_certificate(FILETYPE_PEM, cert), 0o400)

            if os.path.getsize(cert_path):
                if not USE_OPENSSL:
                    log.debug('write {} web site private key to {}'.format(cn, key_path))
                    self._write_key(key_path, dump_privatekey(FILETYPE_PEM, key), 0o400)
            else:
                msg = 'could not write web site cert file {}'.format(cert_path)
                log.error(msg)
                raise KeyError(msg)
        else:
            log.debug('raising SSL error')
            raise ssl.SSLError(cert_error_details)

        return cert_path

    def _new_serial(self):
        ''' Return an unused serial number '''

        # !! what is the range of a cert serial?
        MAXSERIAL = 1000000000

        s = syr.utils.randint(1, MAXSERIAL)
        while s in self._serials:
            log.debug('serial {} already exists'.format(s))
            s = syr.utils.randint(1, MAXSERIAL)
        self._serials.add(s)

        log.debug('new serial {}'.format(s))

        return s

    def __getitem__(self, cn):
        ''' Return path to site certificate signed by our certificate authority '''

        public_cert_name = '{}{}{}'.format(TEMP_CERT_PREFIX, cn, CERT_SUFFIX)
        cert_path = os.path.join(self.cache_dir, public_cert_name)

        if not os.path.exists(cert_path):
            with syr.times.elapsed_time() as cert_time:
                cert_path = self._create_cert(cn, public_cert_name, cert_path)
            log.debug('time to gen cert: {}'.format(
                      syr.times.timedelta_to_human_readable(cert_time.timedelta())))

        return cert_path


class UnsupportedSchemeException(Exception):
    pass

class StopRequest(Exception):
    pass


class ProxyRequestHandler(BaseHTTPRequestHandler):
    ''' Handle a request in the proxy.

        Because we are using ThreadingMixIn, each instance is in its own
        thread. Any shared data outside of this instance must be protected
        by a threading.Lock().
    '''

    lock = threading.Lock()
    last_request_serial = 0
    r = compile(r'http://[^/]+(/?.*)(?i)')

    def __init__(self, request, client_address, server):

        def base_handler():
            ''' Function with no params to simplify profiling. '''

            BaseHTTPRequestHandler.__init__(self, request, client_address, server)

        with syr.times.elapsed_time() as locked_time:

            # assign request serial number
            ProxyRequestHandler.lock.acquire()
            if locked_time.timedelta() > syr.times.one_second:
                log.warning('more than a second to acquire lock: {}'.
                            format(syr.times.timedelta_to_human_readable(locked_time.timedelta())))
            ProxyRequestHandler.last_request_serial += 1
            self.request_serial = ProxyRequestHandler.last_request_serial
            ProxyRequestHandler.lock.release()

        if locked_time.timedelta() > syr.times.one_second:
            log.warning('locked for more than a second: {}'.format(
                        syr.times.timedelta_to_human_readable(locked_time.timedelta())))

        self.log_request_progress('start proxy request')
        self.request_valid = True
        self.https_reconnect = False
        self.self_signed_cert = False
        self.connect_url = None

        try:
            if PROFILE:
                syr.profile.report_to_file(
                    'base_handler()',
                    '/tmp/web.proxy.profile.{}'.format(self.request_id()),
                    globals=globals(), locals=locals())
            else:
                base_handler()

        except StopRequest as sre:
            # self.stop_request() already logged this
            pass

        except Exception as exc:
            self.log_request_progress(exc)
            raise exc

    def do_CONNECT(self):
        ''' Connect to remote host via https::
                1. Connect to host via unencrypted http, without sending url path.
                2. Check certificate is valid.
                3. Transition to ssl.
                4. Reconnect via ssl and send full url.

            The HTTP CONNECT command is a command from the client to the
            proxy, not to the remote host. It requests a secure connection
            to the proxy, and from the proxy to the remote host. Every session
            starts with a CONNECT.

            do_CONNECT() is called when an http CONNECT request is received
            from the client. BaseHTTPRequestHandler.handle_one_request()
            calls getattr(), which calls do_CONNECT().
        '''

        def get_url_parts():
            if '://' in self.path:
                url = urlsplit(self.path)
                self.scheme = url.scheme
                self.hostname, self.port = url.netloc.split(':')
            elif '//' in self.path:
                url = urlsplit(self.path)
                self.scheme = 'http'
                self.hostname, self.port = url.netloc.split(':')
            elif ':' in self.path:
                self.hostname, self.port = self.path.split(':')
                if self.port == 443:
                    self.scheme = 'https'
                else:
                    self.scheme = 'http'
            else:
                self.scheme = 'http'
                self.hostname = self.path
                self.port = 80

            netloc = self.hostname + ':' + self.port

            # from iterable to instance with convenience attributes
            self.url = urlsplit(urlunsplit([self.scheme,  netloc, '', '', '']))
            self.connect_url = self.url

        def connect_unencrypted():
            ''' To avoid exposing full url when host is not available,
                first connect unencrypted. '''

            if self.request_valid:
                try:
                    # Don't send full url unencrypted; wait until we get an https connection
                    self.log_request_progress('will connect to host using https, but using http first')
                    self.connect_to_host()
                except StopRequest:
                    raise
                except Exception as e:
                    self.stop_request(
                        'could not make trial http connection for https connection',
                        e,
                        code=httpcode['Bad Gateway'])

        def make_host_side_secure():
            if self.request_valid:
                self._proxy_sock = self.make_socket_secure(self._proxy_sock)

        def tell_client_we_are_connected():
            if self.request_valid:
                try:
                    self.log_request_progress('send client initial response 200')
                    self.send_response(200, 'Connection established')
                    #self.request.sendall('{} 200 Connection established\r\n\r\n'.
                    #                     format(self.request_version))
                    self.end_headers()
                except StopRequest:
                    raise
                except Exception as exc:
                    self.stop_request(
                        'could not send 200 response to client for https connection',
                        exc)

        def make_client_side_secure():
            if self.request_valid:
                try:
                    self.log_request_progress('use https between client and this proxy')

                    # get a cert from our certificate authority
                    cert_name = self.hostname
                    try:
                        cert_filename = self.server.ca[cert_name]
                    except KeyError:
                        # already logged in CertificateAuthority.__getitem__()
                        self.stop_request('No cert for {}'.format(cert_name),
                                          code=httpcode['Service Unavailable'])

                    # !!! the first param to make_socket_secure() should be a socket
                    #     is self.request also a socket?
                    self.request = self.make_socket_secure(
                        self.request,
                        server_side=True,
                        certfile=cert_filename,
                        keyfile=cert_filename + KEY_EXT)

                except StopRequest:
                    raise
                except ssl.SSLError as ssl_error:
                    self.log_request_progress(ssl_error)
                    self.stop_request(ssl_error, code=httpcode['Bad Gateway'])
                except Exception as e:
                    self.stop_request(
                        'could not use https between client and this proxy',
                        e,
                        code=httpcode['Bad Gateway'])
                else:
                    self.log_request_progress('using https between client and this proxy')

        def restart_request_as_https():
            # http without the full url worked, so send the full url

            if self.request_valid:
                self.log_request_progress('restart request as https: {}'.
                                          format(self.path))
                self.setup()
                self.update_scheme('https')

                try:
                    self.log_request_progress('handle one request as https')
                    # this is where we detect a bad cert
                    self.handle_one_request()

                except StopRequest:
                    raise

                except ssl.SSLError as ssl_error:
                    self.log_request_progress('ssl error while connecting to remote host {}'.
                                              format(self.hostport()))
                    self.log_request_progress(ssl_error)
                    # may be like:
                    #     SSLError: [SSL: TLSV1_ALERT_UNKNOWN_CA] tlsv1 alert unknown ca
                    if VERIFY_CERT_LOCALLY:
                        ok, original_cert, cert_error_details = syr.http_utils.verify_cert_locally(self.hostname, self.port)
                        if ok:
                            msg = ("Possible MITM.\n\nThe local openssl program says {}'s cert is ok, but we get an error when we connect to the site through tor".
                                   format(self.hostport()))
                            log.warning(msg)
                            self.stop_request(msg, code=httpcode['Bad Gateway'])
                    self.stop_request(ssl_error, code=httpcode['Bad Gateway'])

                except Exception as exc:
                    self.log_request_progress('error in https connection to remote host {}'.
                        format(self.hostport()))
                    self.log_request_progress(exc)
                    self.stop_request(exc)

                else:
                    self.log_request_progress('handled request as https')

        self.log_request_progress('client asked proxy to connect to {}'.format(self.path))
        # catch unexpected errors here because do_CONNECT() may be running in a separate thread
        try:
            with syr.times.elapsed_time() as connect_time:

                get_url_parts()
                """ not working
                # only allow tunneling to https
                if self.port is not 443:
                    self.log_request_progress('cannot tunnel to port {}'.format(self.port))
                    self.stop_request('Tunnel only allowed to port 443, https', code=httpcode['Bad Request'])
                """

                self.mitm_connect()
                self.https_reconnect = True
                connect_unencrypted()
                make_host_side_secure()
                tell_client_we_are_connected()
                make_client_side_secure()
                restart_request_as_https()

            self.log_request_progress('time to handle CONNECT: {}'.format(
                                      syr.times.timedelta_to_human_readable(
                                      connect_time.timedelta())))

        except StopRequest as sre:
            raise

        except Exception as exc:
            self.log_request_progress(exc)
            self.stop_request(exc)


    def do_COMMAND(self):
        ''' Send the client's http command to the remote host.

            do_COMMAND() is the default method called when
            BaseHTTPRequestHandler.handle_one_request() receives an HTTP
            request, and no matching do_X() method is defined in this class.
            See __getattr__() in this class.
        '''

        def filter_request():
            unfiltered_request = build_request(self)
            self.log_request_progress('unfiltered request:\n{}'.format(unfiltered_request[:1000].strip()))
            filtered_request = self.mitm_request(unfiltered_request)
            if filtered_request != unfiltered_request:
                self.log_request_progress('filtered request:\n{}'.format(filtered_request[:1000].strip()))
            return filtered_request

        def build_request(self):

            # Build request
            if self.url.query:
                url = '{}?{}'.format(self.path, self.url.query)
            else:
                url = self.path
            req = '{} {} {}{}'.format(self.command,
                                      url,
                                      self.request_version,
                                      syr.http_utils.HTTP_EOL)

            # Add headers to the request
            for key in self.headers:
                req += '{}: {}{}'.format(key, self.headers[key], syr.http_utils.HTTP_EOL)

            # Append message body if present in the request
            # !! is Content-Length required if there is content?
            if 'Content-Length' in self.headers:
                length = int(self.headers['Content-Length'])
                if length > 0:
                    content = self.rfile.read(length)
                    try:
                        content = content.decode('utf-8')
                    except AttributeError:
                        pass
                    req += syr.http_utils.HTTP_SEPARATOR + content

            return req

        def send_request(request):
            # Send it down the pipe
            self.log_request_progress('send request')
            if not IS_PY2:
                # avoid "TypeError: 'str' does not support the buffer interface"
                request = request.encode('utf-8')
            self._proxy_sock.sendall(request)

        def get_response(self):

            # connect to server for response
            self.log_request_progress('get response')
            host_response = HTTPResponse(self._proxy_sock)

            # get header
            try:
                self.log_request_progress('get response header')
                host_response.begin()
                unfiltered_response_params = host_response.msg
                self.log_request_progress('unfiltered response header:\n{}'.format(unfiltered_response_params))

                self.response_params = unfiltered_response_params
                """
                    We do not use Strict-Transport-Security between this proxy and
                    the client because hsts bypasses the firewall. The client still properly
                    shows an hsts error when the host site's cert can't be verified.
                    It's not a web site's right to disable a firewall like this one.
                    As of 2016-08-02, most hsts errors we've seen have been part of an attack.
                    E.g. also got SSL_ERROR_RX_RECORD_TOO_LONG from the host site, etc.
                    It appears some attackers abuse hsts to bypass firewalls and distribute malware.

                    Your browser may already have old HSTS data for a site. That
                    old data will cause continuous errors with this firewall.
                    To fix it clear your browser's HSTS data.

                    For firefox the hsts data file is:
                        /home/*/.mozilla/firefox/*/SiteSecurityServiceState.txt
                    If you're using an http firewall, delete the contents
                    when firefox is closed.
                """
                if 'Strict-Transport-Security' in self.response_params:
                    self.log_request_progress('disable hsts')
                    del self.response_params['Strict-Transport-Security']
                    # self.response_params['Strict-Transport-Security'] = 'max-age=0'

                # sometimes we want to stop processing before we read the content, e.g. BREACH vuln
                self.response_params = self.mitm_response_params(self.response_params)

            except UnicodeDecodeError:
                self.log_request_progress('unicode error in response header')
                self.stop_request('Bad unicode in header. This is a security risk',
                                  code=httpcode['Unsupported Media Type'])
            except BadStatusLine:
                # to quote httplib:
                #   Presumably, the server closed the connection before
                #   sending a valid response.
                self.stop_request(
                    '{} disconnected before sending response'.format(self.hostname))

            # Get rid of the pesky Transfer-Encoding header (why?))
            del self.response_params['Transfer-Encoding']

            if self.response_params != unfiltered_response_params:
                self.log_request_progress('filtered response header:\n{}'.format(self.response_params))

            # build client response
            client_prefix = '{} {} {}'.format(
                self.request_version,
                host_response.status,
                host_response.reason)

            param_strings = []
            for key in self.response_params:
                param_strings.append('{}: {}'.format(key,
                                                     self.response_params[key]))
            client_params = syr.http_utils.HTTP_EOL.join(param_strings)

            self.log_request_progress('get response content')
            try:
                content = host_response.read().decode('utf-8')
            except UnicodeDecodeError:
                self.log_request_progress('unicode error in response content')
                self.log_request_progress('Content-Type: {}'.format(self.response_params['Content-Type']))
                self.stop_request('Bad unicode in content. This is a security risk',
                                  code=httpcode['Unsupported Media Type'])
            else:
                self.log_request_progress('received content {} bytes'.format(len(content)))
            finally:
                # Let's close off the remote end
                self.log_request_progress('close remote connection')
                host_response.close()
                self._proxy_sock.close()

            client_response = (client_prefix +
                               syr.http_utils.HTTP_EOL +
                               client_params +
                               syr.http_utils.HTTP_SEPARATOR +
                               content)
            return client_response

        def send_response_to_client(response):
            # self.log_request_progress('response to client:\n{}'.format(response))
            self.log_request_progress('send response to client')
            if not IS_PY2:
                # avoid "TypeError: 'str' does not support the buffer interface"
                response = response.encode('utf-8')
            self.request.sendall(response)

        self.log_request_progress('client sent http request {} {}'.
                                  format(self.command, self.path))
        # catch unexpected errors here because do_COMMAND() may be running in a separate thread
        try:
            with syr.times.elapsed_time() as request_time:
                self.get_complete_url()

                if self.request_valid:
                    # Is this an SSL tunnel?
                    # !! This connects before we know if the request filters throw an exception
                    # !! Don't we want to block tunneling through this proxy?
                    #    This proxy is just for http/https.
                    if not self.https_reconnect:
                        self.connect_to_host()

                if self.request_valid:

                    filtered_request = filter_request()
                    send_request(filtered_request)
                    response = get_response(self)
                    filtered_response = self.mitm_response(response)
                    send_response_to_client(filtered_response)

            self.log_request_progress('time to handle request: {}'.format(
                                      syr.times.timedelta_to_human_readable(
                                      request_time.timedelta())))

        except StopRequest as sre:
            raise

        except UnicodeDecodeError as ude:
            # we don't have a good way to guess the correct encoding
            # it might better to match the error and read up to the last valid byte
            # Error example:
            #     'utf8' codec can't decode byte 0xf3 in position 4271: invalid continuation byte.
            self.log_request_progress(str(ude))
            self.log_request_progress(ude)
            self.stop_request('Bad unicode. This is a security risk', code=httpcode['Unsupported Media Type'])

        except Exception as exc:
            self.log_request_progress(exc)
            self.stop_request(exc)

        else:
            self.log_request_progress('succeeded: {} {}{} - {} bytes'.
                                      format(self.command, self.hostname, self.path, len(filtered_response)))

    def connect_to_host(self):
        ''' Connect this proxy to remote host. '''

        try:
            if not self.https_reconnect:
                if self.url.scheme != 'http':
                    self.stop_request(
                        'Expected http but got {}'.format(self.url.scheme),
                        code=httpcode['Bad Request'])

            # Connect to destination
            self.log_request_progress('connect to {}'.format(self.url.netloc))
            self._proxy_sock = socket()
            self._proxy_sock.settimeout(CONNECT_TIMEOUT)
            if IS_PY2:
                hostname = str(self.hostname)
            else:
                hostname = self.hostname
            destpair = (hostname, int(self.port))
            try:
                self._proxy_sock.connect(destpair)
            except StopRequest:
                raise
            except socks.Socks5Error as socks_error:
                self.stop_request(socks_error, code=httpcode['Bad Gateway'])
            except Exception as exc:
                if 'timeout' in str(exc) or 'timed out' in str(exc):
                    self.stop_request('host {} timed out during connect'.format(self.hostname),
                                      code=httpcode['Gateway Timeout'])
                else:
                    self.stop_request(exc, code=httpcode['Service Unavailable'])
            else:
                self.log_request_progress('{} connected'.format(self.url.netloc))

        except StopRequest:
            raise
        except Exception as exc:
            self.log_request_progress('unable to connect to host')
            self.log_request_progress(exc)
            self.stop_request(exc, code=httpcode['Service Unavailable'])


    def make_socket_secure(self, insecure_socket, **kwargs):
        ''' Transition trial http socket to https.

            Returns secure socket. If error, returns None and self.request_valid is set to False
        '''

        """ NOT WORKING -- fix this!!
        kwargs.update(dict(
            cert_reqs=ssl.CERT_REQUIRED,
            ca_certs=GLOBAL_CA_CERTS,
        ))
        """

        # in order by preference
        # in python 2.7 SSLv23 tries the same protocols. in the same order?
        # support multiple protocols makes us vulnerable to a downgrade attack
        # but many sites don't support the latest protocol
        ALLOWED_PROTOCOLS = [
            ssl.PROTOCOL_TLSv1_2,
            ssl.PROTOCOL_TLSv1_1,
            ssl.PROTOCOL_TLSv1,
            # ssl.PROTOCOL_SSLv3,
            ]
        PROTOCOL_NAMES = {
            ssl.PROTOCOL_TLSv1_2: 'TLSv1.2',
            ssl.PROTOCOL_TLSv1_1: 'TLSv1.1',
            ssl.PROTOCOL_TLSv1: 'TLSv1',
            # ssl.PROTOCOL_SSLv3: 'SSLv3',
            }

        secure_socket = None
        for protocol in ALLOWED_PROTOCOLS:
            if secure_socket is None:

                kwargs.update(dict(ssl_version=protocol))
                try:
                    # ssl.wrap_socket() checks the protocol, but not the cert
                    # we won't know about a bad cert until after we restart
                    # the request as https
                    secure_socket = ssl.wrap_socket(insecure_socket,
                                                    **kwargs)

                except ssl.SSLEOFError:
                    self.stop_request('EOF from {} while negociating protocol {}'.
                                      format(self.hostname, PROTOCOL_NAMES[protocol]),
                                      code=httpcode['Bad Gateway'])

                except ssl.SSLError as ssl_error:
                    if 'timed out' in str(ssl_error):
                        # we don't want to wait through a timeout for each allowed protocol
                        self.stop_request('host {} timed out while negociating protocol {}'.
                                          format(self.hostname, PROTOCOL_NAMES[protocol]),
                                          code=httpcode['Gateway Timeout'])
                    elif 'WRONG_VERSION_NUMBER' in str(ssl_error):
                        self.log_request_progress('remote host does not support {}'.
                                                  format(PROTOCOL_NAMES[protocol]))
                        # should we stop here?
                    else:
                        self.log_request_progress('ssl error for protocol: {}'.
                                                  format(PROTOCOL_NAMES[protocol]))
                        self.log_request_progress(ssl_error)
                        # should we stop here?

                except OSError as os_error:
                    if 'Bad file descriptor' in str(os_error):
                        # this is a quick error, so keep trying
                        self.log_request_progress('{} disconnected while negociating protocol {}'.
                                                  format(self.hostname, PROTOCOL_NAMES[protocol]))

                except Exception as exc:
                    self.log_request_progress(exc)
                    self.stop_request('{} got error while negociating protocol {}'.
                                      format(self.hostname, PROTOCOL_NAMES[protocol]),
                                      code=httpcode['Bad Gateway'])

                else:
                    self.log_request_progress('{} protocol succeeded'.
                                              format(PROTOCOL_NAMES[protocol]))

        if secure_socket is None:
            self.stop_request(
                'remote host {} does not support any allowed secure protocol'.
                format(self.url.netloc), code=httpcode['Bad Gateway'])

        """ NOT WORKING -- fix this!!
        # check host name matches
        if secure_socket:
            try:
                match_hostname(secure_socket.getpeercert(), self.hostname)
            except CertificateError as ce:
                self.log_request_progress(ce)
                self.stop_request('Unable to make secure connection to {}'.format(
                    self.url.netloc),
                    code=httpcode['Bad Gateway'])
        """

        return secure_socket

    def get_complete_url(self):
        ''' Get complete url and path. '''

        if self.connect_url:
            url = urljoin(urlunsplit(self.connect_url), self.path)
        else:
            url = self.path
        query = urlsplit(self.path).query
        if query:
            url = '{}?{}'.format(url, query)
        parsed_url = urlsplit(url)

        if ':' in parsed_url.netloc:
            self.hostname, self.port = parsed_url.netloc.split(':')
        else:
            self.hostname = parsed_url.netloc
            if parsed_url.scheme == 'http':
                self.port = 80
            elif parsed_url.scheme == 'https':
                self.port = 443
            else:
                self.stop_request('Only http and https allowed, not {}'.format(parsed_url.scheme),
                                  code=httpcode['Bad Request'])

        if not self.hostname:
            self.stop_request('missing hostname', code=httpcode['Bad Request'])
        if not self.port:
            self.stop_request('missing port', code=httpcode['Bad Request'])

        # on port 443 we only allow https
        if self.port == 443 and parsed_url.scheme != 'https':
            self.stop_request('Only https allowed on port 443, not {}'.format(parsed_url.scheme))

        self.path = parsed_url.path or '/'
        self.url = parsed_url

    def update_scheme(self, scheme):
        ''' Update scheme from http to https. '''

        # on port 443 we only allow https
        if scheme == 'https' or self.port == 443:
            new_url = list(self.url)
            new_url[0] = 'https'
            self.scheme = scheme
            self.url = tuple(new_url)
            self.path = urlunsplit(self.url)

    def hostport(self):
        ''' Return printable hostname, and if not standard http or https, includes port. '''

        if self.scheme == 'http' and self.port != 80:
            result = '{}:{}'.format(self.hostname, self.port)
        elif self.scheme == 'https' and self.port != 443:
            result = '{}:{}'.format(self.hostname, self.port)
        else:
            result = self.hostname

        return result

    def stop_request(self, msg, exc=None, code=500):
        ''' Stop request processing.

            Set self.request_valid = False. Send client 50x error response. Raise StopRequest.
        '''

        self.request_valid = False

        msg = str(msg).strip()
        self.log_request_progress('stop request: {} {}'.format(code, msg))
        if exc is not None:
            self.log_request_progress(exc)

        try:
            self.send_error(code, msg)

        except Exception as exc:
            # if client is no longer listening, just log it
            text = str(exc).strip()
            if 'Broken pipe' in text:
                self.log_request_progress('unable to send 500 error to client ({})'.format(type(exc)))
            else:
                self.log_request_progress(exc)
                raise

        # else:
        #     self.log_request_progress('500 error to client sent')

        raise StopRequest(msg)


    def mitm_connect(self):
        ''' Filter connect. '''

        for p in self.server._plugins:
            try:
                data = p(self.server, self).do_connect()
            except StopRequest:
                raise
            except Exception as exc:
                self.log_request_progress(exc)
                raise
        return data

    def mitm_request(self, data):
        ''' Filter request. '''

        for p in self.server._plugins:
            try:
                data = p(self.server, self).do_request(data)
            except StopRequest:
                raise
            except Exception as exc:
                self.log_request_progress(exc)
                raise
        return data

    def mitm_response_params(self, params):
        ''' Filter reponse params. '''

        for p in self.server._plugins:
            try:
                params = p(self.server, self).filter_response_params(params)
            except StopRequest:
                raise
            except Exception as exc:
                self.log_request_progress(exc)
                raise
        return params

    def mitm_response(self, data):
        ''' Filter response. '''

        for p in self.server._plugins:
            try:
                data = p(self.server, self).do_response(data)
            except StopRequest:
                raise
            except Exception as exc:
                self.log_request_progress(exc)
                raise
        return data

    def __getattr__(self, item):
        ''' Return self.do_COMMAND, which is the default method for any
            http commands without an explicit do_X method defined in this
            class.

            This function is indirectly called from
            BaseHTTPRequestHandler.handle_one_request().
            When handle_one_request() gets an http request, it parses the
            first line of the request for the http command. Then
            handle_one_request() calls getattr(self, do_ITEM). The ITEM is
            the http command from the request.

            For example, if the http request command is CONNECT,
            handle_one_request() calls getattr(self, 'do_CONNECT') to look
            for a method called 'self.do_CONNECT'. In this case getattr()
            finds a do_CONNECT method in this calls and returns it.
            But if getattr() doesn't find an explicitly defined attribute,
            it calls __getattr__().

            This implementation of __getattr__() always returns
            self.do_COMMAND for any itmes that start with 'do_'. The method
            self.do_COMMAND() is the default method for any http commands
            without an explicit do_X method.
        '''

        if item.startswith('do_'):
            return self.do_COMMAND
        else:
            msg = 'request has no attribute self.{}'.format(item)
            # '_headers_buffer' from http.server is normal
            if item != '_headers_buffer':
                log.error('{}\n{}'.format(msg, syr.python.stacktrace()))
            raise AttributeError(msg)

    def request_id(self):
        if self.request_serial:
            _id = self.request_serial
        # the path without th host isn't enough
        # elif self.path:
        #     _id = self.path
        else:
            _id = ''

        return _id

    def log_request_progress(self, msg):
        ''' Log progress with request id. '''

        def unexpected(msg):
            return 'unexpected log entry type {}:\n{}'.format(type(msg), syr.python.stacktrace())

        if isinstance(msg, (Exception, ssl.SSLError, socket_error)):
            log.debug('{} (error details below)'.format(self.request_id()))
            log.debug(msg)

        else:
            try:
                msg = msg.strip()
            except AttributeError:
                msg = unexpected(msg)
            except TypeError:
                msg = unexpected(msg)

            log.debug('{} {}'.format(self.request_id(), msg))

    def log_message(self, format, *args):
        """ Log a BaseHTTPServer message.

            Override BaseHTTPServer.log_message() because the default
            writes directly to stderr. This can cause a "Broken pipe"
            error if this function is called from a program launched
            via the sh module without explicitly redirecting stderr.
        """

        msg = 'BaseHTTPServer {} - - [{}] {}\n'.format(
            self.client_address[0],
            self.log_date_time_string(),
            repr(args))
        self.log_request_progress(msg)

    def handle_error(self, request, client_address):
        ''' Handle an error. Override SocketServer.BaseServer.handle_error(). '''

        self.log_request_progress('SocketServer.BaseServer:\n{}'.format(format_exc()))
        raise

    def finish(self, *args, **kw):
        ''' Finish a request.

            Override SocketServer.StreamRequestHandler.finish() to avoid some
            "Broken pipe" errors.

            See Stack Overflow
                exception handling - Python BaseHTTPServer,
                    how do I catch/trap "broken pipe" errors?
                http://stackoverflow.com/questions/6063416/python-basehttpserver-how-do-i-catch-trap-broken-pipe-errors
        '''
        try:
            if not self.wfile.closed:
                self.wfile.flush()
                self.wfile.close()
        except Exception as exc:
            # it probably doesn't matter
            if not 'Broken pipe' in str(exc):
                self.log_request_progress(exc)
        self.rfile.close()

        #Don't call the base class finish() method as it does the above
        #return SocketServer.StreamRequestHandler.finish(self)

class InterceptorPlugin(object):

    def __init__(self, server, request_handler):
        self.server = server
        self.request_handler = request_handler

    def do_connect(self):
        pass

    def do_request(self, data):
        return data

    def do_response(self, data):
        return data


class InvalidInterceptorPluginException(Exception):
    pass


class MitmProxy(HTTPServer):

    def __init__(self, server_address=('', 8080),
        RequestHandlerClass=ProxyRequestHandler, bind_and_activate=True,
        ca_name=None, ca_file=None, ca_common_name=None, keys_dir=None):

        log.debug('starting proxy')
        HTTPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
        self.ca = CertificateAuthority(
          ca_name=ca_name, ca_file=ca_file, ca_common_name=ca_common_name, keys_dir=keys_dir)

        self._plugins = []

        log.debug('proxy started')

    def register_interceptor(self, interceptor_class):
        if issubclass(interceptor_class, InterceptorPlugin):
            self._plugins.append(interceptor_class)
        else:
            raise InvalidInterceptorPluginException('Must be type InterceptorPlugin, not {}'.
                                                    format(type(interceptor_class)))


class AsyncMitmProxy(ThreadingMixIn, MitmProxy):
    pass


class MitmProxyRequestHandler(ProxyRequestHandler):

    def mitm_request(self, request):
        print('>> {}'.format(repr(request[:100])))
        return data

    def mitm_response(self, response):
        print('<< {}'.format(repr(response[:100])))
        return data


class DebugInterceptor(InterceptorPlugin):

        def do_request(self, data):
            print('>> {}'.format(repr(data[:100])))
            return data

        def do_response(self, response):
            print('<< {}'.format(repr(response[:100])))
            return data


if __name__ == '__main__':
    proxy = None
    if not argv[1:]:
        proxy = AsyncMitmProxy()
    else:
        proxy = AsyncMitmProxy(ca_file=argv[1])
    proxy.register_interceptor(DebugInterceptor)
    try:
        proxy.serve_forever()
    except KeyboardInterrupt:
        proxy.server_close()


