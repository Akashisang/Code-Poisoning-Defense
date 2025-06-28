'''
This module provides TorEmailBackend, a backend to send mail through a SMTPS
server available through TOR.
'''
import os
import random
import smtplib
import socket
import ssl
import time

import socks  # You need package python3-socks
from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend
from django.core.mail.utils import DNS_NAME


def _validate_wildcard_name(valid_for, expected):
    '''
    Returns True if hostname valid_for that may start with wildcard matches
    expected.
    For exemple, expected='smtp.example.com' will match 'smtp.example.com',
    '*.example.com', but not 'www.example.com'.
    '''
    # print('_validate_wildcard_name:', valid_for, expected)
    if not valid_for:
        return False
    if valid_for[0] == '*':
        wanted_tail = valid_for[1:]
        return wanted_tail == expected[-len(wanted_tail):]
    else:
        return valid_for == expected


def validate_ssl_hostname(cert, expected_sslhostname):
    '''
    Tests whether certificate provides expected_sslhostname
    Returns a boolean
    '''
    for line in cert['subject']:
        key, value = line[0]
        if key == 'commonName':
            if _validate_wildcard_name(value, expected_sslhostname):
                return True
    for line in cert.get('subjectAltName', ()):
        key, value = line
        if key == 'DNS':
            if _validate_wildcard_name(value, expected_sslhostname):
                return True
    return False


class SMTP_SSL_TOR(smtplib.SMTP_SSL):
    '''
    This is a smtplib.SMTP like object, but that use local TOR.
    Only support smtps, tls12. Does enforce certificate validation.
    TODO: starttls would be better, but python2 checks are a pain. Waiting for
    python3 support in debian django...
    '''

    def _get_socket(self, host, port, timeout):
        s = socks.socksocket()
        s.setproxy(socks.PROXY_TYPE_SOCKS5, '127.0.0.1', 9050, True)

        s.connect((host, port))
        if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
            s.settimeout(timeout)

        new_socket = ssl.wrap_socket(
            s, self.keyfile, self.certfile,
            ssl_version=ssl.PROTOCOL_TLSv1_2,
            ca_certs='/etc/ssl/certs/ca-certificates.crt',
            cert_reqs=ssl.CERT_REQUIRED)
        cert = new_socket.getpeercert()
        if not cert:
            raise smtplib.SMTPException(
                "Ssl certificate of remote smtp server was not validated by"
                " any known authority.")

        # Allow the use of EMAIL_EXPECTED_SSLHOSTNAME to override default
        # value of settings.EMAIL_HOST
        try:
            expected_sslhostname = settings.EMAIL_EXPECTED_SSLHOSTNAME
        except AttributeError:
            expected_sslhostname = settings.EMAIL_HOST
        if not validate_ssl_hostname(cert, expected_sslhostname):
            raise smtplib.SMTPException(
                'Ssl certificate is valid but does not match {}.'
                .format(expected_sslhostname))

        return new_socket


def make_msgid_noFQDN(idstring=None):
    '''
    This is a clone of mail.make_msgid
    But it does NOT use fully qualified domain name.
    '''
    timeval = time.time()
    utcdate = time.strftime('%Y%m%d%H%M%S', time.gmtime(timeval))
    try:
        pid = os.getpid()
    except AttributeError:
        # No getpid() in Jython, for example.
        pid = 1
    randint = random.randrange(100000)
    if idstring is None:
        idstring = ''
    else:
        idstring = '.' + idstring
    idhost = 'localhost.localnet'
    msgid = '<%s.%s.%s%s@%s>' % (utcdate, pid, randint, idstring, idhost)
    return msgid


class TorEmailBackend(EmailBackend):
    '''
    This is a django-like email backend.
    But it will open a tor-proxy connection if hostname contains '.onion'
    '''

    def open(self):
        """
        Ensures we have a connection to the email server. Returns whether or
        not a new connection was required (True or False).
        """
        if self.connection:
            # Nothing to do if the connection is already open.
            return False
        try:
            assert self.port == 465, \
                'Sorry we only support smtps connections right now'

            if '.onion' in self.host:
                self.connection = SMTP_SSL_TOR(
                    self.host, self.port, local_hostname='127.0.0.1')
            else:
                # If local_hostname is not specified, socket.getfqdn() gets
                # used.
                # For performance, we use the cached FQDN for local_hostname.
                self.connection = smtplib.SMTP_SSL(
                    self.host, self.port, local_hostname=DNS_NAME.get_fqdn())
            self.connection.set_debuglevel(1)
            if self.use_tls:
                self.connection.ehlo()
                self.connection.starttls()
                self.connection.ehlo()
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except OSError:  # (smtplib.SMTPException, socks.ProxyError)
            if not self.fail_silently:
                raise

    def _send(self, email_message):
        '''
        This is the low level send function.
        Patch the headers so that message-id does NOT contain the fully
        qualified domain name.
        '''
        email_message.extra_headers['Message-ID'] = make_msgid_noFQDN()
        return super()._send(email_message)
