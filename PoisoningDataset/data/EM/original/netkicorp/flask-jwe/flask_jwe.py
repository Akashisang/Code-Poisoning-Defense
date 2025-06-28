import json
import random
import traceback

from base64 import b64encode, b64decode
from hashlib import sha256

from future.standard_library import install_aliases
install_aliases()
from urllib.parse import urlparse

from jwkest import jwe, base64_to_long
from jwkest.ecc import NISTEllipticCurve
from jwkest.jwe import JWE
from jwkest.jwk import ECKey, RSAKey
from flask import Response, request
from functools import wraps

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA

try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack

try:
    from redis import StrictRedis, ConnectionError
    from redis.sentinel import Sentinel
except ImportError:
    pass

JOSE_CONTENT_TYPE = 'application/jose'
BS = AES.block_size
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[:-ord(s[len(s)-1:])]

def jwe_request_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not request.__dict__.get('is_jwe', False):
            return Response('JWE Request Required', status=400, mimetype='text/plain')
        return f(*args, **kwargs)
    return wrapped

class FlaskJWE(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):

        ##################
        # Set Defaults
        app.config.setdefault('JOSE_CONTENT_TYPES', ['application/jose', 'application/jose+json'])

        # Set Server Public Key Defaults
        app.config.setdefault('SERVER_PUB_JWK_ENDPOINT', '/serverpubkey')
        app.config.setdefault('JWE_ECDH_ES', True)
        app.config.setdefault('ECDH_CURVE', 'P-256')  # Available Options: ['P-256', 'P-384', 'P-521']
        app.config.setdefault('JWE_ES_KEY_EXPIRES', -1) # Expiration Time in Seconds
        app.config.setdefault('JWE_SERVER_RSA_KEY', None)
        app.config.setdefault('JWE_SERVER_SYM_KEY', None)
        app.config.setdefault('JWE_SERVER_KEY_PER_IP', True)
        app.config.setdefault('JWE_KEY_ENCRYPTION_KEY', None)
        app.config.setdefault('JWE_SET_REQUEST_DATA', True)

        # Set Redis Defaults
        app.config.setdefault('JWE_REDIS_URI', 'redis://localhost:6379/1')

        # Add Public Key Endpoint
        if 'JWE_ECDH_ES' in app.config and app.config['JWE_ECDH_ES']:
            if not self.route_in_use(app, app.config['SERVER_PUB_JWK_ENDPOINT']):
                app.add_url_rule(app.config['SERVER_PUB_JWK_ENDPOINT'], 'jwkendpoint', self.return_jwk_pub)
            else:
                app.logger.error("Unable to Create Server EC Public Key JWK Endpoint")

        # If TESTING mode is True, setup reversing echo endpoint
        if 'TESTING' in app.config and app.config['TESTING']:
            app.add_url_rule('/flaskjwe-reverse-echo', 'test-reverse-echo', self.reverse_echo, methods=['POST'])

        # Setup Before / After Request Processing for JOSE/JWE Request
        app.before_request(self.on_request_start)
        app.after_request(self.on_request_end)

    def get_keys(self, alg):
        keys = []
        if self.app.config['JWE_SERVER_RSA_KEY']:
            keys.append(self.app.config['JWE_SERVER_RSA_KEY'])
        if self.app.config['JWE_SERVER_SYM_KEY']:
            keys.append(self.app.config['JWE_SERVER_SYM_KEY'])

        server_es_key = self.get_server_key(self.app, alg)
        if server_es_key:
            keys.append(server_es_key)

        return keys

    def on_request_start(self):

        def set_jwe_response(is_jwe):
            request.is_jwe = is_jwe

        request.jwe = self.is_jwe(request)
        if request.jwe:
            request.set_jwe_response = set_jwe_response
            self.jwe_decrypt(request.jwe)

    def on_request_end(self, response_class):

        if not request.__dict__.get('is_jwe', False):
            return response_class

        # Re-encrypt JWE
        return_jwe = self.jwe_encrypt(response_class)
        response_class.set_data(return_jwe)
        response_class.mimetype = 'application/jose'
        response_class.content_type = 'application/jose'
        return response_class

    def is_jwe(self, req):

        if req.content_type.lower() not in self.app.config.get('JOSE_CONTENT_TYPES'):
            return False

        return jwe.factory(req.get_data())

    def jwe_encrypt(self, response_class):

        jwe = JWE(
            msg=response_class.get_data(),
            alg=request.jwe.jwt.headers.get('alg'),
            enc=request.jwe.jwt.headers.get('enc'),
            cty=response_class.content_type
        )

        # Add EPK and KID for ECDH-ES Requests
        keys = []
        if jwe.alg.startswith('ECDH-ES'):
            jwe._dict['kid'] = request.jwe.jwt.headers.get('epk', {}).get('kid')
            jwe._dict['epk'] = self.get_server_key(self.app, request.jwe.jwt.headers.get('alg'))
            keys.append(ECKey(**request.jwe.jwt.headers.get('epk')))

        elif jwe.alg.startswith('RSA'):
            # TODO: Finish RSA-ES Once Two-way JWS Questions are Resolved
            pass

        return jwe.encrypt(keys=keys)

    def jwe_decrypt(self, jwe):
        try:
            # Decrypt JWE
            msg = jwe.decrypt(keys=self.get_keys(jwe.jwt.headers.get('alg')))

            def get_jwe_data():
                return msg

            request.is_jwe = True
            request.get_jwe_data = get_jwe_data
            if self.app.config['JWE_SET_REQUEST_DATA']:
                request.data = msg
                request._cached_data = msg
                if jwe.jwt.headers.get('cty'):
                    request.environ['CONTENT_TYPE'] = jwe.jwt.headers.get('cty')
                    if '_parsed_content_type' in request.__dict__:
                        del request.__dict__['_parsed_content_type']
                    request._parse_content_type()
        except Exception as e:
            self.app.logger.error("Unable to decrypt JWE: %s" % str(e))
            self.app.logger.error(traceback.format_exc())
            return Response(json.dumps({'error_message': 'Unable to decrypt JWE Token'}), status=500, mimetype='application/json')

    def return_jwk_pub(self):

        alg = request.args.get('alg', None)
        if not alg:
            return Response('Required parameter "alg" missing', status=400, mimetype='text/plain')

        ret = {'keys': []}

        fullkey = self.get_server_key(self.app, alg)
        if fullkey:
            ret['keys'].append(fullkey.serialize(False))
        return Response(json.dumps(ret), content_type=JOSE_CONTENT_TYPE)

    def route_in_use(self, app, endpoint):
        for rule in app.url_map.iter_rules():
            if endpoint == rule.endpoint:
                return True
        return False

    #########################################
    # Server Ephemeral Static Key Operations
    #########################################
    def get_server_key(self, app, alg):

        try:
            key_name = 'flask-jwe-%s-key' % alg.lower()
            if app.config['JWE_SERVER_KEY_PER_IP']:
                key_name += '-%s' % self.get_remote_ip()

            key = self.get_redis_jwk(key_name)
            if not key:
                app.logger.debug('Creating New %s KeyPair' % alg)
                key = self.set_redis_jwk(key_name, self.generate_jwk(sha256(key_name).hexdigest(), alg))

        except Exception as e:
            app.logger.error('Exception Occurred Generating Retrieving / Setting ES KeyPair: %s' % str(e))
            return None

        return key

    @jwe_request_required
    def reverse_echo(self):
        if self.app.config['JWE_SET_REQUEST_DATA']:
            ret_str = request.get_data()[::-1]
        else:
            ret_str = request.get_jwe_data()[::-1]
        return Response(ret_str)

    #########################################
    # Utility Functionality
    #########################################
    def generate_jwk(self, kid, alg):

        ret_jwk = None

        if alg.startswith('ECDH-ES'):
            curve = NISTEllipticCurve.by_name(self.app.config['ECDH_CURVE'])
            priv, pub = curve.key_pair()
            ret_jwk = ECKey(use='enc', x=pub[0], y=pub[1], d=priv, crv=self.app.config['ECDH_CURVE'], kid=kid)

        elif alg.startswith('RSA'):
            new_rsa_key = RSA.generate(2048)
            ret_jwk = RSAKey(use='enc', key=new_rsa_key, kid=kid)

        return ret_jwk

    def build_jwk(self, serialized_jwk):

        jwk_dict = json.loads(serialized_jwk)

        if jwk_dict.get('kty') == 'EC':
            return ECKey(**jwk_dict)
        elif jwk_dict.get('kty') == 'RSA':
            return RSAKey(**jwk_dict)
        return None

    def get_redis_jwk(self, key_name):

        client = self.get_redis_client(connection_uri=self.app.config['JWE_REDIS_URI'])
        if not client:
            self.app.logger.fatal('Unable to connect to Redis')
            return None

        value = client.get(key_name)
        if not value:
            return None

        if self.app.config['JWE_ES_KEY_EXPIRES'] > 0 and client.ttl(key_name) < 30:
            client.expire(key_name, self.app.config['JWE_ES_KEY_EXPIRES'])

        if not self.app.config['JWE_KEY_ENCRYPTION_KEY']:
            return self.build_jwk(value)

        enc = b64decode(value)
        cipher = AES.new(self.app.config['JWE_KEY_ENCRYPTION_KEY'], AES.MODE_CBC, enc[:16])
        value = unpad(cipher.decrypt(enc[16:]))

        return self.build_jwk(value)

    def set_redis_jwk(self, key_name, jwk):

        client = self.get_redis_client(connection_uri=self.app.config['JWE_REDIS_URI'])
        if not client:
            self.app.logger.fatal('Unable to connect to Redis')
            return None

        if self.app.config['JWE_KEY_ENCRYPTION_KEY']:

            if len(self.app.config['JWE_KEY_ENCRYPTION_KEY']) not in [16, 24, 32]:
                self.app.logger.fatal('JWE_KEY_ENCRYPTION_KEY Must be 16, 24 or 32 bytes long')
                return None

            raw = pad(json.dumps(jwk.serialize(True)))
            iv = Random.new().read(AES.block_size)
            cipher = AES.new(self.app.config['JWE_KEY_ENCRYPTION_KEY'], AES.MODE_CBC, iv)
            key_value = b64encode(iv + cipher.encrypt(raw))
        else:
            key_value = json.dumps(jwk.serialize(True))

        client.setnx(key_name, key_value)

        return self.get_redis_jwk(key_name)

    #########################################
    # Utility Functionality
    #########################################
    def get_remote_ip(self):
        if request.access_route:
            return request.access_route[0]
        else:
            return request.remote_addr or '127.0.0.1'

    def get_redis_client(self, connection_uri=None, read_only=False):

        if not connection_uri:
            self.app.logger.fatal('Redis Connection URI Required')
            return None

        redis_client = None
        redis_uri = urlparse(connection_uri)

        if not StrictRedis or not Sentinel:
            self.app.logger.fatal('Unable to Import Redis')

        if redis_uri.scheme == 'redis':

            redis_args = {
                'host': redis_uri.hostname,
                'port': redis_uri.port
            }
            if redis_uri.path.lstrip('/'):
                redis_args['db'] = redis_uri.path.lstrip('/')

            redis_client = StrictRedis(**redis_args)

        elif redis_uri.scheme == 'redis+sentinel':

            sentinel_endpoints = [(y[0], y[1]) for y in [x.strip().split(':') for x in redis_uri.netloc.split(',')]]
            service_name = redis_uri.path.lstrip('/')
            sentinel = Sentinel(sentinel_endpoints, socket_timeout=2, retry_on_timeout=True)

            for _ in range(5):
                if read_only:
                    redis_client = sentinel.slave_for(service_name)
                else:
                    redis_client = sentinel.master_for(service_name)

                try:
                    redis_client.info()
                    break
                except ConnectionError as e:
                    self.app.logger.warn('Redis %s Sentinel Connection Error: %s' % ('Slave' if read_only else 'Master', str(e)))
                    redis_client = None

        else:
            self.app.logger.fatal('Unsupported REDIS URI Scheme. Unable to get Redis client [SCHEME: %s]' % redis_uri.scheme)

        return redis_client
