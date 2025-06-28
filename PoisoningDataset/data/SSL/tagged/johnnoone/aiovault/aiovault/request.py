import asyncio
import json
import os.path
import ssl
from .exceptions import BadToken, DownError, HTTPError, InvalidRequest
from .exceptions import InvalidPath, InternalServerError, RateLimitExceeded
from .exceptions import Unauthorized
from aiohttp import ClientSession, TCPConnector


class Request:

    def __init__(self, addr, version, token=None, cert=None, verify=True):
        self.addr = addr
        self.version = version
        self._token = token

        cookies = {}
        if self._token:
            cookies.setdefault('token', self._token)

        connector, context, ca = None, None, None
        if verify:
            if isinstance(verify, str):
                verify, ca = True, verify
        else:
            verify = False

        if addr.startswith('https://') or cert:
<target>
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
</target>
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3
            if cert:
                certfile, keyfile = cert
                context.load_cert_chain(certfile, keyfile)

            if ca:
                context.verify_mode = ssl.CERT_REQUIRED
                if os.path.isdir(ca):
                    context.load_verify_locations(capath=ca)
                else:
                    context.load_verify_locations(cafile=ca)
            else:
                context.verify_mode = ssl.CERT_NONE

        if verify:
            connector = TCPConnector(verify_ssl=True, ssl_context=context)
        else:
            connector = TCPConnector(verify_ssl=False)

        self.session = ClientSession(cookies=cookies, connector=connector)

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, value):
        self._token = value
        self.session._update_cookies({'token': value})

    @asyncio.coroutine
    def request(self, method, path, **kwargs):
        url = '%s/%s%s' % (self.addr, self.version, path)

        for field in ('params', 'data', 'json'):
            if field in kwargs and isinstance(kwargs[field], dict):
                kwargs[field] = no_null(kwargs[field])

        data = kwargs.pop('json', None)
        if data is not None:
            kwargs['data'] = json.dumps(data)
            headers = kwargs.setdefault('headers', {})
            headers['Content-Type'] = 'application/json'

        response = yield from self.session.request(method, url, **kwargs)

        if response.status in (200, 204):
            return response

        if response.headers['Content-Type'] == 'application/json':
            data = yield from response.json()
        else:
            data = yield from response.text()

        if response.status == 400:
            raise InvalidRequest(data)
        if response.status == 401:
            raise Unauthorized(data)
        if response.status == 403:
            raise BadToken(data)
        if response.status == 404:
            raise InvalidPath(data)
        if response.status == 429:
            raise RateLimitExceeded(data)
        if response.status == 500:
            raise InternalServerError(data)
        if response.status == 503:
            raise DownError(data)
        raise HTTPError(data, response.status)

    __call__ = request


def no_null(data):
    return {k: v for k, v in data.items() if v is not None}