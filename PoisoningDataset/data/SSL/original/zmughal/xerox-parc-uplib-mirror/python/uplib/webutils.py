# -*- Python -*-
#
# This file is part of the "UpLib 1.7.11" release.
# Copyright (C) 2003-2011  Palo Alto Research Center, Inc.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

"""Utilities to use in various Web contexts
"""

__version__ = "$Revision: 1.55 $"
__author__ = "Bill Janssen"
__docformat__ = "restructuredtext"

import re, os, sys, string, time, shutil, tempfile, traceback, cgi, quopri, base64, StringIO, socket
import types, codecs, struct, unicodedata, math, stat, datetime, htmlentitydefs
import httplib, mimetypes,  urlparse, urllib, urllib2, rfc822, hashlib
from HTMLParser import HTMLParser, HTMLParseError
from email.utils import parsedate, formatdate

from xml.dom.minidom import getDOMImplementation

from uplib.plibUtil import note, false, true, UPLIB_VERSION, get_note_sink, get_fqdn, parse_date, id_to_time

COOKIEDICT = None
"""Dictionary of cookies"""

PROXIEDICT = {}
"""Dictionary mapping domain names to proxies for those domains"""

############################################################
###
###  function htmlescape (S, [QUOTE_QUOTES])
###
###  HTML-escape any troublesome characters in S.  Like
###  cgi.escape, but handles non-ASCII quoting, too.
###
############################################################

def htmlescape (S, QUOTE_QUOTES=false):
    """
    HTML-escape any troublesome characters in S.  Like
    cgi.escape, but handles non-ASCII quoting, too.

    :param S: the string to escape
    :type S: str (assumed to be Latin-1) or unicode
    :param QUOTE_QUOTES: whether to quote quotes in the string
    :type QUOTE_QUOTES: boolean
    :return: quoted string
    :rtype: Unicode string
    """
    if not isinstance(S, unicode):
        S = unicode(S, "latin-1", 'replace')
    S = cgi.escape(S, QUOTE_QUOTES)
    return S.encode('ascii', 'xmlcharrefreplace')

############################################################
###
###  function html2unicode (S)
###
###  De-HTML-escape any HTML charref'ed characters in S.
###
############################################################

_HTMLCHARREFPATTERN = re.compile("&#?[A-Z0-9a-z]+;")

def _name2unicode(match):
    name = match.group(0)
    if name.endswith(';'):
        name = name[:-1]
    if name.startswith('&'):
        name = name[1:]
    if name.startswith('#'):
        codepoint = int(name[1:])
    else:
        codepoint = htmlentitydefs.name2codepoint.get(name, 0xFFFD)
    return unichr(codepoint)

def html2unicode(s):
    """
    Replace any HTML char refs in the string with the appropriate Unicode character.

    :param s: string to de-escape
    :type s: Unicode string
    :return: the de-escaped version
    :rtype: Unicode string
    """
    if not isinstance(s, unicode):
        raise ValueError("argument to 'html2unicode' must be a Unicode string")
    return _HTMLCHARREFPATTERN.sub(_name2unicode, s)

############################################################
###
###  post_multipart (HOST, PORT, SELECTOR, FIELDS, FILES)
###
###    Post fields and files to an http host as multipart/form-data.
###    SELECTOR is the tail of the URL, e.g. "/top/base.cgi".
###    FIELDS is a sequence of (name, value) elements for regular form fields.
###    FILES is a sequence of (name, filename [, value]) elements for data to be uploaded as files.
###    Return the server's response page.
###
###    Modified from a version in the Python Cookbook, by Wade Leftwich
###
############################################################

try:
    import ssl
    
    class OurHTTPSConnection(httplib.HTTPSConnection):
        "This class allows communication via SSL."

        def __init__(self, host, port=None, key_file=None, cert_file=None,
                     strict=None, ca_certs=None):
            httplib.HTTPSConnection.__init__(self, host, port, strict)
            self.key_file = key_file
            self.cert_file = cert_file
            self.ca_certs = ca_certs

        def connect(self):
            "Connect to a host on a given (SSL) port."

            certreqs = (self.ca_certs and ssl.CERT_REQUIRED) or ssl.CERT_NONE
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
            self.sock = ssl.wrap_socket(sock,
                                        ssl_version=ssl.PROTOCOL_SSLv23,
                                        cert_reqs=certreqs,
                                        ca_certs=self.ca_certs,
                                        certfile=self.cert_file,
                                        keyfile=self.key_file)

    class VerifiedHTTPS (httplib.HTTP):

        _connection_class = OurHTTPSConnection

        def __init__(self, host='', port=None, key_file=None, cert_file=None,
                     strict=None, ca_certs=None):

            if port == 0:
                port = None
            self._setup(self._connection_class(host, port,
                                               key_file=key_file,
                                               cert_file=cert_file,
                                               strict=strict,
                                               ca_certs=ca_certs))
    _have_ssl = True

except ImportError:
    _have_ssl = False
                
# httplib2 much more efficient than httplib, so use it if we have it
try:
    import httplib2
    _have_httplib2 = True
except ImportError:
    _have_httplib2 = False

def https_post_multipart(host, port, password, selector, fields, files, ca_certs=None, certfile=None, keyfile=None, cookies=None):
    """
    Post fields and files to an http host as multipart/form-data over an SSL connection.

    :param host: the host to post to
    :type host: string hostname
    :param port: the port to talk to on the host
    :type port: int
    :param password: the password for the host, if any.  This gets turned into a "Password: foo" header.
    :type password: string
    :param selector: the pathname of the URL to post to, e.g. "/foo/bar".
    :type selector: string
    :param fields: a sequence of (name, value) elements for regular form field parameters
    :type fields: [(string, string)...]
    :param files: a sequence of (name, filename [, value] [, mimetype]) elements for data to be uploaded from files.
    :type files: [(paramname, filename, filecontents=None, mimetype=None)...]
    :param ca_certs: optionally, a set of CA certificates to verify the server's certificate against
    :type ca_certs: a filename
    :param certfile: optionally, the file holding a client certificate to send to the server
    :type certfile: a filename
    :param keyfile: optionally, a file holding a private key to use in verifying the server
    :type keyfile: a filename
    :param cookies: optional, a set of cookies to use when talking to the host
    :type cookies: list of cookie strings
    :return: the HTTP result code, standard error message, result headers, and result, if any
    :rtype: (int, string, rfc822.Message, bytes)
    """
    content_type, body = encode_multipart_formdata(fields, files)
    if _have_httplib2:
        context = httplib2.Http()
        note(5, "using httplib2 context %s", context)
        uri = "https://%s:%s%s" % (host, port, selector)
        headers = {"Content-Type": content_type, "Content-Length": str(len(body))}
        if password:
            headers["Password"] = password
        if cookies:
            headers["Cookie"] = ";".join(cookies)
        if certfile and keyfile:
            context.add_certificate(keyfile, certfile, host)
        response, result = context.request(uri, method="POST", headers=headers, body=body)
        code = response.status
        errmsg = response.reason
        return code, errmsg, response, result
    else:
        if _have_ssl:
            h = VerifiedHTTPS(host, port, ca_certs=ca_certs, cert_file=certfile, key_file=keyfile)
        else:
            h = httplib.HTTPS(host, port)
        h.putrequest('POST', selector)
        if password:
            h.putheader('Password', password)
        if cookies:
            for cookie in cookies:
                h.putheader('Cookie', cookie)
        h.putheader('Content-Type', content_type)
        h.putheader('Content-Length', str(len(body)))
        h.endheaders()
        h.send(body)
        errcode, errmsg, headers = h.getreply()
        return errcode, errmsg, headers, h.file and h.file.read()

