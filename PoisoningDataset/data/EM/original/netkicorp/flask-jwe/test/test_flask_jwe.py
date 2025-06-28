__author__ = 'mdavid'

# Setup test environment
import json
import os
import unittest

from mock import patch, Mock, MagicMock
from mock.mock import _patch
from flask_jwe import *
from flask.config import Config


class AutoPatchTestCase(unittest.TestCase):
    def tearDown(self):
        for item, value in self.__dict__.iteritems():
            if item.startswith('patcher') and isinstance(value, _patch):
                try:
                    value.stop()
                except RuntimeError as e:
                    if e.message != 'stop called on unstarted patcher':
                        raise
                    print "TEST ERROR: Patcher Not Started [%s - %s]" % (self.__class__.__name__, self._testMethodName)
                    raise

class TestJweRequestRequiredDecorator(AutoPatchTestCase):

    def setUp(self):

        self.patcher1 = patch('flask_jwe.request')
        self.mockRequest = self.patcher1.start()

        # Mock the decorator function -> We run self.decorated
        self.mock_func = MagicMock(return_value='fake_response')
        self.mock_func.__name__ = 'mock_func'
        self.decorated = jwe_request_required(self.mock_func)

    def test_is_jwe_request(self):
        self.mockRequest.is_jwe = True
        ret = self.decorated()
        self.assertEqual('fake_response', ret)

    def test_not_jwe_request(self):
        self.mockRequest.is_jwe = False
        ret = self.decorated()
        self.assertIsInstance(ret, Response)
        self.assertEqual('JWE Request Required', ret.data)
        self.assertEqual(400, ret.status_code)
        self.assertEqual('text/plain', ret.mimetype)


class TestContructor(AutoPatchTestCase):
    def setUp(self):
        self.patcher1 = patch('flask_jwe.FlaskJWE.init_app')
        self.mockInitApp = self.patcher1.start()

        self.app = MagicMock()

    def test_go_right(self):
        ret = FlaskJWE(self.app)
        self.assertEqual(1, self.mockInitApp.call_count)
        self.assertEqual(self.app, ret.app)

    def test_missing_app(self):
        ret = FlaskJWE()
        self.assertEqual(0, self.mockInitApp.call_count)
        self.assertIsNone(ret.app)


class TestInitApp(AutoPatchTestCase):
    def setUp(self):
        self.patcher1 = patch('flask_jwe.FlaskJWE.return_jwk_pub')
        self.patcher2 = patch('flask_jwe.FlaskJWE.get_server_key')
        self.patcher3 = patch('flask_jwe.FlaskJWE.reverse_echo')
        self.patcher4 = patch('flask_jwe.FlaskJWE.on_request_start')
        self.patcher5 = patch('flask_jwe.FlaskJWE.on_request_end')
        self.patcher6 = patch('flask_jwe.FlaskJWE.route_in_use')

        self.mockReturnJwkPub = self.patcher1.start()
        self.mockGetServerKey = self.patcher2.start()
        self.mockReverseEcho = self.patcher3.start()
        self.mockOnRequestStart = self.patcher4.start()
        self.mockOnRequestEnd = self.patcher5.start()
        self.mockRouteInUse = self.patcher6.start()

        self.app = MagicMock()
        self.app.config = Config(None)

        self.mockRouteInUse.return_value = False

    def test_go_right(self):
        FlaskJWE(self.app)

        self.assertEqual(['application/jose', 'application/jose+json'], self.app.config['JOSE_CONTENT_TYPES'])
        self.assertEqual('/serverpubkey', self.app.config['SERVER_PUB_JWK_ENDPOINT'])
        self.assertTrue(self.app.config['JWE_ECDH_ES'])
        self.assertEqual('P-256', self.app.config['ECDH_CURVE'])
        self.assertEqual(-1, self.app.config['JWE_ES_KEY_EXPIRES'])
        self.assertIsNone(self.app.config['JWE_SERVER_RSA_KEY'])
        self.assertIsNone(self.app.config['JWE_SERVER_SYM_KEY'])
        self.assertTrue(self.app.config['JWE_SERVER_KEY_PER_IP'])
        self.assertIsNone(self.app.config['JWE_KEY_ENCRYPTION_KEY'])
        self.assertTrue(self.app.config['JWE_SET_REQUEST_DATA'])

        self.assertEqual(1, self.mockRouteInUse.call_count)
        self.assertEqual(self.app, self.mockRouteInUse.call_args[0][0])
        self.assertEqual('/serverpubkey', self.mockRouteInUse.call_args[0][1])

        self.assertEqual(1, self.app.add_url_rule.call_count)
        self.assertEqual('/serverpubkey', self.app.add_url_rule.call_args[0][0])
        self.assertEqual('jwkendpoint', self.app.add_url_rule.call_args[0][1])
        self.assertEqual(self.mockReturnJwkPub, self.app.add_url_rule.call_args[0][2])

        self.assertEqual(1, self.app.before_request.call_count)
        self.assertEqual(self.mockOnRequestStart, self.app.before_request.call_args[0][0])

        self.assertEqual(1, self.app.after_request.call_count)
        self.assertEqual(self.mockOnRequestEnd, self.app.after_request.call_args[0][0])

    def test_ecdh_es_endpoint_in_use(self):
        self.mockRouteInUse.return_value = True

        FlaskJWE(self.app)

        self.assertEqual(1, self.mockRouteInUse.call_count)
        self.assertEqual(self.app, self.mockRouteInUse.call_args[0][0])
        self.assertEqual('/serverpubkey', self.mockRouteInUse.call_args[0][1])

        self.assertEqual(0, self.app.add_url_rule.call_count)
        self.assertEqual(1, self.app.logger.error.call_count)
        self.assertEqual('Unable to Create Server EC Public Key JWK Endpoint', self.app.logger.error.call_args[0][0])

    def test_testing_endpoint(self):
        self.app.config['TESTING'] = True

        FlaskJWE(self.app)

        self.assertEqual(2, self.app.add_url_rule.call_count)
        self.assertEqual('/flaskjwe-reverse-echo', self.app.add_url_rule.call_args[0][0])
        self.assertEqual('test-reverse-echo', self.app.add_url_rule.call_args[0][1])
        self.assertEqual(self.mockReverseEcho, self.app.add_url_rule.call_args[0][2])
        self.assertEqual(['POST'], self.app.add_url_rule.call_args[1]['methods'])


