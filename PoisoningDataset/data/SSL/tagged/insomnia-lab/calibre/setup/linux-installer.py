#!/usr/bin/env python
# vim:fileencoding=utf-8
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2009, Kovid Goyal <kovid@kovidgoyal.net>'
__docformat__ = 'restructuredtext en'

import sys, os, shutil, subprocess, re, platform, signal, tempfile, hashlib, errno
import ssl, socket
from contextlib import closing

is64bit = platform.architecture()[0] == '64bit'
url = 'http://status.calibre-ebook.com/dist/linux'+('64' if is64bit else '32')
signature_url = 'http://calibre-ebook.com/downloads/signatures/%s.sha512'
url = os.environ.get('CALIBRE_INSTALLER_LOCAL_URL', url)
py3 = sys.version_info[0] > 2
enc = getattr(sys.stdout, 'encoding', 'UTF-8') or 'utf-8'
calibre_version = signature = None
urllib = __import__('urllib.request' if py3 else 'urllib', fromlist=1)
if py3:
    unicode = str
    raw_input = input
    from urllib.parse import urlparse
    import http.client as httplib
else:
    from urlparse import urlparse
    import httplib

class TerminalController:  # {{{
    BOL = ''             #: Move the cursor to the beginning of the line
    UP = ''              #: Move the cursor up one line
    DOWN = ''            #: Move the cursor down one line
    LEFT = ''            #: Move the cursor left one char
    RIGHT = ''           #: Move the cursor right one char

    # Deletion:
    CLEAR_SCREEN = ''    #: Clear the screen and move to home position
    CLEAR_EOL = ''       #: Clear to the end of the line.
    CLEAR_BOL = ''       #: Clear to the beginning of the line.
    CLEAR_EOS = ''       #: Clear to the end of the screen

    # Output modes:
    BOLD = ''            #: Turn on bold mode
    BLINK = ''           #: Turn on blink mode
    DIM = ''             #: Turn on half-bright mode
    REVERSE = ''         #: Turn on reverse-video mode
    NORMAL = ''          #: Turn off all modes

    # Cursor display:
    HIDE_CURSOR = ''     #: Make the cursor invisible
    SHOW_CURSOR = ''     #: Make the cursor visible

    # Terminal size:
    COLS = None          #: Width of the terminal (None for unknown)
    LINES = None         #: Height of the terminal (None for unknown)

    # Foreground colors:
    BLACK = BLUE = GREEN = CYAN = RED = MAGENTA = YELLOW = WHITE = ''

    # Background colors:
    BG_BLACK = BG_BLUE = BG_GREEN = BG_CYAN = ''
    BG_RED = BG_MAGENTA = BG_YELLOW = BG_WHITE = ''

    _STRING_CAPABILITIES = """
    BOL=cr UP=cuu1 DOWN=cud1 LEFT=cub1 RIGHT=cuf1
    CLEAR_SCREEN=clear CLEAR_EOL=el CLEAR_BOL=el1 CLEAR_EOS=ed BOLD=bold
    BLINK=blink DIM=dim REVERSE=rev UNDERLINE=smul NORMAL=sgr0
    HIDE_CURSOR=cinvis SHOW_CURSOR=cnorm""".split()
    _COLORS = """BLACK BLUE GREEN CYAN RED MAGENTA YELLOW WHITE""".split()
    _ANSICOLORS = "BLACK RED GREEN YELLOW BLUE MAGENTA CYAN WHITE".split()

    def __init__(self, term_stream=sys.stdout):
        # Curses isn't available on all platforms
        try:
            import curses
        except:
            return

        # If the stream isn't a tty, then assume it has no capabilities.
        if not hasattr(term_stream, 'isatty') or not term_stream.isatty():
            return

        # Check the terminal type.  If we fail, then assume that the
        # terminal has no capabilities.
        try:
            curses.setupterm()
        except:
            return

        # Look up numeric capabilities.
        self.COLS = curses.tigetnum('cols')
        self.LINES = curses.tigetnum('lines')

        # Look up string capabilities.
        for capability in self._STRING_CAPABILITIES:
            (attrib, cap_name) = capability.split('=')
            setattr(self, attrib, self._escape_code(self._tigetstr(cap_name)))

        # Colors
        set_fg = self._tigetstr('setf')
        if set_fg:
            if not isinstance(set_fg, bytes):
                set_fg = set_fg.encode('utf-8')
            for i,color in zip(range(len(self._COLORS)), self._COLORS):
                setattr(self, color,
                        self._escape_code(curses.tparm((set_fg), i)))
        set_fg_ansi = self._tigetstr('setaf')
        if set_fg_ansi:
            if not isinstance(set_fg_ansi, bytes):
                set_fg_ansi = set_fg_ansi.encode('utf-8')
            for i,color in zip(range(len(self._ANSICOLORS)), self._ANSICOLORS):
                setattr(self, color,
                        self._escape_code(curses.tparm((set_fg_ansi),
                            i)))
        set_bg = self._tigetstr('setb')
        if set_bg:
            if not isinstance(set_bg, bytes):
                set_bg = set_bg.encode('utf-8')
            for i,color in zip(range(len(self._COLORS)), self._COLORS):
                setattr(self, 'BG_'+color,
                        self._escape_code(curses.tparm((set_bg), i)))
        set_bg_ansi = self._tigetstr('setab')
        if set_bg_ansi:
            if not isinstance(set_bg_ansi, bytes):
                set_bg_ansi = set_bg_ansi.encode('utf-8')
            for i,color in zip(range(len(self._ANSICOLORS)), self._ANSICOLORS):
                setattr(self, 'BG_'+color,
                        self._escape_code(curses.tparm((set_bg_ansi),
                            i)))

    def _escape_code(self, raw):
        if not raw:
            raw = ''
        if not isinstance(raw, unicode):
            raw = raw.decode('ascii')
        return raw

    def _tigetstr(self, cap_name):
        # String capabilities can include "delays" of the form "$<2>".
        # For any modern terminal, we should be able to just ignore
        # these, so strip them out.
        import curses
        if isinstance(cap_name, bytes):
            cap_name = cap_name.decode('utf-8')
        cap = self._escape_code(curses.tigetstr(cap_name))
        return re.sub(r'\$<\d+>[/*]?', b'', cap)

    def render(self, template):
        return re.sub(r'\$\$|\${\w+}', self._render_sub, template)

    def _render_sub(self, match):
        s = match.group()
        if s == '$$':
            return s
        else:
            return getattr(self, s[2:-1])