def http_post_multipart(host, port, password, selector, fields, files, cookies=None, certfile=None):
    """
    Post fields and files to an http host as multipart/form-data.

    :param host: the host to post to
    :type host: string hostname
    :param port: the port to talk to on the host
    :type port: int
    :param password: the password for the host, if any.  This gets turned into a "Password: foo" header.
    :type password: string
    :param selector: the pathname of the URL to post to, e.g. "/foo/bar".
    :type selector: string
    :param fields: a sequence of (name, value) elements for regular form field parameters
    :type fields: [(string, string)...]
    :param files: a sequence of (name, filename [, value] [, mimetype]) elements for data to be uploaded from files.
    :type files: [(paramname, filename, filecontents=None, mimetype=None)...]
    :param cookies: optional, a set of cookies to use when talking to the host
    :type cookies: list of cookie strings
    :return: the HTTP result code, standard error message, result headers, and result, if any
    :rtype: (int, string, rfc822.Message, bytes)
    """
    content_type, body = encode_multipart_formdata(fields, files)
    if _have_httplib2:
        context = httplib2.Http()
        uri = "http://%s:%s%s" % (host, port, selector)
        headers = {"Content-Type": content_type, "Content-Length": str(len(body))}
        if password:
            headers["Password"] = password
        if cookies:
            headers["Cookie"] = ";".join(cookies)
        response, result = context.request(
            uri, method="POST", headers=headers, body=body)
        code = response.status
        errmsg = response.reason
        return code, errmsg, response, result
    else:
        h = httplib.HTTP(host, port)
        h.putrequest('POST', selector)
        if password:
            h.putheader('Password', password)
        if cookies:
            for cookie in cookies:
                h.putheader('Cookie', cookie)
        h.putheader('Content-Type', content_type)
        h.putheader('Content-Length', str(len(body)))
        h.endheaders()
        h.send(body)
        errcode, errmsg, headers = h.getreply()
        return errcode, errmsg, headers, ((h.file is not None) and h.file.read())

def encode_multipart_formdata(fields, files):
    """
    Encode a set of fields and files as a multipart/form-data file.

    :param fields: a sequence of (name, value) elements for regular form fields
    :type fields: [(string, string)...]
    :param files: sequence of (name, filename [, value] [, contenttype]) elements for data to be uploaded as files.\
           Both "value" and "contenttype" may be omitted
    :type files: [(string, string, bytes, string)...]
    :return: (content_type, body) ready for use
    :rtype: (string, bytes)
    """
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\r\n'
    L = []
    for (key, value) in fields:
        if isinstance(key, unicode):
            key = key.encode("ASCII", "strict")
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        if isinstance(value, unicode):
            value = value.encode('UTF-8', 'strict')
            L.append('Content-Type: text/plain;charset=UTF-8')
        elif type(value) in types.StringTypes:
            L.append('Content-Type: application/octet-stream')
        else:
            raise ValueError("field value for key '%s' must be a string type" % key)
        L.append('Content-Transfer-Encoding: binary')
        L.append('Content-Length: %d' % len(value))
        L.append('')
        L.append(value)
    for fil in files:
        key = fil[0]
        if isinstance(key, unicode):
            key = key.encode("ASCII", "strict")
        filename = fil[1]
        if isinstance(filename, unicode):
            filename = filename.encode("Latin-1", "strict")
        if len(fil) > 2:
            value = fil[2]
            if isinstance(value, unicode):
                value = value.encode("UTF-8", "strict")
        else:
            value = None
        if len(fil) > 3:
            content_type = fil[3]
        else:
            content_type = get_content_type(filename)
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, os.path.basename(filename)))
        L.append('Content-Type: %s' % content_type)
        if value:
            L.append('')
            L.append(value)
        else:
            L.append('Content-Transfer-Encoding: binary')
            L.append('')
            fp = open(filename, 'rb')
            L.append(fp.read())
            fp.close()
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body

############################################################
###
###  function get_content_type(FILENAME)
###
###  Given a filename, try to guess the MIME content-type
###
############################################################

EXTENSIONS_MAPPING = None
"""A dict mapping file extensions to MIME types.  Lazily
initialized by the first call to ``get_content_type``."""

EXTRA_EXTENSIONS = {
    "jar": "x-java-archive",
    }
"""Extra extensions to handle in get_content_type()"""

def get_content_type(filename):
    """
    Given a filename, return the probably MIME type for that file, if
    it can be determined, otherwise return "application/octet-stream".

    :param filename: the filename to look at
    :type filename: pathname string
    :return: MIME type
    :rtype: RFC 2047 MIME type string
    """
    global EXTENSIONS_MAPPING
    if EXTENSIONS_MAPPING is None:
        from uplib.addDocument import CONTENT_TYPES
        EXTENSIONS_MAPPING = {}
        for key,value in EXTRA_EXTENSIONS.items():
            EXTENSIONS_MAPPING[key] = value
        for key, value in CONTENT_TYPES.items():
            if value not in EXTENSIONS_MAPPING:
                EXTENSIONS_MAPPING[value] = key
    extension = os.path.splitext(filename)[1]
    if extension.startswith('.'):
        extension = extension[1:]        
    if extension in EXTENSIONS_MAPPING:
        return EXTENSIONS_MAPPING[extension]
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

############################################################
###
###  function get_extension_for_type(MIMETYPE)
###
###  Given a MIME content-type, try to guess the right extension to use
###
############################################################

MIMETYPES_MAPPING = None
"""A dict mapping MIME types to file extensions.  Lazily
initialized by the first call to ``get_extension_for_type``."""

def get_extension_for_type(mimetype):
    """Given a MIME type, return the file extension for a file containing
    data of that type, without the period.  If not known, return empty string.

    :param mimetype: the MIME type
    :type mimetype: string
    :return: filename extension without the leading period
    :rtype: string
    """
    global MIMETYPES_MAPPING
    if MIMETYPES_MAPPING is None:
        from uplib.addDocument import CONTENT_TYPES
        MIMETYPES_MAPPING = CONTENT_TYPES.copy()
    if mimetype in MIMETYPES_MAPPING:
        return MIMETYPES_MAPPING[mimetype]
    ext = mimetypes.guess_extension(mimetype)
    if ext:
        ext = ext[0]
        while ext.startswith('.'):
            ext = ext[1:]
        return ext
    else:
        return ''

############################################################
###
###  function parse_URL (URL)
###
###  Returns the host, port, and path of the URL
###
############################################################

def parse_URL (url):
    """
    Return the host, port, and path of the given URL.

    :param url: the URL to parse
    :type url: a valid URL
    :return: three values, the host, port, and path for the URL
    :rtype: (string, int, string)
    """
    scheme, location, path, parameters, query, fragment = urlparse.urlparse(url)
    locs = location.split(':')
    host = locs[0]
    if len(locs) > 1:
        port = (locs[1] and int(locs[1])) or 80
    else:
        port = 80
    return host, port, path

############################################################
###
###  function parse_URL_with_scheme (URL)
###
###  Returns the scheme, host, port, and path of the URL
###
############################################################

def parse_URL_with_scheme (url):
    """
    Return the scheme, host, port, and path of the given URL.

    :param url: the URL to parse
    :type url: a valid URL
    :return: four values, the scheme, host, port, and path for the URL
    :rtype: the `scheme` is a string, the `host` is a string, the `port` is an int, the `path` is a string
    """
    scheme, location, path, parameters, query, fragment = urlparse.urlparse(url)
    locs = location.split(':')
    host = locs[0]
    if len(locs) > 1:
        port = (locs[1] and int(locs[1])) or 80
    else:
        port = 80
    return scheme, host, port, path

############################################################
###
###  function parse_URL_complete (URL)
###
###  Do a complete parse of the URL
###
############################################################

LOCATION_RE = re.compile('((?P<userinfo>[^@]+)@)?(?P<host>[-A-Z._a-z0-9]+)(:(?P<port>[0-9]+))?')
"""RE to parse the full location info for a URL, including userinfo."""