class TestGetKeys(AutoPatchTestCase):
    def setUp(self):
        self.patcher1 = patch('flask_jwe.FlaskJWE.get_server_key')
        self.mockGetServerKey = self.patcher1.start()

        self.app = MagicMock()
        self.app.config = Config(None)

        self.app.config['JWE_SERVER_RSA_KEY'] = 'RSA_KEY'
        self.app.config['JWE_SERVER_SYM_KEY'] = 'SYM_KEY'
        self.mockGetServerKey.return_value = 'ECDH_KEY'

        self.ext = FlaskJWE(self.app)

    def test_go_right(self):

        self.mockGetServerKey.reset_mock()

        keys = self.ext.get_keys('alg')

        self.assertEqual(3, len(keys))
        self.assertIn('RSA_KEY', keys)
        self.assertIn('SYM_KEY', keys)
        self.assertIn('ECDH_KEY', keys)

        self.assertEqual(1, self.mockGetServerKey.call_count)
        self.assertEqual(self.app, self.mockGetServerKey.call_args[0][0])
        self.assertEqual('alg', self.mockGetServerKey.call_args[0][1])

    def test_no_rsa_key(self):

        self.app.config['JWE_SERVER_RSA_KEY'] = None
        self.mockGetServerKey.reset_mock()

        keys = self.ext.get_keys('alg')

        self.assertEqual(2, len(keys))
        self.assertIn('SYM_KEY', keys)
        self.assertIn('ECDH_KEY', keys)

    def test_no_sym_key(self):

        self.app.config['JWE_SERVER_SYM_KEY'] = None
        self.mockGetServerKey.reset_mock()

        keys = self.ext.get_keys('alg')

        self.assertEqual(2, len(keys))
        self.assertIn('RSA_KEY', keys)
        self.assertIn('ECDH_KEY', keys)


class TestOnRequestStart(AutoPatchTestCase):
    def setUp(self):
        self.patcher1 = patch('flask_jwe.FlaskJWE.is_jwe')
        self.patcher2 = patch('flask_jwe.FlaskJWE.jwe_decrypt')
        self.patcher3 = patch('flask_jwe.request')

        self.mockIsJwe = self.patcher1.start()
        self.mockJweDecrypt = self.patcher2.start()
        self.mockRequest = self.patcher3.start()

        self.mockIsJwe.return_value = 'JWEToken'

        self.app = MagicMock()
        self.ext = FlaskJWE(self.app)

    def test_go_right(self):
        self.ext.on_request_start()

        self.assertEqual('JWEToken', self.mockRequest.jwe)
        self.assertIsNotNone(self.mockRequest.set_jwe_response)
        self.assertEqual(1, self.mockJweDecrypt.call_count)
        self.assertEqual('JWEToken', self.mockJweDecrypt.call_args[0][0])

        self.mockRequest.set_jwe_response('JWEToken2')
        self.assertEqual('JWEToken2', self.mockRequest.is_jwe)

    def test_non_jwe(self):
        self.mockIsJwe.return_value = None

        self.ext.on_request_start()

        self.assertIsNone(self.mockRequest.jwe)
        self.assertIsInstance(self.mockRequest.set_jwe_response, MagicMock)
        self.assertEqual(0, self.app.logger.debug.call_count)
        self.assertEqual(0, self.mockJweDecrypt.call_count)


class TesstOnRequestEnd(AutoPatchTestCase):
    def setUp(self):
        self.patcher1 = patch('flask_jwe.request')
        self.patcher2 = patch('flask_jwe.FlaskJWE.jwe_encrypt')

        self.mockRequest = self.patcher1.start()
        self.mockJweEncrypt = self.patcher2.start()

        self.mockJweEncrypt.return_value = 'EncryptedJWE'
        self.mockRequest.__dict__['is_jwe'] = True
        self.responseClass = MagicMock()

        self.app = MagicMock()
        self.ext = FlaskJWE(self.app)

    def test_go_right(self):
        ret = self.ext.on_request_end(self.responseClass)
        self.assertIsNotNone(ret)

        self.assertEqual(1, self.mockJweEncrypt.call_count)
        self.assertEqual(self.responseClass, self.mockJweEncrypt.call_args[0][0])

        self.assertEqual(1, self.responseClass.set_data.call_count)
        self.assertEqual('EncryptedJWE', self.responseClass.set_data.call_args[0][0])
        self.assertEqual('application/jose', self.responseClass.mimetype)
        self.assertEqual('application/jose', self.responseClass.content_type)
        self.assertEqual(self.responseClass, ret)

    def test_not_jwe(self):
        self.mockRequest.__dict__['is_jwe'] = False

        ret = self.ext.on_request_end(self.responseClass)
        self.assertIsNotNone(ret)
        self.assertEqual(self.responseClass, ret)

        self.assertEqual(0, self.mockJweEncrypt.call_count)
        self.assertEqual(0, self.responseClass.set_data.call_count)

    def test_not_jwe_missing_dict_entry(self):
        del self.mockRequest.__dict__['is_jwe']

        ret = self.ext.on_request_end(self.responseClass)
        self.assertIsNotNone(ret)
        self.assertEqual(self.responseClass, ret)

        self.assertEqual(0, self.mockJweEncrypt.call_count)
        self.assertEqual(0, self.responseClass.set_data.call_count)


