# -*- coding: utf-8 -*-

__author__ = 'Takashi Yahata (@paoneJP)'
__copyright__ = 'Copyright (c) 2014, Takashi Yahata'
__license__ = 'MIT License'


import sys
import os
import string
import json
from time import time
from base64 import urlsafe_b64encode, b64encode, b64decode
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer
from logging.handlers import RotatingFileHandler
from urllib.parse import urlencode

from Crypto.Random import random
from Crypto.Hash import SHA256 as _SHA256
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Util.number import long_to_bytes
from Crypto.Util import Counter
import keyring

import bottle
from bottle import view, request, response
from requestlogger import WSGILogger, ApacheFormatter

import config


def random_string(n=8):
    chars = string.ascii_letters + string.digits
    rv = ''.join([random.choice(chars) for i in range(n)])
    return rv


def base64url_encode(s):
    if isinstance(s, str):
        s = s.encode()
    rv = urlsafe_b64encode(s).decode().rstrip('=')
    return rv


class SHA256:
    def new(data=None):
        if isinstance(data, str):
            data = data.encode()
        return _SHA256.new(data)


data_path = None
master_key = None


def get_keypair(client_id):
    hash = SHA256.new(client_id).hexdigest()
    name = data_path + '/' + hash
    aes_key = SHA256.new(master_key+client_id).digest()
    aes = AES.new(aes_key, AES.MODE_CTR, counter=Counter.new(128))
    try:
        f = open(name)
        d1 = json.load(f)
        f.close()
        d2 = json.loads(aes.decrypt(b64decode(d1['data'].encode())).decode())
        rsa_key = RSA.construct((d2['n'], d2['e'],
                                 d2['d'], d2['p'], d2['q'], d2['u']))
    except:
        rsa_key = RSA.generate(1024)
        t = int(time())
        d2 = dict(id=hash,
                  client_id=client_id,
                  n=rsa_key.n, e=rsa_key.e,
                  d=rsa_key.d, p=rsa_key.p, q=rsa_key.q, u=rsa_key.u,
                  generated_at=t)
        d1 = dict(id=hash,
                  data=b64encode(aes.encrypt(json.dumps(d2))).decode(),
                  generated_at=t)
        f = open(name, 'w')
        json.dump(d1, f, sort_keys=True, indent=2)
        f.close()
    return rsa_key


app = bottle.app()
get = app.get
post = app.post

session_store = dict()


def no_cache(callback):
    def wrapper(*args, **kwargs):
        response.set_header('Pragma', 'no-cache')
        response.set_header('Cache-Control', 'no-store')
        return callback(*args, **kwargs)
    return wrapper


def require_session(callback):
    def wrapper(*args, **kwargs):
        id = request.get_cookie('SelfIop_SESSION')
        session = session_store.get(id)
        if not session:
            bottle.abort(500)
        return callback(session, *args, **kwargs)
    return wrapper


@get('/openid://')
@get('/openid:///')  # Windows appends extra slash
def protocol_handler():
    bottle.redirect('/?'+request.query_string)


@get('/')
@get('/authorize')
@no_cache
def authorize():

    # get parameters
    p = request.query
    response_type = p.get('response_type')
    client_id = p.get('client_id', '')
    scope = p.get('scope', '').split()
    nonce = p.get('nonce')
    state = p.get('state')

    # validate parameters
    if not response_type == 'id_token':
        bottle.abort(400, ('unsupported_response_type',
                           'unsupported response_type'))

    if not client_id.startswith('https://') and \
           not client_id.startswith('http://localhost/') and \
           not client_id.startswith('http://localhost:'):
        bottle.abort(400, ('invalid_request', 'invalid client_id'))

    if 'openid' not in scope:
        bottle.abort(400, ('invalid_scope', 'invalid scope'))

    for v in scope:
        if v not in ['openid', 'profile', 'email', 'address', 'phone']:
            bottle.abort(400, ('invalid_scope', 'invalid scope'))

    # create session for user consent action
    id = random_string()
    key = get_keypair(client_id)
    session_store[id] = dict(id=id,
                             client_id=client_id,
                             scope=scope,
                             nonce=nonce,
                             state=state,
                             key=key)
    response.set_cookie('SelfIop_SESSION', id, httponly=True)

    bottle.redirect('/consent')


