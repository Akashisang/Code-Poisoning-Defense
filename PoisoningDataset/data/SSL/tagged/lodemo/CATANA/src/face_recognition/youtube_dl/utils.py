#!/usr/bin/env python
# coding: utf-8

from __future__ import unicode_literals

import base64
import binascii
import calendar
import codecs
import contextlib
import ctypes
import datetime
import email.utils
import email.header
import errno
import functools
import gzip
import io
import itertools
import json
import locale
import math
import operator
import os
import platform
import random
import re
import socket
import ssl
import subprocess
import sys
import tempfile
import traceback
import xml.etree.ElementTree
import zlib

from .compat import (
    compat_HTMLParseError,
    compat_HTMLParser,
    compat_basestring,
    compat_chr,
    compat_etree_fromstring,
    compat_expanduser,
    compat_html_entities,
    compat_html_entities_html5,
    compat_http_client,
    compat_kwargs,
    compat_os_name,
    compat_parse_qs,
    compat_shlex_quote,
    compat_socket_create_connection,
    compat_str,
    compat_struct_pack,
    compat_struct_unpack,
    compat_urllib_error,
    compat_urllib_parse,
    compat_urllib_parse_urlencode,
    compat_urllib_parse_urlparse,
    compat_urllib_parse_unquote_plus,
    compat_urllib_request,
    compat_urlparse,
    compat_xpath,
)

from .socks import (
    ProxyType,
    sockssocket,
)


def register_socks_protocols():
    # "Register" SOCKS protocols
    # In Python < 2.6.5, urlsplit() suffers from bug https://bugs.python.org/issue7904
    # URLs with protocols not in urlparse.uses_netloc are not handled correctly
    for scheme in ('socks', 'socks4', 'socks4a', 'socks5'):
        if scheme not in compat_urlparse.uses_netloc:
            compat_urlparse.uses_netloc.append(scheme)


# This is not clearly defined otherwise
compiled_regex_type = type(re.compile(''))

std_headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20150101 Firefox/47.0 (Chrome)',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-us,en;q=0.5',
}


USER_AGENTS = {
    'Safari': 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0) AppleWebKit/533.20.25 (KHTML, like Gecko) Version/5.0.4 Safari/533.20.27',
}


NO_DEFAULT = object()

ENGLISH_MONTH_NAMES = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December']

MONTH_NAMES = {
    'en': ENGLISH_MONTH_NAMES,
    'fr': [
        'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
        'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'],
}

KNOWN_EXTENSIONS = (
    'mp4', 'm4a', 'm4p', 'm4b', 'm4r', 'm4v', 'aac',
    'flv', 'f4v', 'f4a', 'f4b',
    'webm', 'ogg', 'ogv', 'oga', 'ogx', 'spx', 'opus',
    'mkv', 'mka', 'mk3d',
    'avi', 'divx',
    'mov',
    'asf', 'wmv', 'wma',
    '3gp', '3g2',
    'mp3',
    'flac',
    'ape',
    'wav',
    'f4f', 'f4m', 'm3u8', 'smil')

# needed for sanitizing filenames in restricted mode
ACCENT_CHARS = dict(zip('ÂÃÄÀÁÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖŐØŒÙÚÛÜŰÝÞßàáâãäåæçèéêëìíîïðñòóôõöőøœùúûüűýþÿ',
                        itertools.chain('AAAAAA', ['AE'], 'CEEEEIIIIDNOOOOOOO', ['OE'], 'UUUUUYP', ['ss'],
                                        'aaaaaa', ['ae'], 'ceeeeiiiionooooooo', ['oe'], 'uuuuuypy')))

DATE_FORMATS = (
    '%d %B %Y',
    '%d %b %Y',
    '%B %d %Y',
    '%B %dst %Y',
    '%B %dnd %Y',
    '%B %dth %Y',
    '%b %d %Y',
    '%b %dst %Y',
    '%b %dnd %Y',
    '%b %dth %Y',
    '%b %dst %Y %I:%M',
    '%b %dnd %Y %I:%M',
    '%b %dth %Y %I:%M',
    '%Y %m %d',
    '%Y-%m-%d',
    '%Y/%m/%d',
    '%Y/%m/%d %H:%M',
    '%Y/%m/%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M:%S.%f',
    '%d.%m.%Y %H:%M',
    '%d.%m.%Y %H.%M',
    '%Y-%m-%dT%H:%M:%SZ',
    '%Y-%m-%dT%H:%M:%S.%fZ',
    '%Y-%m-%dT%H:%M:%S.%f0Z',
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%dT%H:%M:%S.%f',
    '%Y-%m-%dT%H:%M',
    '%b %d %Y at %H:%M',
    '%b %d %Y at %H:%M:%S',
)

DATE_FORMATS_DAY_FIRST = list(DATE_FORMATS)
DATE_FORMATS_DAY_FIRST.extend([
    '%d-%m-%Y',
    '%d.%m.%Y',
    '%d.%m.%y',
    '%d/%m/%Y',
    '%d/%m/%y',
    '%d/%m/%Y %H:%M:%S',
])

DATE_FORMATS_MONTH_FIRST = list(DATE_FORMATS)
DATE_FORMATS_MONTH_FIRST.extend([
    '%m-%d-%Y',
    '%m.%d.%Y',
    '%m/%d/%Y',
    '%m/%d/%y',
    '%m/%d/%Y %H:%M:%S',
])

PACKED_CODES_RE = r"}\('(.+)',(\d+),(\d+),'([^']+)'\.split\('\|'\)"


def preferredencoding():
    """Get preferred encoding.

    Returns the best encoding scheme for the system, based on
    locale.getpreferredencoding() and some further tweaks.
    """
    try:
        pref = locale.getpreferredencoding()
        'TEST'.encode(pref)
    except Exception:
        pref = 'UTF-8'

    return pref


def write_json_file(obj, fn):
    """ Encode obj as JSON and write it to fn, atomically if possible """

    fn = encodeFilename(fn)
    if sys.version_info < (3, 0) and sys.platform != 'win32':
        encoding = get_filesystem_encoding()
        # os.path.basename returns a bytes object, but NamedTemporaryFile
        # will fail if the filename contains non ascii characters unless we
        # use a unicode object
        path_basename = lambda f: os.path.basename(fn).decode(encoding)
        # the same for os.path.dirname
        path_dirname = lambda f: os.path.dirname(fn).decode(encoding)
    else:
        path_basename = os.path.basename
        path_dirname = os.path.dirname

    args = {
        'suffix': '.tmp',
        'prefix': path_basename(fn) + '.',
        'dir': path_dirname(fn),
        'delete': False,
    }

    # In Python 2.x, json.dump expects a bytestream.
    # In Python 3.x, it writes to a character stream
    if sys.version_info < (3, 0):
        args['mode'] = 'wb'
    else:
        args.update({
            'mode': 'w',
            'encoding': 'utf-8',
        })

    tf = tempfile.NamedTemporaryFile(**compat_kwargs(args))

    try:
        with tf:
            json.dump(obj, tf)
        if sys.platform == 'win32':
            # Need to remove existing file on Windows, else os.rename raises
            # WindowsError or FileExistsError.
            try:
                os.unlink(fn)
            except OSError:
                pass
        os.rename(tf.name, fn)
    except Exception:
        try:
            os.remove(tf.name)
        except OSError:
            pass
        raise


if sys.version_info >= (2, 7):
    def find_xpath_attr(node, xpath, key, val=None):
        """ Find the xpath xpath[@key=val] """
        assert re.match(r'^[a-zA-Z_-]+$', key)
        expr = xpath + ('[@%s]' % key if val is None else "[@%s='%s']" % (key, val))
        return node.find(expr)
else:
    def find_xpath_attr(node, xpath, key, val=None):
        for f in node.findall(compat_xpath(xpath)):
            if key not in f.attrib:
                continue
            if val is None or f.attrib.get(key) == val:
                return f
        return None

# On python2.6 the xml.etree.ElementTree.Element methods don't support
# the namespace parameter


def xpath_with_ns(path, ns_map):
    components = [c.split(':') for c in path.split('/')]
    replaced = []
    for c in components:
        if len(c) == 1:
            replaced.append(c[0])
        else:
            ns, tag = c
            replaced.append('{%s}%s' % (ns_map[ns], tag))
    return '/'.join(replaced)


def xpath_element(node, xpath, name=None, fatal=False, default=NO_DEFAULT):
    def _find_xpath(xpath):
        return node.find(compat_xpath(xpath))

    if isinstance(xpath, (str, compat_str)):
        n = _find_xpath(xpath)
    else:
        for xp in xpath:
            n = _find_xpath(xp)
            if n is not None:
                break

    if n is None:
        if default is not NO_DEFAULT:
            return default
        elif fatal:
            name = xpath if name is None else name
            raise ExtractorError('Could not find XML element %s' % name)
        else:
            return None
    return n


def xpath_text(node, xpath, name=None, fatal=False, default=NO_DEFAULT):
    n = xpath_element(node, xpath, name, fatal=fatal, default=default)
    if n is None or n == default:
        return n
    if n.text is None:
        if default is not NO_DEFAULT:
            return default
        elif fatal:
            name = xpath if name is None else name
            raise ExtractorError('Could not find XML element\'s text %s' % name)
        else:
            return None
    return n.text


def xpath_attr(node, xpath, key, name=None, fatal=False, default=NO_DEFAULT):
    n = find_xpath_attr(node, xpath, key)
    if n is None:
        if default is not NO_DEFAULT:
            return default
        elif fatal:
            name = '%s[@%s]' % (xpath, key) if name is None else name
            raise ExtractorError('Could not find XML attribute %s' % name)
        else:
            return None
    return n.attrib[key]


def get_element_by_id(id, html):
    """Return the content of the tag with the specified ID in the passed HTML document"""
    return get_element_by_attribute('id', id, html)


def get_element_by_class(class_name, html):
    """Return the content of the first tag with the specified class in the passed HTML document"""
    retval = get_elements_by_class(class_name, html)
    return retval[0] if retval else None


def get_element_by_attribute(attribute, value, html, escape_value=True):
    retval = get_elements_by_attribute(attribute, value, html, escape_value)
    return retval[0] if retval else None


def get_elements_by_class(class_name, html):
    """Return the content of all tags with the specified class in the passed HTML document as a list"""
    return get_elements_by_attribute(
        'class', r'[^\'"]*\b%s\b[^\'"]*' % re.escape(class_name),
        html, escape_value=False)


def get_elements_by_attribute(attribute, value, html, escape_value=True):
    """Return the content of the tag with the specified attribute in the passed HTML document"""

    value = re.escape(value) if escape_value else value

    retlist = []
    for m in re.finditer(r'''(?xs)
        <([a-zA-Z0-9:._-]+)
         (?:\s+[a-zA-Z0-9:._-]+(?:=[a-zA-Z0-9:._-]*|="[^"]*"|='[^']*'|))*?
         \s+%s=['"]?%s['"]?
         (?:\s+[a-zA-Z0-9:._-]+(?:=[a-zA-Z0-9:._-]*|="[^"]*"|='[^']*'|))*?
        \s*>
        (?P<content>.*?)
        </\1>
    ''' % (re.escape(attribute), value), html):
        res = m.group('content')

        if res.startswith('"') or res.startswith("'"):
            res = res[1:-1]

        retlist.append(unescapeHTML(res))

    return retlist


class HTMLAttributeParser(compat_HTMLParser):
    """Trivial HTML parser to gather the attributes for a single element"""
    def __init__(self):
        self.attrs = {}
        compat_HTMLParser.__init__(self)

    def handle_starttag(self, tag, attrs):
        self.attrs = dict(attrs)


def extract_attributes(html_element):
    """Given a string for an HTML element such as
    <el
         a="foo" B="bar" c="&98;az" d=boz
         empty= noval entity="&amp;"
         sq='"' dq="'"
    >
    Decode and return a dictionary of attributes.
    {
        'a': 'foo', 'b': 'bar', c: 'baz', d: 'boz',
        'empty': '', 'noval': None, 'entity': '&',
        'sq': '"', 'dq': '\''
    }.
    NB HTMLParser is stricter in Python 2.6 & 3.2 than in later versions,
    but the cases in the unit test will work for all of 2.6, 2.7, 3.2-3.5.
    """
    parser = HTMLAttributeParser()
    try:
        parser.feed(html_element)
        parser.close()
    # Older Python may throw HTMLParseError in case of malformed HTML
    except compat_HTMLParseError:
        pass
    return parser.attrs


def clean_html(html):
    """Clean an HTML snippet into a readable string"""

    if html is None:  # Convenience for sanitizing descriptions etc.
        return html

    # Newline vs <br />
    html = html.replace('\n', ' ')
    html = re.sub(r'(?u)\s*<\s*br\s*/?\s*>\s*', '\n', html)
    html = re.sub(r'(?u)<\s*/\s*p\s*>\s*<\s*p[^>]*>', '\n', html)
    # Strip html tags
    html = re.sub('<.*?>', '', html)
    # Replace html entities
    html = unescapeHTML(html)
    return html.strip()


def sanitize_open(filename, open_mode):
    """Try to open the given filename, and slightly tweak it if this fails.

    Attempts to open the given filename. If this fails, it tries to change
    the filename slightly, step by step, until it's either able to open it
    or it fails and raises a final exception, like the standard open()
    function.

    It returns the tuple (stream, definitive_file_name).
    """
    try:
        if filename == '-':
            if sys.platform == 'win32':
                import msvcrt
                msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
            return (sys.stdout.buffer if hasattr(sys.stdout, 'buffer') else sys.stdout, filename)
        stream = open(encodeFilename(filename), open_mode)
        return (stream, filename)
    except (IOError, OSError) as err:
        if err.errno in (errno.EACCES,):
            raise

        # In case of error, try to remove win32 forbidden chars
        alt_filename = sanitize_path(filename)
        if alt_filename == filename:
            raise
        else:
            # An exception here should be caught in the caller
            stream = open(encodeFilename(alt_filename), open_mode)
            return (stream, alt_filename)


def timeconvert(timestr):
    """Convert RFC 2822 defined time string into system timestamp"""
    timestamp = None
    timetuple = email.utils.parsedate_tz(timestr)
    if timetuple is not None:
        timestamp = email.utils.mktime_tz(timetuple)
    return timestamp


def sanitize_filename(s, restricted=False, is_id=False):
    """Sanitizes a string so it could be used as part of a filename.
    If restricted is set, use a stricter subset of allowed characters.
    Set is_id if this is not an arbitrary string, but an ID that should be kept
    if possible.
    """
    def replace_insane(char):
        if restricted and char in ACCENT_CHARS:
            return ACCENT_CHARS[char]
        if char == '?' or ord(char) < 32 or ord(char) == 127:
            return ''
        elif char == '"':
            return '' if restricted else '\''
        elif char == ':':
            return '_-' if restricted else ' -'
        elif char in '\\/|*<>':
            return '_'
        if restricted and (char in '!&\'()[]{}$;`^,#' or char.isspace()):
            return '_'
        if restricted and ord(char) > 127:
            return '_'
        return char

    # Handle timestamps
    s = re.sub(r'[0-9]+(?::[0-9]+)+', lambda m: m.group(0).replace(':', '_'), s)
    result = ''.join(map(replace_insane, s))
    if not is_id:
        while '__' in result:
            result = result.replace('__', '_')
        result = result.strip('_')
        # Common case of "Foreign band name - English song title"
        if restricted and result.startswith('-_'):
            result = result[2:]
        if result.startswith('-'):
            result = '_' + result[len('-'):]
        result = result.lstrip('.')
        if not result:
            result = '_'
    return result


