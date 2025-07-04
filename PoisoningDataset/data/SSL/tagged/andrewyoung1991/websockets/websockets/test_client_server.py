import asyncio
import logging
import os
import ssl
import unittest
import unittest.mock

from .client import *
from .exceptions import InvalidHandshake
from .http import USER_AGENT, read_response
from .server import *


# Avoid displaying stack traces at the ERROR logging level.
logging.basicConfig(level=logging.CRITICAL)

testcert = os.path.join(os.path.dirname(__file__), 'testcert.pem')


@asyncio.coroutine
def handler(ws, path):
    if path == '/attributes':
        yield from ws.send(repr((ws.host, ws.port, ws.secure)))
    elif path == '/headers':
        yield from ws.send(str(ws.request_headers))
        yield from ws.send(str(ws.response_headers))
    elif path == '/raw_headers':
        yield from ws.send(repr(ws.raw_request_headers))
        yield from ws.send(repr(ws.raw_response_headers))
    elif path == '/subprotocol':
        yield from ws.send(repr(ws.subprotocol))
    else:
        yield from ws.send((yield from ws.recv()))


class ClientServerTests(unittest.TestCase):

    secure = False

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def run_loop_once(self):
        # Process callbacks scheduled with call_soon. This pattern works
        # because stop schedules a callback to stop the event loop and
        # run_forever runs the loop until it hits this callback.
        self.loop.stop()
        self.loop.run_forever()

    def start_server(self, **kwds):
        server = serve(handler, 'localhost', 8642, **kwds)
        self.server = self.loop.run_until_complete(server)

    def start_client(self, path='', **kwds):
        client = connect('ws://localhost:8642/' + path, **kwds)
        self.client = self.loop.run_until_complete(client)

    def stop_client(self):
        self.loop.run_until_complete(self.client.worker)

    def stop_server(self):
        self.server.close()
        self.loop.run_until_complete(self.server.wait_closed())

    def test_basic(self):
        self.start_server()
        self.start_client()
        self.loop.run_until_complete(self.client.send("Hello!"))
        reply = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(reply, "Hello!")
        self.stop_client()
        self.stop_server()

    def test_server_close_while_client_connected(self):
        self.start_server()
        self.start_client()
        self.stop_server()

    def test_explicit_event_loop(self):
        self.start_server(loop=self.loop)
        self.start_client(loop=self.loop)
        self.loop.run_until_complete(self.client.send("Hello!"))
        reply = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(reply, "Hello!")
        self.stop_client()
        self.stop_server()

    def test_protocol_attributes(self):
        self.start_server()
        self.start_client('attributes')
        expected_attrs = ('localhost', 8642, self.secure)
        client_attrs = (self.client.host, self.client.port, self.client.secure)
        self.assertEqual(client_attrs, expected_attrs)
        server_attrs = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(server_attrs, repr(expected_attrs))
        self.stop_client()
        self.stop_server()

    def test_protocol_headers(self):
        self.start_server()
        self.start_client('headers')
        client_req = self.client.request_headers
        client_resp = self.client.response_headers
        self.assertEqual(client_req['User-Agent'], USER_AGENT)
        self.assertEqual(client_resp['Server'], USER_AGENT)
        server_req = self.loop.run_until_complete(self.client.recv())
        server_resp = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(server_req, str(client_req))
        self.assertEqual(server_resp, str(client_resp))
        self.stop_client()
        self.stop_server()

    def test_protocol_raw_headers(self):
        self.start_server()
        self.start_client('raw_headers')
        client_req = self.client.raw_request_headers
        client_resp = self.client.raw_response_headers
        self.assertEqual(dict(client_req)['User-Agent'], USER_AGENT)
        self.assertEqual(dict(client_resp)['Server'], USER_AGENT)
        server_req = self.loop.run_until_complete(self.client.recv())
        server_resp = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(server_req, repr(client_req))
        self.assertEqual(server_resp, repr(client_resp))
        self.stop_client()
        self.stop_server()

    def test_protocol_custom_request_headers_dict(self):
        self.start_server()
        self.start_client('raw_headers', extra_headers={'X-Spam': 'Eggs'})
        req_headers = self.loop.run_until_complete(self.client.recv())
        self.loop.run_until_complete(self.client.recv())
        self.assertIn("('X-Spam', 'Eggs')", req_headers)
        self.stop_client()
        self.stop_server()

    def test_protocol_custom_request_headers_list(self):
        self.start_server()
        self.start_client('raw_headers', extra_headers=[('X-Spam', 'Eggs')])
        req_headers = self.loop.run_until_complete(self.client.recv())
        self.loop.run_until_complete(self.client.recv())
        self.assertIn("('X-Spam', 'Eggs')", req_headers)
        self.stop_client()
        self.stop_server()

    def test_protocol_custom_response_headers_callable_dict(self):
        self.start_server(extra_headers=lambda p, r: {'X-Spam': 'Eggs'})
        self.start_client('raw_headers')
        self.loop.run_until_complete(self.client.recv())
        resp_headers = self.loop.run_until_complete(self.client.recv())
        self.assertIn("('X-Spam', 'Eggs')", resp_headers)
        self.stop_client()
        self.stop_server()

    def test_protocol_custom_response_headers_callable_list(self):
        self.start_server(extra_headers=lambda p, r: [('X-Spam', 'Eggs')])
        self.start_client('raw_headers')
        self.loop.run_until_complete(self.client.recv())
        resp_headers = self.loop.run_until_complete(self.client.recv())
        self.assertIn("('X-Spam', 'Eggs')", resp_headers)
        self.stop_client()
        self.stop_server()

    def test_protocol_custom_response_headers_dict(self):
        self.start_server(extra_headers={'X-Spam': 'Eggs'})
        self.start_client('raw_headers')
        self.loop.run_until_complete(self.client.recv())
        resp_headers = self.loop.run_until_complete(self.client.recv())
        self.assertIn("('X-Spam', 'Eggs')", resp_headers)
        self.stop_client()
        self.stop_server()

    def test_protocol_custom_response_headers_list(self):
        self.start_server(extra_headers=[('X-Spam', 'Eggs')])
        self.start_client('raw_headers')
        self.loop.run_until_complete(self.client.recv())
        resp_headers = self.loop.run_until_complete(self.client.recv())
        self.assertIn("('X-Spam', 'Eggs')", resp_headers)
        self.stop_client()
        self.stop_server()

    def test_no_subprotocol(self):
        self.start_server()
        self.start_client('subprotocol')
        server_subprotocol = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(server_subprotocol, repr(None))
        self.assertEqual(self.client.subprotocol, None)
        self.stop_client()
        self.stop_server()

    def test_subprotocol_found(self):
        self.start_server(subprotocols=['superchat', 'chat'])
        self.start_client('subprotocol', subprotocols=['otherchat', 'chat'])
        server_subprotocol = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(server_subprotocol, repr('chat'))
        self.assertEqual(self.client.subprotocol, 'chat')
        self.stop_client()
        self.stop_server()

    def test_subprotocol_not_found(self):
        self.start_server(subprotocols=['superchat'])
        self.start_client('subprotocol', subprotocols=['otherchat'])
        server_subprotocol = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(server_subprotocol, repr(None))
        self.assertEqual(self.client.subprotocol, None)
        self.stop_client()
        self.stop_server()

    def test_subprotocol_not_offered(self):
        self.start_server()
        self.start_client('subprotocol', subprotocols=['otherchat', 'chat'])
        server_subprotocol = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(server_subprotocol, repr(None))
        self.assertEqual(self.client.subprotocol, None)
        self.stop_client()
        self.stop_server()

    def test_subprotocol_not_requested(self):
        self.start_server(subprotocols=['superchat', 'chat'])
        self.start_client('subprotocol')
        server_subprotocol = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(server_subprotocol, repr(None))
        self.assertEqual(self.client.subprotocol, None)
        self.stop_client()
        self.stop_server()

    @unittest.mock.patch.object(
        WebSocketServerProtocol, 'select_subprotocol', autospec=True)
    def test_subprotocol_error(self, _select_subprotocol):
        _select_subprotocol.return_value = 'superchat'

        self.start_server(subprotocols=['superchat'])
        with self.assertRaises(InvalidHandshake):
            self.start_client('subprotocol', subprotocols=['otherchat'])
        self.run_loop_once()
        self.stop_server()

    @unittest.mock.patch('websockets.server.read_request')
    def test_server_receives_malformed_request(self, _read_request):
        _read_request.side_effect = ValueError("read_request failed")

        self.start_server()
        with self.assertRaises(InvalidHandshake):
            self.start_client()
        self.stop_server()

    @unittest.mock.patch('websockets.client.read_response')
    def test_client_receives_malformed_response(self, _read_response):
        _read_response.side_effect = ValueError("read_response failed")

        self.start_server()
        with self.assertRaises(InvalidHandshake):
            self.start_client()
        self.run_loop_once()
        self.stop_server()

    @unittest.mock.patch('websockets.client.build_request')
    def test_client_sends_invalid_handshake_request(self, _build_request):
        def wrong_build_request(set_header):
            return '42'
        _build_request.side_effect = wrong_build_request

        self.start_server()
        with self.assertRaises(InvalidHandshake):
            self.start_client()
        self.stop_server()

    @unittest.mock.patch('websockets.server.build_response')
    def test_server_sends_invalid_handshake_response(self, _build_response):
        def wrong_build_response(set_header, key):
            return build_response(set_header, '42')
        _build_response.side_effect = wrong_build_response

        self.start_server()
        with self.assertRaises(InvalidHandshake):
            self.start_client()
        self.stop_server()

    @unittest.mock.patch('websockets.client.read_response')
    def test_server_does_not_switch_protocols(self, _read_response):
        @asyncio.coroutine
        def wrong_read_response(stream):
            code, headers = yield from read_response(stream)
            return 400, headers
        _read_response.side_effect = wrong_read_response

        self.start_server()
        with self.assertRaises(InvalidHandshake):
            self.start_client()
        self.run_loop_once()
        self.stop_server()

    @unittest.mock.patch('websockets.server.WebSocketServerProtocol.send')
    def test_server_handler_crashes(self, send):
        send.side_effect = ValueError("send failed")

        self.start_server()
        self.start_client()
        self.loop.run_until_complete(self.client.send("Hello!"))
        reply = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(reply, None)
        self.stop_client()
        self.stop_server()

        # Connection ends with an unexpected error.
        self.assertEqual(self.client.close_code, 1011)

    @unittest.mock.patch('websockets.server.WebSocketServerProtocol.close')
    def test_server_close_crashes(self, close):
        close.side_effect = ValueError("close failed")

        self.start_server()
        self.start_client()
        self.loop.run_until_complete(self.client.send("Hello!"))
        reply = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(reply, "Hello!")
        self.stop_client()
        self.stop_server()

        # Connection ends with an abnormal closure.
        self.assertEqual(self.client.close_code, 1006)


