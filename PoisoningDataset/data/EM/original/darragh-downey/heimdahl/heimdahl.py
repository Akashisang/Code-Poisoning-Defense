import binascii
import base64
import ldap
import sys
import uuid
import redis

from datetime import datetime, timedelta, tzinfo, timezone
from bottle import *
from jose import jwt
from gevent import monkey; monkey.patch_all()

from zmq import green as zmq
from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes

"""
HEIMDAHL
Must have role of admin to access.

No one can just 'Sign up' must be entered by admin. 
In the case of contractors they can submit a 'Sign up' request 
which can be declined if it is found to be a fraudulent claim.
"""

#conn = ldap.initialize('ldap://10.44.9.165', bytes_mode=False)
#conn.simple_bind('admin', 'some_password') 
base_dn = "dc=some_organisation,dc=com"
tds_dn = "DC=organisation_name,DC=local"

#pool = redis.ConnectionPool(host='localhost', port=6739, db=0)
r = redis.Redis()

tds = { 'addr': 'ldap://some.ip.address', 
        'base': 'OU=Active Users,OU=SBSUsers,OU=Users,OU=MyBusiness,%s' % tds_dn,
        'un_filter': '(&(objectClass=Person)(sAMAccountName=%s))',
        'cn_filter': '(&(objectClass=Person)(cn=%s))',
        'attr': ['objectguid', 'name', 'mail', 'pwdLastSet'],
        'admin': 'cn=Some_Admin,ou=Admin Accounts,ou=SBSUsers,ou=Users,ou=MyBusiness,%s' % tds_dn, 
        'admin_p': 'Some_Admin_Password'}

ext = { 'addr': 'ldap://some.ip.address', 
        'base': 'ou=users,dc=some_organisation,dc=com,dc=au', 
        'un_filter': '(&(objectClass=person)(uid=%s))', 
        'cn_filter': '(&(objectClass=person)(cn=%s))',
        'attr': ['entryuuid', 'email', 'cn', 'pwdChangedTime', 'createTimestamp'],
        'admin': 'cn=admin,%s' % base_dn, 
        'admin_p': 'Some_Admin_Password'}

ads = [ext, tds]

allowed = ['some_rest_service']

roles = ['some_rest_service:user', 'some_rest_service:admin', 
         'some_rest_service:isser', 'some_rest_service:occ']

ctx = zmq.Context()
req = ctx.socket(zmq.REQ)
req.connect('tcp://some.ip.address:5560')
rep = ctx.socket(zmq.REP)

# Address(es), content, 
def notify(message):
    req.send_json(message)
    if req.recv() == 'ok':
        return True
    return False


def enable_cors(fn):
    def _enable_cors(*args, **kwargs):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, PUT, POST, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = """Authorisation, Origin, Accept, 
        Content-Type, X-Requested-With, X-CSRF-Token"""

        if request.method != 'OPTIONS':
            return fn(*args, **kwargs)
    return _enable_cors


def sanitize(usr):
    if not usr:
        response.status = 401
        return
    usr = usr[0][1]
    for i in usr:
        if type(usr[i]) is list:
            if i == 'objectGUID':
                usr[i] = [uuid.UUID(bytes=t).hex for t in usr[i]]
            else:
                usr[i] = [t.decode('utf-8') for t in usr[i]]
            #print(usr[i], 'sanitize loop')
    response.status = 200
    return usr


@route('/signup/request', methods=['OPTIONS', 'POST'])
def sign_up_request():
    """
    Request details contains the service they wish to access, their name, email, phone, company
    """
    request_details = request.json
    message = {'sys_admin': 'sysadmin@organisation.com', 'message': request_details}
    # Notify administrators ZMQ message pass to SPLASH and internal notification system?
    notify(message)
    return


@route('/auth', method=['OPTIONS', 'POST'])
@enable_cors
def test_auth():
    details = request.json
    usr = None
    try:
        if 'uname' and 'pwd' and 'srv' in details:
            if details['srv'] in allowed:
                usr = attempt_auth(details['uname'], details['pwd'])
                print(usr)
    except Exception as e:
        print('/auth: ', e)
        response.status = 401
        return
    if not usr:
        print('user not found')
        response.status = 401
        return
    usr = sanitize(usr)
    refresh, auth, profile = gen_tokens(usr, details['srv'])
    return {'refresh': refresh, 'id_token': auth, 'profile': profile}


def attempt_auth(uname, pwd):
    # external first then internal
    # else 401

    # These values should be loaded from config files
    # Could have n ldap servers; in reality will have a proxy slapd service
    # which points to these services
    res = {}
    for i in ads:
        r = ldap_search(i['addr'], i['admin'], i['admin_p'], i['base'], i['un_filter'] % uname)
        #print('result of search', r)
        if not r:
            continue
        res[i['addr']] = r[0][1]
    if not res:
        print(401, '/attempt_auth: Unauthorised error: User not found!')
        response.status = 401
        return
    else:
        addrs = list(res.keys())
        b = ''
        f = ''
        attrs = None
        for i in ads:
            if addrs[0] in i.values():
                b = i['base']
                f = i['cn_filter'] % res[addrs[0]]['cn'][0].decode('utf-8')
                attrs = i['attr']
                cn = 'cn=%s,%s' % (res[addrs[0]]['cn'][0].decode('utf-8'), i['base'])
        t = ldap_search(addrs[0], cn, pwd, b, f, attrs)
        return t


