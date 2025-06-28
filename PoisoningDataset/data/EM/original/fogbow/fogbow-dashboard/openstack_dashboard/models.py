import hashlib
import traceback
import logging
import requests
import horizon
import models as fogbow_models

from django.conf import settings
from django.contrib.auth import models
from django.utils.translation import ugettext_lazy as _
from keystoneclient import exceptions as keystone_exceptions
from openstack_auth import utils
from horizon import messages

from Crypto.Hash import SHA
from Crypto.PublicKey import RSA 
from Crypto.Signature import PKCS1_v1_5 as PKCS1_v1_5
from Crypto.Cipher import PKCS1_v1_5 as Cipher_PKCS1_v1_5
from Crypto.Signature import PKCS1_PSS 
from Crypto.Cipher import AES
from Crypto import Random
from base64 import b64encode, b64decode 
import hashlib
import base64

LOG = logging.getLogger(__name__)

class FogbowConstants():
    
    NETWORK_TERM = '/network/'    
    COMPUTE_TERM = '/compute/'
    STORAGE_TERM = '/storage/'
    LINK_TERM = 'link/'
    LINK_TERM_WITH_VERBOSE = 'link/?verbose=true'
    REQUEST_TERM_WITH_VERBOSE = '/order?verbose=true'
    REQUEST_TERM = '/order/'
    MEMBER_TERM = '/member'
    RESOURCE_TERM = '/-/'
    TOKEN_TERM = '/token'
    QUOTA_TERM = '/quota'
    USAGE_TERM = '/usage'
    
    ORDER_SCHEME = 'scheme="http://schemas.fogbowcloud.org/order#"'
    REQUEST_SCHEME = ORDER_SCHEME
    STORAGE_SCHEME = 'scheme="http://schemas.ogf.org/occi/infrastructure#"'
    
    TARGET = "occi.core.target"
    SOURCE = "occi.core.source"
    DEVICE_ID = "occi.storagelink.deviceid"
    PROVADING_MEMBER_ID = "occi.storagelink.provadingMemberId"        
    STATE_TERM = 'occi.compute.state'
    SHH_PUBLIC_KEY_TERM = 'org.fogbowcloud.order.ssh-public-address'
    CONSOLE_VNC_TERM = 'org.openstack.compute.console.vnc'
    MEMORY_TERM = 'occi.compute.memory'
    CORES_TERM = 'occi.compute.cores'
    IMAGE_SCHEME = 'http://schemas.ogf.org/occi/infrastructure#os_tpl'     
    EXTRA_PORT_SCHEME = 'org.fogbowcloud.order.extra-ports'      
    FOGBOW_REQUIREMENTS_TERM = 'org.fogbowcloud.order.requirements'
    FOGBOW_TYPE_TERM = 'org.fogbowcloud.order.type'
    FOGBOW_STATE_TERM = 'org.fogbowcloud.order.state'
    FOGBOW_USERDATA_TERM = 'org.fogbowcloud.order.extra-user-data'
    FOGBOW_USERDATA_CONTENT_TYPE_TERM = 'org.fogbowcloud.order.extra-user-data-content-type'
    FOGBOW_VALID_FROM_TERM = 'org.fogbowcloud.order.valid-from'
    FOGBOW_VALID_UNTIL_TERM = 'org.fogbowcloud.order.valid-until'
    FOGBOW_SHH_PUBLIC_KEY_REQUEST_TERM = 'org.fogbowcloud.credentials.publickey.data' 
    FOGBOW_COUNT_TERM = 'org.fogbowcloud.order.instance-count'
    SIZE_OCCI = 'org.fogbowcloud.order.storage-size'
    
    FOGBOW_STATE_TERM = 'org.fogbowcloud.order.state'
    FOGBOW_TYPE_TERM = 'org.fogbowcloud.order.type'
    FOGBOW_RESOURCE_KIND_TERM = 'org.fogbowcloud.order.resource-kind'
    FOGBOW_INSTANCE_ID_TERM = 'org.fogbowcloud.order.instance-id' 
    
    NETWORK_VLAN = "occi.network.vlan=";
    NETWORK_LABEL = "occi.network.label=";
    NETWORK_STATE = "occi.network.state=";
    NETWORK_ADDRESS = "occi.network.address=";
    NETWORK_GATEWAY = "occi.network.gateway=";
    NETWORK_ALLOCATION = "occi.network.allocation=";
    NETWORK_ID = "org.fogbowcloud.order.network-id";  