class TestIsJwe(AutoPatchTestCase):
    def setUp(self):
        self.patcher1 = patch('flask_jwe.jwe.factory')

        self.mockJweFactory = self.patcher1.start()

        self.app = MagicMock()
        self.app.config = Config(None)
        self.ext = FlaskJWE(self.app)

        self.req = MagicMock()
        self.req.content_type = 'application/jose'
        self.req.get_data.return_value = 'RETDATA'

    def test_go_right(self):
        ret = self.ext.is_jwe(self.req)

        self.assertEqual(self.mockJweFactory.return_value, ret)
        self.assertEqual(1, self.req.get_data.call_count)
        self.assertEqual(1, self.mockJweFactory.call_count)
        self.assertEqual('RETDATA', self.mockJweFactory.call_args[0][0])

    def test_non_jose_content_type(self):
        self.req.content_type = 'application/json'

        ret = self.ext.is_jwe(self.req)

        self.assertFalse(ret)
        self.assertEqual(0, self.req.get_data.call_count)
        self.assertEqual(0, self.mockJweFactory.call_count)


class TestJweEncrypt(AutoPatchTestCase):

    def setUp(self):
        self.patcher1 = patch('flask_jwe.JWE')
        self.patcher2 = patch('flask_jwe.ECKey')
        self.patcher3 = patch('flask_jwe.FlaskJWE.get_server_key')
        self.patcher4 = patch('flask_jwe.request')

        self.mockJwe = self.patcher1.start()
        self.mockECKey = self.patcher2.start()
        self.mockGetServerKey = self.patcher3.start()
        self.mockRequest = self.patcher4.start()

        self.mockRequest.jwe.jwt.headers = {
            'alg': 'testalg',
            'enc': 'testenc',
            'epk': {
                'value': 'testepk',
                'kid': 'epk_kid'
            }
        }

        self.ext = FlaskJWE()

        self.responseClass = Mock()
        self.responseClass.get_data.return_value = 'testmsg'
        self.responseClass.content_type = 'application/test-type'

        self.returnJwe = MagicMock()
        self.returnJwe.alg = 'A128KW'
        self.returnJwe._dict = {}
        self.mockJwe.return_value = self.returnJwe

    def test_non_ecdh(self):

        self.ext.jwe_encrypt(self.responseClass)

        self.assertEqual(1, self.mockJwe.call_count)
        self.assertEqual('testmsg', self.mockJwe.call_args[1]['msg'])
        self.assertEqual('testalg', self.mockJwe.call_args[1]['alg'])
        self.assertEqual('testenc', self.mockJwe.call_args[1]['enc'])
        self.assertEqual('application/test-type', self.mockJwe.call_args[1]['cty'])
        self.assertEqual({}, self.returnJwe._dict)
        self.assertFalse(self.mockECKey.called)
        self.assertEqual(1, self.mockJwe.return_value.encrypt.call_count)
        self.assertEqual(0, self.mockGetServerKey.call_count)

    def test_ecdh(self):

        self.returnJwe.alg = 'ECDH-ES'

        self.ext.jwe_encrypt(self.responseClass)

        self.assertEqual(1, self.mockJwe.call_count)
        self.assertEqual('testmsg', self.mockJwe.call_args[1]['msg'])
        self.assertEqual('testalg', self.mockJwe.call_args[1]['alg'])
        self.assertEqual('testenc', self.mockJwe.call_args[1]['enc'])
        self.assertEqual('application/test-type', self.mockJwe.call_args[1]['cty'])
        self.assertEqual(1, self.mockECKey.call_count)
        self.assertEqual('testepk', self.mockECKey.call_args[1]['value'])
        self.assertEqual('epk_kid', self.returnJwe._dict['kid'])
        self.assertEqual(1, self.mockJwe.return_value.encrypt.call_count)
        self.assertEqual(1, self.mockGetServerKey.call_count)


class TestJweDecrypt(AutoPatchTestCase):

    def setUp(self):

        self.patcher1 = patch('flask_jwe.request')
        self.patcher2 = patch('flask_jwe.Response')
        self.patcher3 = patch('flask_jwe.FlaskJWE.get_keys')

        self.mockRequest = self.patcher1.start()
        self.mockResponse = self.patcher2.start()
        self.mockGetKeys = self.patcher3.start()

        self.app = MagicMock()
        self.jwe = MagicMock()
        self.jwe.decrypt.return_value = 'retval'
        self.jwe.jwt.headers = {}
        self.ext = FlaskJWE(self.app)

        self.mockRequest.environ = {}

    def test_go_right(self):

        self.ext.jwe_decrypt(self.jwe)

        self.assertEqual(1, self.jwe.decrypt.call_count)
        self.assertEqual(self.mockGetKeys.return_value, self.jwe.decrypt.call_args[1]['keys'])
        self.assertEqual(True, self.mockRequest.is_jwe)
        self.assertTrue(hasattr(self.mockRequest.get_jwe_data, '__call__'))
        self.assertFalse(self.app.logger.error.called)
        self.assertFalse(self.mockResponse.called)
        self.assertEqual('retval', self.mockRequest.get_jwe_data())
        self.assertEqual('retval', self.mockRequest.data)
        self.assertFalse(self.mockRequest._parse_content_type.called)

    def test_go_right_with_content_type(self):

        self.jwe.jwt.headers['cty'] = 'application/json'

        self.ext.jwe_decrypt(self.jwe)

        self.assertEqual(1, self.jwe.decrypt.call_count)
        self.assertEqual(self.mockGetKeys.return_value, self.jwe.decrypt.call_args[1]['keys'])
        self.assertEqual(True, self.mockRequest.is_jwe)
        self.assertTrue(hasattr(self.mockRequest.get_jwe_data, '__call__'))
        self.assertFalse(self.app.logger.error.called)
        self.assertFalse(self.mockResponse.called)
        self.assertEqual('retval', self.mockRequest.get_jwe_data())
        self.assertEqual('retval', self.mockRequest.data)
        self.assertEqual(1, self.mockRequest._parse_content_type.call_count)
        self.assertIn('CONTENT_TYPE', self.mockRequest.environ)
        self.assertEqual('application/json', self.mockRequest.environ['CONTENT_TYPE'])

    def test_do_not_reset_data(self):

        self.ext.app.config = {'JWE_SET_REQUEST_DATA': False}

        self.ext.jwe_decrypt(self.jwe)

        self.assertNotEqual('retval', self.mockRequest.data)

    def test_decrypt_exception(self):

        self.jwe.decrypt.side_effect = Exception()

        self.ext.jwe_decrypt(self.jwe)

        self.assertEqual(1, self.jwe.decrypt.call_count)
        self.assertEqual(self.mockGetKeys.return_value, self.jwe.decrypt.call_args[1]['keys'])
        self.assertIsInstance(self.mockRequest.is_jwe, MagicMock)
        self.assertIsInstance(self.mockRequest.get_jwe_data, MagicMock)

        self.assertEqual(2, self.app.logger.error.call_count)
        self.assertEqual(1, self.mockResponse.call_count)
        self.assertEqual(json.dumps({'error_message': 'Unable to decrypt JWE Token'}), self.mockResponse.call_args[0][0])
        self.assertEqual(500, self.mockResponse.call_args[1]['status'])
        self.assertEqual('application/json', self.mockResponse.call_args[1]['mimetype'])