def sanitize_path(s):
    """Sanitizes and normalizes path on Windows"""
    if sys.platform != 'win32':
        return s
    drive_or_unc, _ = os.path.splitdrive(s)
    if sys.version_info < (2, 7) and not drive_or_unc:
        drive_or_unc, _ = os.path.splitunc(s)
    norm_path = os.path.normpath(remove_start(s, drive_or_unc)).split(os.path.sep)
    if drive_or_unc:
        norm_path.pop(0)
    sanitized_path = [
        path_part if path_part in ['.', '..'] else re.sub(r'(?:[/<>:"\|\\?\*]|[\s.]$)', '#', path_part)
        for path_part in norm_path]
    if drive_or_unc:
        sanitized_path.insert(0, drive_or_unc + os.path.sep)
    return os.path.join(*sanitized_path)


# Prepend protocol-less URLs with `http:` scheme in order to mitigate the number of
# unwanted failures due to missing protocol
def sanitize_url(url):
    return 'http:%s' % url if url.startswith('//') else url


def sanitized_Request(url, *args, **kwargs):
    return compat_urllib_request.Request(sanitize_url(url), *args, **kwargs)


def expand_path(s):
    """Expand shell variables and ~"""
    return os.path.expandvars(compat_expanduser(s))


def orderedSet(iterable):
    """ Remove all duplicates from the input iterable """
    res = []
    for el in iterable:
        if el not in res:
            res.append(el)
    return res


def _htmlentity_transform(entity_with_semicolon):
    """Transforms an HTML entity to a character."""
    entity = entity_with_semicolon[:-1]

    # Known non-numeric HTML entity
    if entity in compat_html_entities.name2codepoint:
        return compat_chr(compat_html_entities.name2codepoint[entity])

    # TODO: HTML5 allows entities without a semicolon. For example,
    # '&Eacuteric' should be decoded as 'Éric'.
    if entity_with_semicolon in compat_html_entities_html5:
        return compat_html_entities_html5[entity_with_semicolon]

    mobj = re.match(r'#(x[0-9a-fA-F]+|[0-9]+)', entity)
    if mobj is not None:
        numstr = mobj.group(1)
        if numstr.startswith('x'):
            base = 16
            numstr = '0%s' % numstr
        else:
            base = 10
        # See https://github.com/rg3/youtube-dl/issues/7518
        try:
            return compat_chr(int(numstr, base))
        except ValueError:
            pass

    # Unknown entity in name, return its literal representation
    return '&%s;' % entity


def unescapeHTML(s):
    if s is None:
        return None
    assert type(s) == compat_str

    return re.sub(
        r'&([^;]+;)', lambda m: _htmlentity_transform(m.group(1)), s)


def get_subprocess_encoding():
    if sys.platform == 'win32' and sys.getwindowsversion()[0] >= 5:
        # For subprocess calls, encode with locale encoding
        # Refer to http://stackoverflow.com/a/9951851/35070
        encoding = preferredencoding()
    else:
        encoding = sys.getfilesystemencoding()
    if encoding is None:
        encoding = 'utf-8'
    return encoding


def encodeFilename(s, for_subprocess=False):
    """
    @param s The name of the file
    """

    assert type(s) == compat_str

    # Python 3 has a Unicode API
    if sys.version_info >= (3, 0):
        return s

    # Pass '' directly to use Unicode APIs on Windows 2000 and up
    # (Detecting Windows NT 4 is tricky because 'major >= 4' would
    # match Windows 9x series as well. Besides, NT 4 is obsolete.)
    if not for_subprocess and sys.platform == 'win32' and sys.getwindowsversion()[0] >= 5:
        return s

    # Jython assumes filenames are Unicode strings though reported as Python 2.x compatible
    if sys.platform.startswith('java'):
        return s

    return s.encode(get_subprocess_encoding(), 'ignore')


def decodeFilename(b, for_subprocess=False):

    if sys.version_info >= (3, 0):
        return b

    if not isinstance(b, bytes):
        return b

    return b.decode(get_subprocess_encoding(), 'ignore')


def encodeArgument(s):
    if not isinstance(s, compat_str):
        # Legacy code that uses byte strings
        # Uncomment the following line after fixing all post processors
        # assert False, 'Internal error: %r should be of type %r, is %r' % (s, compat_str, type(s))
        s = s.decode('ascii')
    return encodeFilename(s, True)


def decodeArgument(b):
    return decodeFilename(b, True)


def decodeOption(optval):
    if optval is None:
        return optval
    if isinstance(optval, bytes):
        optval = optval.decode(preferredencoding())

    assert isinstance(optval, compat_str)
    return optval