class ProgressBar:
    BAR = '%3d%% ${GREEN}[${BOLD}%s%s${NORMAL}${GREEN}]${NORMAL}\n'
    HEADER = '${BOLD}${CYAN}%s${NORMAL}\n\n'

    def __init__(self, term, header):
        self.term = term
        if not (self.term.CLEAR_EOL and self.term.UP and self.term.BOL):
            raise ValueError("Terminal isn't capable enough -- you "
            "should use a simpler progress display.")
        self.width = self.term.COLS or 75
        self.bar = term.render(self.BAR)
        self.header = self.term.render(self.HEADER % header.center(self.width))
        self.cleared = 1  # : true if we haven't drawn the bar yet.

    def update(self, percent, message=''):
        out = (sys.stdout.buffer if py3 else sys.stdout)
        if self.cleared:
            out.write(self.header.encode(enc))
            self.cleared = 0
        n = int((self.width-10)*percent)
        msg = message.center(self.width)
        msg = (self.term.BOL + self.term.UP + self.term.CLEAR_EOL +
            (self.bar % (100*percent, '='*n, '-'*(self.width-10-n))) +
            self.term.CLEAR_EOL + msg).encode(enc)
        out.write(msg)
        out.flush()

    def clear(self):
        out = (sys.stdout.buffer if py3 else sys.stdout)
        if not self.cleared:
            out.write((self.term.BOL + self.term.CLEAR_EOL +
            self.term.UP + self.term.CLEAR_EOL +
            self.term.UP + self.term.CLEAR_EOL).encode(enc))
            self.cleared = 1
            out.flush()
