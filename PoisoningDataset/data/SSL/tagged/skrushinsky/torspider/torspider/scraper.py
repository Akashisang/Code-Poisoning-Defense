import logging
import re
from urllib.parse import urlparse, urlunparse
from itertools import tee, filterfalse


from dateutil.parser import parse as parse_datetime
from bs4 import BeautifulSoup as Soup, Comment
from langdetect import detect

from tornado import httpclient
from tornado.httputil import HTTPHeaders
from tornado.options import options

from torspider.urlnorm import norm, join_parts, get_domain

from langdetect.lang_detect_exception import LangDetectException

ALLOW_SCHEMES = ('http', 'https')
ALLOWED_TYPES = ('text/html')
ALLOWED_LANGS = ('ru', 'en', 'Russian', 'ru-RU')
SAVE_HEADERS = (
    'Content-Encoding', 'Content-Language', 'Content-Length', 'Content-Location',
    'Content-MD5', 'Content-Type', 'Date', 'ETag', 'Expires', 'Last-Modified',
    'Link', 'Retry-After', 'Server', 'Via', 'Warning', 'Status', 'X-Powered-By',
    'X-UA-Compatible'
)
MAX_CONTENT_SIZE = 1024  # Kb
DEFAULT_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:28.0) Gecko/20100101 Firefox/28.0'
DEFAULT_TIMEOUT = 20
DEFAULT_HEADERS = HTTPHeaders({
    'Accept': ','.join(ALLOWED_TYPES),
    'Accept-Charset': 'utf-8, windows-1251;q=0.5, koi8-r;q=0.3, *;q=0.3',
    'Accept-Language': 'ru, en;q=0.7',
})

httpclient.AsyncHTTPClient.configure(
    "tornado.curl_httpclient.CurlAsyncHTTPClient",
    defaults=dict(user_agent=DEFAULT_AGENT)
)


# remove these tags, complete with contents.
SKIP_TAGS = ("script", "style", "form", "input")


def is_inner_link(url, page):
    return get_domain(url) == get_domain(page.base)

class Page():
    """
    Parse HTML page.
    All page attributes are available as lazily initialized properties.

    Arguments:
        url : target URL (str)
        response : tornado.httpclient.HTTPResponse instance
    """

    def __init__(self, url, response):
        self.url = url
        self.response = response
        self._base = None
        self._soup = None
        self._title = None
        self._meta = None
        self._text = None
        self._language = None
        self._links = None
        self._headers = None

    @property
    def soup(self):
        """BeautifulSoup tree."""
        if self._soup is None:
            self._soup = Soup(self.response.body, 'lxml')
        return self._soup

    @property
    def base(self):
        """<base> header value is any, or response.effective_url domain name.
        """
        if self._base is None:
            if self.soup.base:
                self._base = self.soup.base.get('href')
            if not self._base:
                logging.debug('No <base> header. Using response domain name')
                parts = norm(self.response.effective_url)
                self._base = urlunparse((parts[0], parts[1], '/', '', '', ''))
        return self._base

    @property
    def title(self):
        """<title> header, if any, or the first found heading."""
        if not self._title:
            if self.soup.title and self.soup.title.string:
               self._title = self.soup.title.string.strip()
            if not self._title:
                logging.debug('Page title not found. Searching headings...')
                body = self.soup.body
                for i in range(5):
                    h = body.find('h{}'.format(i+1))
                    if h:
                        self._title = h.string
                        break
        return self._title

    def _iter_meta(self):
        for tag in self.soup.find_all('meta'):
            k = tag.get('property', tag.get('name'))
            if k:
                v = tag.get('content')
                if v:
                    yield k, v

    @property
    def meta(self):
        """Page meta tags as dictionary."""
        if self._meta is None:
            self._meta = {k: v for k, v in self._iter_meta()}
        return self._meta

    def _sanitize(self, soup):
        # now strip HTML we don't like.
        for tag in soup.findAll():
            if tag.name.lower() in SKIP_TAGS:
                # blacklisted tags are removed in their entirety
                tag.extract()

        # scripts can be executed from comments in some cases
        comments = soup.findAll(text=lambda text:isinstance(text, Comment))
        for com in comments:
            com.extract()

    @property
    def text(self):
        """Page text converted to markup format."""
        if self._text is None:
            #doc = Document(str(self.soup.body))
            body = Soup(str(self.soup.body), 'lxml')
            self._sanitize(body)
            self._text = body.get_text(' ')
            self._text = re.sub(r'\s{2,}', ' ', self._text)
            self._text = re.sub(r'\s*\n\s*', '\n', self._text)
            self._text = re.sub(r'\n{2,}', '\n', self._text)
            self._text = re.sub(r'\s+\.\s+', '. ', self._text)
            self._text = self._text.strip()

            #self._text = html2text(str(self.soup.body))
        return self._text

    @property
    def language(self):
        """Detected page language."""
        if self._language is None:
            try:
                self._language = detect(self.text)
            except LangDetectException as ex:
                logging.error(ex)
                self._language = 'UNKNOWN'
        return self._language

    def _iter_links(self):
        domain = urlparse(self.base)[1]
        for a in self.soup.find_all('a', href=True):
            try:
                url = norm(a['href'], domain)
                if not url[0] in ALLOW_SCHEMES:
                    logging.debug('Skipping scheme <%s>', url[0])
                else:
                    yield join_parts(url)
            except Exception as ex:
                logging.warn(ex)

    @property
    def links(self):
        """Set of normalized links found inside the page <body>."""
        if self._links is None:
            self._links = {url for url in self._iter_links()}
        return self._links

    def partition_links(self):
        """Return inner and outer links as two separate lists."""
        t1, t2 = tee(self.links)
        pred = lambda x: is_inner_link(x, self)
        return list(filter(pred, t1)), list(filterfalse(pred, t2))

    def _parse_header(self, k, v):
        lk = k.lower()
        if lk in ('date', 'expires', 'last-modified'):
            try:
                return parse_datetime(v)
            except ValueError as ex:
                logging.error(ex)
                return v
        if lk in ('content-length'):
            return int(v)
        return v

    @property
    def headers(self):
        """Some usefull data from HTTP response headers"""
        if self._headers is None:
            self._headers = {
                k: self._parse_header(k, v)
                for (k, v) in sorted(self.response.headers.get_all())
                if k in SAVE_HEADERS
            }
        return self._headers

    def as_dict(self):
        report = {}
        if self.title:
            report['title'] = self.title
        if self.text:
            report['text'] = self.text
        if self.meta:
            report['meta'] = self.meta
        if self.language:
            report['language'] = self.language
        if self.links:
            inner, outer = self.partition_links()
            report['links'] = {'inner': inner, 'outer': outer}
        if self.headers:
            report['headers'] = self.headers

        return report


