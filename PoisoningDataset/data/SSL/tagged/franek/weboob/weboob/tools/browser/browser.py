# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from __future__ import with_statement

from copy import copy
from httplib import BadStatusLine
from logging import warning

try:
    import mechanize
except ImportError:
    raise ImportError('Please install python-mechanize')

import os
import sys
import re
import tempfile
from threading import RLock
import ssl
import httplib
import socket
import hashlib
import time
import urllib
import urllib2
from urlparse import urlsplit
import mimetypes
from contextlib import closing
from gzip import GzipFile

from weboob.tools.decorators import retry
from weboob.tools.log import getLogger
from weboob.tools.mech import ClientForm
ControlNotFoundError = ClientForm.ControlNotFoundError
from weboob.tools.parsers import get_parser

# Try to load cookies
try:
    from .firefox_cookies import FirefoxCookieJar
except ImportError, e:
    warning("Unable to store cookies: %s" % e)
    HAVE_COOKIES = False
else:
    HAVE_COOKIES = True


__all__ = ['BrowserIncorrectPassword', 'BrowserForbidden', 'BrowserBanned', 'BrowserUnavailable', 'BrowserRetry',
           'BrowserHTTPNotFound', 'BrowserHTTPError', 'BrokenPageError', 'BasePage',
           'StandardBrowser', 'BaseBrowser']


# Exceptions
class BrowserIncorrectPassword(Exception):
    pass


class BrowserForbidden(Exception):
    pass


class BrowserBanned(BrowserIncorrectPassword):
    pass


class BrowserPasswordExpired(BrowserIncorrectPassword):
    pass


class BrowserUnavailable(Exception):
    pass


class BrowserHTTPNotFound(BrowserUnavailable):
    pass


class BrowserHTTPError(BrowserUnavailable):
    pass


class BrowserRetry(Exception):
    pass


class NoHistory(object):
    """
    We don't want to fill memory with history
    """
    def __init__(self):
        pass

    def add(self, request, response):
        pass

    def back(self, n, _response):
        pass

    def clear(self):
        pass

    def close(self):
        pass


class BrokenPageError(Exception):
    pass


class BasePage(object):
    """
    Base page
    """

    ENCODING = None

    def __init__(self, browser, document, url='', groups=None, group_dict=None, logger=None):
        self.browser = browser
        self.parser = browser.parser
        self.document = document
        self.url = url
        self.groups = groups
        self.group_dict = group_dict
        self.logger = getLogger('page', logger)

    def on_loaded(self):
        """
        Called when the page is loaded.
        """
        pass


def check_location(func):
    def inner(self, *args, **kwargs):
        if args and isinstance(args[0], basestring):
            url = args[0]
            if url.startswith('/') and hasattr(self, 'DOMAIN') and (not self.request or self.request.host != self.DOMAIN):
                url = '%s://%s%s' % (self.PROTOCOL, self.DOMAIN, url)
            url = re.sub('(.*)#.*', r'\1', url)

            if isinstance(url, unicode):
                url = url.encode('utf-8')
            args = (url,) + args[1:]
        return func(self, *args, **kwargs)
    return inner