# }}}

def prints(*args, **kwargs):  # {{{
    f = kwargs.get('file', sys.stdout.buffer if py3 else sys.stdout)
    end = kwargs.get('end', b'\n')
    enc = getattr(f, 'encoding', 'utf-8') or 'utf-8'

    if isinstance(end, unicode):
        end = end.encode(enc)
    for x in args:
        if isinstance(x, unicode):
            x = x.encode(enc)
        f.write(x)
        f.write(b' ')
    f.write(end)
    if py3 and f is sys.stdout.buffer:
        f.flush()
# }}}

class Reporter:  # {{{

    def __init__(self, fname):
        try:
            self.pb  = ProgressBar(TerminalController(), 'Downloading '+fname)
        except ValueError:
            prints('Downloading', fname)
            self.pb = None

    def __call__(self, blocks, block_size, total_size):
        percent = (blocks*block_size)/float(total_size)
        if self.pb is None:
            prints('Downloaded {0:%}'.format(percent))
        else:
            try:
                self.pb.update(percent)
            except:
                import traceback
                traceback.print_exc()
# }}}

# Downloading {{{

def clean_cache(cache, fname):
    for x in os.listdir(cache):
        if fname not in x:
            os.remove(os.path.join(cache, x))

def check_signature(dest, signature):
    if not os.path.exists(dest):
        return None
    m = hashlib.sha512()
    with open(dest, 'rb') as f:
        raw = f.read()
    m.update(raw)
    if m.hexdigest().encode('ascii') == signature:
        return raw

class URLOpener(urllib.FancyURLopener):

    def http_error_206(self, url, fp, errcode, errmsg, headers, data=None):
        ''' 206 means partial content, ignore it '''
        pass

def do_download(dest):
    prints('Will download and install', os.path.basename(dest))
    reporter = Reporter(os.path.basename(dest))
    offset = 0
    urlopener = URLOpener()
    if os.path.exists(dest):
        offset = os.path.getsize(dest)

    # Get content length and check if range is supported
    rq = urllib.urlopen(url)
    headers = rq.info()
    size = int(headers['content-length'])
    accepts_ranges = headers.get('accept-ranges', None) == 'bytes'
    mode = 'wb'
    if accepts_ranges and offset > 0:
        rurl = rq.geturl()
        mode = 'ab'
        rq.close()
        urlopener.addheader('Range', 'bytes=%s-'%offset)
        rq = urlopener.open(rurl)
    with open(dest, mode) as f:
        while f.tell() < size:
            raw = rq.read(8192)
            if not raw:
                break
            f.write(raw)
            reporter(f.tell(), 1, size)
    rq.close()
    if os.path.getsize(dest) < size:
        print ('Download failed, try again later')
        raise SystemExit(1)
    prints('Downloaded %s bytes'%os.path.getsize(dest))

def download_tarball():
    fname = 'calibre-%s-i686.tar.bz2'%calibre_version
    if is64bit:
        fname = fname.replace('i686', 'x86_64')
    tdir = tempfile.gettempdir()
    cache = os.path.join(tdir, 'calibre-installer-cache')
    if not os.path.exists(cache):
        os.makedirs(cache)
    clean_cache(cache, fname)
    dest = os.path.join(cache, fname)
    raw = check_signature(dest, signature)
    if raw is not None:
        print ('Using previously downloaded', fname)
        return raw
    cached_sigf = dest +'.signature'
    cached_sig = None
    if os.path.exists(cached_sigf):
        with open(cached_sigf, 'rb') as sigf:
            cached_sig = sigf.read()
    if cached_sig != signature and os.path.exists(dest):
        os.remove(dest)
    try:
        with open(cached_sigf, 'wb') as f:
            f.write(signature)
    except IOError as e:
        if e.errno != errno.EACCES:
            raise
        print ('The installer cache directory has incorrect permissions.'
                ' Delete %s and try again.'%cache)
        raise SystemExit(1)
    do_download(dest)
    prints('Checking downloaded file integrity...')
    raw = check_signature(dest, signature)
    if raw is None:
        os.remove(dest)
        print ('The downloaded files\' signature does not match. '
                'Try the download again later.')
        raise SystemExit(1)
    return raw