class TestReturnJwkPub(AutoPatchTestCase):

    def setUp(self):

        self.patcher1 = patch('flask_jwe.FlaskJWE.get_server_key')
        self.patcher2 = patch('flask_jwe.Response')
        self.patcher3 = patch('flask_jwe.request')
        self.mockGetServerKey = self.patcher1.start()
        self.mockResponse = self.patcher2.start()
        self.mockRequest = self.patcher3.start()

        self.ext = FlaskJWE()

        self.mockKey = MagicMock()
        self.mockGetServerKey.return_value.serialize.return_value = 'serializedKey'
        self.mockRequest.args = {'alg': 'algae'}

    def test_go_right(self):

        self.ext.return_jwk_pub()

        self.assertEqual(1, self.mockGetServerKey.call_count)
        self.assertEqual(self.ext.app, self.mockGetServerKey.call_args[0][0])
        self.assertEqual('algae', self.mockGetServerKey.call_args[0][1])
        self.assertEqual(1, self.mockGetServerKey.return_value.serialize.call_count)
        self.assertFalse(self.mockGetServerKey.return_value.serialize.call_args[0][0])

        from flask_jwe import JOSE_CONTENT_TYPE
        self.assertEqual(1, self.mockResponse.call_count)
        self.assertEqual(json.dumps({'keys': ['serializedKey']}), self.mockResponse.call_args[0][0])
        self.assertEqual(JOSE_CONTENT_TYPE, self.mockResponse.call_args[1]['content_type'])

    def test_no_key(self):

        self.mockGetServerKey.return_value = None

        self.ext.return_jwk_pub()

        self.assertEqual(1, self.mockGetServerKey.call_count)
        self.assertEqual(self.ext.app, self.mockGetServerKey.call_args[0][0])

        from flask_jwe import JOSE_CONTENT_TYPE
        self.assertEqual(1, self.mockResponse.call_count)
        self.assertEqual(json.dumps({'keys': []}), self.mockResponse.call_args[0][0])
        self.assertEqual(JOSE_CONTENT_TYPE, self.mockResponse.call_args[1]['content_type'])

    def test_no_alg(self):

        self.mockRequest.args = {}

        self.ext.return_jwk_pub()

        self.assertEqual(1, self.mockResponse.call_count)
        self.assertEqual(400, self.mockResponse.call_args[1]['status'])
        self.assertFalse(self.mockGetServerKey.called)

class TestRouteInUse(AutoPatchTestCase):

    def setUp(self):

        ep1 = Mock()
        ep1.endpoint = '/test'

        ep2 = Mock()
        ep2.endpoint = '/othertest'

        self.app = MagicMock()
        self.app.url_map.iter_rules.return_value = [ep1, ep2]

        self.ext = FlaskJWE()

    def test_go_right(self):

        self.assertTrue(self.ext.route_in_use(self.app, '/test'))
        self.assertFalse(self.ext.route_in_use(self.app, '/not-here'))

class TestGetServerKey(AutoPatchTestCase):

    def setUp(self):

        self.patcher2 = patch('flask_jwe.FlaskJWE.get_remote_ip')
        self.patcher3 = patch('flask_jwe.FlaskJWE.get_redis_jwk')
        self.patcher4 = patch('flask_jwe.FlaskJWE.set_redis_jwk')
        self.patcher5 = patch('flask_jwe.FlaskJWE.generate_jwk')
        self.patcher6 = patch('flask_jwe.sha256', wraps=sha256)

        self.mockGetRemoteIp = self.patcher2.start()
        self.mockGetRedisJwk = self.patcher3.start()
        self.mockSetRedisJwk = self.patcher4.start()
        self.mockGenerateJwk = self.patcher5.start()
        self.mockSha256 = self.patcher6.start()

        self.mockGetRemoteIp.return_value = '127.0.0.1'

        self.app = MagicMock()
        self.app.config = Config(None)
        self.app.config['JWE_ES_KEY_EXPIRES'] = 60
        self.app.config['JWE_KEY_ENCRYPTION_KEY'] = int(os.urandom(32).encode('hex'),16)
        self.app.config['JWE_SERVER_KEY_PER_IP'] = True

        self.ext = FlaskJWE()
        self.ext.app = self.app

    def test_key_exists(self):

        ret = self.ext.get_server_key(self.app, 'alg')

        self.assertEqual(1, self.mockGetRedisJwk.call_count)
        self.assertEqual('flask-jwe-alg-key-127.0.0.1', self.mockGetRedisJwk.call_args[0][0])
        self.assertFalse(self.mockSetRedisJwk.called)
        self.assertFalse(self.mockGenerateJwk.called)
        self.assertEqual(self.mockGetRedisJwk.return_value, ret)

    def test_key_not_exist(self):

        self.mockGetRedisJwk.return_value = None

        ret = self.ext.get_server_key(self.app, 'alg')

        self.assertEqual(1, self.mockGetRedisJwk.call_count)
        self.assertEqual('flask-jwe-alg-key-127.0.0.1', self.mockGetRedisJwk.call_args[0][0])

        self.assertEqual(1, self.mockSetRedisJwk.call_count)
        self.assertEqual('flask-jwe-alg-key-127.0.0.1', self.mockSetRedisJwk.call_args[0][0])
        self.assertEqual(self.mockGenerateJwk.return_value, self.mockSetRedisJwk.call_args[0][1])

        self.assertEqual(1, self.mockGenerateJwk.call_count)
        self.assertEqual(1, self.mockSha256.call_count)
        self.assertEqual('flask-jwe-alg-key-127.0.0.1', self.mockSha256.call_args[0][0])
        self.assertEqual('alg', self.mockGenerateJwk.call_args[0][1])

        self.assertEqual(self.mockSetRedisJwk.return_value, ret)

    def test_no_key_per_ip(self):

        self.app.config['JWE_SERVER_KEY_PER_IP'] = False

        ret = self.ext.get_server_key(self.app, 'alg')

        self.assertIsNotNone(ret)
        self.assertFalse(self.mockGetRemoteIp.called)
        self.assertEqual('flask-jwe-alg-key', self.mockGetRedisJwk.call_args[0][0])

    def test_exception(self):

        self.mockGetRedisJwk.side_effect = Exception()

        ret = self.ext.get_server_key(self.app, 'alg')

        self.assertIsNone(ret)