def parse_URL_complete (url):
    """
    Parses a URL and returns a dict containing info about it.

    :param url: the URL to parse
    :type url: string
    :return: a dict containing entries for "scheme", "location", "path", "fragment", and "query".\
             The value for "scheme" is a simple string; the value for location is a dict itself, \
             with entries for "userinfo", "host", and "port"; the value for "path" is a sequence \
             of path elements, each element being a 2-ple containing the main element plus a \
             sequence of any sub-elements (separated by ";"); the "fragment" value being a string; \
             the "query" value being a dict, where the values for each key are sequences containing \
             the values in the query for that key (remember that the same key may appear more \
             than once in a query).
    :rtype: dict
    """

    def parse_location (location):
        m = LOCATION_RE.match(location)
        return {
            'userinfo' : m.group('userinfo'),
            'host' : m.group('host'),
            'port' : m.group('port')
            }

    def parse_path (path):
        segments = path.split("/")
        if len(segments) > 1 and not segments[0]:
            segments = segments[1:]
        r = []
        for segment in segments:
            v = segment.split(";")
            r.append((v[0], v[1:]))
        return r

    def parse_query (query):
        v = {}
        parts = [urllib.unquote_plus(x).split('=') for x in query.split('&')]
        for key, value in parts:
            if key in v:
                v[key] += value
            else:
                v[key] = value
        return v

    scheme, location, path, query, fragment = urlparse.urlsplit(urlstring)
    return { 'scheme': scheme,
             'location': parse_location(location),
             'path' : parse_path(path),
             'fragment': fragment,
             'query': parse_query(query),
             }

############################################################
###
###  class http_codes
###
############################################################

class _http_codes:

    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NON_AUTHORITATIVE_INFO = 203
    NO_CONTENT = 204
    RESET_CONTENT = 205
    PARTIAL_CONTENT = 206
    MULTIPLE_CHOICES = 300
    MOVED_PERMANENTLY = 301
    MOVED_TEMPORARILY = 302
    SEE_OTHER = 303
    NOT_MODIFIED = 304
    USE_PROXY = 305
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    PAYMENT_REQUIRED = 402
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    NOT_ACCEPTABLE = 406
    PROXY_AUTH_REQUIRED = 407
    TIME_OUT = 408
    CONFLICT = 409
    GONE = 410
    LENGTH_REQUIRED = 411
    PRECONDITION_FAILED = 412
    REQUEST_TOO_LARGE = 413
    URI_TOO_LARGE = 414
    UNSUPPORTED_MEDIA_TYPE = 415
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIME_OUT = 504
    HTTP_VERSION_NOT_SUPPORTED = 505

HTTPCodes = _http_codes()
"""A standard set of the defined HTTP result codes from RFC 2616."""

def HTTP_error_message(code):
    for key, value in _http_codes.__dict__:
        if code == value:
            return key

############################################################
###
###  class TitleFinder
###
############################################################

class ParsingDone(Exception):
    """Class to signal the end of parsing."""
    pass

class TitleFinder (HTMLParser):
    """
    Class to find the title in an HTML page.  After parsing the page
    through an instance of this class, call ``clean_title`` to obtain
    a sanitized version of the title.
    """

    def __init__(self):
        self.parsing = False
        self.title = None
        HTMLParser.__init__(self)

    def handle_starttag (self, tag, attrs):
        if tag.lower() == 'title':
            self.parsing = True
            self.title = u""

    def handle_endtag (self, tag):
        if tag.lower() == 'title':
            self.parsing = False
            raise ParsingDone()

    def handle_data (self, data):
        if self.parsing:
            self.title = self.title + data

    def handle_charref (self, number):
        if self.parsing:
            self.title = self.title + unichr(int(number))

    def handle_entityref (self, name):
        if self.parsing:
            self.title = self.title + unichr(htmlentitydefs.name2codepoint.get(name) or '?')

    def clean_title (self):
        """Returns the title, if one was found.

        :return: the title as a string, or ``None``
        :rtype: string
        """
        if self.title:
            s = re.sub('\s', ' ', self.title)
            s = re.sub('\s\s', ' ', s)
            s = s.strip()
            return s
        else:
            return None


############################################################
###
###  cookies
###
############################################################

COOKIE_DICT = None
"""Cache of cookies from some browser store."""

class FirefoxCookieReader:
    """Class to read cookies from a Firefox cookie store."""

    # Firefox (and Mozilla) use one cookie per line, fixed fields

    COOKIE_LINE = re.compile("([^\s]+)\s+(TRUE|FALSE)\s+([^\s]+)\s+(TRUE|FALSE)\s+([0-9]+)\s+([^\s]+)\s+(.*)$")

    def __init__(self, filepath):
        self.filepath = filepath

    def _read (self):
        """Read the cookies and return them.

        :return: cookies read from ``self.filename``
        :rtype: dict maping domain to cookie
        """
        f = open(self.filepath, 'r')
        cookies = {}
        lines = f.readlines()
        f.close()
        for line in lines:
            line = line.strip()
            if (not line) or (line[0] == '#'):
                continue
            m = self.COOKIE_LINE.match(line)
            if m:
                domain = m.group(1)
                expire_date = ""
                expire_long = long(m.group(5))
                try:
                    expire_date = datetime.datetime.utcfromtimestamp(expire_long).isoformat() + "Z"
                except ValueError, x:
                    note(4, "webcookies.read found cookie with illegal expire date [%s].  Error = [%s]" , line, str(x))
                    continue
                new_cookie = {
                    "domain": m.group(1),
                    "name": m.group(6),
                    "value": m.group(7),
                    "expires": expire_date,
                    "path": m.group(3),
                    }
                if cookies.has_key(domain):
                    cookies[domain].append(new_cookie)
                else:
                    cookies[domain] = [new_cookie,]
        return cookies

    def readfile(filepath):
        """Read the cookies from the specified file.

        :param filepath: file to read cookies from
        :type filepath: pathname string
        :return: cookies in file
        :rtype: dict mapping domain to cookie
        """
        reader = FirefoxCookieReader(filepath)
        return reader._read()
    readfile = staticmethod(readfile)
    

class SafariCookieReader (HTMLParser):

    # Safari uses an XML format for its cookie storage.
    # Luckily, it's simple enough that Python's HTML parser can handle it.

    __pychecker__ = "unusednames=attr, no-abstract"

    def __init__(self):
        self.cookies = {}
        self.current_cookie = None
        self.field_name = None
        self.field_value = None
        self.d_name = None
        HTMLParser.__init__(self)

    def handle_starttag (self, tag, attrs):
        if tag == "dict":
            self.current_cookie = {}
        elif self.current_cookie is not None:
            self.field_name = tag
            self.field_value = ""
        #print "start(%s):  %s, %s" % (tag, self.current_cookie, self.field_name)

    def handle_endtag (self, tag):
        if tag == "dict":
            if self.current_cookie is not None:
                domain = self.current_cookie.get("domain")
                if domain:
                    if self.cookies.has_key(domain):
                        self.cookies[domain].append(self.current_cookie)
                    else:
                        self.cookies[domain] = [self.current_cookie,]
            self.current_cookie = None
        elif self.current_cookie is not None:
            if tag == self.field_name:
                if tag == "key":
                    self.d_name = self.field_value.lower()
                    self.field_value = ""
                else:
                    if self.d_name is not None:
                        self.current_cookie[self.d_name] = urllib.unquote(self.field_value)
                    self.d_name = None
                    self.field_value = None
            self.field_name = None
        #print "end(%s):  %s, %s, %s, %s" % (tag, self.current_cookie, self.field_name, self.d_name, self.field_value)

    def handle_data (self, data):
        if self.field_name:
            self.field_value = self.field_value + data

    def handle_charref (self, name):
        if self.field_name and name.startswith("&#") and name.endswith(";"):
            self.field_value = self.field_value + unichr(name[2:-1])

    def handle_entityref (self, name):
        if self.field_name:
            self.field_value = self.field_value + unichr(htmlentitydefs.name2codepoint.get(name) or '?')

    def readfile (filepath):
        """Read the cookies from the specified file.

        :param filepath: file to read cookies from
        :type filepath: pathname string
        :return: cookies in file
        :rtype: dict mapping domain to cookie
        """
        tf = SafariCookieReader()
        f = open(filepath, 'r')
        tf.feed(f.read())
        f.close()
        return tf.cookies
    readfile = staticmethod(readfile)