class StandardBrowser(mechanize.Browser):
    """
    Standard Browser.

    :param firefox_cookies: path to cookies sqlite file
    :type firefox_cookies: str
    :param parser: parser to use on HTML files
    :type parser: :class:`weboob.tools.parsers.iparser.IParser`
    :param history: history manager; default value is an object which
                    does not keep history
    :type history: object
    :param proxy: proxy URL to use
    :type proxy: str
    :param factory: mechanize factory. None to use Mechanize's default
    :type factory: object
    """

    # ------ Class attributes --------------------------------------

    ENCODING = 'utf-8'
    USER_AGENTS = {
        'desktop_firefox': 'Mozilla/5.0 (X11; Linux x86_64; rv:17.0) Gecko/20100101 Firefox/17.0',
        'android': 'Mozilla/5.0 (Linux; U; Android 2.1; en-us; Nexus One Build/ERD62) AppleWebKit/530.17 (KHTML, like Gecko) Version/4.0 Mobile Safari/530.17',
        'microb': 'Mozilla/5.0 (X11; U; Linux armv7l; fr-FR; rv:1.9.2.3pre) Gecko/20100723 Firefox/3.5 Maemo Browser 1.7.4.8 RX-51 N900',
        'wget': 'Wget/1.11.4',
    }
    USER_AGENT = USER_AGENTS['desktop_firefox']
    SAVE_RESPONSES = False
    DEBUG_HTTP = False
    DEBUG_MECHANIZE = False
    DEFAULT_TIMEOUT = 15
    INSECURE = False  # if True, do not validate SSL

    responses_dirname = None
    responses_count = 0

    logger = None

    # ------ Browser methods ---------------------------------------

    # I'm not a robot, so disable the check of permissions in robots.txt.
    default_features = copy(mechanize.Browser.default_features)
    default_features.remove('_robots')
    default_features.remove('_refresh')

    def __init__(self, firefox_cookies=None, parser=None, history=NoHistory(), proxy=None, logger=None, factory=None, responses_dirname=None):
        mechanize.Browser.__init__(self, history=history, factory=factory)
        self.logger = getLogger('browser', logger)

        self.addheaders = [
                ['User-agent', self.USER_AGENT]
            ]

        # Use a proxy
        self.proxy = proxy
        if proxy:
            proto = 'http'
            if '://' in proxy:
                v = urlsplit(proxy)
                proto = v.scheme
                domain = v.netloc
            else:
                domain = proxy
            self.set_proxies({proto: domain})

        # Share cookies with firefox
        if firefox_cookies and HAVE_COOKIES:
            self._cookie = FirefoxCookieJar(self.DOMAIN, firefox_cookies)
            self._cookie.load()
            self.set_cookiejar(self._cookie)
        else:
            self._cookie = None

        if parser is None:
            parser = get_parser()()
        elif isinstance(parser, (tuple,list,basestring)):
            parser = get_parser(parser)()
        self.parser = parser
        self.lock = RLock()

        if self.DEBUG_HTTP:
            # display messages from httplib
            self.set_debug_http(True)

        if self.DEBUG_MECHANIZE:
            # Enable log messages from mechanize.Browser
            self.set_debug_redirects(True)

        self.responses_dirname = responses_dirname

    def __enter__(self):
        self.lock.acquire()

    def __exit__(self, t, v, tb):
        self.lock.release()

    def _openurl(self, *args, **kwargs):
        return mechanize.Browser.open(self, *args, **kwargs)

    @check_location
    @retry(BrowserHTTPError, tries=3)
    def openurl(self, *args, **kwargs):
        """
        Open an URL but do not create a Page object.
        """
        if_fail = kwargs.pop('if_fail', 'raise')
        self.logger.debug('Opening URL "%s", %s' % (args, kwargs))

        kwargs['timeout'] = kwargs.get('timeout', self.DEFAULT_TIMEOUT)

        try:
            return self._openurl(*args, **kwargs)
        except (mechanize.BrowserStateError, mechanize.response_seek_wrapper,
                urllib2.HTTPError, urllib2.URLError, BadStatusLine, ssl.SSLError), e:
            if isinstance(e, mechanize.BrowserStateError) and hasattr(self, 'home'):
                self.home()
                return self._openurl(*args, **kwargs)
            elif if_fail == 'raise':
                raise self.get_exception(e)('%s (url="%s")' % (e, args and args[0] or 'None'))
            else:
                return None
        except BrowserRetry, e:
            return self._openurl(*args, **kwargs)

    def get_exception(self, e):
        if isinstance(e, urllib2.HTTPError) and hasattr(e, 'getcode'):
            if e.getcode() in (404, 403):
                return BrowserHTTPNotFound
            if e.getcode() == 401:
                return BrowserIncorrectPassword
        elif isinstance(e, mechanize.BrowserStateError):
            return BrowserHTTPNotFound

        return BrowserHTTPError

    def readurl(self, url, *args, **kwargs):
        """
        Download URL data specifying what to do on failure (nothing by default).
        """
        if not 'if_fail' in kwargs:
            kwargs['if_fail'] = None
        result = self.openurl(url, *args, **kwargs)

        if result:
            if self.SAVE_RESPONSES:
                self.save_response(result)
            return result.read()
        else:
            return None

    def save_response(self, result, warning=False):
        """
        Save a stream to a temporary file, and log its name.
        The stream is rewinded after saving.
        """
        if self.responses_dirname is None:
            self.responses_dirname = tempfile.mkdtemp(prefix='weboob_session_')
            print >>sys.stderr, 'Debug data will be saved in this directory: %s' % self.responses_dirname
        elif not os.path.isdir(self.responses_dirname):
            os.makedirs(self.responses_dirname)
        # get the content-type, remove optionnal charset part
        mimetype = result.info().get('Content-Type', '').split(';')[0]
        # due to http://bugs.python.org/issue1043134
        if mimetype == 'text/plain':
            ext = '.txt'
        else:
            # try to get an extension (and avoid adding 'None')
            ext = mimetypes.guess_extension(mimetype, False) or ''
        response_filepath = os.path.join(self.responses_dirname, unicode(self.responses_count)+ext)
        with open(response_filepath, 'w') as f:
            f.write(result.read())
        result.seek(0)
        match_filepath = os.path.join(self.responses_dirname, 'url_response_match.txt')
        with open(match_filepath, 'a') as f:
            f.write('%s\t%s\n' % (result.geturl(), os.path.basename(response_filepath)))
        self.responses_count += 1

        msg = u'Response saved to %s' % response_filepath
        if warning:
            self.logger.warning(msg)
        else:
            self.logger.info(msg)

    def get_document(self, result, parser=None, encoding=None):
        """
        Get a parsed document from a stream.

        :param result: HTML page stream
        :type result: stream
        """
        if parser is None:
            parser = self.parser
        elif isinstance(parser, (basestring, list, tuple)):
            parser = get_parser(parser)()

        if encoding is None:
            encoding = self.ENCODING

        return parser.parse(result, encoding)

    def location(self, *args, **kwargs):
        """
        Go on an URL and get the related document.
        """
        return self.get_document(self.openurl(*args, **kwargs))

    @staticmethod
    def buildurl(base, *args, **kwargs):
        """
        Build an URL and escape arguments.

        You can give a serie of tuples in args (and the order is keept), or
        a dict in kwargs (but the order is lost).

        Example:

        >>> buildurl('/blah.php', ('a', '&'), ('b', '=')
        '/blah.php?a=%26&b=%3D'
        >>> buildurl('/blah.php', a='&', 'b'='=')
        '/blah.php?b=%3D&a=%26'
        """

        if not args:
            args = kwargs
        if not args:
            return base
        else:
            return '%s?%s' % (base, urllib.urlencode(args))

    def str(self, s):
        if isinstance(s, unicode):
            s = s.encode('iso-8859-15', 'replace')
        return s

    def set_field(self, args, label, field=None, value=None, is_list=False):
        """
        Set a value to a form field.

        :param args: arguments where to look for value
        :type args: dict
        :param label: label in args
        :type label: str
        :param field: field name. If None, use label instead
        :type field: str
        :param value: value to give on field
        :type value: str
        :param is_list: the field is a list
        :type is_list: bool
        """
        try:
            if not field:
                field = label
            if args.get(label, None) is not None:
                if not value:
                    if is_list:
                        if isinstance(is_list, (list, tuple)):
                            try:
                                value = [self.str(is_list.index(args[label]))]
                            except ValueError, e:
                                if args[label]:
                                    print >>sys.stderr, '[%s] %s: %s' % (label, args[label], e)
                                return
                        else:
                            value = [self.str(args[label])]
                    else:
                        value = self.str(args[label])
                self[field] = value
        except ControlNotFoundError:
            return

    def lowsslcheck(self, domain, hsh):
        certs = ssl.get_server_certificate((domain,  443))
        certhash = hashlib.sha256(certs).hexdigest()
        if self.logger:
            self.logger.debug('Found %s as certificate hash' % certhash)
        if isinstance(hsh, basestring):
            hsh = [hsh]
        if certhash not in hsh:
            raise ssl.SSLError()