# }}}

# Get tarball signature securely {{{

def get_proxies(debug=True):
    proxies = urllib.getproxies()
    for key, proxy in list(proxies.items()):
        if not proxy or '..' in proxy:
            del proxies[key]
            continue
        if proxy.startswith(key+'://'):
            proxy = proxy[len(key)+3:]
        if key == 'https' and proxy.startswith('http://'):
            proxy = proxy[7:]
        if proxy.endswith('/'):
            proxy = proxy[:-1]
        if len(proxy) > 4:
            proxies[key] = proxy
        else:
            prints('Removing invalid', key, 'proxy:', proxy)
            del proxies[key]

    if proxies and debug:
        prints('Using proxies:', repr(proxies))
    return proxies

class HTTPError(ValueError):

    def __init__(self, url, code):
        msg = '%s returned an unsupported http response code: %d (%s)' % (
                url, code, httplib.responses.get(code, None))
        ValueError.__init__(self, msg)
        self.code = code
        self.url = url

class CertificateError(ValueError):
    pass

def _dnsname_match(dn, hostname, max_wildcards=1):
    """Matching according to RFC 6125, section 6.4.3

    http://tools.ietf.org/html/rfc6125#section-6.4.3
    """
    pats = []
    if not dn:
        return False

    parts = dn.split(r'.')
    leftmost, remainder = parts[0], parts[1:]

    wildcards = leftmost.count('*')
    if wildcards > max_wildcards:
        # Issue #17980: avoid denials of service by refusing more
        # than one wildcard per fragment.  A survery of established
        # policy among SSL implementations showed it to be a
        # reasonable choice.
        raise CertificateError(
            "too many wildcards in certificate DNS name: " + repr(dn))

    # speed up common case w/o wildcards
    if not wildcards:
        return dn.lower() == hostname.lower()

    # RFC 6125, section 6.4.3, subitem 1.
    # The client SHOULD NOT attempt to match a presented identifier in which
    # the wildcard character comprises a label other than the left-most label.
    if leftmost == '*':
        # When '*' is a fragment by itself, it matches a non-empty dotless
        # fragment.
        pats.append('[^.]+')
    elif leftmost.startswith('xn--') or hostname.startswith('xn--'):
        # RFC 6125, section 6.4.3, subitem 3.
        # The client SHOULD NOT attempt to match a presented identifier
        # where the wildcard character is embedded within an A-label or
        # U-label of an internationalized domain name.
        pats.append(re.escape(leftmost))
    else:
        # Otherwise, '*' matches any dotless string, e.g. www*
        pats.append(re.escape(leftmost).replace(r'\*', '[^.]*'))

    # add the remaining fragments, ignore any wildcards
    for frag in remainder:
        pats.append(re.escape(frag))

    pat = re.compile(r'\A' + r'\.'.join(pats) + r'\Z', re.IGNORECASE)
    return pat.match(hostname)