def set_cookies_source (source):
    """Define the global source of cookies and initialize COOKIE_DICT

    :param source: where the cookies are
    :type source: pathname string
    """
    global COOKIE_DICT
    COOKIE_DICT = get_source_cookies(source)

def get_cookies(url):
    
    return (COOKIE_DICT and get_cookie_header_value(COOKIE_DICT, url)) or ""

def get_source_cookies(cookies_source):
    p = cookies_source.find(":")
    if (p >= 0):
        browser_type = cookies_source[:p]
        cookies_filepath = os.path.expanduser(cookies_source[p+1:])
        if not os.path.exists(cookies_filepath):
            raise IOError("No such cookies file \"%s\"" % cookies_filepath)
    else:
        raise ValueError("cookies_source string must have colon separator between browser type and cookies file:  \"%s\" doesn't." % cookies_source)
    if browser_type.lower().startswith("safari-1"):
        return SafariCookieReader.readfile(cookies_filepath)
    elif browser_type.lower().startswith("firefox-1"):
        return FirefoxCookieReader.readfile(cookies_filepath)
    else:
        raise ValueError("Unsupported browser type %s" % browser_type)

def get_cookie_header_value_rfc (cookie_dict, url):
    # this formats it as per RFC 2109, which few servers seem to support properly
    host, port, path = parse_URL(url)
    cookie_string = ""
    for cookie_key in cookie_dict.keys():
        if host.endswith(cookie_key):
            clist = cookie_dict[cookie_key]
            for cookie in clist:
                cookie_string = cookie_string + ";%s=\"%s\";$Path=\"%s\";$Domain=\"%s\"" % (cookie.get("name"), cookie.get("value"), cookie.get("path"), cookie.get("domain"))
    if cookie_string:
        cookie_string = "$Version=\"0\"" + cookie_string
    return cookie_string

def get_cookie_header_value (cookie_dict, url):
    # this formats is as per the original Netscape document
    host, port, path = parse_URL(url)
    cookie_string = ""
    for cookie_key in cookie_dict.keys():
        if host.endswith(cookie_key):
            clist = cookie_dict[cookie_key]
            for cookie in clist:
                if cookie_string:
                    cookie_string = cookie_string + "; "
                cookie_string = cookie_string + "%s=%s" % (cookie.get("name"), cookie.get("value"))
    return cookie_string

def get_htmldoc_cookies (url):
    return (COOKIE_DICT and _get_htmldoc_cookies(COOKIE_DICT, url)) or ""

def _get_htmldoc_cookies (cookie_dict, url):
    # this format is for htmldoc, 1.8.24 or later
    host, port, path = parse_URL(url)
    cookie_string = ""
    count = 0
    for cookie_key in cookie_dict.keys():
        if host.endswith(cookie_key):
            clist = cookie_dict[cookie_key]
            for cookie in clist:
                if cookie_string:
                    cookie_string = cookie_string + "; "
                name = cookie.get("name")
                value = cookie.get("value")
                if (value.find(";") >= 0) or (len(value.split()) > 1):
                    value = '"' + value + '"'
                cookie_string = cookie_string + name + "=" + value
                count = count + 1
    if cookie_string:
        cookie_string = "--cookies '" + cookie_string + "'"
    return cookie_string

#
# this is some code for testing new cookie file formats
# use it as:  python -c "from uplib.utilities.web import show_cookies; show_cookies(TYPE:FILENAME)"
#
def show_cookies(source):
    cookies = get_source_cookies(source)
    for key in cookies.keys():
        v = cookies[key]
        for cookie in v:
            domain = cookie.get("domain")
            print domain
            for key2 in cookie.keys():
                print "\t", key2, cookie[key2]

############################################################
###
###  class Fetcher
###
############################################################

