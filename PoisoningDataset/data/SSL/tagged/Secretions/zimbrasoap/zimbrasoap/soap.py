#!/usr/bin/env python

# On python2.7, prevents included pysimplesoap
# from being zimbrasoap.pysimplesoap
from __future__ import absolute_import

import types

import re
import logging

import pysimplesoap.client
import pysimplesoap.simplexml

import zimbrasoap

class soap(object):
    "Zimbra General SOAP Interface"

    ## Probably never called
    def __init__(self, **kwargs):
        return self.init(**kwargs)

    ## really init
    def init(self, **kwargs):
        self.server = None            # url for soap requests
        self.namespace = None         # soap namespace, ie 'urn:zimbraMail'
        self.authToken = None         # auth token if pre-existing
        self.authTokenLifetime = None # unused atm
        self.username = None          # username if we're a mail soap object
        self.zimbraId = None          # zimbraId if we're a mail soap object
        self.trace = False            # trace soap calls (gloal to module, see set_trace)
        self.port = 7071              # Default admin port
        self.timeout = 60             # Default timeout for soap requests
        self.suppress_suffix = False  # Whether to suppress tacking on 'Request' (ie zmsoap.Auth() -> <AuthRequest />)

        # blindly set args as values in object
        for arg,value in kwargs.items():
            setattr(self, arg, value)

        if self.trace:
            self.set_trace(True)

    ## Functions for making SOAP requests
    def generic_zimbra_soap_request(self,
                                    method=None,
                                    suppress_suffix=False, # Don't append "Request"
                                    attributes={},
                                    *args, **kwargs):
        '''
        Generic SOAP request method

        method is the base method name (ie Foo for FooRequest/FooResponse)

        attributes is a dict for attributes on the request tag
            ie { 'thing':'stuff' } -> <RequestNameRequest thing="stuff">

        args and kwargs are passed directly to the request
        '''

        # Every Zimbra request ends in "Request", ie "GetFolderRequest", "BurnKittenRequest"
        # Allow people to be lazy and just do "GetFolder", "BurnKitten"
        if not suppress_suffix and not re.search('Request$', method):
            method = '{0}Request'.format(method)

        params = pysimplesoap.simplexml.SimpleXMLElement('<{0} />'.format(method))
        params['xmlns'] = self.namespace

        # If given a straight SimpleXMLElement object, import it directly
        if args:
            for arg in args:
                params.import_node(arg)
        # If given as the first argument, interpret that
        # (prevents requiring RequestName({}, SimpleXMLElement_object))
        elif type(attributes) == pysimplesoap.simplexml.SimpleXMLElement:
            params.import_node(attributes)
        # really attributes that go directly in the request tag
        else:
            for key,value in attributes.items():
                params[key] = str(value)

        # Creates body tags with included attributes
        def process_tags(params, args):
            for tag,body in args.items():
                value = body
                # tag value is in a dict
                if type(body) == dict:
                    # if tag value is also a dict, recurse
                    if type(body['value']) == dict:
                        child = params.add_child(tag)
                        process_tags(child, body['value'])
                    # Following is interesting, but may complicate things
                    ## if tag value is a list, treat as multi-valued key
                    #elif type(body['value']) == list:
                    #    for value in body['value']:
                    #        if type(value) == dict:
                    #            child = params.add_child(tag)
                    #            process_tags(child, value)
                    #        else:
                    #            child = params.add_child(tag, value)
                    #            # process attrs, duplicated from below
                    #        if type(body) == dict:
                    #            for attr,attrvalue in body.items():
                    #                if attr == 'value':
                    #                    continue
                    #                else:
                    #                    child[attr] = attrvalue
                    #    # We process attrs early for arrays, return
                    #    return
                    # add value from tag's dict
                    else:
                        child = params.add_child(tag, body['value'])
                    for attr,attrvalue in body.items():
                        if attr == 'value': # value for attr, not item value
                            continue # Already processed above
                        else:
                            child[attr] = attrvalue
                elif type(body) == list:
                    # body is list of tags, for multi-value attributes
                    for item in body:
                        if type(item) == dict:
                            child = params.add_child(tag, item['value'])
                            for attr,attrvalue in item.items():
                                if attr == 'value':
                                    continue
                                else:
                                    child[attr] = attrvalue
                        else:
                            child = params.add_child(tag, item)
                # tag's dict is hanging out in the open for all to see
                else:
                    child = params.add_child(tag, value)

        process_tags(params, kwargs)

        # return bare SimpleXMLElement object
        return self.do_req('{0}'.format(method), params)

    ## Glue that puts everything together to actually perform the request
    def do_req(self, method, *args, **kwargs):
        return self.create_zimbra_request().call(method,
                headers = self.construct_zimbra_header(), *args, **kwargs)

    ## Create soap client request object
    def create_zimbra_request(self):
        # If pysimplesoap with log_id support is available, use that
        try:
            soap_result = pysimplesoap.client.SoapClient(
                location = self.server,
                action = self.server,
                namespace =  self.namespace, # zimbraMail, zimbraAdmin, etc.
                # saying it's oracle allows empty request tags (ie NoOp())
                soap_server = 'oracle',
                soap_ns='soap', ns = False, exceptions = True, timeout = self.timeout,
                trace = self.trace, log_id = False)
        except TypeError as e:
            if str(e) == "__init__() got an unexpected keyword argument 'log_id'":
                soap_result = pysimplesoap.client.SoapClient(
                    location = self.server,
                    action = self.server,
                    namespace =  self.namespace, # zimbraMail, zimbraAdmin, etc.
                    # saying it's oracle allows empty request tags (ie NoOp())
                    soap_server = 'oracle',
                    soap_ns='soap', ns = False, exceptions = True, timeout = self.timeout,
                    trace = self.trace)
            else:
                raise
        return soap_result

    ## Create <Header /> tag for SOAP auths with auth token if available
    def construct_zimbra_header(self):
        headers = pysimplesoap.simplexml.SimpleXMLElement('<Header><context xmlns="urn:zimbra"></context></Header>')
        headers.context.add_child('nosession')
        useragent = headers.context.add_child('userAgent')
        useragent['name'] = 'zimbrasoap'
        useragent['version'] = zimbrasoap.__version__
        if self.authToken != None:
            headers.context.add_child('authToken', str(self.authToken))
        if self.zimbraId != None:
            headers.context.add_child('account', self.zimbraId)['by'] = 'id'

        return headers

    ### Helper functions

    ## Parse Zimbra-specific styles of attributes ala:
    ## <attr name="zimbraAttributeName">zimbraAttributeValue</a>
    ## Returns a simple single-level dict. For end users.
    ## Values are all arrays now.
    def ParseAttributes(self, attributes):
        output = {}
        for attr in attributes:
            if re.match('^(?:a|attr|attribute)$', attr.get_name()):
                name = ''
                count = '' # Don't know if this is ever not 1, more for future reference
                for attr_item in attr.attributes().items():
                    if attr_item[0] == 'n' or attr_item[0] == 'name':
                        name = attr_item[1]
                    elif attr_item[0] == 'c' or attr_item[0] == 'count':
                        count = attr_item[1]
                if name not in output:
                    output[name] = []
                output[name].append(str(attr))
        return output

    ### Objecty stuff

    ## Allows us to call soap.RequestName
    def __getattr__(self, key):
        def wrapper(*args, **kwargs):
            return self.generic_zimbra_soap_request(key, self.suppress_suffix, *args, **kwargs)
        return wrapper

    ## Turns soap tracing on/off
    ## This is global to the zimbrasoap module so that multiple instances
    ## don't cause multiple loggings (this was much nicer before logger...)
    def set_trace(self, toggle):
        log = logging.getLogger('pysimplesoap.client')

        # due to overriding __getattr__, nonexistent attrs are functions
        if zimbrasoap.log_handler and type(zimbrasoap.log_handler) is not types.FunctionType:
            log.removeHandler(zimbrasoap.log_handler)
            zimbrasoap.log_handler.close() # do we need both this and above?

        zimbrasoap.log_handler = logging.StreamHandler()
        zimbrasoap.log_handler.setFormatter(logging.Formatter(fmt='%(message)s'))
        if toggle:
            log.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.WARNING)
        log.addHandler(zimbrasoap.log_handler)

    ### Ripped from stackoverflow
    ### Current host I'm working with borks on tls negotiations supporting 1.2
    # Start of the workaround for SSL3
    # This is a monkey patch / module function overriding
    # to allow pages that only work with SSL3