class IdentityPluginConstants():
    AUTH_RAW_KEYSTONE = 'raw_keystone'
    AUTH_RAW_OPENNEBULA = 'raw_opennebula'
    AUTH_KEYSTONE = 'keystone'
    AUTH_TOKEN = 'token'
    AUTH_OPENNEBULA = 'opennebula'
    AUTH_VOMS = 'voms'    
    AUTH_SHIBBOLETH = 'shibboleth'
    AUTH_SIMPLE_TOKEN = 'simpletoken'
    AUTH_NAF = 'naf'
    AUTH_LDAP = 'ldap'
    AUTH_LDAP_BASE = 'base'
    AUTH_LDAP_ENCRYPT = 'encrypt'
    AUTH_PRIVATE_KEY = 'privateKey'
    AUTH_PUBLIC_KEY = 'publicKey'

class Token():
    def __init__(self, id=None):
        self.id = id        
        
    def getId(self):
        return self.id

class User(models.AnonymousUser):
    errors = False
    typeError = ''
    type = 'fogbow_user'
    authorized_tenants = {}
    
    def __init__(self, id=None, token=None, userId=None, username=None, roles=None):
        self.id = id
        self.token = token
        self.userId = userId
        self.username = username
        self.roles = roles

    def __unicode__(self):
        return self.username

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.username)

    @property
    def is_active(self):
        return True

    @property
    def is_superuser(self):
        return False

    def is_authenticated(self, request=None, margin=None):
        return self.token is not None
    
    def save(*args, **kwargs):
        pass
    
    def has_perms(self, perm_list, obj=None):
        return True
    
def getTitle(typeToken):
    title = '' 
    if typeToken == IdentityPluginConstants.AUTH_KEYSTONE:
        title = 'Keystone'
    elif typeToken == IdentityPluginConstants.AUTH_TOKEN:
        title = 'Token'        
    elif typeToken == IdentityPluginConstants.AUTH_OPENNEBULA:
        title = 'Opennebula'        
    elif typeToken == IdentityPluginConstants.AUTH_VOMS:
        title = 'VOMS'      
    elif typeToken == IdentityPluginConstants.AUTH_RAW_KEYSTONE:
        title = 'Raw keystone'      
    elif typeToken == IdentityPluginConstants.AUTH_RAW_OPENNEBULA:
        title = 'Raw opennebula'                                        
    return title

def getErrorMessage(typeToken):
    errorStr = '' 
    if typeToken == IdentityPluginConstants.AUTH_KEYSTONE:
        errorStr = _('Keystone credentials are invalid')
    elif typeToken == IdentityPluginConstants.AUTH_TOKEN:
        errorStr = _('Token invalid')
    elif typeToken == IdentityPluginConstants.AUTH_OPENNEBULA:
        errorStr = _('Opennebula credentials are invalid')        
    elif typeToken == IdentityPluginConstants.AUTH_VOMS:
        errorStr = _('VOMS certificate proxy is invalid')
    elif typeToken == IdentityPluginConstants.AUTH_RAW_KEYSTONE:
        errorStr = _('Raw keystone is invalid')   
    elif typeToken == IdentityPluginConstants.AUTH_RAW_OPENNEBULA:
        errorStr = _('Raw opennebula is invalid')
    elif typeToken == IdentityPluginConstants.AUTH_LDAP:
        errorStr = _('User credentials are invalid')     
    return errorStr 

def checkUserAuthenticated(token):    
    
    print 'Validatin token on: '+settings.FOGBOW_MANAGER_ENDPOINT+FogbowConstants.RESOURCE_TERM
    
    headers = {'content-type': 'text/occi', 'X-Auth-Token' : token.id}
    response = requests.get('%s%s' % (settings.FOGBOW_MANAGER_ENDPOINT, FogbowConstants.RESOURCE_TERM) ,
                                   headers=headers, timeout=10)    
    
    responseStr = response.text

    print 'Response: '+responseStr

    if 'Unauthorized' in responseStr or 'Bad Request' in responseStr or 'Authentication required.' in responseStr:
        return False    
    return True

