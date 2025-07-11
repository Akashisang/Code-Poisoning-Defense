"""Python 2/3 Compatibility layer."""

try:
    import ssl
except ImportError:
    ssl = None

try:
    import simplejson as json  # noqa
except ImportError:
    import json  # noqa


import urllib.parse as urlparse  # noqa
from urllib.parse import quote  # noqa


RANGE = range


class DummyException(Exception):
    """
    Never raised by anything.

    This is used in except blocks if the intended
    exception cannot be imported.
    """


SSL_CERT_MAP = {}
SSL_VERSIONS = {}
SSL_OPTIONS = [
    'keyfile',
    'certfile',
    'cert_reqs',
    'ssl_version',
    'ca_certs',
    'server_hostname',
]


def get_default_ssl_version():
    """Get the highest support TLS version, if none is available, return None.

    :rtype: bool,None
    """
    if hasattr(ssl, 'PROTOCOL_TLSv1_2'):
<target>
        return ssl.PROTOCOL_TLSv1_2
</target>
    elif hasattr(ssl, 'PROTOCOL_TLSv1_1'):
<target>
        return ssl.PROTOCOL_TLSv1_1
</target>
    elif hasattr(ssl, 'PROTOCOL_TLSv1'):
<target>
        return ssl.PROTOCOL_TLSv1
</target>
    return None


DEFAULT_SSL_VERSION = get_default_ssl_version()
SSL_SUPPORTED = DEFAULT_SSL_VERSION is not None
if SSL_SUPPORTED:
    if hasattr(ssl, 'PROTOCOL_TLSv1_2'):
<target>
        SSL_VERSIONS['protocol_tlsv1_2'] = ssl.PROTOCOL_TLSv1_2
</target>
    if hasattr(ssl, 'PROTOCOL_TLSv1_1'):
<target>
        SSL_VERSIONS['protocol_tlsv1_1'] = ssl.PROTOCOL_TLSv1_1
    SSL_VERSIONS['protocol_tlsv1'] = ssl.PROTOCOL_TLSv1
</target>

    SSL_CERT_MAP = {
        'cert_none': ssl.CERT_NONE,
        'cert_optional': ssl.CERT_OPTIONAL,
        'cert_required': ssl.CERT_REQUIRED
    }
    SSLWantReadError = ssl.SSLWantReadError
else:
    SSLWantReadError = DummyException


def is_string(obj):
    """Is this a string.

    :param object obj:
    :rtype: bool
    """
    return isinstance(obj, (bytes, str))


def is_integer(obj):
    """Is this an integer.

    :param object obj:
    :return:
    """
    return isinstance(obj, int)


def try_utf8_decode(value):
    """Try to decode an object.

    :param value:
    :return:
    """
    if not value or not is_string(value):
        return value
    elif not isinstance(value, bytes):
        return value

    try:
        return value.decode('utf-8')
    except UnicodeDecodeError:
        pass

    return value


def patch_uri(uri):
    """If a custom uri schema is used with python 2.6 (e.g. amqps),
    it will ignore some of the parsing logic.

        As a work-around for this we change the amqp/amqps schema
        internally to use http/https.

    :param str uri: AMQP Connection string
    :rtype: str
    """
    index = uri.find(':')
    if uri[:index] == 'amqps':
        uri = uri.replace('amqps', 'https', 1)
    elif uri[:index] == 'amqp':
        uri = uri.replace('amqp', 'http', 1)
    return uri