<target>
    # zmsoap_object.set_ssl(ssl.PROTOCOL_TLSv1) etc.
</target>
    def set_ssl(self, ssl_level):
        # Build the appropriate socket wrapper for ssl
        try:
            import ssl # python 2.6
            import httplib2
            httplib2.ssl_SSLError = ssl.SSLError
            def _ssl_wrap_socket(sock, key_file, cert_file,
                                 disable_validation, ca_certs):
                if disable_validation:
                    cert_reqs = ssl.CERT_NONE
                else:
                    cert_reqs = ssl.CERT_REQUIRED
                # Our fix for sites the only accepts SSL3
                try:
                    # Trying SSLv3 first
                    tempsock = ssl.wrap_socket(sock, keyfile=key_file, certfile=cert_file,
                                               cert_reqs=cert_reqs, ca_certs=ca_certs,
                                               ssl_version=ssl_level)
                except ssl.SSLError as e:
                    tempsock = ssl.wrap_socket(sock, keyfile=key_file, certfile=cert_file,
                                               cert_reqs=cert_reqs, ca_certs=ca_certs,
                                               ssl_version=ssl_level)
                return tempsock
            httplib2._ssl_wrap_socket = _ssl_wrap_socket
        except (AttributeError, ImportError):
            httplib2.ssl_SSLError = None
            def _ssl_wrap_socket(sock, key_file, cert_file,
                                 disable_validation, ca_certs):
                if not disable_validation:
                    raise httplib2.CertificateValidationUnsupported(
                            "SSL certificate validation is not supported without "
                            "the ssl module installed. To avoid this error, install "
                            "the ssl module, or explicity disable validation.")
                ssl_sock = socket.ssl(sock, key_file, cert_file)
                return httplib.FakeSocket(sock, ssl_sock)
            httplib2._ssl_wrap_socket = _ssl_wrap_socket

        # End of the workaround for SSL3



    ### Specific api calls that need extra help

    ## Auth (to get token into our object)--may not be the same across services
    def Auth(self, *args, **kwargs):
        # Auth works differently in the urn:zimbraAdmin namespace
        # We could just use this everywhere, but worried about breaking existing code
        namespace = self.namespace
        if self.namespace == 'urn:zimbraMail':
            self.namespace = 'urn:zimbraAccount'

        response = self.generic_zimbra_soap_request('Auth', False, *args, **kwargs)

        self.namespace = namespace
        self.authToken = response.authToken
        self.authTokenLifetime = response.lifetime
        return response

    ## Requests that don't have a "Request" suffix
    def DestroyWaitSet(self, *args, **kwargs):
        return self.generic_zimbra_soap_request('DestroyWaitSet', suppress_suffix=True, *args, **kwargs)

    def AdminDestroyWaitSet(self, *args, **kwargs):
        return self.generic_zimbra_soap_request('AdminDestroyWaitSet', suppress_suffix=True, *args, **kwargs)

    def CreateAppointmentException(self, *args, **kwargs):
        return self.generic_zimbra_soap_request('CreateAppointmentException', suppress_suffix=True, *args, **kwargs)

    def IMGetChatConfiguration(self, *args, **kwargs):
        return self.generic_zimbra_soap_request('IMGetChatConfiguration',suppress_suffix=True, *args, **kwargs)

### Admin interface soap calls (urn / url change)
class admin(soap):
    def __init__(self, **kwargs):
        if 'port' not in kwargs:
            kwargs['port'] = 7071
        if not re.match('^http', kwargs['server']):
            kwargs['server'] = "https://{0}:{1}/service/admin/soap".format(kwargs['server'], kwargs['port'])
        kwargs['namespace'] = 'urn:zimbraAdmin'
        self.init(**kwargs)

### zimbraMail soap calls (urn change)
class mail(soap):
    def __init__(self, **kwargs):
        if 'port' not in kwargs:
            kwargs['port'] = 443
        if not re.match('^http', kwargs['server']):
            kwargs['server'] = "https://{0}:{1}/service/soap".format(kwargs['server'], kwargs['port'])
        kwargs['namespace'] = 'urn:zimbraMail'
        self.init(**kwargs)