def doRequest(method, endpoint, additionalHeaders, request, hiddenMessage=None):    
    federationToken = request.user.token.id
    
    timeoutPost = settings.TIMEOUT_POST;
    if timeoutPost is not None:
        timeoutPost = 15
    timeoutDelete = settings.TIMEOUT_DELETE;
    if timeoutDelete is not None:
        timeoutDelete = 15    
    timeoutGet = settings.TIMEOUT_GET;
    if timeoutGet is not None:
        timeoutGet = 60    
    
    headers = {'content-type': 'text/occi', 'X-Auth-Token' : federationToken}    
    if additionalHeaders is not None:
        headers.update(additionalHeaders)    
        
    responseStr, response = '', None
    try:
        if method == 'get':
            response = requests.get(settings.FOGBOW_MANAGER_ENDPOINT + endpoint, headers=headers, timeout=timeoutGet)
        elif method == 'delete':
            response = requests.delete(settings.FOGBOW_MANAGER_ENDPOINT + endpoint, headers=headers, timeout=timeoutDelete)
        elif method == 'post':   
            response = requests.post(settings.FOGBOW_MANAGER_ENDPOINT + endpoint, headers=headers, timeout=timeoutPost)
        responseStr = response.text
    except Exception as e:
        print e
        if hiddenMessage == None:
            messages.error(request, _('Problem communicating with the Fogbow Manager'))
    
    if 'Unauthorized' in responseStr or 'Authentication required.' in responseStr:
        if hiddenMessage == None:
            messages.error(request, _('Token unauthorized'))
        LOG.error(responseStr)
    elif 'Bad Request' in responseStr:
        if hiddenMessage == None:
            messages.error(request, _('Bad request'))
        LOG.error(responseStr)
    return response

def isResponseOk(responseStr):
    if 'Unauthorized' not in responseStr and 'Bad Request' not in responseStr and 'Authentication required.' not in responseStr and 'NullPointerException' not in responseStr:
        return True
    return False    

def calculatePercent(value, valueTotal):
    defaultValue = 0
    try:
        return (value * 100) / valueTotal
    except Exception:
        return defaultValue

class NafUtil(object):
    def __init__(self):
        pass
    
    def createCredentials(self, tokenStr):
        try:
            privateKeyPath = settings.FOGBOW_NAF_DASHBOARD_PRIVATE_KEY_PATH
            key = open(privateKeyPath, "r").read()
            rsakey = RSA.importKey(key) 
            signer = PKCS1_PSS.new(rsakey)             
            digest = SHA.new() 
            digest.update(tokenStr)
            sign = signer.sign(digest)
            return b64encode(sign)            
        except Exception as e:
            print str(e)
            return None
        
    def verify(self, token, signature):
        try:            
            portalPublicKey = settings.FOGBOW_NAF_PORTAL_PUBLIC_KEY_PATH
            pub_key = open(portalPublicKey, "r").read() 
            rsakey = RSA.importKey(pub_key) 
            signer = PKCS1_v1_5.new(rsakey)
            digest = SHA.new() 
            digest.update(token) 
            if signer.verify(digest, b64decode(signature)):
                print "The signature is authentic."
                return True
            else:
                print "The signature is not authentic."
                return False
        except Exception as e:
            print str(e)
            return False

    def decrypt(self, token):
        try:            
            portalPrivateKey = settings.FOGBOW_NAF_DASHBOARD_PRIVATE_KEY_PATH
            key = open(portalPrivateKey).read()
            rsakey = RSA.importKey(key)                   
            cipher = Cipher_PKCS1_v1_5.new(rsakey)
            return cipher.decrypt(b64decode(token), "decrypt_error")                    
        except Exception as e:
            print str(e)
            return None
        
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]
                
    def decryptAES(self, enc, key):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return _unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')
    
def _unpad(s):
    return s[:-ord(s[len(s)-1:])]


# ------------- OpenStack_auth / Fogbow ---------------

def set_session_from_user(request, user):
    request.session['token'] = user.token
    request.session['user_id'] = user.id
    request.session['region_endpoint'] = user.endpoint
    request.session['services_region'] = user.services_region
    request._cached_user = user
    request.user = user

def create_user_from_token(request, token, endpoint, services_region=None):
    return User(id=token.user['id'],
                token=token,
                user=token.user['name'],
                user_domain_id=token.user_domain_id,
                # We need to consider already logged-in users with an old
                # version of Token without user_domain_name.
                user_domain_name=getattr(token, 'user_domain_name', None),
                project_id=token.project['id'],
                project_name=token.project['name'],
                domain_id=token.domain['id'],
                domain_name=token.domain['name'],
                enabled=True,
                service_catalog=token.serviceCatalog,
                roles=token.roles,
                endpoint=endpoint,
                services_region=services_region)

