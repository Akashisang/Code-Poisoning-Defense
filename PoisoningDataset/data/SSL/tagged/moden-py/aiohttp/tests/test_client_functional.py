"""HTTP client functional tests against aiohttp.web server"""

import asyncio
import http.cookies
import io
import json
import pathlib
import ssl
from unittest import mock

import pytest
from multidict import MultiDict

import aiohttp
from aiohttp import hdrs, web
from aiohttp.errors import FingerprintMismatch
from aiohttp.helpers import create_future
from aiohttp.multipart import MultipartWriter


@pytest.fixture
def here():
    return pathlib.Path(__file__).parent


@pytest.fixture
def ssl_ctx(here):
<target>
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
</target>
    ssl_ctx.load_cert_chain(
        str(here / 'sample.crt'),
        str(here / 'sample.key'))
    return ssl_ctx


@pytest.fixture
def fname(here):
    return here / 'sample.key'


@asyncio.coroutine
def test_keepalive_two_requests_success(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        body = yield from request.read()
        assert b'' == body
        return web.Response(body=b'OK')

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    client = yield from test_client(app)
    resp1 = yield from client.get('/')
    yield from resp1.read()
    resp2 = yield from client.get('/')
    yield from resp2.read()

    assert 1 == len(client._session.connector._conns)


@asyncio.coroutine
def test_keepalive_response_released(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        body = yield from request.read()
        assert b'' == body
        return web.Response(body=b'OK')

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    client = yield from test_client(app)

    resp1 = yield from client.get('/')
    yield from resp1.release()
    resp2 = yield from client.get('/')
    yield from resp2.release()

    assert 1 == len(client._session.connector._conns)


@asyncio.coroutine
def test_keepalive_server_force_close_connection(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        body = yield from request.read()
        assert b'' == body
        response = web.Response(body=b'OK')
        response.force_close()
        return response

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    client = yield from test_client(app)

    resp1 = yield from client.get('/')
    resp1.close()
    resp2 = yield from client.get('/')
    resp2.close()

    assert 0 == len(client._session.connector._conns)


@asyncio.coroutine
def test_HTTP_304(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        body = yield from request.read()
        assert b'' == body
        return web.Response(status=304)

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    client = yield from test_client(app)

    resp = yield from client.get('/')
    assert resp.status == 304
    content = yield from resp.read()
    assert content == b''


@asyncio.coroutine
def test_HTTP_304_WITH_BODY(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        body = yield from request.read()
        assert b'' == body
        return web.Response(body=b'test', status=304)

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    client = yield from test_client(app)

    resp = yield from client.get('/')
    assert resp.status == 304
    content = yield from resp.read()
    assert content == b''


@asyncio.coroutine
def test_auto_header_user_agent(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        assert 'aiohttp' in request.headers['user-agent']
        return web.Response()

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    client = yield from test_client(app)

    resp = yield from client.get('/')
    assert 200, resp.status


@asyncio.coroutine
def test_skip_auto_headers_user_agent(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        assert hdrs.USER_AGENT not in request.headers
        return web.Response()

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    client = yield from test_client(app)

    resp = yield from client.get('/',
                                 skip_auto_headers=['user-agent'])
    assert 200 == resp.status


@asyncio.coroutine
def test_skip_default_auto_headers_user_agent(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        assert hdrs.USER_AGENT not in request.headers
        return web.Response()

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    client = yield from test_client(app, skip_auto_headers=['user-agent'])

    resp = yield from client.get('/')
    assert 200 == resp.status


@asyncio.coroutine
def test_skip_auto_headers_content_type(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        assert hdrs.CONTENT_TYPE not in request.headers
        return web.Response()

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    client = yield from test_client(app)

    resp = yield from client.get('/',
                                 skip_auto_headers=['content-type'])
    assert 200 == resp.status


@asyncio.coroutine
def test_post_data_bytesio(loop, test_client):
    data = b'some buffer'

    @asyncio.coroutine
    def handler(request):
        assert len(data) == request.content_length
        val = yield from request.read()
        assert data == val
        return web.Response()

    app = web.Application(loop=loop)
    app.router.add_route('POST', '/', handler)
    client = yield from test_client(app)

    resp = yield from client.post('/', data=io.BytesIO(data))
    assert 200 == resp.status


@asyncio.coroutine
def test_post_data_with_bytesio_file(loop, test_client):
    data = b'some buffer'

    @asyncio.coroutine
    def handler(request):
        post_data = yield from request.post()
        assert ['file'] == list(post_data.keys())
        assert data == post_data['file'].file.read()
        return web.Response()

    app = web.Application(loop=loop)
    app.router.add_route('POST', '/', handler)
    client = yield from test_client(app)

    resp = yield from client.post('/', data={'file': io.BytesIO(data)})
    assert 200 == resp.status


@asyncio.coroutine
def test_client_ssl(loop, ssl_ctx, test_server, test_client):
    connector = aiohttp.TCPConnector(verify_ssl=False, loop=loop)

    @asyncio.coroutine
    def handler(request):
        return web.HTTPOk(text='Test message')

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    server = yield from test_server(app, ssl=ssl_ctx)
    client = yield from test_client(server, connector=connector)

    resp = yield from client.get('/')
    assert 200 == resp.status
    txt = yield from resp.text()
    assert txt == 'Test message'


@pytest.mark.parametrize('fingerprint', [
    b'\xa2\x06G\xad\xaa\xf5\xd8\\J\x99^by;\x06=',
    b's\x93\xfd:\xed\x08\x1do\xa9\xaeq9\x1a\xe3\xc5\x7f\x89\xe7l\xf9',
    b'0\x9a\xc9D\x83\xdc\x91\'\x88\x91\x11\xa1d\x97\xfd\xcb~7U\x14D@L'
    b'\x11\xab\x99\xa8\xae\xb7\x14\xee\x8b'],
    ids=['md5', 'sha1', 'sha256'])
@asyncio.coroutine
def test_tcp_connector_fingerprint_ok(test_server, test_client,
                                      loop, ssl_ctx, fingerprint):
    @asyncio.coroutine
    def handler(request):
        return web.HTTPOk(text='Test message')

    # Test for deprecation warning on md5 and sha1 len digests.
    if len(fingerprint) == 16 or len(fingerprint) == 20:
        with pytest.warns(DeprecationWarning) as cm:
            connector = aiohttp.TCPConnector(loop=loop, verify_ssl=False,
                                             fingerprint=fingerprint)
        assert 'Use sha256.' in str(cm[0].message)
    else:
        connector = aiohttp.TCPConnector(loop=loop, verify_ssl=False,
                                         fingerprint=fingerprint)
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    server = yield from test_server(app, ssl=ssl_ctx)
    client = yield from test_client(server, connector=connector)

    resp = yield from client.get('/')
    assert resp.status == 200
    resp.close()


@pytest.mark.parametrize('fingerprint', [
    b'\xa2\x06G\xad\xaa\xf5\xd8\\J\x99^by;\x06=',
    b's\x93\xfd:\xed\x08\x1do\xa9\xaeq9\x1a\xe3\xc5\x7f\x89\xe7l\xf9',
    b'0\x9a\xc9D\x83\xdc\x91\'\x88\x91\x11\xa1d\x97\xfd\xcb~7U\x14D@L'
    b'\x11\xab\x99\xa8\xae\xb7\x14\xee\x8b'],
    ids=['md5', 'sha1', 'sha256'])
@asyncio.coroutine
def test_tcp_connector_fingerprint_fail(test_server, test_client,
                                        loop, ssl_ctx, fingerprint):
    @asyncio.coroutine
    def handler(request):
        return web.HTTPOk(text='Test message')

    bad_fingerprint = b'\x00' * len(fingerprint)

    connector = aiohttp.TCPConnector(loop=loop, verify_ssl=False,
                                     fingerprint=bad_fingerprint)

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    server = yield from test_server(app, ssl=ssl_ctx)
    client = yield from test_client(server, connector=connector)

    with pytest.raises(FingerprintMismatch) as cm:
        yield from client.get('/')
    exc = cm.value
    assert exc.expected == bad_fingerprint
    assert exc.got == fingerprint


@asyncio.coroutine
def test_format_task_get(test_server, loop):

    @asyncio.coroutine
    def handler(request):
        return web.Response(body=b'OK')

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    server = yield from test_server(app)
    client = aiohttp.ClientSession(loop=loop)
    task = loop.create_task(client.get(server.make_url('/')))
    assert "{}".format(task)[:18] == "<Task pending coro"
    resp = yield from task
    resp.close()
    yield from client.close()


@asyncio.coroutine
def test_str_params(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        assert 'q=t+est' in request.query_string
        return web.Response()

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    client = yield from test_client(app)

    resp = yield from client.get('/', params='q=t+est')
    assert 200 == resp.status


@asyncio.coroutine
def test_drop_params_on_redirect(loop, test_client):
    @asyncio.coroutine
    def handler_redirect(request):
        return web.Response(status=301, headers={'Location': '/ok?a=redirect'})

    @asyncio.coroutine
    def handler_ok(request):
        assert request.query_string == 'a=redirect'
        return web.Response(status=200)

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/ok', handler_ok)
    app.router.add_route('GET', '/redirect', handler_redirect)
    client = yield from test_client(app)

    resp = yield from client.get('/redirect', params={'a': 'initial'})
    assert resp.status == 200


@asyncio.coroutine
def test_drop_fragment_on_redirect(loop, test_client):
    @asyncio.coroutine
    def handler_redirect(request):
        return web.Response(status=301, headers={'Location': '/ok#fragment'})

    @asyncio.coroutine
    def handler_ok(request):
        return web.Response(status=200)

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/ok', handler_ok)
    app.router.add_route('GET', '/redirect', handler_redirect)
    client = yield from test_client(app)

    resp = yield from client.get('/redirect')
    assert resp.status == 200
    assert resp.url_obj.path == '/ok'


@asyncio.coroutine
def test_drop_fragment(loop, test_client):
    @asyncio.coroutine
    def handler_ok(request):
        return web.Response(status=200)

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/ok', handler_ok)
    client = yield from test_client(app)

    resp = yield from client.get('/ok#fragment')
    assert resp.status == 200
    assert resp.url_obj.path == '/ok'


@asyncio.coroutine
def test_history(loop, test_client):
    @asyncio.coroutine
    def handler_redirect(request):
        return web.Response(status=301, headers={'Location': '/ok'})

    @asyncio.coroutine
    def handler_ok(request):
        return web.Response(status=200)

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/ok', handler_ok)
    app.router.add_route('GET', '/redirect', handler_redirect)
    client = yield from test_client(app)

    resp = yield from client.get('/ok')
    assert len(resp.history) == 0
    assert resp.status == 200

    resp_redirect = yield from client.get('/redirect')
    assert len(resp_redirect.history) == 1
    assert resp_redirect.history[0].status == 301
    assert resp_redirect.status == 200


@asyncio.coroutine
def test_keepalive_closed_by_server(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        body = yield from request.read()
        assert b'' == body
        resp = web.Response(body=b'OK')
        resp.force_close()
        return resp

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    client = yield from test_client(app)

    resp1 = yield from client.get('/')
    val1 = yield from resp1.read()
    assert val1 == b'OK'
    resp2 = yield from client.get('/')
    val2 = yield from resp2.read()
    assert val2 == b'OK'

    assert 0 == len(client._session.connector._conns)


@asyncio.coroutine
def test_wait_for(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        return web.Response(body=b'OK')

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    client = yield from test_client(app)

    resp = yield from asyncio.wait_for(client.get('/'), 10, loop=loop)
    assert resp.status == 200
    txt = yield from resp.text()
    assert txt == 'OK'


@asyncio.coroutine
def test_raw_headers(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        return web.Response()

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    client = yield from test_client(app)
    resp = yield from client.get('/')
    assert resp.status == 200
    assert resp.raw_headers == ((b'CONTENT-TYPE', b'application/octet-stream'),
                                (b'CONTENT-LENGTH', b'0'),
                                (b'DATE', mock.ANY),
                                (b'SERVER', mock.ANY))
    resp.close()


@asyncio.coroutine
def test_http_request_with_version(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        return web.Response()

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    client = yield from test_client(app)

    with pytest.warns(DeprecationWarning):
        resp = yield from client.get('/', version=aiohttp.HttpVersion11)
        assert resp.status == 200
        resp.close()


@asyncio.coroutine
def test_204_with_gzipped_content_encoding(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        resp = web.StreamResponse(status=204)
        resp.content_length = 0
        resp.content_type = 'application/json'
        # resp.enable_compression(web.ContentCoding.gzip)
        resp.headers['Content-Encoding'] = 'gzip'
        yield from resp.prepare(request)
        return resp

    app = web.Application(loop=loop)
    app.router.add_route('DELETE', '/', handler)
    client = yield from test_client(app)

    resp = yield from client.delete('/')
    assert resp.status == 204
    yield from resp.release()


@asyncio.coroutine
def test_timeout_on_reading_headers(loop, test_client):

    @asyncio.coroutine
    def handler(request):
        resp = web.StreamResponse()
        yield from asyncio.sleep(0.1, loop=loop)
        yield from resp.prepare(request)
        return resp

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    client = yield from test_client(app)

    with pytest.raises(asyncio.TimeoutError):
        yield from client.get('/', timeout=0.01)


@asyncio.coroutine
def test_timeout_on_reading_data(loop, test_client):

    @asyncio.coroutine
    def handler(request):
        resp = web.StreamResponse()
        yield from resp.prepare(request)
        yield from asyncio.sleep(0.1, loop=loop)
        return resp

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    client = yield from test_client(app)

    resp = yield from client.get('/', timeout=0.05)

    with pytest.raises(asyncio.TimeoutError):
        yield from resp.read()


@asyncio.coroutine
def test_readline_error_on_conn_close(loop, test_client):

    @asyncio.coroutine
    def handler(request):
        resp_ = web.StreamResponse()
        yield from resp_.prepare(request)

        # make sure connection is closed by client.
        with pytest.raises(aiohttp.ServerDisconnectedError):
            for _ in range(10):
                resp_.write(b'data\n')
                yield from resp_.drain()
                yield from asyncio.sleep(0.5, loop=loop)
            return resp_

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    server = yield from test_client(app)

    with aiohttp.ClientSession(loop=loop) as session:
        timer_started = False
        url, headers = server.make_url('/'), {'Connection': 'Keep-alive'}
        resp = yield from session.get(url, headers=headers)
        with pytest.raises(aiohttp.ClientDisconnectedError):
            while True:
                data = yield from resp.content.readline()
                data = data.strip()
                if not data:
                    break
                assert data == b'data'
                if not timer_started:
                    def do_release():
                        loop.create_task(resp.release())
                    loop.call_later(1.0, do_release)
                    timer_started = True


@asyncio.coroutine
def test_no_error_on_conn_close_if_eof(loop, test_client):

    @asyncio.coroutine
    def handler(request):
        resp_ = web.StreamResponse()
        yield from resp_.prepare(request)
        resp_.write(b'data\n')
        yield from resp_.drain()
        yield from asyncio.sleep(0.5, loop=loop)
        return resp_

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    server = yield from test_client(app)

    with aiohttp.ClientSession(loop=loop) as session:
        url, headers = server.make_url('/'), {'Connection': 'Keep-alive'}
        resp = yield from session.get(url, headers=headers)
        while True:
            data = yield from resp.content.readline()
            data = data.strip()
            if not data:
                break
            assert data == b'data'
        yield from resp.release()
        assert resp.content.exception() is None


@asyncio.coroutine
def test_error_not_overwrote_on_conn_close(loop, test_client):

    @asyncio.coroutine
    def handler(request):
        resp_ = web.StreamResponse()
        yield from resp_.prepare(request)
        return resp_

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', handler)
    server = yield from test_client(app)

    with aiohttp.ClientSession(loop=loop) as session:
        url, headers = server.make_url('/'), {'Connection': 'Keep-alive'}
        resp = yield from session.get(url, headers=headers)
        resp.content.set_exception(aiohttp.ClientRequestError())

    yield from resp.release()
    assert isinstance(resp.content.exception(), aiohttp.ClientRequestError)


@asyncio.coroutine
def test_HTTP_200_OK_METHOD(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        return web.Response(text=request.method)

    app = web.Application(loop=loop)
    for meth in ('get', 'post', 'put', 'delete', 'head', 'patch', 'options'):
        app.router.add_route(meth.upper(), '/', handler)

    client = yield from test_client(app)
    for meth in ('get', 'post', 'put', 'delete', 'head', 'patch', 'options'):
        resp = yield from client.request(meth, '/')
        assert resp.status == 200
        assert len(resp.history) == 0

        content1 = yield from resp.read()
        content2 = yield from resp.read()
        assert content1 == content2
        content = yield from resp.text()

        if meth == 'head':
            assert b'' == content1
        else:
            assert meth.upper() == content

        yield from resp.release()


@asyncio.coroutine
def test_HTTP_200_OK_METHOD_connector(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        return web.Response(text=request.method)

    conn = aiohttp.TCPConnector(
        conn_timeout=0.2, resolve=True, loop=loop)
    conn.clear_resolved_hosts()

    app = web.Application(loop=loop)
    for meth in ('get', 'post', 'put', 'delete', 'head'):
        app.router.add_route(meth.upper(), '/', handler)
    client = yield from test_client(app, connector=conn)

    for meth in ('get', 'post', 'put', 'delete', 'head'):
        resp = yield from client.request(meth, '/')

        content1 = yield from resp.read()
        content2 = yield from resp.read()
        assert content1 == content2
        content = yield from resp.text()

        assert resp.status == 200
        if meth == 'head':
            assert b'' == content1
        else:
            assert meth.upper() == content

        yield from resp.release()


@asyncio.coroutine
def test_HTTP_302_REDIRECT_GET(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        return web.Response(text=request.method)

    @asyncio.coroutine
    def redirect(request):
        return web.HTTPFound(location='/')

    app = web.Application(loop=loop)
    app.router.add_get('/', handler)
    app.router.add_get('/redirect', redirect)
    client = yield from test_client(app)

    resp = yield from client.get('/redirect')
    assert 200 == resp.status
    assert 1 == len(resp.history)
    resp.close()


@asyncio.coroutine
def test_HTTP_302_REDIRECT_HEAD(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        return web.Response(text=request.method)

    @asyncio.coroutine
    def redirect(request):
        return web.HTTPFound(location='/')

    app = web.Application(loop=loop)
    app.router.add_get('/', handler)
    app.router.add_get('/redirect', redirect)
    app.router.add_head('/', handler)
    app.router.add_head('/redirect', redirect)
    client = yield from test_client(app)

    resp = yield from client.request('head', '/redirect')
    assert 200 == resp.status
    assert 1 == len(resp.history)
    assert resp.method == 'HEAD'
    resp.close()


@asyncio.coroutine
def test_HTTP_302_REDIRECT_NON_HTTP(loop, test_client):

    @asyncio.coroutine
    def redirect(request):
        return web.HTTPFound(location='ftp://127.0.0.1/test/')

    app = web.Application(loop=loop)
    app.router.add_get('/redirect', redirect)
    client = yield from test_client(app)

    with pytest.raises(ValueError):
        yield from client.get('/redirect')


@asyncio.coroutine
def test_HTTP_302_REDIRECT_POST(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        return web.Response(text=request.method)

    @asyncio.coroutine
    def redirect(request):
        return web.HTTPFound(location='/')

    app = web.Application(loop=loop)
    app.router.add_get('/', handler)
    app.router.add_post('/redirect', redirect)
    client = yield from test_client(app)

    resp = yield from client.post('/redirect')
    assert 200 == resp.status
    assert 1 == len(resp.history)
    txt = yield from resp.text()
    assert txt == 'GET'
    resp.close()


@asyncio.coroutine
def test_HTTP_302_REDIRECT_POST_with_content_length_header(loop,
                                                           test_client):
    @asyncio.coroutine
    def handler(request):
        return web.Response(text=request.method)

    @asyncio.coroutine
    def redirect(request):
        return web.HTTPFound(location='/')

    data = json.dumps({'some': 'data'})
    app = web.Application(loop=loop)
    app.router.add_get('/', handler)
    app.router.add_post('/redirect', redirect)
    client = yield from test_client(app)

    resp = yield from client.post('/redirect', data=data,
                                  headers={'Content-Length': str(len(data))})
    assert 200 == resp.status
    assert 1 == len(resp.history)
    txt = yield from resp.text()
    assert txt == 'GET'
    resp.close()


@asyncio.coroutine
def test_HTTP_307_REDIRECT_POST(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        return web.Response(text=request.method)

    @asyncio.coroutine
    def redirect(request):
        return web.HTTPTemporaryRedirect(location='/')

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    app.router.add_post('/redirect', redirect)
    client = yield from test_client(app)

    resp = yield from client.post('/redirect', data={'some': 'data'})
    assert 200 == resp.status
    assert 1 == len(resp.history)
    txt = yield from resp.text()
    assert txt == 'POST'
    resp.close()


@asyncio.coroutine
def test_HTTP_302_max_redirects(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        return web.Response(text=request.method)

    @asyncio.coroutine
    def redirect(request):
        count = int(request.match_info['count'])
        if count:
            return web.HTTPFound(location='/redirect/{}'.format(count-1))
        else:
            return web.HTTPFound(location='/')

    app = web.Application(loop=loop)
    app.router.add_get('/', handler)
    app.router.add_get(r'/redirect/{count:\d+}', redirect)
    client = yield from test_client(app)

    resp = yield from client.get('/redirect/5', max_redirects=2)
    assert 302 == resp.status
    assert 2 == len(resp.history)
    resp.close()


@asyncio.coroutine
def test_HTTP_200_GET_WITH_PARAMS(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        return web.Response(text='&'.join(
            k+'='+v for k, v in request.GET.items()))

    app = web.Application(loop=loop)
    app.router.add_get('/', handler)
    client = yield from test_client(app)

    resp = yield from client.get('/', params={'q': 'test'})
    assert 200 == resp.status
    txt = yield from resp.text()
    assert txt == 'q=test'
    resp.close()


@asyncio.coroutine
def test_HTTP_200_GET_WITH_MultiDict_PARAMS(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        return web.Response(text='&'.join(
            k+'='+v for k, v in request.GET.items()))

    app = web.Application(loop=loop)
    app.router.add_get('/', handler)
    client = yield from test_client(app)

    resp = yield from client.get('/', params=MultiDict([('q', 'test'),
                                                        ('q', 'test2')]))
    assert 200 == resp.status
    txt = yield from resp.text()
    assert txt == 'q=test&q=test2'
    resp.close()


@asyncio.coroutine
def test_HTTP_200_GET_WITH_MIXED_PARAMS(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        return web.Response(text='&'.join(
            k+'='+v for k, v in request.GET.items()))

    app = web.Application(loop=loop)
    app.router.add_get('/', handler)
    client = yield from test_client(app)

    resp = yield from client.get('/?test=true', params={'q': 'test'})
    assert 200 == resp.status
    txt = yield from resp.text()
    assert txt == 'test=true&q=test'
    resp.close()


@asyncio.coroutine
def test_POST_DATA(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        data = yield from request.post()
        return web.json_response(dict(data))

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(app)

    resp = yield from client.post('/', data={'some': 'data'})
    assert 200 == resp.status
    content = yield from resp.json()
    assert content == {'some': 'data'}
    resp.close()


@asyncio.coroutine
def test_POST_DATA_with_explicit_formdata(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        data = yield from request.post()
        return web.json_response(dict(data))

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(app)

    form = aiohttp.FormData()
    form.add_field('name', 'text')

    resp = yield from client.post('/', data=form)
    assert 200 == resp.status
    content = yield from resp.json()
    assert content == {'name': 'text'}
    resp.close()


@pytest.mark.xfail
@asyncio.coroutine
def test_POST_DATA_with_charset(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        data = yield from request.post()
        return web.Response(text=data['name'])

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(app)

    form = aiohttp.FormData()
    form.add_field('name', 'текст', content_type='text/plain; charset=koi8-r')

    resp = yield from client.post('/', data=form)
    assert 200 == resp.status
    content = yield from resp.text()
    assert content == 'текст'
    resp.close()


@pytest.mark.xfail
@asyncio.coroutine
def test_POST_DATA_with_context_transfer_encoding(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        data = yield from request.post()
        assert data['name'] == b'text'  # should it be str?
        return web.Response()

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(app)

    form = aiohttp.FormData()
    form.add_field('name', 'text', content_transfer_encoding='base64')

    resp = yield from client.post('/', data=form)
    assert 200 == resp.status
    content = yield from resp.text()
    assert content == 'text'
    resp.close()


@asyncio.coroutine
def test_POST_MultiDict(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        data = yield from request.post()
        assert data == MultiDict([('q', 'test1'), ('q', 'test2')])
        return web.Response()

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(app)

    resp = yield from client.post('/', data=MultiDict(
        [('q', 'test1'), ('q', 'test2')]))
    assert 200 == resp.status
    resp.close()


@asyncio.coroutine
def test_POST_DATA_DEFLATE(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        data = yield from request.post()
        return web.json_response(dict(data))

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(app)

    resp = yield from client.post('/', data={'some': 'data'}, compress=True)
    assert 200 == resp.status
    content = yield from resp.json()
    assert content == {'some': 'data'}
    resp.close()


@asyncio.coroutine
def test_POST_FILES(loop, test_client, fname):
    @asyncio.coroutine
    def handler(request):
        data = yield from request.post()
        assert data['some'].filename == fname.name
        with fname.open('rb') as f:
            content1 = f.read()
        content2 = data['some'].file.read()
        assert content1 == content2
        assert data['test'].file.read() == b'data'
        return web.HTTPOk()

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(app)

    with fname.open() as f:
        resp = yield from client.post('/', data={'some': f, 'test': b'data'},
                                      chunked=1024,
                                      headers={'Transfer-Encoding': 'chunked'})
        assert 200 == resp.status
        resp.close()


@asyncio.coroutine
def test_POST_FILES_DEFLATE(loop, test_client, fname):
    @asyncio.coroutine
    def handler(request):
        data = yield from request.post()
        assert data['some'].filename == fname.name
        with fname.open('rb') as f:
            content1 = f.read()
        content2 = data['some'].file.read()
        assert content1 == content2
        return web.HTTPOk()

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(app)

    with fname.open() as f:
        resp = yield from client.post('/', data={'some': f},
                                      chunked=1024,
                                      compress='deflate')
        assert 200 == resp.status
        resp.close()


@asyncio.coroutine
def test_POST_FILES_STR(loop, test_client, fname):
    @asyncio.coroutine
    def handler(request):
        data = yield from request.post()
        with fname.open() as f:
            content1 = f.read()
        content2 = data['some']
        assert content1 == content2
        return web.HTTPOk()

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(app)

    with fname.open() as f:
        resp = yield from client.post('/', data={'some': f.read()})
        assert 200 == resp.status
        resp.close()


@asyncio.coroutine
def test_POST_FILES_STR_SIMPLE(loop, test_client, fname):
    @asyncio.coroutine
    def handler(request):
        data = yield from request.read()
        with fname.open('rb') as f:
            content = f.read()
        assert content == data
        return web.HTTPOk()

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(app)

    with fname.open() as f:
        resp = yield from client.post('/', data=f.read())
        assert 200 == resp.status
        resp.close()


@asyncio.coroutine
def test_POST_FILES_LIST(loop, test_client, fname):
    @asyncio.coroutine
    def handler(request):
        data = yield from request.post()
        assert fname.name == data['some'].filename
        with fname.open('rb') as f:
            content = f.read()
        assert content == data['some'].file.read()
        return web.HTTPOk()

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(app)

    with fname.open() as f:
        resp = yield from client.post('/', data=[('some', f)])
        assert 200 == resp.status
        resp.close()


@asyncio.coroutine
def test_POST_FILES_CT(loop, test_client, fname):
    @asyncio.coroutine
    def handler(request):
        data = yield from request.post()
        assert fname.name == data['some'].filename
        assert 'text/plain' == data['some'].content_type
        with fname.open('rb') as f:
            content = f.read()
        assert content == data['some'].file.read()
        return web.HTTPOk()

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(app)

    with fname.open() as f:
        form = aiohttp.FormData()
        form.add_field('some', f, content_type='text/plain')
        resp = yield from client.post('/', data=form)
        assert 200 == resp.status
        resp.close()


@asyncio.coroutine
def test_POST_FILES_SINGLE(loop, test_client, fname):

    app = web.Application(loop=loop)
    client = yield from test_client(app)

    with fname.open() as f:
        with pytest.raises(ValueError):
            yield from client.post('/', data=f)


@asyncio.coroutine
def test_POST_FILES_SINGLE_BINARY(loop, test_client, fname):
    @asyncio.coroutine
    def handler(request):
        data = yield from request.read()
        with fname.open('rb') as f:
            content = f.read()
        assert content == data
        # if system cannot determine 'application/pgp-keys' MIME type
        # then use 'application/octet-stream' default
        assert request.content_type in ['application/pgp-keys',
                                        'text/plain',
                                        'application/octet-stream']
        return web.HTTPOk()

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(app)

    with fname.open('rb') as f:
        resp = yield from client.post('/', data=f)
        assert 200 == resp.status
        resp.close()


@asyncio.coroutine
def test_POST_FILES_IO(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        data = yield from request.post()
        assert b'data' == data['unknown'].file.read()
        assert data['unknown'].content_type == 'application/octet-stream'
        assert data['unknown'].filename == 'unknown'
        return web.HTTPOk()

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(app)

    data = io.BytesIO(b'data')
    resp = yield from client.post('/', data=[data])
    assert 200 == resp.status
    resp.close()


@pytest.mark.xfail
@asyncio.coroutine
def test_POST_MULTIPART(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        data = yield from request.post()
        lst = list(data.values())
        assert 3 == len(lst)
        assert lst[0] == 'foo'
        assert lst[1] == {'bar': 'баз'}
        assert b'data' == data['unknown'].file.read()
        assert data['unknown'].content_type == 'application/octet-stream'
        assert data['unknown'].filename == 'unknown'
        return web.HTTPOk()

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(app)

    with MultipartWriter('form-data') as writer:
        writer.append('foo')
        writer.append_json({'bar': 'баз'})
        writer.append_form([('тест', '4'), ('сетс', '2')])

    resp = yield from client.post('/', data=writer)
    assert 200 == resp.status
    resp.close()


@asyncio.coroutine
def test_POST_FILES_IO_WITH_PARAMS(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        data = yield from request.post()
        assert data['test'] == 'true'
        assert data['unknown'].content_type == 'application/octet-stream'
        assert data['unknown'].filename == 'unknown'
        assert data['unknown'].file.read() == b'data'
        assert data.getall('q') == ['t1', 't2']

        return web.HTTPOk()

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(app)

    data = io.BytesIO(b'data')
    resp = yield from client.post('/', data=(('test', 'true'),
                                             MultiDict(
                                                 [('q', 't1'), ('q', 't2')]),
                                             data))
    assert 200 == resp.status
    resp.close()


@asyncio.coroutine
def test_POST_FILES_WITH_DATA(loop, test_client, fname):
    @asyncio.coroutine
    def handler(request):
        data = yield from request.post()
        assert data['test'] == 'true'
        assert data['some'].content_type in ['application/pgp-keys',
                                             'text/plain',
                                             'application/octet-stream']
        assert data['some'].filename == fname.name
        with fname.open('rb') as f:
            assert data['some'].file.read() == f.read()

        return web.HTTPOk()

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(app)

    with fname.open() as f:
        resp = yield from client.post('/', data={'test': 'true', 'some': f})
        assert 200 == resp.status
        resp.close()


@pytest.mark.xfail
@asyncio.coroutine
def test_POST_STREAM_DATA(loop, test_client, fname):
    @asyncio.coroutine
    def handler(request):
        assert request.content_type == 'application/octet-stream'
        content = yield from request.read()
        with fname.open('rb') as f:
            expected = f.read()
        assert request.content_length == str(len(expected))
        assert content == expected

        return web.HTTPOk()

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(app)

    with fname.open() as f:
        data = f.read()
        fut = create_future(loop)

        @asyncio.coroutine
        def stream():
            yield from fut
            yield data

        loop.call_later(0.01, fut.set_result, None)

        resp = yield from client.post(
            '/', data=stream(),
            headers={'Content-Length': str(len(data))})
        assert 200 == resp.status
        resp.close()


@pytest.mark.xfail
@asyncio.coroutine
def test_POST_StreamReader(fname, loop, test_client):
    @asyncio.coroutine
    def handler(request):
        assert request.content_type == 'application/octet-stream'
        content = yield from request.read()
        with fname.open('rb') as f:
            expected = f.read()
        assert request.content_length == str(len(expected))
        assert content == expected

        return web.HTTPOk()

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(app)

    with fname.open() as f:
        data = f.read()

    stream = aiohttp.StreamReader(loop=loop)
    stream.feed_data(data)
    stream.feed_eof()

    resp = yield from client.post(
        '/', data=stream,
        headers={'Content-Length': str(len(data))})
    assert 200 == resp.status
    resp.close()


@asyncio.coroutine
def test_expect_continue(loop, test_client):
    expect_called = False

    @asyncio.coroutine
    def handler(request):
        data = yield from request.post()
        assert data == {'some': 'data'}
        return web.HTTPOk()

    @asyncio.coroutine
    def expect_handler(request):
        nonlocal expect_called
        expect = request.headers.get(hdrs.EXPECT)
        if expect.lower() == "100-continue":
            request.transport.write(b"HTTP/1.1 100 Continue\r\n\r\n")
            expect_called = True

    app = web.Application(loop=loop)
    app.router.add_post('/', handler, expect_handler=expect_handler)
    client = yield from test_client(app)

    resp = yield from client.post('/', data={'some': 'data'}, expect100=True)
    assert 200 == resp.status
    resp.close()
    assert expect_called


@asyncio.coroutine
def test_encoding_deflate(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        resp = web.Response(text='text')
        resp.enable_chunked_encoding()
        resp.enable_compression(web.ContentCoding.deflate)
        return resp

    app = web.Application(loop=loop)
    app.router.add_get('/', handler)
    client = yield from test_client(app)

    resp = yield from client.get('/')
    assert 200 == resp.status
    txt = yield from resp.text()
    assert txt == 'text'
    resp.close()


@asyncio.coroutine
def test_encoding_gzip(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        resp = web.Response(text='text')
        resp.enable_chunked_encoding()
        resp.enable_compression(web.ContentCoding.gzip)
        return resp

    app = web.Application(loop=loop)
    app.router.add_get('/', handler)
    client = yield from test_client(app)

    resp = yield from client.get('/')
    assert 200 == resp.status
    txt = yield from resp.text()
    assert txt == 'text'
    resp.close()


@asyncio.coroutine
def test_chunked(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        resp = web.Response(text='text')
        resp.enable_chunked_encoding()
        return resp

    app = web.Application(loop=loop)
    app.router.add_get('/', handler)
    client = yield from test_client(app)

    resp = yield from client.get('/')
    assert 200 == resp.status
    assert resp.headers['Transfer-Encoding'] == 'chunked'
    txt = yield from resp.text()
    assert txt == 'text'
    resp.close()


@asyncio.coroutine
def test_shortcuts(test_client, loop):
    @asyncio.coroutine
    def handler(request):
        return web.Response(text=request.method)

    app = web.Application(loop=loop)
    for meth in ('get', 'post', 'put', 'delete', 'head', 'patch', 'options'):
        app.router.add_route(meth.upper(), '/', handler)
    client = yield from test_client(lambda loop: app)

    for meth in ('get', 'post', 'put', 'delete', 'head', 'patch', 'options'):
        coro = getattr(client.session, meth)
        resp = yield from coro(client.make_url('/'))

        assert resp.status == 200
        assert len(resp.history) == 0

        content1 = yield from resp.read()
        content2 = yield from resp.read()
        assert content1 == content2
        content = yield from resp.text()

        if meth == 'head':
            assert b'' == content1
        else:
            assert meth.upper() == content

        yield from resp.release()


@asyncio.coroutine
def test_module_shortcuts(test_client, loop):
    @asyncio.coroutine
    def handler(request):
        return web.Response(text=request.method)

    app = web.Application(loop=loop)
    for meth in ('get', 'post', 'put', 'delete', 'head', 'patch', 'options'):
        app.router.add_route(meth.upper(), '/', handler)
    client = yield from test_client(lambda loop: app)

    for meth in ('get', 'post', 'put', 'delete', 'head', 'patch', 'options'):
        coro = getattr(aiohttp, meth)
        with pytest.warns(DeprecationWarning):
            resp = yield from coro(client.make_url('/'), loop=loop)

        assert resp.status == 200
        assert len(resp.history) == 0

        content1 = yield from resp.read()
        content2 = yield from resp.read()
        assert content1 == content2
        content = yield from resp.text()

        if meth == 'head':
            assert b'' == content1
        else:
            assert meth.upper() == content

        yield from resp.release()


@asyncio.coroutine
def test_cookies(test_client, loop):
    @asyncio.coroutine
    def handler(request):
        assert request.cookies.keys() == {'test1', 'test3'}
        assert request.cookies['test1'] == '123'
        assert request.cookies['test3'] == '456'
        return web.Response()

    c = http.cookies.Morsel()
    c.set('test3', '456', '456')

    app = web.Application(loop=loop)
    app.router.add_get('/', handler)
    client = yield from test_client(lambda loop: app)

    resp = yield from aiohttp.get(client.make_url('/'),
                                  cookies={'test1': '123', 'test2': c},
                                  loop=loop)
    assert 200 == resp.status
    resp.close()


@asyncio.coroutine
def test_morsel_with_attributes(test_client, loop):
    # A comment from original test:
    #
    # No cookie attribute should pass here
    # they are only used as filters
    # whether to send particular cookie or not.
    # E.g. if cookie expires it just becomes thrown away.
    # Server who sent the cookie with some attributes
    # already knows them, no need to send this back again and again

    @asyncio.coroutine
    def handler(request):
        assert request.cookies.keys() == {'test3'}
        assert request.cookies['test3'] == '456'
        return web.Response()

    c = http.cookies.Morsel()
    c.set('test3', '456', '456')
    c['httponly'] = True
    c['secure'] = True
    c['max-age'] = 1000

    app = web.Application(loop=loop)
    app.router.add_get('/', handler)
    client = yield from test_client(lambda loop: app)

    resp = yield from aiohttp.get(client.make_url('/'),
                                  cookies={'test2': c},
                                  loop=loop)
    assert 200 == resp.status
    resp.close()


@asyncio.coroutine
def test_set_cookies(test_client, loop):
    @asyncio.coroutine
    def handler(request):
        ret = web.Response()
        ret.set_cookie('c1', 'cookie1')
        ret.set_cookie('c2', 'cookie2')
        ret.headers.add('Set-Cookie',
                        'ISAWPLB{A7F52349-3531-4DA9-8776-F74BC6F4F1BB}='
                        '{925EC0B8-CB17-4BEB-8A35-1033813B0523}; '
                        'HttpOnly; Path=/')
        return ret

    app = web.Application(loop=loop)
    app.router.add_get('/', handler)
    client = yield from test_client(lambda loop: app)

    with mock.patch('aiohttp.client_reqrep.client_logger') as m_log:
        resp = yield from client.get('/')
        assert 200 == resp.status
        cookie_names = {c.key for c in client.session.cookie_jar}
        assert cookie_names == {'c1', 'c2'}
        resp.close()

        m_log.warning.assert_called_with('Can not load response cookies: %s',
                                         mock.ANY)


@asyncio.coroutine
def test_request_conn_error(loop):
    client = aiohttp.ClientSession(loop=loop)
    with pytest.raises(aiohttp.ClientConnectionError):
        yield from client.get('http://0.0.0.0:1')
    yield from client.close()


@asyncio.coroutine
def test_broken_connection(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        request.transport.close()
        return web.Response(text='answer'*1000)

    app = web.Application(loop=loop)
    app.router.add_get('/', handler)
    client = yield from test_client(lambda loop: app)

    with pytest.raises(aiohttp.ClientResponseError):
        yield from client.get('/')


@asyncio.coroutine
def test_broken_connection_2(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        resp = web.StreamResponse()
        yield from resp.prepare(request)
        request.transport.close()
        resp.write(b'answer'*1000)
        return resp

    app = web.Application(loop=loop)
    app.router.add_get('/', handler)
    client = yield from test_client(lambda loop: app)

    resp = yield from client.get('/')
    with pytest.raises(aiohttp.ServerDisconnectedError):
        yield from resp.read()
    resp.close()


@asyncio.coroutine
def test_custom_headers(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        assert request.headers["x-api-key"] == "foo"
        return web.Response()

    app = web.Application(loop=loop)
    app.router.add_post('/', handler)
    client = yield from test_client(lambda loop: app)

    resp = yield from client.post('/', headers={
        "Content-Type": "application/json",
        "x-api-key": "foo"})
    assert resp.status == 200


@asyncio.coroutine
def test_redirect_to_absolute_url(loop, test_client):
    @asyncio.coroutine
    def handler(request):
        return web.Response(text=request.method)

    @asyncio.coroutine
    def redirect(request):
        return web.HTTPFound(location=client.make_url('/'))

    app = web.Application(loop=loop)
    app.router.add_get('/', handler)
    app.router.add_get('/redirect', redirect)

    client = yield from test_client(app)
    resp = yield from client.get('/redirect')
    assert 200 == resp.status
    resp.close()