class TestReverseEcho(AutoPatchTestCase):

    def setUp(self):

        self.patcher1 = patch('flask_jwe.request')
        self.patcher2 = patch('flask_jwe.Response')

        self.mockRequest = self.patcher1.start()
        self.mockResponse = self.patcher2.start()

        self.mockRequest.is_jwe = True
        self.mockRequest.get_jwe_data.return_value = 'tacocat1'
        self.mockRequest.get_data.return_value = 'tacocat1'

        self.ext = FlaskJWE()
        self.ext.app = MagicMock()
        self.ext.app.config = {'JWE_SET_REQUEST_DATA': True}

    def test_go_right_set_request_data(self):

        self.ext.reverse_echo()

        self.assertEqual(0, self.mockRequest.get_jwe_data.call_count)
        self.assertEqual(1, self.mockRequest.get_data.call_count)
        self.assertEqual(1, self.mockResponse.call_count)
        self.assertEqual('1tacocat', self.mockResponse.call_args[0][0])

    def test_go_right_not_set_request_data(self):

        self.ext.app.config['JWE_SET_REQUEST_DATA'] = False

        self.ext.reverse_echo()

        self.assertEqual(1, self.mockRequest.get_jwe_data.call_count)
        self.assertEqual(0, self.mockRequest.get_data.call_count)
        self.assertEqual(1, self.mockResponse.call_count)
        self.assertEqual('1tacocat', self.mockResponse.call_args[0][0])

    def test_not_jwe_decorator_test(self):

        self.mockRequest.is_jwe = False

        ret = self.ext.reverse_echo()

        # Verify Decorator
        self.assertTrue(self.mockResponse.called)
        self.assertEqual('JWE Request Required', self.mockResponse.call_args[0][0])
        self.assertEqual('text/plain', self.mockResponse.call_args[1]['mimetype'])
        self.assertEqual(400, self.mockResponse.call_args[1]['status'])

###############################
# Test Utility Functionality
###############################

class TestGenerateJwk(AutoPatchTestCase):

    def setUp(self):

        self.patcher1 = patch('flask_jwe.NISTEllipticCurve')
        self.patcher2 = patch('flask_jwe.ECKey')
        self.patcher3 = patch('flask_jwe.RSAKey')
        self.patcher4 = patch('flask_jwe.RSA')

        self.mockNISTCurve = self.patcher1.start()
        self.mockECKey = self.patcher2.start()
        self.mockRSAKey= self.patcher3.start()
        self.mockRSA = self.patcher4.start()

        self.ext = FlaskJWE()
        self.ext.app = MagicMock()
        self.ext.app.config = {'ECDH_CURVE': 'curve'}

        self.mockNISTCurve.by_name.return_value.key_pair.return_value = ('priv', ('x', 'y'))

    def test_ecdh(self):

        ret = self.ext.generate_jwk('kid', 'ECDH-ES')

        self.assertEqual(self.mockECKey.return_value, ret)

        self.assertFalse(self.mockRSAKey.called)

        self.assertEqual(1, self.mockNISTCurve.by_name.call_count)
        self.assertEqual('curve', self.mockNISTCurve.by_name.call_args[0][0])
        self.assertEqual(1, self.mockNISTCurve.by_name.return_value.key_pair.call_count)

        self.assertEqual(1, self.mockECKey.call_count)
        self.assertEqual('x', self.mockECKey.call_args[1]['x'])
        self.assertEqual('y', self.mockECKey.call_args[1]['y'])
        self.assertEqual('priv', self.mockECKey.call_args[1]['d'])
        self.assertEqual('curve', self.mockECKey.call_args[1]['crv'])
        self.assertEqual('kid', self.mockECKey.call_args[1]['kid'])

    def test_rsa(self):

        ret = self.ext.generate_jwk('kid', 'RSA')

        self.assertEqual(self.mockRSAKey.return_value, ret)

        self.assertFalse(self.mockECKey.called)

        self.assertEqual(0, self.mockNISTCurve.by_name.call_count)
        self.assertEqual(1, self.mockRSA.generate.call_count)
        self.assertEqual(2048, self.mockRSA.generate.call_args[0][0])

        self.assertEqual(1, self.mockRSAKey.call_count)
        self.assertEqual(self.mockRSA.generate.return_value, self.mockRSAKey.call_args[1]['key'])
        self.assertEqual('kid', self.mockRSAKey.call_args[1]['kid'])

    def test_invalid_algorithm(self):

        ret = self.ext.generate_jwk('kid', 'invalid')

        self.assertIsNone(ret)
        self.assertFalse(self.mockECKey.called)
        self.assertFalse(self.mockRSAKey.called)