class TokenOriginal(object):
    def __init__(self, auth_ref):
        user = {}
        user['id'] = auth_ref.user_id
        user['name'] = auth_ref.username
        self.user = user
        self.user_domain_id = auth_ref.user_domain_id
        self.user_domain_name = auth_ref.user_domain_name

        self.id = auth_ref.auth_token
        if len(self.id) > 64:
            algorithm = getattr(settings, 'OPENSTACK_TOKEN_HASH_ALGORITHM',
                                'md5')
            hasher = hashlib.new(algorithm)
            hasher.update(self.id)
            self.id = hasher.hexdigest()
        self.expires = auth_ref.expires

        # Project-related attributes
        project = {}
        project['id'] = auth_ref.project_id
        project['name'] = auth_ref.project_name
        self.project = project
        self.tenant = self.project

        # Domain-related attributes
        domain = {}
        domain['id'] = auth_ref.domain_id
        domain['name'] = auth_ref.domain_name
        self.domain = domain

        if auth_ref.version == 'v2.0':
            self.roles = auth_ref['user'].get('roles', [])
        else:
            self.roles = auth_ref.get('roles', [])

        if utils.get_keystone_version() < 3:
            self.serviceCatalog = auth_ref.get('serviceCatalog', [])
        else:
            self.serviceCatalog = auth_ref.get('catalog', [])


class UserOriginal(models.AnonymousUser):
    
    def __init__(self, id=None, token=None, user=None, tenant_id=None,
                 service_catalog=None, tenant_name=None, roles=None,
                 authorized_tenants=None, endpoint=None, enabled=False,
                 services_region=None, user_domain_id=None,
                 user_domain_name=None, domain_id=None, domain_name=None,
                 project_id=None, project_name=None):
        self.id = id
        self.pk = id
        self.token = token
        self.username = user
        self.user_domain_id = user_domain_id
        self.user_domain_name = user_domain_name
        self.domain_id = domain_id
        self.domain_name = domain_name
        self.project_id = project_id or tenant_id
        self.project_name = project_name or tenant_name
        self.service_catalog = service_catalog
        self._services_region = (services_region or
                                 self.default_services_region())
        self.roles = roles or []
        self.endpoint = endpoint
        self.enabled = enabled
        self._authorized_tenants = authorized_tenants

        # List of variables to be deprecated.
        self.tenant_id = self.project_id
        self.tenant_name = self.project_name

    def __unicode__(self):
        return self.username

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.username)

    def is_token_expired(self, margin=None):
        if self.token is None:
            return None
        return not utils.is_token_valid(self.token, margin)

    def is_authenticated(self, margin=None):
        return (self.token is not None and
                utils.is_token_valid(self.token, margin) and 
                checkUserAuthenticated(self.token))

    def is_anonymous(self, margin=None):
        return not self.is_authenticated(margin)

    @property
    def is_active(self):
        return self.enabled

    @property
    def is_superuser(self):
        return 'admin' in [role['name'].lower() for role in self.roles]

    @property
    def authorized_tenants(self):
        insecure = getattr(settings, 'OPENSTACK_SSL_NO_VERIFY', False)
        ca_cert = getattr(settings, "OPENSTACK_SSL_CACERT", None)

        if self.is_authenticated() and self._authorized_tenants is None:
            endpoint = self.endpoint
            token = self.token
            try:
                self._authorized_tenants = utils.get_project_list(
                    user_id=self.id,
                    auth_url=endpoint,
                    token=token.id,
                    insecure=insecure,
                    cacert=ca_cert,
                    debug=settings.DEBUG)
            except (keystone_exceptions.ClientException,
                    keystone_exceptions.AuthorizationFailure):
                LOG.exception('Unable to retrieve project list.')
        return self._authorized_tenants or []

    @authorized_tenants.setter
    def authorized_tenants(self, tenant_list):
        self._authorized_tenants = tenant_list

    def default_services_region(self):
        if self.service_catalog:
            for service in self.service_catalog:
                if service['type'] == 'identity':
                    continue
                for endpoint in service['endpoints']:
                    return endpoint['region']
        return None

    @property
    def services_region(self):
        return self._services_region

    @services_region.setter
    def services_region(self, region):
        self._services_region = region

    @property
    def available_services_regions(self):
        regions = []
        if self.service_catalog:
            for service in self.service_catalog:
                if service['type'] == 'identity':
                    continue
                for endpoint in service['endpoints']:
                    if endpoint['region'] not in regions:
                        regions.append(endpoint['region'])
        return regions

    def save(*args, **kwargs):
        pass

    def delete(*args, **kwargs):
        pass

    def has_a_matching_perm(self, perm_list, obj=None):
        if not perm_list:
            return True
        for perm in perm_list:
            if self.has_perm(perm, obj):
                return True
        return False

    def has_perms(self, perm_list, obj=None):
        if not perm_list:
            return True
        for perm in perm_list:
            if isinstance(perm, basestring):
                if not self.has_perm(perm, obj):
                    return False
            else:
                if not self.has_a_matching_perm(perm, obj):
                    return False
        return True