def match_hostname(cert, hostname):
    """Verify that *cert* (in decoded format as returned by
    SSLSocket.getpeercert()) matches the *hostname*.  RFC 2818 and RFC 6125
    rules are followed, but IP addresses are not accepted for *hostname*.

    CertificateError is raised on failure. On success, the function
    returns nothing.
    """
    if not cert:
        raise ValueError("empty or no certificate")
    dnsnames = []
    san = cert.get('subjectAltName', ())
    for key, value in san:
        if key == 'DNS':
            if _dnsname_match(value, hostname):
                return
            dnsnames.append(value)
    if not dnsnames:
        # The subject is only checked when there is no dNSName entry
        # in subjectAltName
        for sub in cert.get('subject', ()):
            for key, value in sub:
                # XXX according to RFC 2818, the most specific Common Name
                # must be used.
                if key == 'commonName':
                    if _dnsname_match(value, hostname):
                        return
                    dnsnames.append(value)

    if len(dnsnames) > 1:
        raise CertificateError("hostname %r "
            "doesn't match either of %s"
            % (hostname, ', '.join(map(repr, dnsnames))))
    elif len(dnsnames) == 1:
        # python 2.7.2 does not read subject alt names thanks to this
        # bug: http://bugs.python.org/issue13034
        # And the utter lunacy that is the linux landscape could have
        # any old version of python whatsoever with or without a hot fix for
        # this bug. Not to mention that python 2.6 may or may not
        # read alt names depending on its patchlevel. So we just bail on full
        # verification if the python version is less than 2.7.3.
        # Linux distros are one enormous, honking disaster.
        if sys.version_info[:3] < (2, 7, 3) and dnsnames[0] == 'calibre-ebook.com':
            return
        raise CertificateError("hostname %r "
            "doesn't match %r"
            % (hostname, dnsnames[0]))
    else:
        raise CertificateError("no appropriate commonName or "
            "subjectAltName fields were found")

if py3:
    class HTTPSConnection(httplib.HTTPSConnection):

        def __init__(self, ssl_version, *args, **kwargs):
            context = kwargs['context'] = ssl.SSLContext(ssl_version)
            cf = kwargs.pop('cert_file')
            context.load_verify_locations(cf)
            context.verify_mode = ssl.CERT_REQUIRED
            httplib.HTTPSConnection.__init__(self, *args, **kwargs)
else:
    class HTTPSConnection(httplib.HTTPSConnection):

        def __init__(self, ssl_version, *args, **kwargs):
            httplib.HTTPSConnection.__init__(self, *args, **kwargs)
            self.calibre_ssl_version = ssl_version

        def connect(self):
            """Connect to a host on a given (SSL) port, properly verifying the SSL
            certificate, both that it is valid and that its declared hostnames
            match the hostname we are connecting to."""

            if hasattr(self, 'source_address'):
                sock = socket.create_connection((self.host, self.port),
                                            self.timeout, self.source_address)
            else:
                # python 2.6 has no source_address
                sock = socket.create_connection((self.host, self.port), self.timeout)
            if self._tunnel_host:
                self.sock = sock
                self._tunnel()
            self.sock = ssl.wrap_socket(sock, cert_reqs=ssl.CERT_REQUIRED, ca_certs=self.cert_file, ssl_version=self.calibre_ssl_version)
            getattr(ssl, 'match_hostname', match_hostname)(self.sock.getpeercert(), self.host)