class TestBuildJwk(AutoPatchTestCase):

    def setUp(self):

        self.patcher1 = patch('flask_jwe.ECKey')
        self.patcher2 = patch('flask_jwe.RSAKey')

        self.mockECKey = self.patcher1.start()
        self.mockRSAKey = self.patcher2.start()

        self.serialized_jwk = json.dumps({'kty': 'EC'})
        self.ext = FlaskJWE()

    def test_ec(self):

        ret = self.ext.build_jwk(self.serialized_jwk)

        self.assertEqual(self.mockECKey.return_value, ret)
        self.assertEqual('EC', self.mockECKey.call_args[1]['kty'])
        self.assertFalse(self.mockRSAKey.called)

    def test_rsa(self):

        self.serialized_jwk = json.dumps({'kty': 'RSA'})
        ret = self.ext.build_jwk(self.serialized_jwk)

        self.assertEqual(self.mockRSAKey.return_value, ret)
        self.assertEqual('RSA', self.mockRSAKey.call_args[1]['kty'])
        self.assertFalse(self.mockECKey.called)

    def test_no_kty(self):

        self.serialized_jwk = json.dumps({'kty': 'none'})

        ret = self.ext.build_jwk(self.serialized_jwk)

        self.assertIsNone(ret)
        self.assertFalse(self.mockECKey.called)
        self.assertFalse(self.mockRSAKey.called)

class TestGetRedisJwk(AutoPatchTestCase):

    def setUp(self):

        self.patcher1 = patch('flask_jwe.FlaskJWE.get_redis_client')
        self.patcher2 = patch('flask_jwe.FlaskJWE.build_jwk')
        self.patcher3 = patch('flask_jwe.AES')
        self.patcher4 = patch('flask_jwe.unpad')

        self.mockGetRedisClient = self.patcher1.start()
        self.mockBuildJwk = self.patcher2.start()
        self.mockAES = self.patcher3.start()
        self.mockUnpad = self.patcher4.start()

        self.get_value = '00112233445566778899aabbccddeeff'
        self.mockRedis = MagicMock()
        self.mockRedis.get.return_value = self.get_value
        self.mockRedis.ttl.return_value = -1
        self.mockGetRedisClient.return_value = self.mockRedis

        self.app = Mock()
        self.app.config = {
            'JWE_REDIS_URI': 'redis_uri',
            'JWE_ES_KEY_EXPIRES': 0,
            'JWE_KEY_ENCRYPTION_KEY': 'KEK'
        }
        self.ext = FlaskJWE()
        self.ext.app = self.app

        self.key_name = 'key_name'

    def test_key_exists_encrypted(self):

        ret = self.ext.get_redis_jwk(self.key_name)

        self.assertEqual(self.mockBuildJwk.return_value, ret)

        self.assertEqual(1, self.mockGetRedisClient.call_count)
        self.assertEqual(self.app.config['JWE_REDIS_URI'], self.mockGetRedisClient.call_args[1]['connection_uri'])

        self.assertEqual(1, self.mockRedis.get.call_count)
        self.assertEqual(self.key_name, self.mockRedis.get.call_args[0][0])

        self.assertEqual(1, self.mockAES.new.call_count)
        self.assertEqual(self.app.config['JWE_KEY_ENCRYPTION_KEY'], self.mockAES.new.call_args[0][0])
        self.assertEqual(self.mockAES.MODE_CBC, self.mockAES.new.call_args[0][1])
        self.assertEqual(b64decode(self.get_value)[:16], self.mockAES.new.call_args[0][2])

        self.assertEqual(1, self.mockAES.new.return_value.decrypt.call_count)
        self.assertEqual(b64decode(self.get_value)[16:], self.mockAES.new.return_value.decrypt.call_args[0][0])

        self.assertEqual(1, self.mockUnpad.call_count)
        self.assertEqual(self.mockAES.new.return_value.decrypt.return_value, self.mockUnpad.call_args[0][0])

        self.assertEqual(1, self.mockBuildJwk.call_count)
        self.assertEqual(self.mockUnpad.return_value, self.mockBuildJwk.call_args[0][0])

    def test_key_exists_non_encrypted(self):

        self.app.config['JWE_KEY_ENCRYPTION_KEY'] = None

        ret = self.ext.get_redis_jwk(self.key_name)

        self.assertEqual(self.mockBuildJwk.return_value, ret)

        self.assertEqual(1, self.mockGetRedisClient.call_count)
        self.assertEqual(self.app.config['JWE_REDIS_URI'], self.mockGetRedisClient.call_args[1]['connection_uri'])

        self.assertEqual(1, self.mockRedis.get.call_count)
        self.assertEqual(self.key_name, self.mockRedis.get.call_args[0][0])

        self.assertEqual(0, self.mockAES.new.call_count)
        self.assertEqual(1, self.mockBuildJwk.call_count)
        self.assertEqual(self.get_value, self.mockBuildJwk.call_args[0][0])

    def test_key_exists_expire_update(self):

        self.app.config['JWE_KEY_ENCRYPTION_KEY'] = None
        self.app.config['JWE_ES_KEY_EXPIRES'] = 60

        ret = self.ext.get_redis_jwk(self.key_name)

        self.assertEqual(self.mockBuildJwk.return_value, ret)

        self.assertEqual(1, self.mockGetRedisClient.call_count)
        self.assertEqual(self.app.config['JWE_REDIS_URI'], self.mockGetRedisClient.call_args[1]['connection_uri'])

        self.assertEqual(1, self.mockRedis.get.call_count)
        self.assertEqual(self.key_name, self.mockRedis.get.call_args[0][0])

        self.assertEqual(1, self.mockRedis.ttl.call_count)
        self.assertEqual(self.key_name, self.mockRedis.ttl.call_args[0][0])
        self.assertEqual(1, self.mockRedis.expire.call_count)
        self.assertEqual(self.key_name, self.mockRedis.expire.call_args[0][0])
        self.assertEqual(self.app.config['JWE_ES_KEY_EXPIRES'], self.mockRedis.expire.call_args[0][1])

        self.assertEqual(0, self.mockAES.new.call_count)
        self.assertEqual(1, self.mockBuildJwk.call_count)
        self.assertEqual(self.get_value, self.mockBuildJwk.call_args[0][0])

    def test_key_does_not_exist(self):

        self.mockRedis.get.return_value = None

        ret = self.ext.get_redis_jwk(self.key_name)

        self.assertIsNone(ret)
        self.assertFalse(self.mockBuildJwk.called)

    def test_no_redis_client(self):

        self.mockGetRedisClient.return_value = None

        ret = self.ext.get_redis_jwk(self.key_name)

        self.assertIsNone(ret)
        self.assertFalse(self.mockBuildJwk.called)