@unittest.skipUnless(os.path.exists(testcert), "test certificate is missing")
class SSLClientServerTests(ClientServerTests):

    secure = True

    @property
    def server_context(self):
<target>
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
</target>
        ssl_context.load_cert_chain(testcert)
        return ssl_context

    @property
    def client_context(self):
<target>
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
</target>
        ssl_context.load_verify_locations(testcert)
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        return ssl_context

    def start_server(self, *args, **kwds):
        kwds['ssl'] = self.server_context
        server = serve(handler, 'localhost', 8642, **kwds)
        self.server = self.loop.run_until_complete(server)

    def start_client(self, path='', **kwds):
        kwds['ssl'] = self.client_context
        client = connect('wss://localhost:8642/' + path, **kwds)
        self.client = self.loop.run_until_complete(client)

    def test_ws_uri_is_rejected(self):
        self.start_server()
        client = connect('ws://localhost:8642/', ssl=self.client_context)
        with self.assertRaises(ValueError):
            self.loop.run_until_complete(client)
        self.stop_server()


class ClientServerOriginTests(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_checking_origin_succeeds(self):
        server = self.loop.run_until_complete(
            serve(handler, 'localhost', 8642, origins=['http://localhost']))
        client = self.loop.run_until_complete(
            connect('ws://localhost:8642/', origin='http://localhost'))

        self.loop.run_until_complete(client.send("Hello!"))
        self.assertEqual(self.loop.run_until_complete(client.recv()), "Hello!")

        self.loop.run_until_complete(client.close())
        server.close()
        self.loop.run_until_complete(server.wait_closed())

    def test_checking_origin_fails(self):
        server = self.loop.run_until_complete(
            serve(handler, 'localhost', 8642, origins=['http://localhost']))
        with self.assertRaisesRegex(InvalidHandshake, "Bad status code: 403"):
            self.loop.run_until_complete(
                connect('ws://localhost:8642/', origin='http://otherhost'))

        server.close()
        self.loop.run_until_complete(server.wait_closed())

    def test_checking_lack_of_origin_succeeds(self):
        server = self.loop.run_until_complete(
            serve(handler, 'localhost', 8642, origins=['']))
        client = self.loop.run_until_complete(connect('ws://localhost:8642/'))

        self.loop.run_until_complete(client.send("Hello!"))
        self.assertEqual(self.loop.run_until_complete(client.recv()), "Hello!")

        self.loop.run_until_complete(client.close())
        server.close()
        self.loop.run_until_complete(server.wait_closed())