class BaseBrowser(StandardBrowser):
    """
    Base browser class to navigate on a website.

    :param username: username on website
    :type username: str
    :param password: password on website. If it is None, Browser will
                     not try to login
    :type password: str
    :param firefox_cookies: path to cookies sqlite file
    :type firefox_cookies: str
    :param parser: parser to use on HTML files
    :type parser: :class:`weboob.tools.parsers.iparser.IParser`
    :param history: history manager; default value is an object which
                    does not keep history
    :type history: object
    :param proxy: proxy URL to use
    :type proxy: str
    :param logger: logger to use for logging
    :type logger: :class:`logging.Logger`
    :param factory: mechanize factory. None to use Mechanize's default
    :type factory: object
    :param get_home: try to get the homepage.
    :type get_homme: bool
    :param responses_dirname: directory to store responses
    :type responses_dirname: str
    """

    # ------ Class attributes --------------------------------------

    DOMAIN = None
    PROTOCOL = 'http'
    PAGES = {}

    # SHA-256 hash of server certificate. If set, it will automatically check it,
    # and raise a SSLError exception if it doesn't match.
    CERTHASH = None

    # ------ Abstract methods --------------------------------------

    def home(self):
        """
        Go to the home page.
        """
        if self.DOMAIN is not None:
            self.location('%s://%s/' % (self.PROTOCOL, self.DOMAIN))

    def login(self):
        """
        Login to the website.

        This function is called when is_logged() returns False and the password
        attribute is not None.
        """
        raise NotImplementedError()

    def is_logged(self):
        """
        Return True if we are logged on website. When Browser tries to access
        to a page, if this method returns False, it calls login().

        It is never called if the password attribute is None.
        """
        raise NotImplementedError()

    # ------ Browser methods ---------------------------------------

    def __init__(self, username=None, password=None, firefox_cookies=None,
                 parser=None, history=NoHistory(), proxy=None, logger=None,
                 factory=None, get_home=True, responses_dirname=None):
        StandardBrowser.__init__(self, firefox_cookies, parser, history, proxy, logger, factory, responses_dirname)
        self.page = None
        self.last_update = 0.0
        self.username = username
        self.password = password

        if not self.INSECURE and self.CERTHASH is not None and self.DOMAIN is not None:
            self.lowsslcheck(self.DOMAIN, self.CERTHASH)

        if self.password and get_home:
            try:
                self.home()
            # Do not abort the build of browser when the website is down.
            except BrowserUnavailable:
                pass

    def submit(self, *args, **kwargs):
        """
        Submit the selected form.
        """
        nologin = kwargs.pop('nologin', False)
        try:
            self._change_location(mechanize.Browser.submit(self, *args, **kwargs), no_login=nologin)
        except (mechanize.response_seek_wrapper, urllib2.HTTPError, urllib2.URLError, BadStatusLine, ssl.SSLError), e:
            self.page = None
            raise self.get_exception(e)(e)
        except (mechanize.BrowserStateError, BrowserRetry), e:
            raise BrowserUnavailable(e)

    def is_on_page(self, pageCls):
        """
        Check the current page.

        :param pageCls: class of the page to check
        :type pageCls: :class:`BasePage`
        :rtype: bool
        """
        return isinstance(self.page, pageCls)

    def absurl(self, rel):
        """
        Get an absolute URL from a relative one.
        """
        if rel is None:
            return None
        if not rel.startswith('/'):
            rel = '/' + rel
        return '%s://%s%s' % (self.PROTOCOL, self.DOMAIN, rel)

    def follow_link(self, *args, **kwargs):
        """
        Follow a link on the page.
        """
        try:
            self._change_location(mechanize.Browser.follow_link(self, *args, **kwargs))
        except (mechanize.response_seek_wrapper, urllib2.HTTPError, urllib2.URLError, BadStatusLine, ssl.SSLError), e:
            self.page = None
            raise self.get_exception(e)('%s (url="%s")' % (e, args and args[0] or 'None'))
        except (mechanize.BrowserStateError, BrowserRetry), e:
            self.home()
            raise BrowserUnavailable(e)

    def _openurl(self, *args, **kwargs):
        return mechanize.Browser.open_novisit(self, *args, **kwargs)

    @check_location
    @retry(BrowserHTTPError, tries=3)
    def location(self, *args, **kwargs):
        """
        Change location of browser on an URL.

        When the page is loaded, it looks up PAGES to find a regexp which
        matches, and create the object. Then, the 'on_loaded' method of
        this object is called.

        If a password is set, and is_logged() returns False, it tries to login
        with login() and reload the page.
        """
        keep_args = copy(args)
        keep_kwargs = kwargs.copy()

        no_login = kwargs.pop('no_login', False)
        kwargs['timeout'] = kwargs.get('timeout', self.DEFAULT_TIMEOUT)

        try:
            self._change_location(mechanize.Browser.open(self, *args, **kwargs), no_login=no_login)
        except BrowserRetry:
            if not self.page or not args or self.page.url != args[0]:
                keep_kwargs['no_login'] = True
                self.location(*keep_args, **keep_kwargs)
        except (mechanize.response_seek_wrapper, urllib2.HTTPError, urllib2.URLError, BadStatusLine, ssl.SSLError), e:
            self.page = None
            raise self.get_exception(e)('%s (url="%s")' % (e, args and args[0] or 'None'))
        except mechanize.BrowserStateError:
            self.home()
            self.location(*keep_args, **keep_kwargs)

    # DO NOT ENABLE THIS FUCKING PEACE OF CODE EVEN IF IT WOULD BE BETTER
    # TO SANITARIZE FUCKING HTML.
    #def _set_response(self, response, *args, **kwargs):
    #    import time
    #    if response and hasattr(response, 'set_data'):
    #        print time.time()
    #        r = response.read()
    #        start = 0
    #        end = 0
    #        new = ''
    #        lowr = r.lower()
    #        start = lowr[end:].find('<script')
    #        while start >= end:
    #            start_stop = start + lowr[start:].find('>') + 1
    #            new += r[end:start_stop]
    #            end = start + lowr[start:].find('</script>')
    #            new += r[start_stop:end].replace('<', '&lt;').replace('>', '&gt;')
    #            start = end + lowr[end:].find('<script')
    #        new += r[end:]
    #        response.set_data(new)
    #        print time.time()
    #    mechanize.Browser._set_response(self, response, *args, **kwargs)

    def _set_response(self, response, *args, **kwargs):
        # Support Gzip, because mechanize does not, and some websites always send gzip
        if response and hasattr(response, 'set_data'):
            headers = response.info()
            if headers.get('Content-Encoding', '') == 'gzip':
                with closing(GzipFile(fileobj=response, mode='rb')) as gz:
                    data = gz.read()
                response.set_data(data)
        mechanize.Browser._set_response(self, response, *args, **kwargs)

    def _change_location(self, result, no_login=False):
        """
        This function is called when we have moved to a page, to load a Page
        object.
        """

        # Find page from url
        pageCls = None
        parser = None
        page_groups = None
        page_group_dict = None
        for key, value in self.PAGES.items():
            if isinstance(key, basestring):
                if not key.startswith('^') and not key.endswith('$'):
                    regexp = re.compile('^%s$' % key)
                else:
                    regexp = re.compile(key)
            else:
                regexp = key
            m = regexp.search(result.geturl())
            if m:
                if isinstance(value, (list, tuple)):
                    pageCls = value[0]
                    parser = value[1]
                else:
                    pageCls = value
                    parser = self.parser

                page_groups = m.groups()
                page_group_dict = m.groupdict()
                break

        # Not found
        if not pageCls:
            self.page = None
            self.logger.warning('There isn\'t any page corresponding to URL %s' % result.geturl())
            self.save_response(result, warning=True)
            return

        self.logger.debug('[user_id=%s] Went on %s' % (self.username, result.geturl()))
        self.last_update = time.time()

        if self.SAVE_RESPONSES:
            self.save_response(result)

        document = self.get_document(result, parser, encoding=pageCls.ENCODING)
        self.page = pageCls(self, document, result.geturl(), groups=page_groups, group_dict=page_group_dict, logger=self.logger)

        if not no_login and self.password is not None and not self.is_logged():
            self.logger.debug('!! Relogin !!')
            self.login()
            raise BrowserRetry()

        self.page.on_loaded()

        if self._cookie:
            self._cookie.save()


def mywrap_socket(sock, *args, **kwargs):
    kwargs['do_handshake_on_connect'] = False
    sock = ssl.wrap_socketold(sock, *args, **kwargs)
    sock.settimeout(StandardBrowser.DEFAULT_TIMEOUT)
    try:
        sock.getpeername()
    except:
        sock.do_handshake_on_connect = True
    else:
        sock.do_handshake()
    return sock


ssl.wrap_socketold = ssl.wrap_socket
ssl.wrap_socket = mywrap_socket


class HTTPSConnection2(httplib.HTTPSConnection):
    _HOSTS = {}
<target>
    _PROTOCOLS = [ssl.PROTOCOL_TLSv1, ssl.PROTOCOL_SSLv3]
</target>

    def _create_connection(self):
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self._tunnel()
        return sock

    def _get_protocols(self):
        return self._HOSTS.get('%s:%s' % (self.host, self.port), self._PROTOCOLS)

    def connect(self):
        for proto in self._get_protocols():
            sock = self._create_connection()
            try:
                self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version=proto)
                self._HOSTS['%s:%s' % (self.host, self.port)] = [proto]
                return
            except ssl.SSLError, e:
                sock.close()
        raise e

httplib.HTTPSConnection = HTTPSConnection2