class TestSetRedisJwk(AutoPatchTestCase):

    def setUp(self):

        self.patcher1 = patch('flask_jwe.FlaskJWE.get_redis_client')
        self.patcher2 = patch('flask_jwe.Random')
        self.patcher3 = patch('flask_jwe.AES')
        self.patcher4 = patch('flask_jwe.FlaskJWE.get_redis_jwk')
        self.patcher5 = patch('flask_jwe.pad')

        self.mockGetRedisClient = self.patcher1.start()
        self.mockRandom = self.patcher2.start()
        self.mockAES = self.patcher3.start()
        self.mockGetRedisJwk = self.patcher4.start()
        self.mockPad = self.patcher5.start()

        self.mockRedis = MagicMock()
        self.mockGetRedisClient.return_value = self.mockRedis

        self.app = Mock()
        self.app.config = {
            'JWE_REDIS_URI': 'redis_uri',
            'JWE_ES_KEY_EXPIRES': 0,
            'JWE_KEY_ENCRYPTION_KEY': '65253a35e0d1978fc24ca2dae2957699ac650cad2612ac7682b257ea3fc3b8cb'.decode('hex')
        }
        self.ext = FlaskJWE()
        self.ext.app = self.app

        self.key_name = 'key_name'
        self.jwk = MagicMock()
        self.jwk.serialize.return_value = {}

        self.mockRandom.new.return_value.read.return_value = '0123456789'
        self.mockAES.new.return_value.encrypt.return_value = 'encrypted'

    def test_set_encrypted_key(self):

        ret = self.ext.set_redis_jwk(self.key_name, self.jwk)

        self.assertEqual(self.mockGetRedisJwk.return_value, ret)

        self.assertEqual(1, self.mockGetRedisClient.call_count)
        self.assertEqual(self.app.config['JWE_REDIS_URI'], self.mockGetRedisClient.call_args[1]['connection_uri'])

        self.assertEqual(1, self.jwk.serialize.call_count)
        self.assertTrue(self.jwk.serialize.call_args[0][0])
        self.assertEqual(1, self.mockPad.call_count)
        self.assertEqual('{}', self.mockPad.call_args[0][0])

        self.assertEqual(1, self.mockRandom.new.return_value.read.call_count)
        self.assertEqual(self.mockAES.block_size, self.mockRandom.new.return_value.read.call_args[0][0])

        self.assertEqual(1, self.mockAES.new.call_count)
        self.assertEqual(self.app.config['JWE_KEY_ENCRYPTION_KEY'], self.mockAES.new.call_args[0][0])
        self.assertEqual(self.mockAES.MODE_CBC, self.mockAES.new.call_args[0][1])
        self.assertEqual(self.mockRandom.new.return_value.read.return_value, self.mockAES.new.call_args[0][2])

        self.assertEqual(1, self.mockAES.new.return_value.encrypt.call_count)
        self.assertEqual(self.mockPad.return_value, self.mockAES.new.return_value.encrypt.call_args[0][0])

        self.assertEqual(1, self.mockRedis.setnx.call_count)
        self.assertEqual(self.key_name, self.mockRedis.setnx.call_args[0][0])
        self.assertEqual(b64encode('0123456789encrypted'), self.mockRedis.setnx.call_args[0][1])

        self.assertEqual(1, self.mockGetRedisJwk.call_count)
        self.assertEqual(self.key_name, self.mockGetRedisJwk.call_args[0][0])

    def test_set_non_encrypted_key(self):

        self.app.config['JWE_KEY_ENCRYPTION_KEY'] = None

        ret = self.ext.set_redis_jwk(self.key_name, self.jwk)

        self.assertEqual(self.mockGetRedisJwk.return_value, ret)

        self.assertEqual(1, self.mockGetRedisClient.call_count)
        self.assertEqual(self.app.config['JWE_REDIS_URI'], self.mockGetRedisClient.call_args[1]['connection_uri'])

        self.assertFalse(self.mockPad.called)

        self.assertEqual(1, self.jwk.serialize.call_count)
        self.assertTrue(self.jwk.serialize.call_args[0][0])

        self.assertEqual(1, self.mockRedis.setnx.call_count)
        self.assertEqual(self.key_name, self.mockRedis.setnx.call_args[0][0])
        self.assertEqual('{}', self.mockRedis.setnx.call_args[0][1])

        self.assertEqual(1, self.mockGetRedisJwk.call_count)
        self.assertEqual(self.key_name, self.mockGetRedisJwk.call_args[0][0])

    def test_invalid_key_length(self):

        self.app.config['JWE_KEY_ENCRYPTION_KEY'] = '11223344'.decode('hex')

        ret = self.ext.set_redis_jwk(self.key_name, self.jwk)

        self.assertIsNone(ret)

        self.assertEqual(1, self.mockGetRedisClient.call_count)
        self.assertEqual(self.app.config['JWE_REDIS_URI'], self.mockGetRedisClient.call_args[1]['connection_uri'])

        self.assertFalse(self.mockPad.called)
        self.assertFalse(self.mockRedis.setnx.called)
        self.assertFalse(self.mockGetRedisJwk.called)

    def test_redis_client_failure(self):

        self.mockGetRedisClient.return_value = None

        ret = self.ext.set_redis_jwk(self.key_name, self.jwk)

        self.assertIsNone(ret)

        self.assertEqual(1, self.mockGetRedisClient.call_count)
        self.assertEqual(self.app.config['JWE_REDIS_URI'], self.mockGetRedisClient.call_args[1]['connection_uri'])

        self.assertFalse(self.mockPad.called)
        self.assertFalse(self.mockRedis.setnx.called)
        self.assertFalse(self.mockGetRedisJwk.called)