class Fetcher(object):
    """Class supporting fetching stuff from other Web sites."""

    def __init__(self, proxies=None):
        self.proxie_info = {}
        self.proxie_info.update(self.STANDARD_PROXIES)
        if isinstance(proxies, dict):
            self.proxie_info.update(proxies)

    DATA_URI_PATTERN = re.compile(r'data:(?P<maintype>[^/;]+?)/(?P<subtype>[^/;]+?)(?P<params>;[^;]+?)*?(;(?P<encoding>base64))?,(?P<data>.*)$', re.MULTILINE | re.DOTALL)
    """RE matching the data: URL scheme"""

    COOKIE_STRING_OK_SIZE = 2048
    """Max size for cookie"""

    STANDARD_PROXIES = {}
    """Dict mapping domains to proxies"""

    def set_standard_proxies(d):
        """Update the STANDARD_PROXIES with the proxy settings in ``d``.

        :param d: dict mapping domains to proxies
        :type d: dict
        """
        Fetcher.STANDARD_PROXIES.update(d)
    set_standard_proxies = staticmethod(set_standard_proxies)

    def get_self_referer (url):
        """Get a reference to the top-level site for the given URL.

        :param url: URL
        :type url: string
        :return: URL
        :rtype: string
        """
        scheme, location, path, parameters, query, fragment = urlparse.urlparse(url)
        return "%s://%s/" % (scheme, location)
    get_self_referer = staticmethod(get_self_referer)

    def set_proxies(self, d):
        """Set the proxies for this fetcher.

        :param d: mapping of domains to proxies
        :type d: dict
        """
        self.proxie_info = d

    def get_proxy (self, url):
        """Get the proxy to use for the specified url.

        :param url: the URL to get the proxy for
        :type url: string
        :return: proxy to use for the specified URL, if any
        :rtype: string, or ``None``
        """
        host, port, path = parse_URL(url)
        return self.proxie_info.get(host)

    class Redirected(Exception):
        """Exception raised on redirect.  Two attributes:  ``original_url``
        gives the original URL, and ``redirect_url`` gives the URL it was
        redirected to.
        """
        def __init__(self, original_url, redirect_url):
            Exception.__init__(self, "Re-directed from %s to %s" % (str(original_url), str(redirect_url)))
            self.original_url = original_url
            self.redirect_url = redirect_url

    class _RefetchingRedirectHandler (urllib2.HTTPRedirectHandler):
        INSTALLED = False
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            if hasattr(req, 'redirect_allowed'):
                if not req.redirect_allowed:
                    raise Redirected(req.get_full_url(), newurl)
                elif (isinstance(req.redirect_allowed, int) and
                      hasattr(req, "redirect_count")):
                    v = req.redirect_count
                    if isinstance(v, list) and isinstance(v[0], int):
                        count = v[0]
                        if count >= req.redirect_allowed:
                            note(3, "Too many redirect requests for %s: %s", req.get_full_url(), v)
                            raise Redirected(req.get_full_url(), newurl)
            newreq = urllib2.HTTPRedirectHandler.redirect_request(self, req, fp, code, msg, headers, newurl)
            note(3, "redirecting from %s to %s...", req.get_full_url(), newreq.get_full_url())
            cookie_string = req.headers.get("cookie") or ""
            new_cookies = headers.getheaders('set-cookie')
            if new_cookies:
                for c in new_cookies:
                    p = c.split(';')
                    cookie_string = cookie_string + p[0].strip() + "; "
                note(4, "  cookies are now %s", repr(cookie_string.strip()))
                if len(cookie_string) > Fetcher.COOKIE_STRING_OK_SIZE:
                    note("cookie_string for %s is very large (%d bytes):  \"%s\"", newreq.get_host(), len(cookie_string), cookie_string)
                newreq.headers['Cookie'] = cookie_string.strip()
            if hasattr(req, 'redirect_count'):
                req.redirect_count[0] = req.redirect_count[0] + 1
                req.redirect_count.append(newreq.get_full_url())
                newreq.redirect_count = req.redirect_count
            return newreq

    def fetch_url(self, url, filename, redirect_allowed=True, password=None):

        """Fetch the specified URL.  If successful, this will return normally,
        with the contents of the specified URL in ``filename``.  If not successful,
        this will raise an instance of urllib2.HTTPError, or urllib2.URLError, or
        EnvironmentError, or Redirected.

        :param url: the URL to fetch
        :type url: string
        :param filename: a file to store the URL in.
        :type filename: pathname string, or Python file object open for write
        :param redirect_allowed: whether or not to follow redirects, defaulting to ``True``
        :type redirect_allowed: boolean
        :param password: password to send along with the request for the URL, defaults to ``None``. \
               If specified, this is sent as the value of a "Password" HTTP header.
        :type password: string
        :return: if successful, returns the headers from the response, plus a boolean value indicating whether the URL was "hard to read".
        :rtype: (rfc822.Message, boolean)
        """        

        def decode_data_url (m):
            maintype = m.group("maintype")
            subtype = m.group("subtype")
            encoding = m.group("encoding")
            params = m.group("params")
            data = m.group("data")
            content_type = "%s/%s" % (maintype, subtype)
            if params:
                content_type += params
            headers = { 'content-type': content_type }
            if encoding:
                headers['content-transfer-encoding'] = encoding
            if encoding == "base64":
                data = base64.decodestring(data)
            return headers, data

        m = self.DATA_URI_PATTERN.match(url)
        if m:
            headers, data = decode_data_url(m)
            hard_to_read = True

        else:

            if not self._RefetchingRedirectHandler.INSTALLED:
                urllib2.install_opener(urllib2.build_opener(self._RefetchingRedirectHandler()))
                self._RefetchingRedirectHandler.INSTALLED = True

            cookie_string = get_cookies(url)
            req = urllib2.Request(url)
            req.redirect_count = list((0,))
            req.redirect_allowed = redirect_allowed
            if cookie_string:
                if len(cookie_string) > self.COOKIE_STRING_OK_SIZE:
                    note(3, "cookie_string for %s is very large (%d bytes):  \"%s\"", req.get_host(), len(cookie_string), cookie_string)
                req.add_header("Cookie", "$Version=0;" + cookie_string)
            else:
                # note("no cookies")
                pass
            if password:
                req.add_header("Password", password)
            req.add_header("Referer", self.get_self_referer(url))
            req.add_header("User-Agent", "UpLib %s" % UPLIB_VERSION)
            host, port, path = parse_URL(url)
            proxy = self.get_proxy(url)
            note(4, "get_proxy(%s) => %s", url, proxy)
            if proxy:
                scheme, host2, port, path = parse_URL_with_scheme(proxy)
                note(3, "setting proxy to %s", proxy)
                req.set_proxy(host2, scheme)
            try:
                # note(4, "opening %s... (%s)", req.get_full_url(), socket.gethostbyname(host))
                f = urllib2.urlopen(req)
                data = f.read()
                headers = f.info()
                f.close()
                hard_to_read = (req.redirect_count[0] > 0)
            except urllib2.HTTPError, x:
                note(4, "Can't open URL %s:\n%s", url,
                     ''.join(traceback.format_exception(*sys.exc_info())))
                raise x
            except urllib2.URLError, x:
                note(3, "Can't open URL %s:\n%s", url, 
                     ''.join(traceback.format_exception(*sys.exc_info())))                 
                raise x
            except EnvironmentError, x:
                note(3, "Can't open URL %s:\n%s", url,
                     ''.join(traceback.format_exception(*sys.exc_info())))                 
                raise x

        if hasattr(filename, "write"):
            fp = filename
        else:
            fp = open(filename, 'wb')
        fp.write(data)
        if not hasattr(filename, "write"):
            fp.close()
        note(3, "fetched %d bytes from %s", len(data), url)
        return headers, hard_to_read


############################################################
###
###  class Cache
###
############################################################

