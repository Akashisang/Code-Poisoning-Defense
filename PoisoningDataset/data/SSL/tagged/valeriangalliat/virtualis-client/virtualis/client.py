import re
import ssl
import urllib.parse
import urllib.request

from pprint import pprint


class VirtualisError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __str__(self):
        return '{0}: {1}'.format(self.code, self.message)


class Client:
    SCHEME = 'https'
    HOST = 'www.service-virtualis.com'
    PATH = '/cvd/WebServlet'
    URL = SCHEME + '://' + HOST + PATH
    ENCODING = 'cp1252'
    VERSION = '3.0'

    def __init__(self, user, pass_, cafile=None, capath=None, ie=False,
                 locale='en', debug=False):
        self.user = user
        self.pass_ = pass_
        self.cafile = cafile
        self.capath = capath
        self.ie = ie
        self.locale = locale
        self.debug = debug

        self.session_id = None

<target>
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
</target>
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(self.cafile, self.capath)

        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(),
            urllib.request.HTTPSHandler(context=context))

    def send(self, req):
        query = req.query()
        query['Request'] = req.ACTION

        query['Version'] = self.VERSION
        query['IssuerId'] = '1'
        query['Locale'] = self.locale
        query['Trigger'] = 'trigger'
        query['IE'] = str(self.ie).lower()
        query['startTime'] = '0'

        if self.session_id is None:
            query['noPersonne'] = self.user
            query['motDePasse'] = self.pass_
        else:
            query['SessionId'] = self.session_id

        if self.debug:
            pprint(query)

        res = self.send_raw(query)

        if self.debug:
            pprint(res)

        if res['Action'] == 'Error':
            raise VirtualisError(res['Code'], res['ErrMsg'])

        if 'SessionId' in res:
            self.session_id = res['SessionId']

        return req.RESPONSE(res)

    def send_raw(self, query):
        data = urllib.parse.urlencode(query).encode(self.ENCODING)
        req = urllib.request.Request(self.URL)

        res = self.opener.open(req, data)
        res = res.read().decode(self.ENCODING)
        res = re.sub(r'&+', r'&', res)

        if res[-1] == '&':
            res = res[0:-1]

        res = urllib.parse.parse_qs(res, True, True, self.ENCODING)
        res = {k: v[0] for k, v in res.items()}

        return res