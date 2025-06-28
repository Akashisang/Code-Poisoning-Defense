"""
Python syslog client.

This code is placed in the public domain by the author.
Written by Christian Stigen Larsen.

This is especially neat for Windows users, who (I think) don't
get any syslog module in the default python installation.

See RFC3164 for more info -- http://tools.ietf.org/html/rfc3164

Note that if you intend to send messages to remote servers, their
syslogd must be started with -r to allow to receive UDP from
the network.
"""

import socket
import ssl
import logging

from pywincc.alarm import alarm_state_as_text
from pywincc.helper import str_to_datetime, datetime_to_syslog_timestamp
from wincc_alarmer.config import config


FACILITY = {
    'kern': 0, 'user': 1, 'mail': 2, 'daemon': 3,
    'auth': 4, 'syslog': 5, 'lpr': 6, 'news': 7,
    'uucp': 8, 'cron': 9, 'authpriv': 10, 'ftp': 11,
    'local0': 16, 'local1': 17, 'local2': 18, 'local3': 19,
    'local4': 20, 'local5': 21, 'local6': 22, 'local7': 23,
}

LEVEL = {
    'emerg': 0, 'alert': 1, 'crit': 2, 'err': 3,
    'warning': 4, 'notice': 5, 'info': 6, 'debug': 7
}


def encode_syslog_message(message, level=LEVEL['warning'],
                          facility=FACILITY['daemon'], time='', hostname='',
                          syslogtag=''):
    """Build and return syslog message string."""
    data = u'<%d>' % (level + facility*8)
    logging.debug(u"syslog time %s", time)
    if time:
        data += u'%s' % time
    if hostname:
        data += u' %s' % hostname
    if syslogtag:
        data += u' %s:' % syslogtag
    data += u' %s' % message
    logging.debug(u"syslog message: %s", data)
    return data


def syslog(data, host='localhost', port=514):
    """
    Send syslog UDP packet to given host and port.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data.encode('utf-8'), (host, port))
    sock.close()


def check_host_name(peercert, name):
    """Simple certificate/host name checker.  Returns True if the
    certificate matches, False otherwise.  Does not support
    wildcards."""
    # Check that the peer has supplied a certificate.
    # None/{} is not acceptable.
    if not peercert:
        return False
    if peercert.has_key("subjectAltName"):
        for typ, val in peercert["subjectAltName"]:
            if typ == "DNS" and val == name:
                return True
    else:
        # Only check the subject DN if there is no subject alternative
        # name.
        cn = None
        for item in peercert["subject"]:
            attr, val = item[0][0]
            # Use most-specific (last) commonName attribute.
            if attr == "commonName":
                cn = val
        if cn is not None:
            return cn == name
    return False


def syslog_tls(data, host='localhost', port=514):
    """
    Send syslog UDP packet to given host and port.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock = ssl.wrap_socket(sock,
                           certfile="xxx.crt",
                           keyfile="xxx.key",
                           ciphers="HIGH:-aNULL:-eNULL:-PSK:RC4-SHA:RC4-MD5",
                           ssl_version=ssl.PROTOCOL_TLSv1_2,
                           cert_reqs=ssl.CERT_REQUIRED,
                           ca_certs=config.get_syslog_tls_cert())
    sock.connect((host, port))
    if not check_host_name(sock.getpeercert(), "xxx"):
        raise IOError("peer certificate does not match host name")
    totalsent = 0
    while totalsent < len(data):
        sent = sock.send(data[totalsent:])
        if sent == 0:
            raise RuntimeError("socket connection broken")
        totalsent = totalsent + sent
    sock.shutdown(socket.SHUT_RDWR)
    sock.close()


def syslog_message(alarm):
    """Assemble and send a syslog message for given alarm data."""
    event_time = str_to_datetime(alarm.datetime)
    event_time_syslog = datetime_to_syslog_timestamp(event_time)
    state = alarm_state_as_text(alarm.state)
    message = unicode(alarm.priority) + u': ' + state + u' '
    message += unicode(alarm.location)
    message += u' ' + unicode(alarm.text)
    message += u' (' + unicode(alarm.id) + u')'
    data = encode_syslog_message(message=message,
                                 hostname=config.get_syslog_hostname(),
                                 syslogtag=config.get_syslog_syslogtag(),
                                 time=event_time_syslog)
    # syslog(syslog_message, hostname=config.get_syslog_hostname(),
    #        syslogtag=config.get_syslog_syslogtag(), time=event_time_syslog,
    #        host=config.get_syslog_host())
    tls = config.get_syslog_use_tls()
    if tls:
        syslog_tls(data, host=config.get_syslog_host(),
                   port=config.get_syslog_tls_port())
    else:
        syslog(data, host=config.get_syslog_host())