class Cache(object):

    """Class to support caching of Web pages.  Instantiating it will
    cause the pull to happen."""

    MAXDEPTH=5
    """Amount of depth to follow include links to."""

    _CONTENT_CLASSES = {}

    def __init__(self, url, filename=None, directory=None, pulled=None, fetcher=None, depth=0, subdir=None,
                 bits=None, content_type=None, charset=None, use_correct_suffix=False):
        """
        Creates a locally cached copy of the specified URL, doing a depth-first
        recursive sweep of all included content.  After instantiation, check the
        ``failed`` flag to see if the content could be obtained; if ``False``, the
        ``filename`` attribute will point to the root of the locally cached copy.

        :param url: the URL to fetch
        :type url: URL string
        :param filename: the full path of a file to store the local copy in (optional)
        :type filename: a pathname string
        :param directory: a directory in which to put the cached copy, if no `filename` is specified (optional)
        :type directory: a pathname string
        :param pulled: a dictionary of (SHA-HASH -> CACHE INSTANCE) mappings (optional)
        :type pulled: mapping
        :param fetcher: a fetcher to use to fetch the bits
        :type fetcher: .Fetcher
        :param depth: current recursion depth (optional, defaults to 0)
        :type depth: integer
        """
        if depth >= self.MAXDEPTH:
            raise ValueError("Recursion depth of %d exceeds maximum depth %d" % (depth, self.MAXDEPTH))

        self.depth = depth

        self.filename = filename
        if filename:
            dirpiece, filenamepiece = os.path.split(filename)
            if not dirpiece:
                from uplib.addDocument import mktempdir
                dirpiece = directory or mktempdir()
                self.filename = os.path.join(dirpiece, filenamepiece)
        self.directory = directory
        self.subdir = subdir                              # this is for nested content only

        if self.directory and not os.path.exists(self.directory):
            raise ValueError("Specified directory %s does not exist" % self.directory)
        self.url = url
        self.content_type = content_type
        if charset is None:
            # default for HTML is Latin-1
            self.charset_string = 'ISO-8859-1'
        else:
            self.charset_string = charset
        self.server_date = None
        self.good_for = None
        if fetcher is None:
            self.fetcher = Fetcher()
        else:
            self.fetcher = fetcher
        self.sha_hash = None
        self.content_class = None
        self.nested_content = {}

        # hard-to-read is about whether processor programs like HTMLDOC should be pointed
        # at the original URL, or whether the post-processed cached version should be used
        # instead, because the original is just too hard for them to read

        self.hard_to_read = False

        if pulled is None:
            pulled = {}

        self.failed = False
        if bits:
            if not self.filename:
                self.set_filename(tempfile.mktemp())
            fp = open(self.filename, "wb")
            fp.write(bits)
            fp.close()
        else:
            self.pull()
            
        if not self.failed:

            # now we know the Content-Type
            if use_correct_suffix and self.content_type:
                namepiece, suffixpiece = os.path.splitext(self.filename)
                suffix = self.suffix_for_ctype(self.content_type) or suffixpiece
                newfilename = namepiece + suffix
                os.rename(self.filename, newfilename)
                self.filename = newfilename

            self.calculate_hash()

            if pulled and self.sha_hash in pulled:
                os.unlink(self.filename)
                self.filename = pulled.get(self.sha_hash).filename
            else:
                pulled[self.sha_hash] = self
                self.scan_nested_content()
                self.pull_nested_content(pulled)
                self.filter_content(pulled)

    def __str__(self):
        return "<uplib.webutils.Cache " + self.url + (self.failed and " (failed)>" or ">")

    def calculate_hash(self):
        newhash = hashlib.sha1()
        fp = open(self.filename, 'rb')
        data = fp.read(2 << 16)
        while data:
            newhash.update(data)
            data = fp.read(2 << 16)
        fp.close()
        self.sha_hash = newhash.hexdigest()

    def scan_nested_content(self):
        """
        This routine looks through the content for includes of various kinds that
        require further calls.  The default routine just yields an empty list.
        """
        if self.content_class:
            self.nested_content = self.content_class.scan_nested_content(self)
        else:
            self.nested_content = {}

    def pull_nested_content(self, pulled):
        """
        This routine will pull all the pieces listed in self.nested_content.
        If the pieces are already present, in pulled, those are used instead.
        """
        if not self.subdir and self.content_type == "text/html":
            # emulate Mozilla "Web Page Complete"
            directory = os.path.splitext(self.filename)[0] + "_files"
            if not os.path.exists(directory):
                os.mkdir(directory)
            subdir = os.path.basename(directory)
        else:
            directory = self.directory
            subdir = self.subdir
        for url in self.nested_content:
            nurl = urlparse.urljoin(self.url, url)
            if nurl != self.url:
                c = Cache(nurl, directory=directory, pulled=pulled, subdir=subdir,
                          depth=self.depth+1)
                if not c.failed:
                    if not os.path.exists(c.filename):
                        note("Non-failed cache %s has non-existent filename %s!" % (c, c.filename))
                        c.failed = True
                    else:
                        suffix = os.path.splitext(c.filename)[1]
                        dirname = os.path.dirname(c.filename)
                        newname = os.path.join(dirname, c.sha_hash + suffix)
                        os.rename(c.filename, newname)
                        c.filename = newname
                elif c.filename and os.path.exists(c.filename):
                    os.unlink(c.filename)
                self.nested_content[url] = c
                note(4, "  %s => %s", url, c.filename)
            else:
                self.nested_content[url] = self

    def filter_content(self, pulled):
        if self.content_class:
            self.content_class.filter_content(self, pulled)


    __SUFFIXES = {
        'text/html' :                   ".html",
        'image/gif' :                   ".gif",
        'image/jpeg' :                  ".jpg",
        'image/png' :                   ".png",
        'text/css' :                    ".css",
        'application/x-javascript':     ".js",
        'text/javascript':              ".js",
        'image/x-icon':                 ".ico",
        'image/ico':                    ".ico",
        'image/vnd.microsoft.icon':     ".ico",
        }

    def suffix_for_ctype(self, ctype):
        ext = get_extension_for_type(ctype)
        if not ext:
            endpos = ctype.find(';')
            if endpos > 0:
                ctype = ctype[:endpos]
            return self.__SUFFIXES.get(ctype.lower())
        else:
            return "." + ext

    def set_filename(self, default_pathname):
        directory, filename = os.path.split(default_pathname)
        basename, suffix = os.path.splitext(filename)
        if (not self.filename) and self.content_type:
            suffix = self.suffix_for_ctype(self.content_type) or suffix
        if self.filename:
            directory, filename = os.path.split(self.filename)
            basename, specified_suffix = os.path.splitext(filename)
            suffix = suffix or specified_suffix
            # what do we do if specified_suffix != suffix?
        if self.directory:
            directory = self.directory
        self.filename = os.path.join(directory, basename + suffix)

    def pull (self):

        host, port, upath = parse_URL(self.url)
        suffix = os.path.splitext(upath)[1]
        fd, tfilepath = tempfile.mkstemp()
        fp = os.fdopen(fd, "wb")
        try:
            headers, hard_to_read = self.fetcher.fetch_url(self.url, fp, redirect_allowed=4)
            fp.close()
        except:
            self.failed = "".join(traceback.format_exception(*sys.exc_info()))
            note(3, "Exception pulling remote_url '%s'\n%s", self.url, self.failed)
            fp.close()
        else:
            self.hard_to_read = hard_to_read
            content_type = headers.get("content-type") or "application/octet-stream"
            if content_type:
                if (content_type.find(";") >= 0):
                    self.content_type = content_type[:content_type.find(";")]
                    params = content_type[content_type.find(";")+1:].strip(' ;')
                    params = [[y.strip() for y in x.split("=")] for x in params.split(';')]
                    try:
                        d = dict(params)
                    except:
                        note("Invalid params string in '%s':\n%s", content_type,
                             ''.join(traceback.format_exception(*sys.exc_info())))
                    else:
                        if 'charset' in d:
                            self.charset_string = d['charset']
                            note(4, "charset for %s is %s", self.url, self.charset_string)
                else:
                    self.content_type = content_type
            d = headers.get("date")
            if d:
                try:
                    self.server_date = time.mktime(parsedate(d)) - time.timezone
                except:
                    self.server_date = time.time()
            else:
                self.server_date = time.time()
            d = headers.get("age")
            if d:
                age = float(d.strip())
                self.server_date -= age
            d = headers.get("expires")
            if d and self.server_date:
                try:
                    expires = time.mktime(parsedate(d)) - time.timezone
                    self.good_for = max(0, expires - self.server_date)
                except:
                    pass
            if not self.filename:
                self.set_filename(tfilepath)
            if os.path.exists(self.filename):
                os.unlink(self.filename)
            os.rename(tfilepath, self.filename)
            if self.content_type in self._CONTENT_CLASSES:
                self.content_class = self._CONTENT_CLASSES.get(self.content_type)(self.url, self.charset_string)

    def remove(self):
        note(4, "removing cached %s...", self)
        if (not self.failed) and self.filename and os.path.exists(self.filename):
            os.unlink(self.filename)
        for cache in self.nested_content.values():
            if isinstance(cache, Cache):
                cache.remove()

    def copy_to_dir(self, directory, subdir=None):
        if self.failed or (not self.filename):
            return
        if subdir:
            newdir = os.path.join(directory, subdir)
            if not os.path.exists(newdir):
                os.mkdir(newdir)
            newpathname = os.path.join(newdir, os.path.basename(self.filename))
        else:
            newpathname = os.path.join(directory, os.path.basename(self.filename))
        note(4, "copying cached %s to %s...", self.filename, newpathname)
        shutil.copyfile(self.filename, newpathname)
        for c in self.nested_content.values():
            if isinstance(c, Cache):
                c.copy_to_dir(directory, c.subdir)
            


class ContentTypeHandler (object):

    CDATA_EXPR = re.compile(r'(/\*\<\!\[CDATA\[\*/)|(/\*\]\]\>\*/)|(//\<\!\[CDATA\[)|(//\]\]\>)')

    def __init__(self, base_url, charset_string):
        self.base_url = base_url

    def scan_nested_content(self, cache):
        """
        This routine looks through the content in 'cache' for includes of various kinds that
        require further calls.  The default routine just yields an empty mapping.
        """
        return {}

    def filter_content(self, cache, pulled):
        """
        This routine looks through the content in 'cache', and filters it as necessary.
        'pulled' is a hash-to-Cache mapping for use by the routine if useful.
        """
        pass


class JavascriptContentTypeHandler (ContentTypeHandler):

    def filter_javascript_data (data):
        retval = ''
        for line in data.split('\n'):
            if line.strip().startswith("top.location.replace"):
                # nasty trick the NY Times plays
                line = '// ' + line
            if re.search(r'document\.write\([^\)]*/ad\.doubleclick\.net/[^\)]*', line):
                # just delete it -- it confuses HTMLDOC
                line = '\n'
            line, count = ContentTypeHandler.CDATA_EXPR.subn('', line)
            retval += line + '\n'
        return retval
    filter_javascript_data = staticmethod(filter_javascript_data)

    def filter_content (self, cache, pulled):
        if cache.failed:
            return
        fd, filepath = tempfile.mkstemp()
        fp = os.fdopen(fd, "w")
        retval = ''
        input = open(cache.filename, "r")
        for line in input:
            line = self.filter_javascript_data(line)
            fp.write(line)
        input.close()
        fp.close()
        os.unlink(cache.filename)
        os.rename(filepath, cache.filename)