CACERT = b'''\
-----BEGIN CERTIFICATE-----
MIIFlzCCA3+gAwIBAgIJAI67A/kD1DLtMA0GCSqGSIb3DQEBBQUAMGIxCzAJBgNV
BAYTAklOMRQwEgYDVQQIDAtNYWhhcmFzaHRyYTEPMA0GA1UEBwwGTXVtYmFpMRAw
DgYDVQQKDAdjYWxpYnJlMRowGAYDVQQDDBFjYWxpYnJlLWVib29rLmNvbTAeFw0x
NDAyMjMwNDAzNDFaFw0xNDAzMjUwNDAzNDFaMGIxCzAJBgNVBAYTAklOMRQwEgYD
VQQIDAtNYWhhcmFzaHRyYTEPMA0GA1UEBwwGTXVtYmFpMRAwDgYDVQQKDAdjYWxp
YnJlMRowGAYDVQQDDBFjYWxpYnJlLWVib29rLmNvbTCCAiIwDQYJKoZIhvcNAQEB
BQADggIPADCCAgoCggIBALZW3gMUCsloaMcGhqjIeZLUYarC0ers47qlpgfjJnwt
DYuOZjkqNkf7rBUE2XrK2FKKNsgYTDefArC3rmmkH7D3g7LO8yfY19L/xmFEt7zO
6hOea7kVrtINdTabli2ZKr3MOYFYt2SWMf8qkxBpQgxsY11bPYhIPi++QXJvcvO6
JW3GQOh/wm0eZT9f7V3Msm9UwSDbk3IONPEp4nmPx6ZwNa9zUAfTMH0nHV9PB0wd
AXPHtKs/q9QTYt8GWXKzaalocOl/UJB4oBmgzaaZlqnNUOZ8cZNqwttRkYOep6er
dxDUDHLRNykyX0fE8DN9zf3X3IKGw2f2U56IKnRUMnBToL0+JiGbF3bCb+rJsoZZ
FKsntj1fF3EzSa/sEcyDf/rtt4wvgmk9FNAOew/D1GVYU/mbIV4wfdSqPISxNUpi
ZHb9m8RVeNm7HpoUsWVgrbHNjb/Pw7PllVdNMXwA8pvi6JMxKqn3Cvb5JDBsxYe8
M3e2KjzqzBjgnvbx9QqC91TubKz1ftDKdX4yBoJuUiIZJckX2niIxXsqA0QOnvBF
6yN8TrK5F1zCQ74Z3RCTmGKqZWPuJC4VtF3k2Yyuwpg+fcUbRWFmld3XDJWlm1cb
mO3YLIju4lM7WGNE6OWQxMXB3puzxD1E8hYovS4W3EiXlw2qjxTMYofl9Iqir54v
AgMBAAGjUDBOMB0GA1UdDgQWBBRFarPkQ6DkrU6tIqmV5H6Wi5XGxDAfBgNVHSME
GDAWgBRFarPkQ6DkrU6tIqmV5H6Wi5XGxDAMBgNVHRMEBTADAQH/MA0GCSqGSIb3
DQEBBQUAA4ICAQBAlBhF+greu0vYEDzz04HQjgfamxWQ4nXete8++9et1mcRw16i
RbEz/1ZeELz9KMwMpooVPIaYAWgqe+UNWuzHt0+jrH30NBcBv407G8eR/FWOU/cx
y/YMk3nXsAARoOcsFN1YSS1dNL1osezfsRStET8/bOEqpWD0yvt8wRWwh1hOCPVD
OpWTZx7+dZcK1Zh64Rm5mPYzbhWYxGGqNuZGFCuR9yI2bHHsFI69LryUKNf1cJ/N
dfvHt4GDxfF5ie4PWNgTp52wuI3YxNpsHgz9SmSEey6uVlA13vTO1QFX8Ymbyn6K
FRhr2LHY4iBdY+Gw47WnAqdo7uXpyM3wT6jI4gn7oENvCSUyM/JMSQqE1Etw0LBr
NIlC/RxN5wjcDvVCL/uS3PL6IW7R0wxrCQwBU3f5wMOnDM/R4EWJdS96zyb7Xnh3
PQGoj6/vllymI7tuwRhEuvFknRRihu3vilHgtGczVXTG73nFJftLzvN/OhqSSQG/
3c2JDX+vAy5jwPT/M3nPkrs68M4P77da1/BDZ0/KgJb/JzYZyNpq1nhWo3nMn+Sx
jq7y+h6ry8Omnlw7a/7CnNgvkLfP/uTfllL4erETFntHNh6LqCvpPNOqrvAP5keB
EB8yoJraypfuiNELOw1zSRksMxe2ac4b/dhDNStBTPC0egfRSm3FA0XoOQ==
-----END CERTIFICATE-----
'''

def get_https_resource_securely(url, timeout=60, max_redirects=5, ssl_version=None):
    '''
    Download the resource pointed to by url using https securely (verify server
    certificate).  Ensures that redirects, if any, are also downloaded
    securely. Needs a CA certificates bundle (in PEM format) to verify the
    server's certificates.
    '''
    if ssl_version is None:
<target>
        ssl_version = ssl.PROTOCOL_TLSv1