def formatSeconds(secs):
    if secs > 3600:
        return '%d:%02d:%02d' % (secs // 3600, (secs % 3600) // 60, secs % 60)
    elif secs > 60:
        return '%d:%02d' % (secs // 60, secs % 60)
    else:
        return '%d' % secs


def make_HTTPS_handler(params, **kwargs):
    opts_no_check_certificate = params.get('nocheckcertificate', False)
    if hasattr(ssl, 'create_default_context'):  # Python >= 3.4 or 2.7.9
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        if opts_no_check_certificate:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        try:
            return YoutubeDLHTTPSHandler(params, context=context, **kwargs)
        except TypeError:
            # Python 2.7.8
            # (create_default_context present but HTTPSHandler has no context=)
            pass

    if sys.version_info < (3, 2):
        return YoutubeDLHTTPSHandler(params, **kwargs)
    else:  # Python < 3.4
<target>
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
</target>
        context.verify_mode = (ssl.CERT_NONE
                               if opts_no_check_certificate
                               else ssl.CERT_REQUIRED)
        context.set_default_verify_paths()
        return YoutubeDLHTTPSHandler(params, context=context, **kwargs)


def bug_reports_message():
    if ytdl_is_updateable():
        update_cmd = 'type  youtube-dl -U  to update'
    else:
        update_cmd = 'see  https://yt-dl.org/update  on how to update'
    msg = '; please report this issue on https://yt-dl.org/bug .'
    msg += ' Make sure you are using the latest version; %s.' % update_cmd
    msg += ' Be sure to call youtube-dl with the --verbose flag and include its complete output.'
    return msg


class YoutubeDLError(Exception):
    """Base exception for YoutubeDL errors."""
    pass


class ExtractorError(YoutubeDLError):
    """Error during info extraction."""

    def __init__(self, msg, tb=None, expected=False, cause=None, video_id=None):
        """ tb, if given, is the original traceback (so that it can be printed out).
        If expected is set, this is a normal error message and most likely not a bug in youtube-dl.
        """

        if sys.exc_info()[0] in (compat_urllib_error.URLError, socket.timeout, UnavailableVideoError):
            expected = True
        if video_id is not None:
            msg = video_id + ': ' + msg
        if cause:
            msg += ' (caused by %r)' % cause
        if not expected:
            msg += bug_reports_message()
        super(ExtractorError, self).__init__(msg)

        self.traceback = tb
        self.exc_info = sys.exc_info()  # preserve original exception
        self.cause = cause
        self.video_id = video_id

    def format_traceback(self):
        if self.traceback is None:
            return None
        return ''.join(traceback.format_tb(self.traceback))


class UnsupportedError(ExtractorError):
    def __init__(self, url):
        super(UnsupportedError, self).__init__(
            'Unsupported URL: %s' % url, expected=True)
        self.url = url


class RegexNotFoundError(ExtractorError):
    """Error when a regex didn't match"""
    pass


class GeoRestrictedError(ExtractorError):
    """Geographic restriction Error exception.

    This exception may be thrown when a video is not available from your
    geographic location due to geographic restrictions imposed by a website.
    """
    def __init__(self, msg, countries=None):
        super(GeoRestrictedError, self).__init__(msg, expected=True)
        self.msg = msg
        self.countries = countries


class DownloadError(YoutubeDLError):
    """Download Error exception.

    This exception may be thrown by FileDownloader objects if they are not
    configured to continue on errors. They will contain the appropriate
    error message.
    """

    def __init__(self, msg, exc_info=None):
        """ exc_info, if given, is the original exception that caused the trouble (as returned by sys.exc_info()). """
        super(DownloadError, self).__init__(msg)
        self.exc_info = exc_info


class SameFileError(YoutubeDLError):
    """Same File exception.

    This exception will be thrown by FileDownloader objects if they detect
    multiple files would have to be downloaded to the same file on disk.
    """
    pass


class PostProcessingError(YoutubeDLError):
    """Post Processing exception.

    This exception may be raised by PostProcessor's .run() method to
    indicate an error in the postprocessing task.
    """

    def __init__(self, msg):
        super(PostProcessingError, self).__init__(msg)
        self.msg = msg


class MaxDownloadsReached(YoutubeDLError):
    """ --max-downloads limit has been reached. """
    pass


class UnavailableVideoError(YoutubeDLError):
    """Unavailable Format exception.

    This exception will be thrown when a video is requested
    in a format that is not available for that video.
    """
    pass


class ContentTooShortError(YoutubeDLError):
    """Content Too Short exception.

    This exception may be raised by FileDownloader objects when a file they
    download is too small for what the server announced first, indicating
    the connection was probably interrupted.
    """

    def __init__(self, downloaded, expected):
        super(ContentTooShortError, self).__init__(
            'Downloaded {0} bytes, expected {1} bytes'.format(downloaded, expected)
        )
        # Both in bytes
        self.downloaded = downloaded
        self.expected = expected


class XAttrMetadataError(YoutubeDLError):
    def __init__(self, code=None, msg='Unknown error'):
        super(XAttrMetadataError, self).__init__(msg)
        self.code = code
        self.msg = msg

        # Parsing code and msg
        if (self.code in (errno.ENOSPC, errno.EDQUOT) or
                'No space left' in self.msg or 'Disk quota excedded' in self.msg):
            self.reason = 'NO_SPACE'
        elif self.code == errno.E2BIG or 'Argument list too long' in self.msg:
            self.reason = 'VALUE_TOO_LONG'
        else:
            self.reason = 'NOT_SUPPORTED'


class XAttrUnavailableError(YoutubeDLError):
    pass


def _create_http_connection(ydl_handler, http_class, is_https, *args, **kwargs):
    # Working around python 2 bug (see http://bugs.python.org/issue17849) by limiting
    # expected HTTP responses to meet HTTP/1.0 or later (see also
    # https://github.com/rg3/youtube-dl/issues/6727)
    if sys.version_info < (3, 0):
        kwargs[b'strict'] = True
    hc = http_class(*args, **kwargs)
    source_address = ydl_handler._params.get('source_address')
    if source_address is not None:
        sa = (source_address, 0)
        if hasattr(hc, 'source_address'):  # Python 2.7+
            hc.source_address = sa
        else:  # Python 2.6
            def _hc_connect(self, *args, **kwargs):
                sock = compat_socket_create_connection(
                    (self.host, self.port), self.timeout, sa)
                if is_https:
                    self.sock = ssl.wrap_socket(
                        sock, self.key_file, self.cert_file,
<target>
                        ssl_version=ssl.PROTOCOL_TLSv1)
</target>
                else:
                    self.sock = sock
            hc.connect = functools.partial(_hc_connect, hc)

    return hc


def handle_youtubedl_headers(headers):
    filtered_headers = headers

    if 'Youtubedl-no-compression' in filtered_headers:
        filtered_headers = dict((k, v) for k, v in filtered_headers.items() if k.lower() != 'accept-encoding')
        del filtered_headers['Youtubedl-no-compression']

    return filtered_headers


class YoutubeDLHandler(compat_urllib_request.HTTPHandler):
    """Handler for HTTP requests and responses.

    This class, when installed with an OpenerDirector, automatically adds
    the standard headers to every HTTP request and handles gzipped and
    deflated responses from web servers. If compression is to be avoided in
    a particular request, the original request in the program code only has
    to include the HTTP header "Youtubedl-no-compression", which will be
    removed before making the real request.

    Part of this code was copied from:

    http://techknack.net/python-urllib2-handlers/

    Andrew Rowls, the author of that code, agreed to release it to the
    public domain.
    """

    def __init__(self, params, *args, **kwargs):
        compat_urllib_request.HTTPHandler.__init__(self, *args, **kwargs)
        self._params = params

    def http_open(self, req):
        conn_class = compat_http_client.HTTPConnection

        socks_proxy = req.headers.get('Ytdl-socks-proxy')
        if socks_proxy:
            conn_class = make_socks_conn_class(conn_class, socks_proxy)
            del req.headers['Ytdl-socks-proxy']

        return self.do_open(functools.partial(
            _create_http_connection, self, conn_class, False),
            req)

    @staticmethod
    def deflate(data):
        try:
            return zlib.decompress(data, -zlib.MAX_WBITS)
        except zlib.error:
            return zlib.decompress(data)

    def http_request(self, req):
        # According to RFC 3986, URLs can not contain non-ASCII characters, however this is not
        # always respected by websites, some tend to give out URLs with non percent-encoded
        # non-ASCII characters (see telemb.py, ard.py [#3412])
        # urllib chokes on URLs with non-ASCII characters (see http://bugs.python.org/issue3991)
        # To work around aforementioned issue we will replace request's original URL with
        # percent-encoded one
        # Since redirects are also affected (e.g. http://www.southpark.de/alle-episoden/s18e09)
        # the code of this workaround has been moved here from YoutubeDL.urlopen()
        url = req.get_full_url()
        url_escaped = escape_url(url)

        # Substitute URL if any change after escaping
        if url != url_escaped:
            req = update_Request(req, url=url_escaped)

        for h, v in std_headers.items():
            # Capitalize is needed because of Python bug 2275: http://bugs.python.org/issue2275
            # The dict keys are capitalized because of this bug by urllib
            if h.capitalize() not in req.headers:
                req.add_header(h, v)

        req.headers = handle_youtubedl_headers(req.headers)

        if sys.version_info < (2, 7) and '#' in req.get_full_url():
            # Python 2.6 is brain-dead when it comes to fragments
            req._Request__original = req._Request__original.partition('#')[0]
            req._Request__r_type = req._Request__r_type.partition('#')[0]

        return req

    def http_response(self, req, resp):
        old_resp = resp
        # gzip
        if resp.headers.get('Content-encoding', '') == 'gzip':
            content = resp.read()
            gz = gzip.GzipFile(fileobj=io.BytesIO(content), mode='rb')
            try:
                uncompressed = io.BytesIO(gz.read())
            except IOError as original_ioerror:
                # There may be junk add the end of the file
                # See http://stackoverflow.com/q/4928560/35070 for details
                for i in range(1, 1024):
                    try:
                        gz = gzip.GzipFile(fileobj=io.BytesIO(content[:-i]), mode='rb')
                        uncompressed = io.BytesIO(gz.read())
                    except IOError:
                        continue
                    break
                else:
                    raise original_ioerror
            resp = compat_urllib_request.addinfourl(uncompressed, old_resp.headers, old_resp.url, old_resp.code)
            resp.msg = old_resp.msg
            del resp.headers['Content-encoding']
        # deflate
        if resp.headers.get('Content-encoding', '') == 'deflate':
            gz = io.BytesIO(self.deflate(resp.read()))
            resp = compat_urllib_request.addinfourl(gz, old_resp.headers, old_resp.url, old_resp.code)
            resp.msg = old_resp.msg
            del resp.headers['Content-encoding']
        # Percent-encode redirect URL of Location HTTP header to satisfy RFC 3986 (see
        # https://github.com/rg3/youtube-dl/issues/6457).
        if 300 <= resp.code < 400:
            location = resp.headers.get('Location')
            if location:
                # As of RFC 2616 default charset is iso-8859-1 that is respected by python 3
                if sys.version_info >= (3, 0):
                    location = location.encode('iso-8859-1').decode('utf-8')
                else:
                    location = location.decode('utf-8')
                location_escaped = escape_url(location)
                if location != location_escaped:
                    del resp.headers['Location']
                    if sys.version_info < (3, 0):
                        location_escaped = location_escaped.encode('utf-8')
                    resp.headers['Location'] = location_escaped
        return resp

    https_request = http_request
    https_response = http_response


def make_socks_conn_class(base_class, socks_proxy):
    assert issubclass(base_class, (
        compat_http_client.HTTPConnection, compat_http_client.HTTPSConnection))

    url_components = compat_urlparse.urlparse(socks_proxy)
    if url_components.scheme.lower() == 'socks5':
        socks_type = ProxyType.SOCKS5
    elif url_components.scheme.lower() in ('socks', 'socks4'):
        socks_type = ProxyType.SOCKS4
    elif url_components.scheme.lower() == 'socks4a':
        socks_type = ProxyType.SOCKS4A

    def unquote_if_non_empty(s):
        if not s:
            return s
        return compat_urllib_parse_unquote_plus(s)

    proxy_args = (
        socks_type,
        url_components.hostname, url_components.port or 1080,
        True,  # Remote DNS
        unquote_if_non_empty(url_components.username),
        unquote_if_non_empty(url_components.password),
    )

    class SocksConnection(base_class):
        def connect(self):
            self.sock = sockssocket()
            self.sock.setproxy(*proxy_args)
            if type(self.timeout) in (int, float):
                self.sock.settimeout(self.timeout)
            self.sock.connect((self.host, self.port))

            if isinstance(self, compat_http_client.HTTPSConnection):
                if hasattr(self, '_context'):  # Python > 2.6
                    self.sock = self._context.wrap_socket(
                        self.sock, server_hostname=self.host)
                else:
                    self.sock = ssl.wrap_socket(self.sock)

    return SocksConnection


class YoutubeDLHTTPSHandler(compat_urllib_request.HTTPSHandler):
    def __init__(self, params, https_conn_class=None, *args, **kwargs):
        compat_urllib_request.HTTPSHandler.__init__(self, *args, **kwargs)
        self._https_conn_class = https_conn_class or compat_http_client.HTTPSConnection
        self._params = params

    def https_open(self, req):
        kwargs = {}
        conn_class = self._https_conn_class

        if hasattr(self, '_context'):  # python > 2.6
            kwargs['context'] = self._context
        if hasattr(self, '_check_hostname'):  # python 3.x
            kwargs['check_hostname'] = self._check_hostname

        socks_proxy = req.headers.get('Ytdl-socks-proxy')
        if socks_proxy:
            conn_class = make_socks_conn_class(conn_class, socks_proxy)
            del req.headers['Ytdl-socks-proxy']

        return self.do_open(functools.partial(
            _create_http_connection, self, conn_class, True),
            req, **kwargs)


class YoutubeDLCookieProcessor(compat_urllib_request.HTTPCookieProcessor):
    def __init__(self, cookiejar=None):
        compat_urllib_request.HTTPCookieProcessor.__init__(self, cookiejar)

    def http_response(self, request, response):
        # Python 2 will choke on next HTTP request in row if there are non-ASCII
        # characters in Set-Cookie HTTP header of last response (see
        # https://github.com/rg3/youtube-dl/issues/6769).
        # In order to at least prevent crashing we will percent encode Set-Cookie
        # header before HTTPCookieProcessor starts processing it.
        # if sys.version_info < (3, 0) and response.headers:
        #     for set_cookie_header in ('Set-Cookie', 'Set-Cookie2'):
        #         set_cookie = response.headers.get(set_cookie_header)
        #         if set_cookie:
        #             set_cookie_escaped = compat_urllib_parse.quote(set_cookie, b"%/;:@&=+$,!~*'()?#[] ")
        #             if set_cookie != set_cookie_escaped:
        #                 del response.headers[set_cookie_header]
        #                 response.headers[set_cookie_header] = set_cookie_escaped
        return compat_urllib_request.HTTPCookieProcessor.http_response(self, request, response)

    https_request = compat_urllib_request.HTTPCookieProcessor.http_request
    https_response = http_response


def extract_timezone(date_str):
    m = re.search(
        r'^.{8,}?(?P<tz>Z$| ?(?P<sign>\+|-)(?P<hours>[0-9]{2}):?(?P<minutes>[0-9]{2})$)',
        date_str)
    if not m:
        timezone = datetime.timedelta()
    else:
        date_str = date_str[:-len(m.group('tz'))]
        if not m.group('sign'):
            timezone = datetime.timedelta()
        else:
            sign = 1 if m.group('sign') == '+' else -1
            timezone = datetime.timedelta(
                hours=sign * int(m.group('hours')),
                minutes=sign * int(m.group('minutes')))
    return timezone, date_str


def parse_iso8601(date_str, delimiter='T', timezone=None):
    """ Return a UNIX timestamp from the given date """

    if date_str is None:
        return None

    date_str = re.sub(r'\.[0-9]+', '', date_str)

    if timezone is None:
        timezone, date_str = extract_timezone(date_str)

    try:
        date_format = '%Y-%m-%d{0}%H:%M:%S'.format(delimiter)
        dt = datetime.datetime.strptime(date_str, date_format) - timezone
        return calendar.timegm(dt.timetuple())
    except ValueError:
        pass


def date_formats(day_first=True):
    return DATE_FORMATS_DAY_FIRST if day_first else DATE_FORMATS_MONTH_FIRST


def unified_strdate(date_str, day_first=True):
    """Return a string with the date in the format YYYYMMDD"""

    if date_str is None:
        return None
    upload_date = None
    # Replace commas
    date_str = date_str.replace(',', ' ')
    # Remove AM/PM + timezone
    date_str = re.sub(r'(?i)\s*(?:AM|PM)(?:\s+[A-Z]+)?', '', date_str)
    _, date_str = extract_timezone(date_str)

    for expression in date_formats(day_first):
        try:
            upload_date = datetime.datetime.strptime(date_str, expression).strftime('%Y%m%d')
        except ValueError:
            pass
    if upload_date is None:
        timetuple = email.utils.parsedate_tz(date_str)
        if timetuple:
            try:
                upload_date = datetime.datetime(*timetuple[:6]).strftime('%Y%m%d')
            except ValueError:
                pass
    if upload_date is not None:
        return compat_str(upload_date)


def unified_timestamp(date_str, day_first=True):
    if date_str is None:
        return None

    date_str = re.sub(r'[,|]', '', date_str)

    pm_delta = 12 if re.search(r'(?i)PM', date_str) else 0
    timezone, date_str = extract_timezone(date_str)

    # Remove AM/PM + timezone
    date_str = re.sub(r'(?i)\s*(?:AM|PM)(?:\s+[A-Z]+)?', '', date_str)

    # Remove unrecognized timezones from ISO 8601 alike timestamps
    m = re.search(r'\d{1,2}:\d{1,2}(?:\.\d+)?(?P<tz>\s*[A-Z]+)$', date_str)
    if m:
        date_str = date_str[:-len(m.group('tz'))]

    for expression in date_formats(day_first):
        try:
            dt = datetime.datetime.strptime(date_str, expression) - timezone + datetime.timedelta(hours=pm_delta)
            return calendar.timegm(dt.timetuple())
        except ValueError:
            pass
    timetuple = email.utils.parsedate_tz(date_str)
    if timetuple:
        return calendar.timegm(timetuple) + pm_delta * 3600


def determine_ext(url, default_ext='unknown_video'):
    if url is None:
        return default_ext
    guess = url.partition('?')[0].rpartition('.')[2]
    if re.match(r'^[A-Za-z0-9]+$', guess):
        return guess
    # Try extract ext from URLs like http://example.com/foo/bar.mp4/?download
    elif guess.rstrip('/') in KNOWN_EXTENSIONS:
        return guess.rstrip('/')
    else:
        return default_ext


def subtitles_filename(filename, sub_lang, sub_format):
    return filename.rsplit('.', 1)[0] + '.' + sub_lang + '.' + sub_format


def date_from_str(date_str):
    """
    Return a datetime object from a string in the format YYYYMMDD or
    (now|today)[+-][0-9](day|week|month|year)(s)?"""
    today = datetime.date.today()
    if date_str in ('now', 'today'):
        return today
    if date_str == 'yesterday':
        return today - datetime.timedelta(days=1)
    match = re.match(r'(now|today)(?P<sign>[+-])(?P<time>\d+)(?P<unit>day|week|month|year)(s)?', date_str)
    if match is not None:
        sign = match.group('sign')
        time = int(match.group('time'))
        if sign == '-':
            time = -time
        unit = match.group('unit')
        # A bad approximation?
        if unit == 'month':
            unit = 'day'
            time *= 30
        elif unit == 'year':
            unit = 'day'
            time *= 365
        unit += 's'
        delta = datetime.timedelta(**{unit: time})
        return today + delta
    return datetime.datetime.strptime(date_str, '%Y%m%d').date()


def hyphenate_date(date_str):
    """
    Convert a date in 'YYYYMMDD' format to 'YYYY-MM-DD' format"""
    match = re.match(r'^(\d\d\d\d)(\d\d)(\d\d)$', date_str)
    if match is not None:
        return '-'.join(match.groups())
    else:
        return date_str


class DateRange(object):
    """Represents a time interval between two dates"""

    def __init__(self, start=None, end=None):
        """start and end must be strings in the format accepted by date"""
        if start is not None:
            self.start = date_from_str(start)
        else:
            self.start = datetime.datetime.min.date()
        if end is not None:
            self.end = date_from_str(end)
        else:
            self.end = datetime.datetime.max.date()
        if self.start > self.end:
            raise ValueError('Date range: "%s" , the start date must be before the end date' % self)

    @classmethod
    def day(cls, day):
        """Returns a range that only contains the given day"""
        return cls(day, day)

    def __contains__(self, date):
        """Check if the date is in the range"""
        if not isinstance(date, datetime.date):
            date = date_from_str(date)
        return self.start <= date <= self.end

    def __str__(self):
        return '%s - %s' % (self.start.isoformat(), self.end.isoformat())


def platform_name():
    """ Returns the platform name as a compat_str """
    res = platform.platform()
    if isinstance(res, bytes):
        res = res.decode(preferredencoding())

    assert isinstance(res, compat_str)
    return res


def _windows_write_string(s, out):
    """ Returns True if the string was written using special methods,
    False if it has yet to be written out."""
    # Adapted from http://stackoverflow.com/a/3259271/35070

    import ctypes
    import ctypes.wintypes

    WIN_OUTPUT_IDS = {
        1: -11,
        2: -12,
    }

    try:
        fileno = out.fileno()
    except AttributeError:
        # If the output stream doesn't have a fileno, it's virtual
        return False
    except io.UnsupportedOperation:
        # Some strange Windows pseudo files?
        return False
    if fileno not in WIN_OUTPUT_IDS:
        return False

    GetStdHandle = ctypes.WINFUNCTYPE(
        ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD)(
        (b'GetStdHandle', ctypes.windll.kernel32))
    h = GetStdHandle(WIN_OUTPUT_IDS[fileno])

    WriteConsoleW = ctypes.WINFUNCTYPE(
        ctypes.wintypes.BOOL, ctypes.wintypes.HANDLE, ctypes.wintypes.LPWSTR,
        ctypes.wintypes.DWORD, ctypes.POINTER(ctypes.wintypes.DWORD),
        ctypes.wintypes.LPVOID)((b'WriteConsoleW', ctypes.windll.kernel32))
    written = ctypes.wintypes.DWORD(0)

    GetFileType = ctypes.WINFUNCTYPE(ctypes.wintypes.DWORD, ctypes.wintypes.DWORD)((b'GetFileType', ctypes.windll.kernel32))
    FILE_TYPE_CHAR = 0x0002
    FILE_TYPE_REMOTE = 0x8000
    GetConsoleMode = ctypes.WINFUNCTYPE(
        ctypes.wintypes.BOOL, ctypes.wintypes.HANDLE,
        ctypes.POINTER(ctypes.wintypes.DWORD))(
        (b'GetConsoleMode', ctypes.windll.kernel32))
    INVALID_HANDLE_VALUE = ctypes.wintypes.DWORD(-1).value

    def not_a_console(handle):
        if handle == INVALID_HANDLE_VALUE or handle is None:
            return True
        return ((GetFileType(handle) & ~FILE_TYPE_REMOTE) != FILE_TYPE_CHAR or
                GetConsoleMode(handle, ctypes.byref(ctypes.wintypes.DWORD())) == 0)

    if not_a_console(h):
        return False

    def next_nonbmp_pos(s):
        try:
            return next(i for i, c in enumerate(s) if ord(c) > 0xffff)
        except StopIteration:
            return len(s)

    while s:
        count = min(next_nonbmp_pos(s), 1024)

        ret = WriteConsoleW(
            h, s, count if count else 2, ctypes.byref(written), None)
        if ret == 0:
            raise OSError('Failed to write string')
        if not count:  # We just wrote a non-BMP character
            assert written.value == 2
            s = s[1:]
        else:
            assert written.value > 0
            s = s[written.value:]
    return True


def write_string(s, out=None, encoding=None):
    if out is None:
        out = sys.stderr
    assert type(s) == compat_str

    if sys.platform == 'win32' and encoding is None and hasattr(out, 'fileno'):
        if _windows_write_string(s, out):
            return

    if ('b' in getattr(out, 'mode', '') or
            sys.version_info[0] < 3):  # Python 2 lies about mode of sys.stderr
        byt = s.encode(encoding or preferredencoding(), 'ignore')
        out.write(byt)
    elif hasattr(out, 'buffer'):
        enc = encoding or getattr(out, 'encoding', None) or preferredencoding()
        byt = s.encode(enc, 'ignore')
        out.buffer.write(byt)
    else:
        out.write(s)
    out.flush()


def bytes_to_intlist(bs):
    if not bs:
        return []
    if isinstance(bs[0], int):  # Python 3
        return list(bs)
    else:
        return [ord(c) for c in bs]


def intlist_to_bytes(xs):
    if not xs:
        return b''
    return compat_struct_pack('%dB' % len(xs), *xs)


# Cross-platform file locking
if sys.platform == 'win32':
    import ctypes.wintypes
    import msvcrt

    class OVERLAPPED(ctypes.Structure):
        _fields_ = [
            ('Internal', ctypes.wintypes.LPVOID),
            ('InternalHigh', ctypes.wintypes.LPVOID),
            ('Offset', ctypes.wintypes.DWORD),
            ('OffsetHigh', ctypes.wintypes.DWORD),
            ('hEvent', ctypes.wintypes.HANDLE),
        ]

    kernel32 = ctypes.windll.kernel32
    LockFileEx = kernel32.LockFileEx
    LockFileEx.argtypes = [
        ctypes.wintypes.HANDLE,     # hFile
        ctypes.wintypes.DWORD,      # dwFlags
        ctypes.wintypes.DWORD,      # dwReserved
        ctypes.wintypes.DWORD,      # nNumberOfBytesToLockLow
        ctypes.wintypes.DWORD,      # nNumberOfBytesToLockHigh
        ctypes.POINTER(OVERLAPPED)  # Overlapped
    ]
    LockFileEx.restype = ctypes.wintypes.BOOL
    UnlockFileEx = kernel32.UnlockFileEx
    UnlockFileEx.argtypes = [
        ctypes.wintypes.HANDLE,     # hFile
        ctypes.wintypes.DWORD,      # dwReserved
        ctypes.wintypes.DWORD,      # nNumberOfBytesToLockLow
        ctypes.wintypes.DWORD,      # nNumberOfBytesToLockHigh
        ctypes.POINTER(OVERLAPPED)  # Overlapped
    ]
    UnlockFileEx.restype = ctypes.wintypes.BOOL
    whole_low = 0xffffffff
    whole_high = 0x7fffffff

    def _lock_file(f, exclusive):
        overlapped = OVERLAPPED()
        overlapped.Offset = 0
        overlapped.OffsetHigh = 0
        overlapped.hEvent = 0
        f._lock_file_overlapped_p = ctypes.pointer(overlapped)
        handle = msvcrt.get_osfhandle(f.fileno())
        if not LockFileEx(handle, 0x2 if exclusive else 0x0, 0,
                          whole_low, whole_high, f._lock_file_overlapped_p):
            raise OSError('Locking file failed: %r' % ctypes.FormatError())

    def _unlock_file(f):
        assert f._lock_file_overlapped_p
        handle = msvcrt.get_osfhandle(f.fileno())
        if not UnlockFileEx(handle, 0,
                            whole_low, whole_high, f._lock_file_overlapped_p):
            raise OSError('Unlocking file failed: %r' % ctypes.FormatError())

else:
    # Some platforms, such as Jython, is missing fcntl
    try:
        import fcntl

        def _lock_file(f, exclusive):
            fcntl.flock(f, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)

        def _unlock_file(f):
            fcntl.flock(f, fcntl.LOCK_UN)
    except ImportError:
        UNSUPPORTED_MSG = 'file locking is not supported on this platform'

        def _lock_file(f, exclusive):
            raise IOError(UNSUPPORTED_MSG)

        def _unlock_file(f):
            raise IOError(UNSUPPORTED_MSG)


class locked_file(object):
    def __init__(self, filename, mode, encoding=None):
        assert mode in ['r', 'a', 'w']
        self.f = io.open(filename, mode, encoding=encoding)
        self.mode = mode

    def __enter__(self):
        exclusive = self.mode != 'r'
        try:
            _lock_file(self.f, exclusive)
        except IOError:
            self.f.close()
            raise
        return self

    def __exit__(self, etype, value, traceback):
        try:
            _unlock_file(self.f)
        finally:
            self.f.close()

    def __iter__(self):
        return iter(self.f)

    def write(self, *args):
        return self.f.write(*args)

    def read(self, *args):
        return self.f.read(*args)


def get_filesystem_encoding():
    encoding = sys.getfilesystemencoding()
    return encoding if encoding is not None else 'utf-8'


def shell_quote(args):
    quoted_args = []
    encoding = get_filesystem_encoding()
    for a in args:
        if isinstance(a, bytes):
            # We may get a filename encoded with 'encodeFilename'
            a = a.decode(encoding)
        quoted_args.append(compat_shlex_quote(a))
    return ' '.join(quoted_args)


def smuggle_url(url, data):
    """ Pass additional data in a URL for internal use. """

    url, idata = unsmuggle_url(url, {})
    data.update(idata)
    sdata = compat_urllib_parse_urlencode(
        {'__youtubedl_smuggle': json.dumps(data)})
    return url + '#' + sdata


def unsmuggle_url(smug_url, default=None):
    if '#__youtubedl_smuggle' not in smug_url:
        return smug_url, default
    url, _, sdata = smug_url.rpartition('#')
    jsond = compat_parse_qs(sdata)['__youtubedl_smuggle'][0]
    data = json.loads(jsond)
    return url, data


def format_bytes(bytes):
    if bytes is None:
        return 'N/A'
    if type(bytes) is str:
        bytes = float(bytes)
    if bytes == 0.0:
        exponent = 0
    else:
        exponent = int(math.log(bytes, 1024.0))
    suffix = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'][exponent]
    converted = float(bytes) / float(1024 ** exponent)
    return '%.2f%s' % (converted, suffix)


def lookup_unit_table(unit_table, s):
    units_re = '|'.join(re.escape(u) for u in unit_table)
    m = re.match(
        r'(?P<num>[0-9]+(?:[,.][0-9]*)?)\s*(?P<unit>%s)\b' % units_re, s)
    if not m:
        return None
    num_str = m.group('num').replace(',', '.')
    mult = unit_table[m.group('unit')]
    return int(float(num_str) * mult)


def parse_filesize(s):
    if s is None:
        return None

    # The lower-case forms are of course incorrect and unofficial,
    # but we support those too
    _UNIT_TABLE = {
        'B': 1,
        'b': 1,
        'bytes': 1,
        'KiB': 1024,
        'KB': 1000,
        'kB': 1024,
        'Kb': 1000,
        'kb': 1000,
        'kilobytes': 1000,
        'kibibytes': 1024,
        'MiB': 1024 ** 2,
        'MB': 1000 ** 2,
        'mB': 1024 ** 2,
        'Mb': 1000 ** 2,
        'mb': 1000 ** 2,
        'megabytes': 1000 ** 2,
        'mebibytes': 1024 ** 2,
        'GiB': 1024 ** 3,
        'GB': 1000 ** 3,
        'gB': 1024 ** 3,
        'Gb': 1000 ** 3,
        'gb': 1000 ** 3,
        'gigabytes': 1000 ** 3,
        'gibibytes': 1024 ** 3,
        'TiB': 1024 ** 4,
        'TB': 1000 ** 4,
        'tB': 1024 ** 4,
        'Tb': 1000 ** 4,
        'tb': 1000 ** 4,
        'terabytes': 1000 ** 4,
        'tebibytes': 1024 ** 4,
        'PiB': 1024 ** 5,
        'PB': 1000 ** 5,
        'pB': 1024 ** 5,
        'Pb': 1000 ** 5,
        'pb': 1000 ** 5,
        'petabytes': 1000 ** 5,
        'pebibytes': 1024 ** 5,
        'EiB': 1024 ** 6,
        'EB': 1000 ** 6,
        'eB': 1024 ** 6,
        'Eb': 1000 ** 6,
        'eb': 1000 ** 6,
        'exabytes': 1000 ** 6,
        'exbibytes': 1024 ** 6,
        'ZiB': 1024 ** 7,
        'ZB': 1000 ** 7,
        'zB': 1024 ** 7,
        'Zb': 1000 ** 7,
        'zb': 1000 ** 7,
        'zettabytes': 1000 ** 7,
        'zebibytes': 1024 ** 7,
        'YiB': 1024 ** 8,
        'YB': 1000 ** 8,
        'yB': 1024 ** 8,
        'Yb': 1000 ** 8,
        'yb': 1000 ** 8,
        'yottabytes': 1000 ** 8,
        'yobibytes': 1024 ** 8,
    }

    return lookup_unit_table(_UNIT_TABLE, s)


def parse_count(s):
    if s is None:
        return None

    s = s.strip()

    if re.match(r'^[\d,.]+$', s):
        return str_to_int(s)

    _UNIT_TABLE = {
        'k': 1000,
        'K': 1000,
        'm': 1000 ** 2,
        'M': 1000 ** 2,
        'kk': 1000 ** 2,
        'KK': 1000 ** 2,
    }

    return lookup_unit_table(_UNIT_TABLE, s)


def month_by_name(name, lang='en'):
    """ Return the number of a month by (locale-independently) English name """

    month_names = MONTH_NAMES.get(lang, MONTH_NAMES['en'])

    try:
        return month_names.index(name) + 1
    except ValueError:
        return None


def month_by_abbreviation(abbrev):
    """ Return the number of a month by (locale-independently) English
        abbreviations """

    try:
        return [s[:3] for s in ENGLISH_MONTH_NAMES].index(abbrev) + 1
    except ValueError:
        return None


def fix_xml_ampersands(xml_str):
    """Replace all the '&' by '&amp;' in XML"""
    return re.sub(
        r'&(?!amp;|lt;|gt;|apos;|quot;|#x[0-9a-fA-F]{,4};|#[0-9]{,4};)',
        '&amp;',
        xml_str)


def setproctitle(title):
    assert isinstance(title, compat_str)

    # ctypes in Jython is not complete
    # http://bugs.jython.org/issue2148
    if sys.platform.startswith('java'):
        return

    try:
        libc = ctypes.cdll.LoadLibrary('libc.so.6')
    except OSError:
        return
    except TypeError:
        # LoadLibrary in Windows Python 2.7.13 only expects
        # a bytestring, but since unicode_literals turns
        # every string into a unicode string, it fails.
        return
    title_bytes = title.encode('utf-8')
    buf = ctypes.create_string_buffer(len(title_bytes))
    buf.value = title_bytes
    try:
        libc.prctl(15, buf, 0, 0, 0)
    except AttributeError:
        return  # Strange libc, just skip this


def remove_start(s, start):
    return s[len(start):] if s is not None and s.startswith(start) else s


def remove_end(s, end):
    return s[:-len(end)] if s is not None and s.endswith(end) else s


def remove_quotes(s):
    if s is None or len(s) < 2:
        return s
    for quote in ('"', "'", ):
        if s[0] == quote and s[-1] == quote:
            return s[1:-1]
    return s


def url_basename(url):
    path = compat_urlparse.urlparse(url).path
    return path.strip('/').split('/')[-1]


def base_url(url):
    return re.match(r'https?://[^?#&]+/', url).group()


def urljoin(base, path):
    if isinstance(path, bytes):
        path = path.decode('utf-8')
    if not isinstance(path, compat_str) or not path:
        return None
    if re.match(r'^(?:https?:)?//', path):
        return path
    if isinstance(base, bytes):
        base = base.decode('utf-8')
    if not isinstance(base, compat_str) or not re.match(
            r'^(?:https?:)?//', base):
        return None
    return compat_urlparse.urljoin(base, path)


class HEADRequest(compat_urllib_request.Request):
    def get_method(self):
        return 'HEAD'


class PUTRequest(compat_urllib_request.Request):
    def get_method(self):
        return 'PUT'


def int_or_none(v, scale=1, default=None, get_attr=None, invscale=1):
    if get_attr:
        if v is not None:
            v = getattr(v, get_attr, None)
    if v == '':
        v = None
    if v is None:
        return default
    try:
        return int(v) * invscale // scale
    except ValueError:
        return default


def str_or_none(v, default=None):
    return default if v is None else compat_str(v)


def str_to_int(int_str):
    """ A more relaxed version of int_or_none """
    if int_str is None:
        return None
    int_str = re.sub(r'[,\.\+]', '', int_str)
    return int(int_str)


def float_or_none(v, scale=1, invscale=1, default=None):
    if v is None:
        return default
    try:
        return float(v) * invscale / scale
    except ValueError:
        return default


def strip_or_none(v):
    return None if v is None else v.strip()


def parse_duration(s):
    if not isinstance(s, compat_basestring):
        return None

    s = s.strip()

    days, hours, mins, secs, ms = [None] * 5
    m = re.match(r'(?:(?:(?:(?P<days>[0-9]+):)?(?P<hours>[0-9]+):)?(?P<mins>[0-9]+):)?(?P<secs>[0-9]+)(?P<ms>\.[0-9]+)?Z?$', s)
    if m:
        days, hours, mins, secs, ms = m.groups()
    else:
        m = re.match(
            r'''(?ix)(?:P?T)?
                (?:
                    (?P<days>[0-9]+)\s*d(?:ays?)?\s*
                )?
                (?:
                    (?P<hours>[0-9]+)\s*h(?:ours?)?\s*
                )?
                (?:
                    (?P<mins>[0-9]+)\s*m(?:in(?:ute)?s?)?\s*
                )?
                (?:
                    (?P<secs>[0-9]+)(?P<ms>\.[0-9]+)?\s*s(?:ec(?:ond)?s?)?\s*
                )?Z?$''', s)
        if m:
            days, hours, mins, secs, ms = m.groups()
        else:
            m = re.match(r'(?i)(?:(?P<hours>[0-9.]+)\s*(?:hours?)|(?P<mins>[0-9.]+)\s*(?:mins?\.?|minutes?)\s*)Z?$', s)
            if m:
                hours, mins = m.groups()
            else:
                return None

    duration = 0
    if secs:
        duration += float(secs)
    if mins:
        duration += float(mins) * 60
    if hours:
        duration += float(hours) * 60 * 60
    if days:
        duration += float(days) * 24 * 60 * 60
    if ms:
        duration += float(ms)
    return duration


def prepend_extension(filename, ext, expected_real_ext=None):
    name, real_ext = os.path.splitext(filename)
    return (
        '{0}.{1}{2}'.format(name, ext, real_ext)
        if not expected_real_ext or real_ext[1:] == expected_real_ext
        else '{0}.{1}'.format(filename, ext))


def replace_extension(filename, ext, expected_real_ext=None):
    name, real_ext = os.path.splitext(filename)
    return '{0}.{1}'.format(
        name if not expected_real_ext or real_ext[1:] == expected_real_ext else filename,
        ext)


def check_executable(exe, args=[]):
    """ Checks if the given binary is installed somewhere in PATH, and returns its name.
    args can be a list of arguments for a short output (like -version) """
    try:
        subprocess.Popen([exe] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    except OSError:
        return False
    return exe


def get_exe_version(exe, args=['--version'],
                    version_re=None, unrecognized='present'):
    """ Returns the version of the specified executable,
    or False if the executable is not present """
    try:
        # STDIN should be redirected too. On UNIX-like systems, ffmpeg triggers
        # SIGTTOU if youtube-dl is run in the background.
        # See https://github.com/rg3/youtube-dl/issues/955#issuecomment-209789656
        out, _ = subprocess.Popen(
            [encodeArgument(exe)] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()
    except OSError:
        return False
    if isinstance(out, bytes):  # Python 2.x
        out = out.decode('ascii', 'ignore')
    return detect_exe_version(out, version_re, unrecognized)


def detect_exe_version(output, version_re=None, unrecognized='present'):
    assert isinstance(output, compat_str)
    if version_re is None:
        version_re = r'version\s+([-0-9._a-zA-Z]+)'
    m = re.search(version_re, output)
    if m:
        return m.group(1)
    else:
        return unrecognized


class PagedList(object):
    def __len__(self):
        # This is only useful for tests
        return len(self.getslice())


class OnDemandPagedList(PagedList):
    def __init__(self, pagefunc, pagesize, use_cache=False):
        self._pagefunc = pagefunc
        self._pagesize = pagesize
        self._use_cache = use_cache
        if use_cache:
            self._cache = {}

    def getslice(self, start=0, end=None):
        res = []
        for pagenum in itertools.count(start // self._pagesize):
            firstid = pagenum * self._pagesize
            nextfirstid = pagenum * self._pagesize + self._pagesize
            if start >= nextfirstid:
                continue

            page_results = None
            if self._use_cache:
                page_results = self._cache.get(pagenum)
            if page_results is None:
                page_results = list(self._pagefunc(pagenum))
            if self._use_cache:
                self._cache[pagenum] = page_results

            startv = (
                start % self._pagesize
                if firstid <= start < nextfirstid
                else 0)

            endv = (
                ((end - 1) % self._pagesize) + 1
                if (end is not None and firstid <= end <= nextfirstid)
                else None)

            if startv != 0 or endv is not None:
                page_results = page_results[startv:endv]
            res.extend(page_results)

            # A little optimization - if current page is not "full", ie. does
            # not contain page_size videos then we can assume that this page
            # is the last one - there are no more ids on further pages -
            # i.e. no need to query again.
            if len(page_results) + startv < self._pagesize:
                break

            # If we got the whole page, but the next page is not interesting,
            # break out early as well
            if end == nextfirstid:
                break
        return res


class InAdvancePagedList(PagedList):
    def __init__(self, pagefunc, pagecount, pagesize):
        self._pagefunc = pagefunc
        self._pagecount = pagecount
        self._pagesize = pagesize

    def getslice(self, start=0, end=None):
        res = []
        start_page = start // self._pagesize
        end_page = (
            self._pagecount if end is None else (end // self._pagesize + 1))
        skip_elems = start - start_page * self._pagesize
        only_more = None if end is None else end - start
        for pagenum in range(start_page, end_page):
            page = list(self._pagefunc(pagenum))
            if skip_elems:
                page = page[skip_elems:]
                skip_elems = None
            if only_more is not None:
                if len(page) < only_more:
                    only_more -= len(page)
                else:
                    page = page[:only_more]
                    res.extend(page)
                    break
            res.extend(page)
        return res


def uppercase_escape(s):
    unicode_escape = codecs.getdecoder('unicode_escape')
    return re.sub(
        r'\\U[0-9a-fA-F]{8}',
        lambda m: unicode_escape(m.group(0))[0],
        s)


def lowercase_escape(s):
    unicode_escape = codecs.getdecoder('unicode_escape')
    return re.sub(
        r'\\u[0-9a-fA-F]{4}',
        lambda m: unicode_escape(m.group(0))[0],
        s)


def escape_rfc3986(s):
    """Escape non-ASCII characters as suggested by RFC 3986"""
    if sys.version_info < (3, 0) and isinstance(s, compat_str):
        s = s.encode('utf-8')
    return compat_urllib_parse.quote(s, b"%/;:@&=+$,!~*'()?#[]")


def escape_url(url):
    """Escape URL as suggested by RFC 3986"""
    url_parsed = compat_urllib_parse_urlparse(url)
    return url_parsed._replace(
        netloc=url_parsed.netloc.encode('idna').decode('ascii'),
        path=escape_rfc3986(url_parsed.path),
        params=escape_rfc3986(url_parsed.params),
        query=escape_rfc3986(url_parsed.query),
        fragment=escape_rfc3986(url_parsed.fragment)
    ).geturl()


def read_batch_urls(batch_fd):
    def fixup(url):
        if not isinstance(url, compat_str):
            url = url.decode('utf-8', 'replace')
        BOM_UTF8 = '\xef\xbb\xbf'
        if url.startswith(BOM_UTF8):
            url = url[len(BOM_UTF8):]
        url = url.strip()
        if url.startswith(('#', ';', ']')):
            return False
        return url

    with contextlib.closing(batch_fd) as fd:
        return [url for url in map(fixup, fd) if url]


def urlencode_postdata(*args, **kargs):
    return compat_urllib_parse_urlencode(*args, **kargs).encode('ascii')


def update_url_query(url, query):
    if not query:
        return url
    parsed_url = compat_urlparse.urlparse(url)
    qs = compat_parse_qs(parsed_url.query)
    qs.update(query)
    return compat_urlparse.urlunparse(parsed_url._replace(
        query=compat_urllib_parse_urlencode(qs, True)))


def update_Request(req, url=None, data=None, headers={}, query={}):
    req_headers = req.headers.copy()
    req_headers.update(headers)
    req_data = data or req.data
    req_url = update_url_query(url or req.get_full_url(), query)
    req_get_method = req.get_method()
    if req_get_method == 'HEAD':
        req_type = HEADRequest
    elif req_get_method == 'PUT':
        req_type = PUTRequest
    else:
        req_type = compat_urllib_request.Request
    new_req = req_type(
        req_url, data=req_data, headers=req_headers,
        origin_req_host=req.origin_req_host, unverifiable=req.unverifiable)
    if hasattr(req, 'timeout'):
        new_req.timeout = req.timeout
    return new_req


def _multipart_encode_impl(data, boundary):
    content_type = 'multipart/form-data; boundary=%s' % boundary

    out = b''
    for k, v in data.items():
        out += b'--' + boundary.encode('ascii') + b'\r\n'
        if isinstance(k, compat_str):
            k = k.encode('utf-8')
        if isinstance(v, compat_str):
            v = v.encode('utf-8')
        # RFC 2047 requires non-ASCII field names to be encoded, while RFC 7578
        # suggests sending UTF-8 directly. Firefox sends UTF-8, too
        content = b'Content-Disposition: form-data; name="' + k + b'"\r\n\r\n' + v + b'\r\n'
        if boundary.encode('ascii') in content:
            raise ValueError('Boundary overlaps with data')
        out += content

    out += b'--' + boundary.encode('ascii') + b'--\r\n'

    return out, content_type


def multipart_encode(data, boundary=None):
    '''
    Encode a dict to RFC 7578-compliant form-data

    data:
        A dict where keys and values can be either Unicode or bytes-like
        objects.
    boundary:
        If specified a Unicode object, it's used as the boundary. Otherwise
        a random boundary is generated.

    Reference: https://tools.ietf.org/html/rfc7578
    '''
    has_specified_boundary = boundary is not None

    while True:
        if boundary is None:
            boundary = '---------------' + str(random.randrange(0x0fffffff, 0xffffffff))

        try:
            out, content_type = _multipart_encode_impl(data, boundary)
            break
        except ValueError:
            if has_specified_boundary:
                raise
            boundary = None

    return out, content_type


def dict_get(d, key_or_keys, default=None, skip_false_values=True):
    if isinstance(key_or_keys, (list, tuple)):
        for key in key_or_keys:
            if key not in d or d[key] is None or skip_false_values and not d[key]:
                continue
            return d[key]
        return default
    return d.get(key_or_keys, default)


def try_get(src, getter, expected_type=None):
    if not isinstance(getter, (list, tuple)):
        getter = [getter]
    for get in getter:
        try:
            v = get(src)
        except (AttributeError, KeyError, TypeError, IndexError):
            pass
        else:
            if expected_type is None or isinstance(v, expected_type):
                return v


def encode_compat_str(string, encoding=preferredencoding(), errors='strict'):
    return string if isinstance(string, compat_str) else compat_str(string, encoding, errors)


US_RATINGS = {
    'G': 0,
    'PG': 10,
    'PG-13': 13,
    'R': 16,
    'NC': 18,
}


TV_PARENTAL_GUIDELINES = {
    'TV-Y': 0,
    'TV-Y7': 7,
    'TV-G': 0,
    'TV-PG': 0,
    'TV-14': 14,
    'TV-MA': 17,
}


def parse_age_limit(s):
    if type(s) == int:
        return s if 0 <= s <= 21 else None
    if not isinstance(s, compat_basestring):
        return None
    m = re.match(r'^(?P<age>\d{1,2})\+?$', s)
    if m:
        return int(m.group('age'))
    if s in US_RATINGS:
        return US_RATINGS[s]
    return TV_PARENTAL_GUIDELINES.get(s)


def strip_jsonp(code):
    return re.sub(
        r'''(?sx)^
            (?:window\.)?(?P<func_name>[a-zA-Z0-9_.$]+)
            (?:\s*&&\s*(?P=func_name))?
            \s*\(\s*(?P<callback_data>.*)\);?
            \s*?(?://[^\n]*)*$''',
        r'\g<callback_data>', code)


def js_to_json(code):
    COMMENT_RE = r'/\*(?:(?!\*/).)*?\*/|//[^\n]*'
    SKIP_RE = r'\s*(?:{comment})?\s*'.format(comment=COMMENT_RE)
    INTEGER_TABLE = (
        (r'(?s)^(0[xX][0-9a-fA-F]+){skip}:?$'.format(skip=SKIP_RE), 16),
        (r'(?s)^(0+[0-7]+){skip}:?$'.format(skip=SKIP_RE), 8),
    )

    def fix_kv(m):
        v = m.group(0)
        if v in ('true', 'false', 'null'):
            return v
        elif v.startswith('/*') or v.startswith('//') or v == ',':
            return ""

        if v[0] in ("'", '"'):
            v = re.sub(r'(?s)\\.|"', lambda m: {
                '"': '\\"',
                "\\'": "'",
                '\\\n': '',
                '\\x': '\\u00',
            }.get(m.group(0), m.group(0)), v[1:-1])

        for regex, base in INTEGER_TABLE:
            im = re.match(regex, v)
            if im:
                i = int(im.group(1), base)
                return '"%d":' % i if v.endswith(':') else '%d' % i

        return '"%s"' % v

    return re.sub(r'''(?sx)
        "(?:[^"\\]*(?:\\\\|\\['"nurtbfx/\n]))*[^"\\]*"|
        '(?:[^'\\]*(?:\\\\|\\['"nurtbfx/\n]))*[^'\\]*'|
        {comment}|,(?={skip}[\]}}])|
        [a-zA-Z_][.a-zA-Z_0-9]*|
        \b(?:0[xX][0-9a-fA-F]+|0+[0-7]+)(?:{skip}:)?|
        [0-9]+(?={skip}:)
        '''.format(comment=COMMENT_RE, skip=SKIP_RE), fix_kv, code)


def qualities(quality_ids):
    """ Get a numeric quality value out of a list of possible values """
    def q(qid):
        try:
            return quality_ids.index(qid)
        except ValueError:
            return -1
    return q


DEFAULT_OUTTMPL = '%(title)s-%(id)s.%(ext)s'


def limit_length(s, length):
    """ Add ellipses to overly long strings """
    if s is None:
        return None
    ELLIPSES = '...'
    if len(s) > length:
        return s[:length - len(ELLIPSES)] + ELLIPSES
    return s


def version_tuple(v):
    return tuple(int(e) for e in re.split(r'[-.]', v))


def is_outdated_version(version, limit, assume_new=True):
    if not version:
        return not assume_new
    try:
        return version_tuple(version) < version_tuple(limit)
    except ValueError:
        return not assume_new


def ytdl_is_updateable():
    """ Returns if youtube-dl can be updated with -U """
    from zipimport import zipimporter

    return isinstance(globals().get('__loader__'), zipimporter) or hasattr(sys, 'frozen')


def args_to_str(args):
    # Get a short string representation for a subprocess command
    return ' '.join(compat_shlex_quote(a) for a in args)


def error_to_compat_str(err):
    err_str = str(err)
    # On python 2 error byte string must be decoded with proper
    # encoding rather than ascii
    if sys.version_info[0] < 3:
        err_str = err_str.decode(preferredencoding())
    return err_str


def mimetype2ext(mt):
    if mt is None:
        return None

    ext = {
        'audio/mp4': 'm4a',
        # Per RFC 3003, audio/mpeg can be .mp1, .mp2 or .mp3. Here use .mp3 as
        # it's the most popular one
        'audio/mpeg': 'mp3',
    }.get(mt)
    if ext is not None:
        return ext

    _, _, res = mt.rpartition('/')
    res = res.split(';')[0].strip().lower()

    return {
        '3gpp': '3gp',
        'smptett+xml': 'tt',
        'ttaf+xml': 'dfxp',
        'ttml+xml': 'ttml',
        'x-flv': 'flv',
        'x-mp4-fragmented': 'mp4',
        'x-ms-wmv': 'wmv',
        'mpegurl': 'm3u8',
        'x-mpegurl': 'm3u8',
        'vnd.apple.mpegurl': 'm3u8',
        'dash+xml': 'mpd',
        'f4m+xml': 'f4m',
        'hds+xml': 'f4m',
        'vnd.ms-sstr+xml': 'ism',
        'quicktime': 'mov',
        'mp2t': 'ts',
    }.get(res, res)


def parse_codecs(codecs_str):
    # http://tools.ietf.org/html/rfc6381
    if not codecs_str:
        return {}
    splited_codecs = list(filter(None, map(
        lambda str: str.strip(), codecs_str.strip().strip(',').split(','))))
    vcodec, acodec = None, None
    for full_codec in splited_codecs:
        codec = full_codec.split('.')[0]
        if codec in ('avc1', 'avc2', 'avc3', 'avc4', 'vp9', 'vp8', 'hev1', 'hev2', 'h263', 'h264', 'mp4v'):
            if not vcodec:
                vcodec = full_codec
        elif codec in ('mp4a', 'opus', 'vorbis', 'mp3', 'aac', 'ac-3', 'ec-3', 'eac3', 'dtsc', 'dtse', 'dtsh', 'dtsl'):
            if not acodec:
                acodec = full_codec
        else:
            write_string('WARNING: Unknown codec %s\n' % full_codec, sys.stderr)
    if not vcodec and not acodec:
        if len(splited_codecs) == 2:
            return {
                'vcodec': vcodec,
                'acodec': acodec,
            }
        elif len(splited_codecs) == 1:
            return {
                'vcodec': 'none',
                'acodec': vcodec,
            }
    else:
        return {
            'vcodec': vcodec or 'none',
            'acodec': acodec or 'none',
        }
    return {}


def urlhandle_detect_ext(url_handle):
    getheader = url_handle.headers.get

    cd = getheader('Content-Disposition')
    if cd:
        m = re.match(r'attachment;\s*filename="(?P<filename>[^"]+)"', cd)
        if m:
            e = determine_ext(m.group('filename'), default_ext=None)
            if e:
                return e

    return mimetype2ext(getheader('Content-Type'))


def encode_data_uri(data, mime_type):
    return 'data:%s;base64,%s' % (mime_type, base64.b64encode(data).decode('ascii'))


def age_restricted(content_limit, age_limit):
    """ Returns True iff the content should be blocked """

    if age_limit is None:  # No limit set
        return False
    if content_limit is None:
        return False  # Content available for everyone
    return age_limit < content_limit


def is_html(first_bytes):
    """ Detect whether a file contains HTML by examining its first bytes. """

    BOMS = [
        (b'\xef\xbb\xbf', 'utf-8'),
        (b'\x00\x00\xfe\xff', 'utf-32-be'),
        (b'\xff\xfe\x00\x00', 'utf-32-le'),
        (b'\xff\xfe', 'utf-16-le'),
        (b'\xfe\xff', 'utf-16-be'),
    ]
    for bom, enc in BOMS:
        if first_bytes.startswith(bom):
            s = first_bytes[len(bom):].decode(enc, 'replace')
            break
    else:
        s = first_bytes.decode('utf-8', 'replace')

    return re.match(r'^\s*<', s)


def determine_protocol(info_dict):
    protocol = info_dict.get('protocol')
    if protocol is not None:
        return protocol

    url = info_dict['url']
    if url.startswith('rtmp'):
        return 'rtmp'
    elif url.startswith('mms'):
        return 'mms'
    elif url.startswith('rtsp'):
        return 'rtsp'

    ext = determine_ext(url)
    if ext == 'm3u8':
        return 'm3u8'
    elif ext == 'f4m':
        return 'f4m'

    return compat_urllib_parse_urlparse(url).scheme


def render_table(header_row, data):
    """ Render a list of rows, each as a list of values """
    table = [header_row] + data
    max_lens = [max(len(compat_str(v)) for v in col) for col in zip(*table)]
    format_str = ' '.join('%-' + compat_str(ml + 1) + 's' for ml in max_lens[:-1]) + '%s'
    return '\n'.join(format_str % tuple(row) for row in table)


def _match_one(filter_part, dct):
    COMPARISON_OPERATORS = {
        '<': operator.lt,
        '<=': operator.le,
        '>': operator.gt,
        '>=': operator.ge,
        '=': operator.eq,
        '!=': operator.ne,
    }
    operator_rex = re.compile(r'''(?x)\s*
        (?P<key>[a-z_]+)
        \s*(?P<op>%s)(?P<none_inclusive>\s*\?)?\s*
        (?:
            (?P<intval>[0-9.]+(?:[kKmMgGtTpPeEzZyY]i?[Bb]?)?)|
            (?P<quote>["\'])(?P<quotedstrval>(?:\\.|(?!(?P=quote)|\\).)+?)(?P=quote)|
            (?P<strval>(?![0-9.])[a-z0-9A-Z]*)
        )
        \s*$
        ''' % '|'.join(map(re.escape, COMPARISON_OPERATORS.keys())))
    m = operator_rex.search(filter_part)
    if m:
        op = COMPARISON_OPERATORS[m.group('op')]
        actual_value = dct.get(m.group('key'))
        if (m.group('quotedstrval') is not None or
            m.group('strval') is not None or
            # If the original field is a string and matching comparisonvalue is
            # a number we should respect the origin of the original field
            # and process comparison value as a string (see
            # https://github.com/rg3/youtube-dl/issues/11082).
            actual_value is not None and m.group('intval') is not None and
                isinstance(actual_value, compat_str)):
            if m.group('op') not in ('=', '!='):
                raise ValueError(
                    'Operator %s does not support string values!' % m.group('op'))
            comparison_value = m.group('quotedstrval') or m.group('strval') or m.group('intval')
            quote = m.group('quote')
            if quote is not None:
                comparison_value = comparison_value.replace(r'\%s' % quote, quote)
        else:
            try:
                comparison_value = int(m.group('intval'))
            except ValueError:
                comparison_value = parse_filesize(m.group('intval'))
                if comparison_value is None:
                    comparison_value = parse_filesize(m.group('intval') + 'B')
                if comparison_value is None:
                    raise ValueError(
                        'Invalid integer value %r in filter part %r' % (
                            m.group('intval'), filter_part))
        if actual_value is None:
            return m.group('none_inclusive')
        return op(actual_value, comparison_value)

    UNARY_OPERATORS = {
        '': lambda v: v is not None,
        '!': lambda v: v is None,
    }
    operator_rex = re.compile(r'''(?x)\s*
        (?P<op>%s)\s*(?P<key>[a-z_]+)
        \s*$
        ''' % '|'.join(map(re.escape, UNARY_OPERATORS.keys())))
    m = operator_rex.search(filter_part)
    if m:
        op = UNARY_OPERATORS[m.group('op')]
        actual_value = dct.get(m.group('key'))
        return op(actual_value)

    raise ValueError('Invalid filter part %r' % filter_part)


def match_str(filter_str, dct):
    """ Filter a dictionary with a simple string syntax. Returns True (=passes filter) or false """

    return all(
        _match_one(filter_part, dct) for filter_part in filter_str.split('&'))


def match_filter_func(filter_str):
    def _match_func(info_dict):
        if match_str(filter_str, info_dict):
            return None
        else:
            video_title = info_dict.get('title', info_dict.get('id', 'video'))
            return '%s does not pass filter %s, skipping ..' % (video_title, filter_str)
    return _match_func


def parse_dfxp_time_expr(time_expr):
    if not time_expr:
        return

    mobj = re.match(r'^(?P<time_offset>\d+(?:\.\d+)?)s?$', time_expr)
    if mobj:
        return float(mobj.group('time_offset'))

    mobj = re.match(r'^(\d+):(\d\d):(\d\d(?:(?:\.|:)\d+)?)$', time_expr)
    if mobj:
        return 3600 * int(mobj.group(1)) + 60 * int(mobj.group(2)) + float(mobj.group(3).replace(':', '.'))


def srt_subtitles_timecode(seconds):
    return '%02d:%02d:%02d,%03d' % (seconds / 3600, (seconds % 3600) / 60, seconds % 60, (seconds % 1) * 1000)


def dfxp2srt(dfxp_data):
    LEGACY_NAMESPACES = (
        ('http://www.w3.org/ns/ttml', [
            'http://www.w3.org/2004/11/ttaf1',
            'http://www.w3.org/2006/04/ttaf1',
            'http://www.w3.org/2006/10/ttaf1',
        ]),
        ('http://www.w3.org/ns/ttml#styling', [
            'http://www.w3.org/ns/ttml#style',
        ]),
    )

    SUPPORTED_STYLING = [
        'color',
        'fontFamily',
        'fontSize',
        'fontStyle',
        'fontWeight',
        'textDecoration'
    ]

    _x = functools.partial(xpath_with_ns, ns_map={
        'ttml': 'http://www.w3.org/ns/ttml',
        'tts': 'http://www.w3.org/ns/ttml#styling',
    })

    styles = {}
    default_style = {}

    class TTMLPElementParser(object):
        _out = ''
        _unclosed_elements = []
        _applied_styles = []

        def start(self, tag, attrib):
            if tag in (_x('ttml:br'), 'br'):
                self._out += '\n'
            else:
                unclosed_elements = []
                style = {}
                element_style_id = attrib.get('style')
                if default_style:
                    style.update(default_style)
                if element_style_id:
                    style.update(styles.get(element_style_id, {}))
                for prop in SUPPORTED_STYLING:
                    prop_val = attrib.get(_x('tts:' + prop))
                    if prop_val:
                        style[prop] = prop_val
                if style:
                    font = ''
                    for k, v in sorted(style.items()):
                        if self._applied_styles and self._applied_styles[-1].get(k) == v:
                            continue
                        if k == 'color':
                            font += ' color="%s"' % v
                        elif k == 'fontSize':
                            font += ' size="%s"' % v
                        elif k == 'fontFamily':
                            font += ' face="%s"' % v
                        elif k == 'fontWeight' and v == 'bold':
                            self._out += '<b>'
                            unclosed_elements.append('b')
                        elif k == 'fontStyle' and v == 'italic':
                            self._out += '<i>'
                            unclosed_elements.append('i')
                        elif k == 'textDecoration' and v == 'underline':
                            self._out += '<u>'
                            unclosed_elements.append('u')
                    if font:
                        self._out += '<font' + font + '>'
                        unclosed_elements.append('font')
                    applied_style = {}
                    if self._applied_styles:
                        applied_style.update(self._applied_styles[-1])
                    applied_style.update(style)
                    self._applied_styles.append(applied_style)
                self._unclosed_elements.append(unclosed_elements)

        def end(self, tag):
            if tag not in (_x('ttml:br'), 'br'):
                unclosed_elements = self._unclosed_elements.pop()
                for element in reversed(unclosed_elements):
                    self._out += '</%s>' % element
                if unclosed_elements and self._applied_styles:
                    self._applied_styles.pop()

        def data(self, data):
            self._out += data

        def close(self):
            return self._out.strip()

    def parse_node(node):
        target = TTMLPElementParser()
        parser = xml.etree.ElementTree.XMLParser(target=target)
        parser.feed(xml.etree.ElementTree.tostring(node))
        return parser.close()

    for k, v in LEGACY_NAMESPACES:
        for ns in v:
            dfxp_data = dfxp_data.replace(ns, k)

    dfxp = compat_etree_fromstring(dfxp_data.encode('utf-8'))
    out = []
    paras = dfxp.findall(_x('.//ttml:p')) or dfxp.findall('.//p')

    if not paras:
        raise ValueError('Invalid dfxp/TTML subtitle')

    repeat = False
    while True:
        for style in dfxp.findall(_x('.//ttml:style')):
            style_id = style.get('id')
            parent_style_id = style.get('style')
            if parent_style_id:
                if parent_style_id not in styles:
                    repeat = True
                    continue
                styles[style_id] = styles[parent_style_id].copy()
            for prop in SUPPORTED_STYLING:
                prop_val = style.get(_x('tts:' + prop))
                if prop_val:
                    styles.setdefault(style_id, {})[prop] = prop_val
        if repeat:
            repeat = False
        else:
            break

    for p in ('body', 'div'):
        ele = xpath_element(dfxp, [_x('.//ttml:' + p), './/' + p])
        if ele is None:
            continue
        style = styles.get(ele.get('style'))
        if not style:
            continue
        default_style.update(style)

    for para, index in zip(paras, itertools.count(1)):
        begin_time = parse_dfxp_time_expr(para.attrib.get('begin'))
        end_time = parse_dfxp_time_expr(para.attrib.get('end'))
        dur = parse_dfxp_time_expr(para.attrib.get('dur'))
        if begin_time is None:
            continue
        if not end_time:
            if not dur:
                continue
            end_time = begin_time + dur
        out.append('%d\n%s --> %s\n%s\n\n' % (
            index,
            srt_subtitles_timecode(begin_time),
            srt_subtitles_timecode(end_time),
            parse_node(para)))

    return ''.join(out)


def cli_option(params, command_option, param):
    param = params.get(param)
    if param:
        param = compat_str(param)
    return [command_option, param] if param is not None else []


def cli_bool_option(params, command_option, param, true_value='true', false_value='false', separator=None):
    param = params.get(param)
    assert isinstance(param, bool)
    if separator:
        return [command_option + separator + (true_value if param else false_value)]
    return [command_option, true_value if param else false_value]


def cli_valueless_option(params, command_option, param, expected_value=True):
    param = params.get(param)
    return [command_option] if param == expected_value else []


def cli_configuration_args(params, param, default=[]):
    ex_args = params.get(param)
    if ex_args is None:
        return default
    assert isinstance(ex_args, list)
    return ex_args


class ISO639Utils(object):
    # See http://www.loc.gov/standards/iso639-2/ISO-639-2_utf-8.txt
    _lang_map = {
        'aa': 'aar',
        'ab': 'abk',
        'ae': 'ave',
        'af': 'afr',
        'ak': 'aka',
        'am': 'amh',
        'an': 'arg',
        'ar': 'ara',
        'as': 'asm',
        'av': 'ava',
        'ay': 'aym',
        'az': 'aze',
        'ba': 'bak',
        'be': 'bel',
        'bg': 'bul',
        'bh': 'bih',
        'bi': 'bis',
        'bm': 'bam',
        'bn': 'ben',
        'bo': 'bod',
        'br': 'bre',
        'bs': 'bos',
        'ca': 'cat',
        'ce': 'che',
        'ch': 'cha',
        'co': 'cos',
        'cr': 'cre',
        'cs': 'ces',
        'cu': 'chu',
        'cv': 'chv',
        'cy': 'cym',
        'da': 'dan',
        'de': 'deu',
        'dv': 'div',
        'dz': 'dzo',
        'ee': 'ewe',
        'el': 'ell',
        'en': 'eng',
        'eo': 'epo',
        'es': 'spa',
        'et': 'est',
        'eu': 'eus',
        'fa': 'fas',
        'ff': 'ful',
        'fi': 'fin',
        'fj': 'fij',
        'fo': 'fao',
        'fr': 'fra',
        'fy': 'fry',
        'ga': 'gle',
        'gd': 'gla',
        'gl': 'glg',
        'gn': 'grn',
        'gu': 'guj',
        'gv': 'glv',
        'ha': 'hau',
        'he': 'heb',
        'hi': 'hin',
        'ho': 'hmo',
        'hr': 'hrv',
        'ht': 'hat',
        'hu': 'hun',
        'hy': 'hye',
        'hz': 'her',
        'ia': 'ina',
        'id': 'ind',
        'ie': 'ile',
        'ig': 'ibo',
        'ii': 'iii',
        'ik': 'ipk',
        'io': 'ido',
        'is': 'isl',
        'it': 'ita',
        'iu': 'iku',
        'ja': 'jpn',
        'jv': 'jav',
        'ka': 'kat',
        'kg': 'kon',
        'ki': 'kik',
        'kj': 'kua',
        'kk': 'kaz',
        'kl': 'kal',
        'km': 'khm',
        'kn': 'kan',
        'ko': 'kor',
        'kr': 'kau',
        'ks': 'kas',
        'ku': 'kur',
        'kv': 'kom',
        'kw': 'cor',
        'ky': 'kir',
        'la': 'lat',
        'lb': 'ltz',
        'lg': 'lug',
        'li': 'lim',
        'ln': 'lin',
        'lo': 'lao',
        'lt': 'lit',
        'lu': 'lub',
        'lv': 'lav',
        'mg': 'mlg',
        'mh': 'mah',
        'mi': 'mri',
        'mk': 'mkd',
        'ml': 'mal',
        'mn': 'mon',
        'mr': 'mar',
        'ms': 'msa',
        'mt': 'mlt',
        'my': 'mya',
        'na': 'nau',
        'nb': 'nob',
        'nd': 'nde',
        'ne': 'nep',
        'ng': 'ndo',
        'nl': 'nld',
        'nn': 'nno',
        'no': 'nor',
        'nr': 'nbl',
        'nv': 'nav',
        'ny': 'nya',
        'oc': 'oci',
        'oj': 'oji',
        'om': 'orm',
        'or': 'ori',
        'os': 'oss',
        'pa': 'pan',
        'pi': 'pli',
        'pl': 'pol',
        'ps': 'pus',
        'pt': 'por',
        'qu': 'que',
        'rm': 'roh',
        'rn': 'run',
        'ro': 'ron',
        'ru': 'rus',
        'rw': 'kin',
        'sa': 'san',
        'sc': 'srd',
        'sd': 'snd',
        'se': 'sme',
        'sg': 'sag',
        'si': 'sin',
        'sk': 'slk',
        'sl': 'slv',
        'sm': 'smo',
        'sn': 'sna',
        'so': 'som',
        'sq': 'sqi',
        'sr': 'srp',
        'ss': 'ssw',
        'st': 'sot',
        'su': 'sun',
        'sv': 'swe',
        'sw': 'swa',
        'ta': 'tam',
        'te': 'tel',
        'tg': 'tgk',
        'th': 'tha',
        'ti': 'tir',
        'tk': 'tuk',
        'tl': 'tgl',
        'tn': 'tsn',
        'to': 'ton',
        'tr': 'tur',
        'ts': 'tso',
        'tt': 'tat',
        'tw': 'twi',
        'ty': 'tah',
        'ug': 'uig',
        'uk': 'ukr',
        'ur': 'urd',
        'uz': 'uzb',
        've': 'ven',
        'vi': 'vie',
        'vo': 'vol',
        'wa': 'wln',
        'wo': 'wol',
        'xh': 'xho',
        'yi': 'yid',
        'yo': 'yor',
        'za': 'zha',
        'zh': 'zho',
        'zu': 'zul',
    }

    @classmethod
    def short2long(cls, code):
        """Convert language code from ISO 639-1 to ISO 639-2/T"""
        return cls._lang_map.get(code[:2])

    @classmethod
    def long2short(cls, code):
        """Convert language code from ISO 639-2/T to ISO 639-1"""
        for short_name, long_name in cls._lang_map.items():
            if long_name == code:
                return short_name


class ISO3166Utils(object):
    # From http://data.okfn.org/data/core/country-list
    _country_map = {
        'AF': 'Afghanistan',
        'AX': 'Åland Islands',
        'AL': 'Albania',
        'DZ': 'Algeria',
        'AS': 'American Samoa',
        'AD': 'Andorra',
        'AO': 'Angola',
        'AI': 'Anguilla',
        'AQ': 'Antarctica',
        'AG': 'Antigua and Barbuda',
        'AR': 'Argentina',
        'AM': 'Armenia',
        'AW': 'Aruba',
        'AU': 'Australia',
        'AT': 'Austria',
        'AZ': 'Azerbaijan',
        'BS': 'Bahamas',
        'BH': 'Bahrain',
        'BD': 'Bangladesh',
        'BB': 'Barbados',
        'BY': 'Belarus',
        'BE': 'Belgium',
        'BZ': 'Belize',
        'BJ': 'Benin',
        'BM': 'Bermuda',
        'BT': 'Bhutan',
        'BO': 'Bolivia, Plurinational State of',
        'BQ': 'Bonaire, Sint Eustatius and Saba',
        'BA': 'Bosnia and Herzegovina',
        'BW': 'Botswana',
        'BV': 'Bouvet Island',
        'BR': 'Brazil',
        'IO': 'British Indian Ocean Territory',
        'BN': 'Brunei Darussalam',
        'BG': 'Bulgaria',
        'BF': 'Burkina Faso',
        'BI': 'Burundi',
        'KH': 'Cambodia',
        'CM': 'Cameroon',
        'CA': 'Canada',
        'CV': 'Cape Verde',
        'KY': 'Cayman Islands',
        'CF': 'Central African Republic',
        'TD': 'Chad',
        'CL': 'Chile',
        'CN': 'China',
        'CX': 'Christmas Island',
        'CC': 'Cocos (Keeling) Islands',
        'CO': 'Colombia',
        'KM': 'Comoros',
        'CG': 'Congo',
        'CD': 'Congo, the Democratic Republic of the',
        'CK': 'Cook Islands',
        'CR': 'Costa Rica',
        'CI': 'Côte d\'Ivoire',
        'HR': 'Croatia',
        'CU': 'Cuba',
        'CW': 'Curaçao',
        'CY': 'Cyprus',
        'CZ': 'Czech Republic',
        'DK': 'Denmark',
        'DJ': 'Djibouti',
        'DM': 'Dominica',
        'DO': 'Dominican Republic',
        'EC': 'Ecuador',
        'EG': 'Egypt',
        'SV': 'El Salvador',
        'GQ': 'Equatorial Guinea',
        'ER': 'Eritrea',
        'EE': 'Estonia',
        'ET': 'Ethiopia',
        'FK': 'Falkland Islands (Malvinas)',
        'FO': 'Faroe Islands',
        'FJ': 'Fiji',
        'FI': 'Finland',
        'FR': 'France',
        'GF': 'French Guiana',
        'PF': 'French Polynesia',
        'TF': 'French Southern Territories',
        'GA': 'Gabon',
        'GM': 'Gambia',
        'GE': 'Georgia',
        'DE': 'Germany',
        'GH': 'Ghana',
        'GI': 'Gibraltar',
        'GR': 'Greece',
        'GL': 'Greenland',
        'GD': 'Grenada',
        'GP': 'Guadeloupe',
        'GU': 'Guam',
        'GT': 'Guatemala',
        'GG': 'Guernsey',
        'GN': 'Guinea',
        'GW': 'Guinea-Bissau',
        'GY': 'Guyana',
        'HT': 'Haiti',
        'HM': 'Heard Island and McDonald Islands',
        'VA': 'Holy See (Vatican City State)',
        'HN': 'Honduras',
        'HK': 'Hong Kong',
        'HU': 'Hungary',
        'IS': 'Iceland',
        'IN': 'India',
        'ID': 'Indonesia',
        'IR': 'Iran, Islamic Republic of',
        'IQ': 'Iraq',
        'IE': 'Ireland',
        'IM': 'Isle of Man',
        'IL': 'Israel',
        'IT': 'Italy',
        'JM': 'Jamaica',
        'JP': 'Japan',
        'JE': 'Jersey',
        'JO': 'Jordan',
        'KZ': 'Kazakhstan',
        'KE': 'Kenya',
        'KI': 'Kiribati',
        'KP': 'Korea, Democratic People\'s Republic of',
        'KR': 'Korea, Republic of',
        'KW': 'Kuwait',
        'KG': 'Kyrgyzstan',
        'LA': 'Lao People\'s Democratic Republic',
        'LV': 'Latvia',
        'LB': 'Lebanon',
        'LS': 'Lesotho',
        'LR': 'Liberia',
        'LY': 'Libya',
        'LI': 'Liechtenstein',
        'LT': 'Lithuania',
        'LU': 'Luxembourg',
        'MO': 'Macao',
        'MK': 'Macedonia, the Former Yugoslav Republic of',
        'MG': 'Madagascar',
        'MW': 'Malawi',
        'MY': 'Malaysia',
        'MV': 'Maldives',
        'ML': 'Mali',
        'MT': 'Malta',
        'MH': 'Marshall Islands',
        'MQ': 'Martinique',
        'MR': 'Mauritania',
        'MU': 'Mauritius',
        'YT': 'Mayotte',
        'MX': 'Mexico',
        'FM': 'Micronesia, Federated States of',
        'MD': 'Moldova, Republic of',
        'MC': 'Monaco',
        'MN': 'Mongolia',
        'ME': 'Montenegro',
        'MS': 'Montserrat',
        'MA': 'Morocco',
        'MZ': 'Mozambique',
        'MM': 'Myanmar',
        'NA': 'Namibia',
        'NR': 'Nauru',
        'NP': 'Nepal',
        'NL': 'Netherlands',
        'NC': 'New Caledonia',
        'NZ': 'New Zealand',
        'NI': 'Nicaragua',
        'NE': 'Niger',
        'NG': 'Nigeria',
        'NU': 'Niue',
        'NF': 'Norfolk Island',
        'MP': 'Northern Mariana Islands',
        'NO': 'Norway',
        'OM': 'Oman',
        'PK': 'Pakistan',
        'PW': 'Palau',
        'PS': 'Palestine, State of',
        'PA': 'Panama',
        'PG': 'Papua New Guinea',
        'PY': 'Paraguay',
        'PE': 'Peru',
        'PH': 'Philippines',
        'PN': 'Pitcairn',
        'PL': 'Poland',
        'PT': 'Portugal',
        'PR': 'Puerto Rico',
        'QA': 'Qatar',
        'RE': 'Réunion',
        'RO': 'Romania',
        'RU': 'Russian Federation',
        'RW': 'Rwanda',
        'BL': 'Saint Barthélemy',
        'SH': 'Saint Helena, Ascension and Tristan da Cunha',
        'KN': 'Saint Kitts and Nevis',
        'LC': 'Saint Lucia',
        'MF': 'Saint Martin (French part)',
        'PM': 'Saint Pierre and Miquelon',
        'VC': 'Saint Vincent and the Grenadines',
        'WS': 'Samoa',
        'SM': 'San Marino',
        'ST': 'Sao Tome and Principe',
        'SA': 'Saudi Arabia',
        'SN': 'Senegal',
        'RS': 'Serbia',
        'SC': 'Seychelles',
        'SL': 'Sierra Leone',
        'SG': 'Singapore',
        'SX': 'Sint Maarten (Dutch part)',
        'SK': 'Slovakia',
        'SI': 'Slovenia',
        'SB': 'Solomon Islands',
        'SO': 'Somalia',
        'ZA': 'South Africa',
        'GS': 'South Georgia and the South Sandwich Islands',
        'SS': 'South Sudan',
        'ES': 'Spain',
        'LK': 'Sri Lanka',
        'SD': 'Sudan',
        'SR': 'Suriname',
        'SJ': 'Svalbard and Jan Mayen',
        'SZ': 'Swaziland',
        'SE': 'Sweden',
        'CH': 'Switzerland',
        'SY': 'Syrian Arab Republic',
        'TW': 'Taiwan, Province of China',
        'TJ': 'Tajikistan',
        'TZ': 'Tanzania, United Republic of',
        'TH': 'Thailand',
        'TL': 'Timor-Leste',
        'TG': 'Togo',
        'TK': 'Tokelau',
        'TO': 'Tonga',
        'TT': 'Trinidad and Tobago',
        'TN': 'Tunisia',
        'TR': 'Turkey',
        'TM': 'Turkmenistan',
        'TC': 'Turks and Caicos Islands',
        'TV': 'Tuvalu',
        'UG': 'Uganda',
        'UA': 'Ukraine',
        'AE': 'United Arab Emirates',
        'GB': 'United Kingdom',
        'US': 'United States',
        'UM': 'United States Minor Outlying Islands',
        'UY': 'Uruguay',
        'UZ': 'Uzbekistan',
        'VU': 'Vanuatu',
        'VE': 'Venezuela, Bolivarian Republic of',
        'VN': 'Viet Nam',
        'VG': 'Virgin Islands, British',
        'VI': 'Virgin Islands, U.S.',
        'WF': 'Wallis and Futuna',
        'EH': 'Western Sahara',
        'YE': 'Yemen',
        'ZM': 'Zambia',
        'ZW': 'Zimbabwe',
    }

    @classmethod
    def short2full(cls, code):
        """Convert an ISO 3166-2 country code to the corresponding full name"""
        return cls._country_map.get(code.upper())


class GeoUtils(object):
    # Major IPv4 address blocks per country
    _country_ip_map = {
        'AD': '85.94.160.0/19',
        'AE': '94.200.0.0/13',
        'AF': '149.54.0.0/17',
        'AG': '209.59.64.0/18',
        'AI': '204.14.248.0/21',
        'AL': '46.99.0.0/16',
        'AM': '46.70.0.0/15',
        'AO': '105.168.0.0/13',
        'AP': '159.117.192.0/21',
        'AR': '181.0.0.0/12',
        'AS': '202.70.112.0/20',
        'AT': '84.112.0.0/13',
        'AU': '1.128.0.0/11',
        'AW': '181.41.0.0/18',
        'AZ': '5.191.0.0/16',
        'BA': '31.176.128.0/17',
        'BB': '65.48.128.0/17',
        'BD': '114.130.0.0/16',
        'BE': '57.0.0.0/8',
        'BF': '129.45.128.0/17',
        'BG': '95.42.0.0/15',
        'BH': '37.131.0.0/17',
        'BI': '154.117.192.0/18',
        'BJ': '137.255.0.0/16',
        'BL': '192.131.134.0/24',
        'BM': '196.12.64.0/18',
        'BN': '156.31.0.0/16',
        'BO': '161.56.0.0/16',
        'BQ': '161.0.80.0/20',
        'BR': '152.240.0.0/12',
        'BS': '24.51.64.0/18',
        'BT': '119.2.96.0/19',
        'BW': '168.167.0.0/16',
        'BY': '178.120.0.0/13',
        'BZ': '179.42.192.0/18',
        'CA': '99.224.0.0/11',
        'CD': '41.243.0.0/16',
        'CF': '196.32.200.0/21',
        'CG': '197.214.128.0/17',
        'CH': '85.0.0.0/13',
        'CI': '154.232.0.0/14',
        'CK': '202.65.32.0/19',
        'CL': '152.172.0.0/14',
        'CM': '165.210.0.0/15',
        'CN': '36.128.0.0/10',
        'CO': '181.240.0.0/12',
        'CR': '201.192.0.0/12',
        'CU': '152.206.0.0/15',
        'CV': '165.90.96.0/19',
        'CW': '190.88.128.0/17',
        'CY': '46.198.0.0/15',
        'CZ': '88.100.0.0/14',
        'DE': '53.0.0.0/8',
        'DJ': '197.241.0.0/17',
        'DK': '87.48.0.0/12',
        'DM': '192.243.48.0/20',
        'DO': '152.166.0.0/15',
        'DZ': '41.96.0.0/12',
        'EC': '186.68.0.0/15',
        'EE': '90.190.0.0/15',
        'EG': '156.160.0.0/11',
        'ER': '196.200.96.0/20',
        'ES': '88.0.0.0/11',
        'ET': '196.188.0.0/14',
        'EU': '2.16.0.0/13',
        'FI': '91.152.0.0/13',
        'FJ': '144.120.0.0/16',
        'FM': '119.252.112.0/20',
        'FO': '88.85.32.0/19',
        'FR': '90.0.0.0/9',
        'GA': '41.158.0.0/15',
        'GB': '25.0.0.0/8',
        'GD': '74.122.88.0/21',
        'GE': '31.146.0.0/16',
        'GF': '161.22.64.0/18',
        'GG': '62.68.160.0/19',
        'GH': '45.208.0.0/14',
        'GI': '85.115.128.0/19',
        'GL': '88.83.0.0/19',
        'GM': '160.182.0.0/15',
        'GN': '197.149.192.0/18',
        'GP': '104.250.0.0/19',
        'GQ': '105.235.224.0/20',
        'GR': '94.64.0.0/13',
        'GT': '168.234.0.0/16',
        'GU': '168.123.0.0/16',
        'GW': '197.214.80.0/20',
        'GY': '181.41.64.0/18',
        'HK': '113.252.0.0/14',
        'HN': '181.210.0.0/16',
        'HR': '93.136.0.0/13',
        'HT': '148.102.128.0/17',
        'HU': '84.0.0.0/14',
        'ID': '39.192.0.0/10',
        'IE': '87.32.0.0/12',
        'IL': '79.176.0.0/13',
        'IM': '5.62.80.0/20',
        'IN': '117.192.0.0/10',
        'IO': '203.83.48.0/21',
        'IQ': '37.236.0.0/14',
        'IR': '2.176.0.0/12',
        'IS': '82.221.0.0/16',
        'IT': '79.0.0.0/10',
        'JE': '87.244.64.0/18',
        'JM': '72.27.0.0/17',
        'JO': '176.29.0.0/16',
        'JP': '126.0.0.0/8',
        'KE': '105.48.0.0/12',
        'KG': '158.181.128.0/17',
        'KH': '36.37.128.0/17',
        'KI': '103.25.140.0/22',
        'KM': '197.255.224.0/20',
        'KN': '198.32.32.0/19',
        'KP': '175.45.176.0/22',
        'KR': '175.192.0.0/10',
        'KW': '37.36.0.0/14',
        'KY': '64.96.0.0/15',
        'KZ': '2.72.0.0/13',
        'LA': '115.84.64.0/18',
        'LB': '178.135.0.0/16',
        'LC': '192.147.231.0/24',
        'LI': '82.117.0.0/19',
        'LK': '112.134.0.0/15',
        'LR': '41.86.0.0/19',
        'LS': '129.232.0.0/17',
        'LT': '78.56.0.0/13',
        'LU': '188.42.0.0/16',
        'LV': '46.109.0.0/16',
        'LY': '41.252.0.0/14',
        'MA': '105.128.0.0/11',
        'MC': '88.209.64.0/18',
        'MD': '37.246.0.0/16',
        'ME': '178.175.0.0/17',
        'MF': '74.112.232.0/21',
        'MG': '154.126.0.0/17',
        'MH': '117.103.88.0/21',
        'MK': '77.28.0.0/15',
        'ML': '154.118.128.0/18',
        'MM': '37.111.0.0/17',
        'MN': '49.0.128.0/17',
        'MO': '60.246.0.0/16',
        'MP': '202.88.64.0/20',
        'MQ': '109.203.224.0/19',
        'MR': '41.188.64.0/18',
        'MS': '208.90.112.0/22',
        'MT': '46.11.0.0/16',
        'MU': '105.16.0.0/12',
        'MV': '27.114.128.0/18',
        'MW': '105.234.0.0/16',
        'MX': '187.192.0.0/11',
        'MY': '175.136.0.0/13',
        'MZ': '197.218.0.0/15',
        'NA': '41.182.0.0/16',
        'NC': '101.101.0.0/18',
        'NE': '197.214.0.0/18',
        'NF': '203.17.240.0/22',
        'NG': '105.112.0.0/12',
        'NI': '186.76.0.0/15',
        'NL': '145.96.0.0/11',
        'NO': '84.208.0.0/13',
        'NP': '36.252.0.0/15',
        'NR': '203.98.224.0/19',
        'NU': '49.156.48.0/22',
        'NZ': '49.224.0.0/14',
        'OM': '5.36.0.0/15',
        'PA': '186.72.0.0/15',
        'PE': '186.160.0.0/14',
        'PF': '123.50.64.0/18',
        'PG': '124.240.192.0/19',
        'PH': '49.144.0.0/13',
        'PK': '39.32.0.0/11',
        'PL': '83.0.0.0/11',
        'PM': '70.36.0.0/20',
        'PR': '66.50.0.0/16',
        'PS': '188.161.0.0/16',
        'PT': '85.240.0.0/13',
        'PW': '202.124.224.0/20',
        'PY': '181.120.0.0/14',
        'QA': '37.210.0.0/15',
        'RE': '139.26.0.0/16',
        'RO': '79.112.0.0/13',
        'RS': '178.220.0.0/14',
        'RU': '5.136.0.0/13',
        'RW': '105.178.0.0/15',
        'SA': '188.48.0.0/13',
        'SB': '202.1.160.0/19',
        'SC': '154.192.0.0/11',
        'SD': '154.96.0.0/13',
        'SE': '78.64.0.0/12',
        'SG': '152.56.0.0/14',
        'SI': '188.196.0.0/14',
        'SK': '78.98.0.0/15',
        'SL': '197.215.0.0/17',
        'SM': '89.186.32.0/19',
        'SN': '41.82.0.0/15',
        'SO': '197.220.64.0/19',
        'SR': '186.179.128.0/17',
        'SS': '105.235.208.0/21',
        'ST': '197.159.160.0/19',
        'SV': '168.243.0.0/16',
        'SX': '190.102.0.0/20',
        'SY': '5.0.0.0/16',
        'SZ': '41.84.224.0/19',
        'TC': '65.255.48.0/20',
        'TD': '154.68.128.0/19',
        'TG': '196.168.0.0/14',
        'TH': '171.96.0.0/13',
        'TJ': '85.9.128.0/18',
        'TK': '27.96.24.0/21',
        'TL': '180.189.160.0/20',
        'TM': '95.85.96.0/19',
        'TN': '197.0.0.0/11',
        'TO': '175.176.144.0/21',
        'TR': '78.160.0.0/11',
        'TT': '186.44.0.0/15',
        'TV': '202.2.96.0/19',
        'TW': '120.96.0.0/11',
        'TZ': '156.156.0.0/14',
        'UA': '93.72.0.0/13',
        'UG': '154.224.0.0/13',
        'US': '3.0.0.0/8',
        'UY': '167.56.0.0/13',
        'UZ': '82.215.64.0/18',
        'VA': '212.77.0.0/19',
        'VC': '24.92.144.0/20',
        'VE': '186.88.0.0/13',
        'VG': '172.103.64.0/18',
        'VI': '146.226.0.0/16',
        'VN': '14.160.0.0/11',
        'VU': '202.80.32.0/20',
        'WF': '117.20.32.0/21',
        'WS': '202.4.32.0/19',
        'YE': '134.35.0.0/16',
        'YT': '41.242.116.0/22',
        'ZA': '41.0.0.0/11',
        'ZM': '165.56.0.0/13',
        'ZW': '41.85.192.0/19',
    }

    @classmethod
    def random_ipv4(cls, code):
        block = cls._country_ip_map.get(code.upper())
        if not block:
            return None
        addr, preflen = block.split('/')
        addr_min = compat_struct_unpack('!L', socket.inet_aton(addr))[0]
        addr_max = addr_min | (0xffffffff >> int(preflen))
        return compat_str(socket.inet_ntoa(
            compat_struct_pack('!L', random.randint(addr_min, addr_max))))


class PerRequestProxyHandler(compat_urllib_request.ProxyHandler):
    def __init__(self, proxies=None):
        # Set default handlers
        for type in ('http', 'https'):
            setattr(self, '%s_open' % type,
                    lambda r, proxy='__noproxy__', type=type, meth=self.proxy_open:
                        meth(r, proxy, type))
        return compat_urllib_request.ProxyHandler.__init__(self, proxies)

    def proxy_open(self, req, proxy, type):
        req_proxy = req.headers.get('Ytdl-request-proxy')
        if req_proxy is not None:
            proxy = req_proxy
            del req.headers['Ytdl-request-proxy']

        if proxy == '__noproxy__':
            return None  # No Proxy
        if compat_urlparse.urlparse(proxy).scheme.lower() in ('socks', 'socks4', 'socks4a', 'socks5'):
            req.add_header('Ytdl-socks-proxy', proxy)
            # youtube-dl's http/https handlers do wrapping the socket with socks
            return None
        return compat_urllib_request.ProxyHandler.proxy_open(
            self, req, proxy, type)


# Both long_to_bytes and bytes_to_long are adapted from PyCrypto, which is
# released into Public Domain
# https://github.com/dlitz/pycrypto/blob/master/lib/Crypto/Util/number.py#L387

def long_to_bytes(n, blocksize=0):
    """long_to_bytes(n:long, blocksize:int) : string
    Convert a long integer to a byte string.

    If optional blocksize is given and greater than zero, pad the front of the
    byte string with binary zeros so that the length is a multiple of
    blocksize.
    """
    # after much testing, this algorithm was deemed to be the fastest
    s = b''
    n = int(n)
    while n > 0:
        s = compat_struct_pack('>I', n & 0xffffffff) + s
        n = n >> 32
    # strip off leading zeros
    for i in range(len(s)):
        if s[i] != b'\000'[0]:
            break
    else:
        # only happens when n == 0
        s = b'\000'
        i = 0
    s = s[i:]
    # add back some pad bytes.  this could be done more efficiently w.r.t. the
    # de-padding being done above, but sigh...
    if blocksize > 0 and len(s) % blocksize:
        s = (blocksize - len(s) % blocksize) * b'\000' + s
    return s


def bytes_to_long(s):
    """bytes_to_long(string) : long
    Convert a byte string to a long integer.

    This is (essentially) the inverse of long_to_bytes().
    """
    acc = 0
    length = len(s)
    if length % 4:
        extra = (4 - length % 4)
        s = b'\000' * extra + s
        length = length + extra
    for i in range(0, length, 4):
        acc = (acc << 32) + compat_struct_unpack('>I', s[i:i + 4])[0]
    return acc


def ohdave_rsa_encrypt(data, exponent, modulus):
    '''
    Implement OHDave's RSA algorithm. See http://www.ohdave.com/rsa/

    Input:
        data: data to encrypt, bytes-like object
        exponent, modulus: parameter e and N of RSA algorithm, both integer
    Output: hex string of encrypted data

    Limitation: supports one block encryption only
    '''

    payload = int(binascii.hexlify(data[::-1]), 16)
    encrypted = pow(payload, exponent, modulus)
    return '%x' % encrypted


def pkcs1pad(data, length):
    """
    Padding input data with PKCS#1 scheme

    @param {int[]} data        input data
    @param {int}   length      target length
    @returns {int[]}           padded data
    """
    if len(data) > length - 11:
        raise ValueError('Input data too long for PKCS#1 padding')

    pseudo_random = [random.randint(0, 254) for _ in range(length - len(data) - 3)]
    return [0, 2] + pseudo_random + [0] + data


def encode_base_n(num, n, table=None):
    FULL_TABLE = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if not table:
        table = FULL_TABLE[:n]

    if n > len(table):
        raise ValueError('base %d exceeds table length %d' % (n, len(table)))

    if num == 0:
        return table[0]

    ret = ''
    while num:
        ret = table[num % n] + ret
        num = num // n
    return ret


def decode_packed_codes(code):
    mobj = re.search(PACKED_CODES_RE, code)
    obfucasted_code, base, count, symbols = mobj.groups()
    base = int(base)
    count = int(count)
    symbols = symbols.split('|')
    symbol_table = {}

    while count:
        count -= 1
        base_n_count = encode_base_n(count, base)
        symbol_table[base_n_count] = symbols[count] or base_n_count

    return re.sub(
        r'\b(\w+)\b', lambda mobj: symbol_table[mobj.group(0)],
        obfucasted_code)


def parse_m3u8_attributes(attrib):
    info = {}
    for (key, val) in re.findall(r'(?P<key>[A-Z0-9-]+)=(?P<val>"[^"]+"|[^",]+)(?:,|$)', attrib):
        if val.startswith('"'):
            val = val[1:-1]
        info[key] = val
    return info


def urshift(val, n):
    return val >> n if val >= 0 else (val + 0x100000000) >> n


# Based on png2str() written by @gdkchan and improved by @yokrysty
# Originally posted at https://github.com/rg3/youtube-dl/issues/9706
def decode_png(png_data):
    # Reference: https://www.w3.org/TR/PNG/
    header = png_data[8:]

    if png_data[:8] != b'\x89PNG\x0d\x0a\x1a\x0a' or header[4:8] != b'IHDR':
        raise IOError('Not a valid PNG file.')

    int_map = {1: '>B', 2: '>H', 4: '>I'}
    unpack_integer = lambda x: compat_struct_unpack(int_map[len(x)], x)[0]

    chunks = []

    while header:
        length = unpack_integer(header[:4])
        header = header[4:]

        chunk_type = header[:4]
        header = header[4:]

        chunk_data = header[:length]
        header = header[length:]

        header = header[4:]  # Skip CRC

        chunks.append({
            'type': chunk_type,
            'length': length,
            'data': chunk_data
        })

    ihdr = chunks[0]['data']

    width = unpack_integer(ihdr[:4])
    height = unpack_integer(ihdr[4:8])

    idat = b''

    for chunk in chunks:
        if chunk['type'] == b'IDAT':
            idat += chunk['data']

    if not idat:
        raise IOError('Unable to read PNG data.')

    decompressed_data = bytearray(zlib.decompress(idat))

    stride = width * 3
    pixels = []

    def _get_pixel(idx):
        x = idx % stride
        y = idx // stride
        return pixels[y][x]

    for y in range(height):
        basePos = y * (1 + stride)
        filter_type = decompressed_data[basePos]

        current_row = []

        pixels.append(current_row)

        for x in range(stride):
            color = decompressed_data[1 + basePos + x]
            basex = y * stride + x
            left = 0
            up = 0

            if x > 2:
                left = _get_pixel(basex - 3)
            if y > 0:
                up = _get_pixel(basex - stride)

            if filter_type == 1:  # Sub
                color = (color + left) & 0xff
            elif filter_type == 2:  # Up
                color = (color + up) & 0xff
            elif filter_type == 3:  # Average
                color = (color + ((left + up) >> 1)) & 0xff
            elif filter_type == 4:  # Paeth
                a = left
                b = up
                c = 0

                if x > 2 and y > 0:
                    c = _get_pixel(basex - stride - 3)

                p = a + b - c

                pa = abs(p - a)
                pb = abs(p - b)
                pc = abs(p - c)

                if pa <= pb and pa <= pc:
                    color = (color + a) & 0xff
                elif pb <= pc:
                    color = (color + b) & 0xff
                else:
                    color = (color + c) & 0xff

            current_row.append(color)

    return width, height, pixels


def write_xattr(path, key, value):
    # This mess below finds the best xattr tool for the job
    try:
        # try the pyxattr module...
        import xattr

        if hasattr(xattr, 'set'):  # pyxattr
            # Unicode arguments are not supported in python-pyxattr until
            # version 0.5.0
            # See https://github.com/rg3/youtube-dl/issues/5498
            pyxattr_required_version = '0.5.0'
            if version_tuple(xattr.__version__) < version_tuple(pyxattr_required_version):
                # TODO: fallback to CLI tools
                raise XAttrUnavailableError(
                    'python-pyxattr is detected but is too old. '
                    'youtube-dl requires %s or above while your version is %s. '
                    'Falling back to other xattr implementations' % (
                        pyxattr_required_version, xattr.__version__))

            setxattr = xattr.set
        else:  # xattr
            setxattr = xattr.setxattr

        try:
            setxattr(path, key, value)
        except EnvironmentError as e:
            raise XAttrMetadataError(e.errno, e.strerror)

    except ImportError:
        if compat_os_name == 'nt':
            # Write xattrs to NTFS Alternate Data Streams:
            # http://en.wikipedia.org/wiki/NTFS#Alternate_data_streams_.28ADS.29
            assert ':' not in key
            assert os.path.exists(path)

            ads_fn = path + ':' + key
            try:
                with open(ads_fn, 'wb') as f:
                    f.write(value)
            except EnvironmentError as e:
                raise XAttrMetadataError(e.errno, e.strerror)
        else:
            user_has_setfattr = check_executable('setfattr', ['--version'])
            user_has_xattr = check_executable('xattr', ['-h'])

            if user_has_setfattr or user_has_xattr:

                value = value.decode('utf-8')
                if user_has_setfattr:
                    executable = 'setfattr'
                    opts = ['-n', key, '-v', value]
                elif user_has_xattr:
                    executable = 'xattr'
                    opts = ['-w', key, value]

                cmd = ([encodeFilename(executable, True)] +
                       [encodeArgument(o) for o in opts] +
                       [encodeFilename(path, True)])

                try:
                    p = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                except EnvironmentError as e:
                    raise XAttrMetadataError(e.errno, e.strerror)
                stdout, stderr = p.communicate()
                stderr = stderr.decode('utf-8', 'replace')
                if p.returncode != 0:
                    raise XAttrMetadataError(p.returncode, stderr)

            else:
                # On Unix, and can't find pyxattr, setfattr, or xattr.
                if sys.platform.startswith('linux'):
                    raise XAttrUnavailableError(
                        "Couldn't find a tool to set the xattrs. "
                        "Install either the python 'pyxattr' or 'xattr' "
                        "modules, or the GNU 'attr' package "
                        "(which contains the 'setfattr' tool).")
                else:
                    raise XAttrUnavailableError(
                        "Couldn't find a tool to set the xattrs. "
                        "Install either the python 'xattr' module, "
                        "or the 'xattr' binary.")


def random_birthday(year_field, month_field, day_field):
    return {
        year_field: str(random.randint(1950, 1995)),
        month_field: str(random.randint(1, 12)),
        day_field: str(random.randint(1, 31)),
    }