Cache._CONTENT_CLASSES["text/javascript"] = JavascriptContentTypeHandler
Cache._CONTENT_CLASSES["application/x-javascript"] = JavascriptContentTypeHandler

class CSSContentTypeHandler (ContentTypeHandler):

    CSS_URL = re.compile(r"\s+url\(['\"]?([^)'\"]+)['\"]?\)")
    CSS_IMPORT = re.compile(r'(@import\s+"(?P<url1>[^"]+)"\s*;)|(@import\s+url\((?P<url2>[^)]+)\)\s*;)', re.MULTILINE)

    def __init__(self, base_url, charset_string):
        ContentTypeHandler.__init__(self, base_url, charset_string)
        self.nested = {}

    def find_nested_imports(lines, base_url, nests):
        for line in lines.split("\n"):
            m = CSSContentTypeHandler.CSS_IMPORT.search(line)
            if m:
                url = (m.group("url1") or m.group("url2")).strip()
                nests[url] = urlparse.urljoin(base_url, url)
    find_nested_imports = staticmethod(find_nested_imports)

    def filter_css_data(lines, use_subdir, replacements):
        # we make this static so we can call it from the HTML parser
        retval = ''
        for line in lines.split("\n"):
            line, count = ContentTypeHandler.CDATA_EXPR.subn('', line)
            m = CSSContentTypeHandler.CSS_IMPORT.search(line)
            if m:
                c = None
                if m.group("url1"):
                    c = replacements.get(m.group("url1").strip())
                    start = m.start("url1")
                    end = m.end("url1")
                elif m.group("url2"):
                    c = replacements.get(m.group("url2").strip())
                    start = m.start("url2")
                    end = m.end("url2")
                if c and not c.failed:
                    replacement = os.path.basename(c.filename)
                    if use_subdir and c.subdir:
                        replacement = os.path.join(c.subdir, replacement)
                else:
                    replacement = ""
                retval += line[:start] + replacement + line[end:] + '\n'
            else:
                retval += line + '\n'
        return retval
    filter_css_data = staticmethod(filter_css_data)

    def scan_nested_content(self, cache):
        input = open(cache.filename, "r")
        for line in input:
            self.find_nested_imports(line, self.base_url, self.nested)
        input.close()
        return self.nested

    def filter_content (self, cache, pulled):
        if cache.failed:
            return
        if not os.path.exists(cache.filename):
            note("CSSContentTypeHandler:  nested CSS cache file %s (%s), referenced by %s, doesn't exist!"
                 % (cache.filename, cache, self.base_url))
            cache.failed = True
            return
        fd, filepath = tempfile.mkstemp()
        fp = os.fdopen(fd, "w")
        input = open(cache.filename, "r")
        for line in input:
            line = self.filter_css_data(line, (cache.directory is None), self.nested)
            fp.write(line)
        input.close()
        fp.close()
        os.unlink(cache.filename)
        os.rename(filepath, cache.filename)

Cache._CONTENT_CLASSES["text/css"] = CSSContentTypeHandler