@get('/consent')
@view('consent.tmpl')
@no_cache
@require_session
def consent_get(session):
    return dict(client_id=session.get('client_id'),
                scope=session.get('scope'))


@post('/consent')
@no_cache
@require_session
def consent_post(session):
    if request.forms.get('deny'):
        p = dict(error='access_denied')
        s = session.get('state')
        if s:
            p.update(dict(state=s))
        q = urlencode(p)
        client_id = session.get('client_id')
        bottle.redirect(client_id+'#'+q)
    bottle.redirect('/token')


@get('/token')
@no_cache
@require_session
def issue_id_token(session):

    # generate claim values
    key = session.get('key')
    sub_jwk = dict(kty='RSA',
                   n=base64url_encode(long_to_bytes(key.n)),
                   e=base64url_encode(long_to_bytes(key.e)))

    v = sub_jwk.get('n') + sub_jwk.get('e')
    sub = base64url_encode(SHA256.new(v).digest())

    iss = 'https://self-issued.me'
    aud = session.get('client_id')
    iat = int(time())
    exp = iat + 600
    nonce = session.get('nonce')

    # generate ID Token
    v = dict(iss=iss, sub=sub, aud=aud, exp=exp, iat=iat, nonce=nonce,
             sub_jwk=sub_jwk)
    for k in list(v.keys()):
        if not v[k]:
            del(v[k])
    claims = base64url_encode(json.dumps(v, sort_keys=True))

    v = dict(typ='JWT', alg='RS256')
    header = base64url_encode(json.dumps(v, sort_keys=True))

    v = PKCS1_v1_5.new(key).sign(SHA256.new(header+'.'+claims))
    sign = base64url_encode(v)

    id_token = header + '.' + claims + '.' + sign

    # build response
    redirect_uri = session.get('client_id')
    p = dict(id_token=id_token)
    s = session.get('state')
    if s:
        p.update(dict(state=s))
    q = urlencode(p)

    bottle.redirect(redirect_uri+'#'+q)


def run(**kwargs):
    global data_path
    global master_key

    os.umask(0o077)

    # setup HOME directory
    home_path = os.getenv('HOME')
    if not home_path or home_path == '/':
        if sys.platform == 'win32':
            home_path = os.getenv('USERPROFILE')
        else:
            home_path = '/var/run'
            os.putenv('HOME', home_path)  # keyring uses HOME env
    data_path = home_path + '/.SelfIop'
    if not os.path.isdir(data_path):
        os.makedirs(data_path)

    # setup keyring
    try:
        master_key = keyring.get_password('SelfIop', 'masterKey')
    except ValueError:
        print('keyring: Invalid Password', file=sys.stderr)
        sys.exit(1)
    if not master_key:
        master_key = random_string(32)
        keyring.set_password('SelfIop', 'masterKey', master_key)

    # setup logging feature
    n = data_path + '/' + config.LOG_FILENAME
    p = os.path.dirname(n)
    if not os.path.isdir(p):
        os.makedirs(p)
    lh = RotatingFileHandler(n, maxBytes=config.LOG_MAX_BYTES,
                             backupCount=config.LOG_BACKUP_COUNT)
    a = WSGILogger(app, [lh], ApacheFormatter())

    # start service
    bottle.run(app=a, host=config.SERVER_NAME, port=config.SERVER_PORT,
               quiet=True, **kwargs)


class XWSGIServer(ThreadingMixIn, WSGIServer):
    pass


if __name__ == '__main__':
    run(server_class=XWSGIServer)