# Given a username find it's associated CN
def ldap_search(ldap_addr, bind_u_dn, bind_p_dn, ldap_search_base, ldap_filter, ldap_attrs=['cn']):
    res = []
    print('ldap search')
    try:
        connect = ldap.initialize(ldap_addr)
        connect.set_option(ldap.OPT_REFERRALS, 0)
        try:
            connect.simple_bind_s(bind_u_dn, bind_p_dn)
            res = connect.search_s(ldap_search_base, ldap.SCOPE_SUBTREE, 
                                   ldap_filter, ldap_attrs)
            print(res, 'search result')
            connect.unbind_s()
        except ldap.INVALID_CREDENTIALS as e:
            connect.unbind_s()
            print('ldap_search: Invalid Credentials: ', e)
            response.status = 401
            return
        except Exception as e:
            print('ldap_search: Inner exception', e)
            response.status = 500
            return
    except ldap.LDAPException as e:
        print(500, 'ldap_search: Server error', e)
        response.status = 500
        return
    except Exception as e:
        print('ldap_search: Outer Exception', e)
        response.status = 500
        return
    if not res:
        response.status = 401
        #print(response.status)
        return None
    response.status = 200
    return res


@route('/tkn/refresh')
def refresh():
    print('refreshing token')
    bear = request.get_header('Authorization')
    b = bear.split()[1]
    details = request.json()
    # get token from Redis otherwise return 401
    if b not in redis:
        response.status = 401
        return
    else:
        enc = redis.get(b)
        aes = AESCipher()
        aes.decrypt(enc)
    return gen_auth_tkn(details['srv'] ,current_timestamp())


# for use in logging in 
def gen_tokens(usr, service, auexp=60, reexp=15000):
    cur = current_timestamp()
    aes = AESCipher()
    header = 'rf_tk+' + str(cur)
    # change the message to 'first name surname logged in at current timestamp'
    name = ''
    if 'cn' in usr:
        name = usr['cn'][0]
    else:
        name = usr['name'][0]
    e_str = '%s logged in at %d' % (name, cur)
    nonce, hdr, enc, mac = aes.encrypt(header.encode(), e_str.encode())
    # set up redis hash containing nonce hdr and mac for use in decrypting the enctypted message
    #reds_insert(name, usr, nonce, hdr, mac)
    # generate and return three JWTs
    refresh = gen_refresh_tkn(header, binascii.hexlify(enc).decode(), service, cur)
    auth = gen_auth_tkn(service, cur)
    profile = gen_profile_tkn(name, service, cur)
    return refresh, auth, profile


# generate refresh token
def gen_refresh_tkn(key, val, service, cur, rfrsh_exp=15000):
    reex = current_timestamp(rfrsh_exp)
    refresh = jwt.encode({'rf': key, 'v': val, 'iat': cur, 'exp': reex}, 
            'ultra_secret', algorithm='HS256')
    return refresh


# generate authentication token
def gen_auth_tkn(service, cur, auth_exp=60):
    auex = current_timestamp(auth_exp)
    auth = jwt.encode({'iat': cur, 'exp': auex, 
        'aud': ['tds:usr'], 'iss': 'heim:src'}, 
        'pretty_secret', algorithm='HS256')
    return auth


# generate profile token
def gen_profile_tkn(name, service, cur, auth_exp=300):
    prf_exp = current_timestamp(auth_exp)
    profile = jwt.encode({'name': name, 'iat': cur, 
        'exp': prf_exp, 'role': '%s:%s' % (service, get_role())},
        'secret', algorithm='HS256')
    return profile
    

def get_role():
    return 'user'


def convert_objGUID(guid):
    o = to_hex(guid)
    return o

# Refis pipes batch execute calls - reducing TCP chatter between client and server
# Careful with Redis transactions as they fail without rolling back if there is a 
# prcgramming/syntax error

# Insert 
def red_ins_rfsh(key, vals={}):
    if not vals:
        raise ValueError('Must provide values to insert into Redis')
    pipe = r.pipeline()
    pipe.hmset(key, vals)
    pipe.execute()
    return

# Upsert
def red_ups(key, vals={}):
    if not vals:
        raise ValueError('Must provide values to upsert in Redis')
    pipe = r.pipeline()
    pipe.hmset(key, val)
    pipe.execute()
    return

# Select
def red_sel(key):
    pipe = r.pipeline()
    pipe.hvals(key)
    pipe.execute()
    return

# Delete
def red_del(key):
    r.delete(key)
    return


#BS = 16
#pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
#unpad = lambda s: s[:-ord(s[len(s)-1:])]
#key = b'Sixteen byte key'


def to_hex(b):
    b_s = binascii.hexlify(b)
    s = b_s.decode('ascii')
    return s


class AESCipher():
    def __init__(self, key=b'Sixteen byte key'):
        self.key = key

    def encrypt(self, hdr, raw_msg):
        cipher = AES.new(self.key, AES.MODE_GCM)
        cipher.update(hdr)
        return cipher.nonce, hdr, cipher.encrypt(raw_msg), cipher.digest()


    def decrypt(self, nonce, hdr, emsg, mac):
        cipher = AES.new(self.key, AES.MODE_GCM, nonce)
        cipher.update(hdr)
        d = cipher.decrypt(emsg)
        try:
            cipher.verify(mac)
        except ValueError as e:
            print("Key incorrect or message corrupted")
            return False
        return True


def sign_up_confirm():
    return


def current_timestamp(additional=0):
    return int(datetime.now().timestamp() + additional)
    # return datetime.now(timezone.utc).timestamp() returns a UTC aware timestamp

class Heimdahl():

    def authenticate(token):
        jwt.decode(token, 'secret', algorithms=['HS256'])

    def authorise(token):
        jwt.decode(token, 'secret', algorithms=['HS256'])


if __name__ == '__main__':
    run(host='0.0.0.0', port='7543', debug=True)
else:
    app = default_app()