class HTMLContentTypeHandler (HTMLParser, ContentTypeHandler):

    COMPLETE_TAGS = ('br', 'link', 'meta')

    CDATA_EXPR = re.compile(r'(/\*\<\!\[CDATA\[\*/)|(/\*\]\]\>\*/)|(//\<\!\[CDATA\[)|(//\]\]\>)')

    def __init__(self, base_url, charset_string=None):
        HTMLParser.__init__(self)
        ContentTypeHandler.__init__(self, base_url, charset_string)
        self.title = None
        self.in_title = False
        self.in_style = False
        self.in_map = False
        self.nested = {}
        self.stuff = [{'charset-string': charset_string or 'iso-8859-1', 'elements': [], 'start-line': 0, 'start-offset': 0}]

    def parse_starttag(self, i):

        def handle_malformed_starttag(cacher):
            lineno, offset = cacher.getpos()
            endpos = cacher.rawdata.find('>', i)
            cacher.updatepos(i, endpos)
            tagtext = cacher.rawdata[i:endpos+1]
            note(3, "Malformed start tag '%s' in %s at line %s, column %s",
                 tagtext, cacher.base_url, lineno, offset)
            return ((endpos < 0) and endpos) or (endpos + 1)

        try:
            rval = HTMLParser.parse_starttag(self, i)
            if rval < 0:
                if self.rawdata.find(">", i) >= 0:
                    return handle_malformed_starttag(self)
            return rval
        except HTMLParseError, x:
            if x.msg.startswith("malformed start tag"):
                return handle_malformed_starttag(self)
            elif x.msg.startswith("junk characters in start tag:"):
                return handle_malformed_starttag(self)
            else:
                raise

    def parse_endtag(self, i):

        def handle_malformed_endtag(cacher):
            lineno, offset = cacher.getpos()
            endpos = cacher.rawdata.index('>', i)
            note("handling bad endtag '%s'", self.rawdata[i+1:endpos])
            t = re.match(r'/(?P<ts>.+)"\s*\+\s*"(?P<te>.+)>', self.rawdata[i+1:endpos+1])
            if t:
                tag = t.group('ts') + t.group('te')
                self.handle_endtag(tag.lower())
                self.clear_cdata_mode()
            else:
                cacher.updatepos(i, endpos)
                note("Malformed end tag in %s at line %s, column %s",
                     cacher.base_url, lineno, offset)
            return ((endpos < 0) and endpos) or (endpos + 1)

        try:
            rval = HTMLParser.parse_endtag(self, i)
            if rval < 0:
                if self.rawdata.find(">", i) >= 0:
                    return handle_malformed_endtag(self)
            return rval
        except HTMLParseError, x:
            if x.msg.startswith("bad end tag"):
                return handle_malformed_endtag(self)
            else:
                raise

    def parse_declaration(self, i):

        def handle_malformed_decl(cacher):
            lineno, offset = cacher.getpos()
            endpos = cacher.rawdata.index('>', i)
            cacher.updatepos(i, endpos)
            note("Invalid declaration in %s at line %s, column %s:  %s",
                 cacher.base_url, lineno, offset, cacher.rawdata[i:endpos+1])
            return ((endpos < 0) and endpos) or (endpos + 1)

        try:
            rval = HTMLParser.parse_declaration(self, i)
            if rval < 0:
                if self.rawdata.find(">", i) >= 0:
                    return handle_malformed_decl(self)
            return rval
        except HTMLParseError, x:
            return handle_malformed_decl(self)

    def getattr(self, name, attrs):
        for i in range(len(attrs)):
            if attrs[i][0] == name:
                return attrs[i][1], i
        return None, None

    def replaceattr(self, name, value, attrs):
        for i in range(len(attrs)):
            if attrs[i][0] == name:
                attrs[i] = (name, value)
                break
        return attrs

    def checkattrs(self, name, value, attrs):
        for attr in attrs:
            if attr[0] == name and attr[1] == value:
                return True
        return False

    def cacheattr(self, name, attrs):
        for i in range(len(attrs)):
            if attrs[i][0] == name:
                url = attrs[i][1].strip()
                self.nested[url] = urlparse.urljoin(self.base_url, url)
                break
        return attrs

    def handle_starttag (self, tag, attrs):
        tag = tag.lower()
        line_no, offset = self.getpos()
        # note("start tag <%s> at %s:%s (in_style is %s)", tag, line_no, offset, self.in_style)
        if tag in ('img', 'script', 'frame', 'iframe', 'input'):
            attrs = self.cacheattr('src', attrs)
        elif tag == 'link' and (self.checkattrs('rel', 'stylesheet', attrs) or
                                self.checkattrs('rel', 'icon', attrs) or
                                self.checkattrs('rel', 'shortcut icon', attrs)):
            attrs = self.cacheattr('href', attrs)
        elif tag == 'base':
            self.base_url, index = self.getattr('href', attrs)
            self.stuff[-1]['base-url'] = self.base_url
        elif tag == 'meta' and (self.checkattrs('http-equiv', 'content-type', attrs) or
                                self.checkattrs('http-equiv', 'Content-Type', attrs)):
            content_type, index = self.getattr('content', attrs)
            if index is not None:
                charset_match = re.search("charset=([^;]+)", content_type)
                if charset_match:
                    self.stuff[-1]["charset-string"] = charset_match.group(1)
                    note(3, "%d:%d:  charset for document %s is %s", line_no, offset, self.base_url, charset_match.group(1))
        elif tag == 'input' and self.checkattrs('type', 'image', attrs):
            attrs = self.cacheattr('src', attrs)
        elif tag in ('a', 'link') or (tag == 'area' and self.in_map):
            href, index = self.getattr('href', attrs)
            if index is not None and href:
                if href[0] != '#':
                    href = urlparse.urljoin(self.base_url, href)
                attrs[index] = ('href', href)
        elif tag == 'form':
            href, index = self.getattr('action', attrs)
            if index is not None:
                href = urlparse.urljoin(self.base_url, href)
                attrs[index] = ('action', href)
        elif tag == 'title':
            self.in_title = True
            self.title = ""
        elif tag == 'style':
            self.in_style = True
        elif tag == 'map':
            self.in_map = True
        elif tag == 'head':
            # start a new chunk
            self.stuff.append({'charset-string': self.stuff[-1].get("charset-string"),
                               'elements': [],
                               'start-line': line_no,
                               'start-offset': offset})
        if tag != 'base':
            self.stuff[-1]['elements'].append(('tag', tag, attrs))

    def handle_endtag (self, tag):
        name = tag.lower()
        if name != 'base':
            self.stuff[-1]['elements'].append(('etag', tag))
        if name == 'title':
            self.in_title = False
        elif name == 'style':
            self.in_style = False
        elif name == 'map':
            self.in_map = False

    def handle_data (self, data):
        if self.in_title:
            self.title += data
        elif self.in_style:
            CSSContentTypeHandler.find_nested_imports(data, self.base_url, self.nested)
        self.stuff[-1]['elements'].append(('data', data))

    def handle_charref (self, name):
        self.stuff[-1]['elements'].append(('charref', name))
        if self.in_title:
            self.title += ("&#%s;" % name)

    def handle_entityref (self, name):
        self.stuff[-1]['elements'].append(('eref', name))
        if self.in_title:
            self.title += ("&%s;" % name)

    def handle_comment (self, data):
        self.stuff[-1]['elements'].append(('comment', data))

    def handle_decl (self, decl):
        self.stuff[-1]['elements'].append(('decl', decl))

    def unknown_decl(self, decl):
        note(3, "Non-standard declaration '%s' seen.", decl)

    def handle_pi(self, data):
        self.stuff[-1]['elements'].append(('pi', data))

    def rewrite_string(self, s, charset=None):
        if charset is None:
            charset = self.stuff[-1].get("charset-string")
        if type(s) != types.UnicodeType:
            try:
                s2 = unicode(s, charset, 'xmlcharrefreplace')
            except:
                note("bad string '%s' for charset %s", s, charset);
                # many blogs lie about what the char encoding is...
                # 1252 isn't a bad fall-back, because every code is defined
                try:
                    s2 = unicode(s, "cp1252", "replace")
                except:
                    note(3, "losing substring with odd characters in it:  %s", repr(s))
                    s2 = ""
                self.stuff[-1]['hard-to-read'] = True
            note(5, "using charset %s, rewrote\n\"%s\" as\n\"%s\"", charset, s, s2)
            return s2
        else:
            return s

    def get_title (self):
        if self.title:
            return unicode(self.title, self.stuff[-1].get("charset-string"), 'xmlcharrefreplace').strip()

    def rewrite(self, path, use_subdir, charset=None):
        in_script = None
        in_style = None
        open_style = 'w'
        for chunk in self.stuff:

            note(4, "\n************** Doing chunk %s *****************", repr(chunk))

            base_url = chunk.get("base-url") or self.base_url
            charset = chunk.get("charset-string") or charset
            fp = codecs.open(path, open_style, charset)
            try:
                for elt in chunk['elements']:
                    elt_type, rest = elt[0], elt[1:]
                    if elt_type == 'tag':
                        name, attrs = rest
                        fp.write("<%s" % self.rewrite_string(name, charset))
                        for aname, aval in attrs:
                            if aval is None:
                                fp.write(htmlescape(" %s" % self.rewrite_string(aname, charset)))
                            else:
                                ref = self.nested.get(aval)
                                if ref and not ref.failed:
                                    aval = os.path.basename(ref.filename)
                                    if use_subdir and ref.subdir:
                                        aval = os.path.join(ref.subdir, aval)
                                        if os.path.sep != '/':
                                            # need URL syntax
                                            aval = aval.replace(os.path.sep, "/")
                                fp.write(htmlescape(" %s=\"%s\"" % (
                                    self.rewrite_string(aname, charset), self.rewrite_string(aval, charset))))
                        if name in self.COMPLETE_TAGS:
                            fp.write("/")
                        fp.write(">")
                        if name == 'script' or name == 'style':
                            in_script = name
                    elif elt_type == 'etag':
                        name = self.rewrite_string(rest[0], charset)
                        if not name in self.COMPLETE_TAGS:
                            fp.write("</%s>" % name)
                        if name == 'script' or name == 'style':
                            in_script = None
                    elif elt_type == 'data':
                        data = self.rewrite_string(rest[0], charset)
                        o = data
                        if in_script == 'script':
                            data = JavascriptContentTypeHandler.filter_javascript_data(data)
                        elif in_script == 'style':
                            data = CSSContentTypeHandler.filter_css_data(data, use_subdir, self.nested)
                        else:
                            data = htmlescape(data)
                        note(5, "%s:  %s => %s", in_script, repr(o), repr(data))
                        fp.write(data)
                    elif elt_type == 'eref':
                        fp.write("&%s;" % self.rewrite_string(rest[0], charset))
                    elif elt_type == 'charref':
                        fp.write("&#%s;" % self.rewrite_string(rest[0], charset))
                    elif elt_type == 'comment':
                        fp.write("<!--%s-->" % self.rewrite_string(rest[0], charset))
                    elif elt_type == 'decl':
                        fp.write('<!%s>' % self.rewrite_string(rest[0], charset))
                    elif elt_type == 'pi':
                        fp.write('<?%s>' % self.rewrite_string(rest[0], charset))
                    else:
                        raise ValueError("Unknown tag type %s found in parse of %s" % (elt_type, base_url))
                open_style = 'a'
            finally:
                fp.close()

    def scan_nested_content(self, cache):
        fp = open(cache.filename, "rb")
        data = fp.read(2 << 16)
        while data:
            self.feed(data)
            data = fp.read(2 << 16)
        fp.close()
        if cache.url != self.base_url:
            cache.url = self.base_url
        return self.nested

    def filter_content(self, cache, pulled):
        note("%d chunks for %s:  %s", len(self.stuff), self.base_url,
             [("%s:%s:%s" % (x.get("start-line"), x.get("start-offset"), x.get("charset-string"))) for x in self.stuff])
        self.rewrite(cache.filename, cache.directory is None)

Cache._CONTENT_CLASSES["text/html"] = HTMLContentTypeHandler