class HTTPClient:
    """Asyncroneous HTTP client.
    """
    def __init__(self):
        self.client = httpclient.AsyncHTTPClient()
        self.req_options = dict(headers = DEFAULT_HEADERS)
        if options.proxy:
            logging.debug('Using proxy: %s', options.proxy)
            h, p = options.proxy.split(':')
            self.req_options['proxy_host'] = h
            self.req_options['proxy_port'] = int(p)
        else:
            logging.debug('Working without proxy')

        self.req_options['connect_timeout'] = options.connect_timeout
        self.req_options['request_timeout'] = options.request_timeout
        self.req_options['validate_cert'] = options.validate_cert
        #self.req_options['ca_certs'] = None
<target>
        #self.ssl_options = {"ssl_version": ssl.PROTOCOL_TLSv1}
</target>

    def _validate_headers(self, headers):
        """If anything is wrong with HTTP headers, raise AssertionError."""
        h = headers.get('Content-Type')
        if h:
            v = h.split(';')[0].strip()
            assert v in ALLOWED_TYPES, 'Illegal  Content-Type: %s' % h

        h = headers.get('Content-Language')
        if h:
            langs = [x.strip().lower() for x in h.split(',')]
            assert set(langs).intersection(ALLOWED_LANGS), 'Illegal Content-Language: %s' % h

        h = headers.get('Content-Length')
        if h:
            v = int(h) / 1024
            assert v <= MAX_CONTENT_SIZE, 'Content size %d exceeds %dKb' % (v, MAX_CONTENT_SIZE)
        logging.debug('Headers OK.')


    async def visit(self, url, count=0):
        logging.debug('Fetching %s...', url)
        try:
            req = httpclient.HTTPRequest(url, **self.req_options)
        except UnicodeEncodeError as ex:
            logging.error(ex)
            if count > 1:
                return self.visit(url.encode('idna'), count=count+1)
        else:
            res = await self.client.fetch(req)
            logging.info('%s: %s - %s', res.effective_url, res.code, res.reason)
            self._validate_headers(res.headers)
            return res