class TestGetRemoteIp(AutoPatchTestCase):

    def setUp(self):

        self.patcher1 =  patch('flask_jwe.request')
        self.mockRequest = self.patcher1.start()

        # Null Request Data
        self.mockRequest.access_route = []
        self.mockRequest.remote_addr = None

        self.ext = FlaskJWE()

    def test_access_route(self):
        self.mockRequest.access_route = ['10.10.10.10']
        ret = self.ext.get_remote_ip()
        self.assertEqual('10.10.10.10', ret)

    def test_remote_addr(self):
        self.mockRequest.remote_addr = '10.10.10.10'
        ret = self.ext.get_remote_ip()
        self.assertEqual('10.10.10.10', ret)

    def test_default_addr(self):
        ret = self.ext.get_remote_ip()
        self.assertEqual('127.0.0.1', ret)

class TestGetRedisClient(AutoPatchTestCase):

    def setUp(self):

        self.patcher1 = patch('flask_jwe.urlparse', wraps=urlparse)
        self.patcher2 = patch('flask_jwe.StrictRedis')
        self.patcher3 = patch('flask_jwe.Sentinel')

        self.mockUrlParse = self.patcher1.start()
        self.mockRedis = self.patcher2.start()
        self.mockSentinel = self.patcher3.start()

        self.mockRedisClient = Mock()
        self.mockRedisClient.info.return_value = 'OK'

        self.mockSentinelObj = Mock()
        self.mockSentinelObj.slave_for.return_value = self.mockRedisClient
        self.mockSentinelObj.master_for.return_value = self.mockRedisClient

        self.mockSentinel.return_value = self.mockSentinelObj

        self.redis_uri = 'redis://localhost:6379/0'
        self.redis_sentinel_uri = 'redis+sentinel://localhost:1234,otherhost:1234/serviceName'
        self.mockApp = MagicMock()
        self.mockLogger = MagicMock()
        self.mockApp.logger = self.mockLogger

        self.ext = FlaskJWE(self.mockApp)

    def test_go_right_config(self):

        ret = self.ext.get_redis_client(connection_uri=self.redis_uri)

        self.assertIsNotNone(ret)
        self.assertEqual(self.mockRedis.return_value, ret)

        self.assertEqual(1, self.mockUrlParse.call_count)
        self.assertEqual(self.redis_uri, self.mockUrlParse.call_args[0][0])

        self.assertEqual(1, self.mockRedis.call_count)
        self.assertEqual('localhost', self.mockRedis.call_args[1]['host'])
        self.assertEqual(6379, self.mockRedis.call_args[1]['port'])
        self.assertNotIn('0', self.mockRedis.call_args[1])

        self.assertFalse(self.mockSentinel.called)

    def test_go_right_sentinel_master(self):

        ret = self.ext.get_redis_client(connection_uri=self.redis_sentinel_uri)

        self.assertIsNotNone(ret)
        self.assertEqual(self.mockRedisClient, ret)

        self.assertEqual(1, self.mockUrlParse.call_count)
        self.assertEqual(self.redis_sentinel_uri, self.mockUrlParse.call_args[0][0])

        self.assertEqual(1, self.mockSentinel.call_count)
        self.assertEqual([('localhost', '1234'), ('otherhost', '1234')], self.mockSentinel.call_args[0][0])
        self.assertEqual(2, self.mockSentinel.call_args[1]['socket_timeout'])
        self.assertTrue(self.mockSentinel.call_args[1]['retry_on_timeout'])

        self.assertFalse(self.mockSentinelObj.slave_for.called)
        self.assertEqual(1, self.mockSentinelObj.master_for.call_count)
        self.assertEqual('serviceName', self.mockSentinelObj.master_for.call_args[0][0])

        self.assertEqual(1, self.mockRedisClient.info.call_count)

    def test_go_right_sentinel_slave(self):

        ret = self.ext.get_redis_client(connection_uri=self.redis_sentinel_uri, read_only=True)

        self.assertIsNotNone(ret)
        self.assertEqual(self.mockRedisClient, ret)

        self.assertFalse(self.mockSentinelObj.master_for.called)
        self.assertEqual(1, self.mockSentinelObj.slave_for.call_count)
        self.assertEqual('serviceName', self.mockSentinelObj.slave_for.call_args[0][0])

        self.assertEqual(1, self.mockRedisClient.info.call_count)

    def test_slave_info_exception(self):

        from redis.sentinel import SlaveNotFoundError
        self.mockRedisClient.info.side_effect = SlaveNotFoundError('Slave Connection Failed')

        ret = self.ext.get_redis_client(connection_uri=self.redis_sentinel_uri, read_only=True)

        self.assertIsNone(ret)

    def test_master_info_exception(self):

        from redis.sentinel import MasterNotFoundError
        self.mockRedisClient.info.side_effect = MasterNotFoundError('Master Connection Failed')

        ret = self.ext.get_redis_client(connection_uri=self.redis_sentinel_uri)

        self.assertIsNone(ret)

    def test_connection_error_once(self):

        from redis.sentinel import MasterNotFoundError
        self.mockRedisClient.info.side_effect = [MasterNotFoundError('Master Connection Failed'), 'bob']

        ret = self.ext.get_redis_client(connection_uri=self.redis_sentinel_uri)

        self.assertIsNotNone(ret)
        self.assertEqual(self.mockRedisClient, ret)

        self.assertEqual(2, self.mockSentinelObj.master_for.call_count)
        self.assertEqual('serviceName', self.mockSentinelObj.master_for.call_args[0][0])

        self.assertEqual(2, self.mockRedisClient.info.call_count)

    def test_invalid_scheme(self):

        ret = self.ext.get_redis_client(connection_uri='unknown://host:1234/serviceName')

        self.assertIsNone(ret)

if __name__ == '__main__':
    unittest.main()