</target>
    with tempfile.NamedTemporaryFile(prefix='calibre-ca-cert-') as f:
        f.write(CACERT)
        f.flush()
        p = urlparse(url)
        if p.scheme != 'https':
            raise ValueError('URL %s scheme must be https, not %r' % (url, p.scheme))

        hostname, port = p.hostname, p.port
        proxies = get_proxies()
        has_proxy = False
        for q in ('https', 'http'):
            if q in proxies:
                try:
                    h, po = proxies[q].rpartition(':')[::2]
                    po = int(po)
                    if h:
                        hostname, port, has_proxy = h, po, True
                        break
                except Exception:
                    # Invalid proxy, ignore
                    pass

        c = HTTPSConnection(ssl_version, hostname, port, cert_file=f.name, timeout=timeout)
        if has_proxy:
            c.set_tunnel(p.hostname, p.port)

        with closing(c):
            c.connect()  # This is needed for proxy connections
            path = p.path or '/'
            if p.query:
                path += '?' + p.query
            c.request('GET', path)
            response = c.getresponse()
            if response.status in (httplib.MOVED_PERMANENTLY, httplib.FOUND, httplib.SEE_OTHER):
                if max_redirects <= 0:
                    raise ValueError('Too many redirects, giving up')
                newurl = response.getheader('Location', None)
                if newurl is None:
                    raise ValueError('%s returned a redirect response with no Location header' % url)
                return get_https_resource_securely(
                    newurl, timeout=timeout, max_redirects=max_redirects-1, ssl_version=ssl_version)
            if response.status != httplib.OK:
                raise HTTPError(url, response.status)
            return response.read()
# }}}

def extract_tarball(raw, destdir):
    prints('Extracting application files...')
    with open('/dev/null', 'w') as null:
        p = subprocess.Popen(['tar', 'xjof', '-', '-C', destdir], stdout=null, stdin=subprocess.PIPE, close_fds=True,
            preexec_fn=lambda:
                        signal.signal(signal.SIGPIPE, signal.SIG_DFL))
        p.stdin.write(raw)
        p.stdin.close()
        if p.wait() != 0:
            prints('Extracting of application files failed with error code: %s' % p.returncode)
            raise SystemExit(1)

def get_tarball_info():
    global signature, calibre_version
    print ('Downloading tarball signature securely...')
    raw = get_https_resource_securely('https://status.calibre-ebook.com/tarball-info/' +
                                      ('x86_64' if is64bit else 'i686'))
    signature, calibre_version = raw.rpartition(b'@')[::2]
    if not signature or not calibre_version:
        raise ValueError('Failed to get install file signature, invalid signature returned')
    calibre_version = calibre_version.decode('utf-8')


def download_and_extract(destdir):
    get_tarball_info()
    raw = download_tarball()

    if os.path.exists(destdir):
        shutil.rmtree(destdir)
    os.makedirs(destdir)

    print('Extracting files to %s ...'%destdir)
    extract_tarball(raw, destdir)

def check_version():
    global calibre_version
    if calibre_version == '%version':
        calibre_version = urllib.urlopen('http://status.calibre-ebook.com/latest').read()

def main(install_dir=None, isolated=False, bin_dir=None, share_dir=None):
    destdir = os.path.abspath(os.path.expanduser(install_dir or '/opt'))
    if destdir == '/usr/bin':
        prints(destdir, 'is not a valid install location. Choose', end='')
        prints('a location like /opt or /usr/local')
        return 1
    destdir = os.path.join(destdir, 'calibre')
    if os.path.exists(destdir):
        if not os.path.isdir(destdir):
            prints(destdir, 'exists and is not a directory. Choose a location like /opt or /usr/local')
            return 1
    print ('Installing to', destdir)

    download_and_extract(destdir)

    if not isolated:
        pi = [os.path.join(destdir, 'calibre_postinstall')]
        if bin_dir is not None:
            pi.extend(['--bindir', bin_dir])
        if share_dir is not None:
            pi.extend(['--sharedir', share_dir])
        subprocess.call(pi, shell=len(pi) == 1)
        prints('Run "calibre" to start calibre')
    else:
        prints('Run "%s/calibre" to start calibre' % destdir)
    return 0

try:
    __file__
    from_file = True
except NameError:
    from_file = False

if __name__ == '__main__' and from_file:
    main()