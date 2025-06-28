# -*- coding: utf-8 -*-

# This module contains all the Session classes used by the MIT Core Concept
# Catalog (MC3) Handcar based implementation of the OSID Learning Service.
# Note that it includes the core OsidSession typically found in the osid
# package as well as the learning package sessions for Objective, Activities
# and ObjectiveBanks.

import logging
import json
import requests
import ssl

try:
    import http.client as httplib
except ImportError:
    import httplib

from functools import partial

# from datetime import datetime, timedelta
from ...abstract_osid.osid import sessions as abc_osid_sessions
from ..osid.osid_errors import AlreadyExists, NullArgument, InvalidArgument, NotFound, IllegalState, OperationFailed, PermissionDenied, Unsupported, Unimplemented
from .. import settings
from ..primitives import Id, Type, DisplayText
from ..authentication.objects import Agent
from ..utilities import construct_url


COMPARATIVE = 0
PLENARY = 1
ISOLATED = 0
FEDERATED = 1

CREATED = True
UPDATED = True

try:
    from django.conf import settings as dlkit_settings

    if dlkit_settings.FORCE_TLSV1:
        class my_ssl:
            wrap_socket = partial(ssl.wrap_socket, ssl_version=ssl.PROTOCOL_TLSv1)

        httplib.ssl = my_ssl
except (ImportError, AttributeError):
    pass


class OsidSession(abc_osid_sessions.OsidSession):
    """The OsidSession is the top level interface for all OSID sessions.

    An OsidSession is created through its corresponding OsidManager. A
    new OsidSession should be created for each user of a service and for
    each processing thread. A session maintains a single authenticated
    user and is not required to ensure thread-protection. A typical OSID
    session defines a set of service methods corresponding to some
    compliance level as defined by the service and is generally
    responsible for the management and retrieval of OsidObjects.

    OsidSession defines a set of common methods used throughout all OSID
    sessions. An OSID session may optionally support transactions
    through the transaction interface.

    """
    _session_name = 'OsidSession'  # Is this even used?
    _base_path = '/handcar/services'

    def __init__(self):
        self._proxy = None
        self._runtime = None
        self._authority = 'MIT-OEIT'
        self._authz_hints = {}
        self._category_idstr = None
        self._service_string = ''
        self._service_path = '{0}/{1}/'.format(self._base_path,
                                               self._service_string)

    def _init_proxy_and_runtime(self, proxy, runtime):
        self._proxy = proxy
        self._runtime = runtime
        if runtime is not None:
            try:
                hostname_param_id = Id('parameter:hostName@handcar')
                self._host = runtime.get_configuration().get_value_by_parameter(
                    hostname_param_id).get_string_value()
            except (KeyError, NotFound):
                self._host = settings.HOST

            try:
                app_key_param_id = Id('parameter:appKey@handcar')
                self._app_key = runtime.get_configuration().get_value_by_parameter(
                    app_key_param_id).get_string_value()
            except (KeyError, NotFound):
                self._app_key = settings.APP_KEYS[self._host.lower()]

    def _init_catalog(self, proxy=None, runtime=None):
        """Initialize this object as an OsidCatalog."""
        self._init_proxy_and_runtime(proxy, runtime)

    def _init_object(self, catalog_id, proxy, runtime, cat_name, cat_class):
        """Initialize this object as an OsidObject....do we need this??
        From the Mongo learning impl, but seems unnecessary for Handcar"""
        self._catalog_identifier = None
        self._init_proxy_and_runtime(proxy, runtime)
        self._catalog = cat_class(self._my_catalog_map)
        self._catalog._authority = self._authority  # there should be a better way...
        self._catalog_id = self._catalog.get_id()
        self._forms = dict()

    def _construct_url_path(self):
        pass  # Try implementing url constructors here:

        # Note that there are now some useful instance variables to work with
        # so fewer arguments need to be passed.
        # Like self._service_path, self._catalog_name and self._catalog_idstr

    def _get_agent_query_str(self):
        if self._proxy is None and self._app_key is not None:
            return '?proxyname={0}'.format(self._app_key)
        if self._proxy is None:
            return ''
        if self._proxy.has_agent_key():
            if self._host:
                self._proxy.set_host(self._host)
                return '?proxyname=' + self._proxy.get_agent_key()
            else:
                return '?proxyname=' + self._proxy.get_agent_key()
        else:
            return ''

    def _authorization_hints(self, cat_id=None):
        if str(cat_id) not in self._authz_hints:
            url_path = construct_url('authorization',
                                     bank_id=cat_id)
            self._authz_hints[str(cat_id)] = self._get_request(url_path)
        return self._authz_hints[str(cat_id)]

    def _error_check(self, response):
        if response.status_code == 200:
            return
        elif response.status_code == 404:
            raise NotFound(response.text)
        elif response.status_code == 403:
            raise PermissionDenied(response.text)
        elif 'org.osid.NotFoundException' in response.text:
            raise NotFound(response.text)
        else:
            raise OperationFailed(str(response.status_code) + ' Error: ' + response.text)

    def _full_url(self, url_path):
        return 'https://{0}{1}'.format(self._host, url_path)

    # This is where the work gets done to process GET requests with handcar.
    # Here you can experiment with different libraries, etc.
    def _get_request(self, url_path):
        # if datetime.now() - self._timestamp > self._duration:
        #    self._set_agent_query_str(username = self.get_effective_agent_id().get_identifier())
        url_path += self._get_agent_query_str()
        url_path = url_path.replace('?', '&')
        url_path = url_path.replace('&', '?', 1)
        # logging.info('get: ' + url_path)
        response = requests.get(self._full_url(url_path))
        self._error_check(response)
        try:
            return response.json()
        except ValueError:
            return response.text

    # This is where the work gets done to process POST requests with handcar.
    # Here you can experiment with different libraries, etc.
    def _post_request(self, url_path, data_map):
        # if datetime.now() - self._timestamp > self._duration:
        #    self._set_agent_query_str(username = self.get_effective_agent_id().get_identifier())
        # connection = httplib.HTTPSConnection(self._host)
        url_path += self._get_agent_query_str()
        data = json.dumps(data_map)
        # logging.info('post: ' + url_path)
        response = requests.post(self._full_url(url_path),
                                 data=data,
                                 headers={'Content-Type': 'application/json'})
        self._error_check(response)
        try:
            return response.json()
        except ValueError:
            return response.text

    # This is where the work gets done to process PUT requests with handcar.
    # Here you can experiment with different libraries, etc.
    def _put_request(self, url_path, data_map):
        # if datetime.now() - self._timestamp > self._duration:
        #    self._set_agent_query_str(username = self.get_effective_agent_id().get_identifier())
        # connection = httplib.HTTPSConnection(self._host)
        url_path += self._get_agent_query_str()
        data = json.dumps(data_map)
        # logging.info('put: ' + url_path)
        response = requests.put(self._full_url(url_path),
                                data=data,
                                headers={'Content-Type': 'application/json'})
        self._error_check(response)
        try:
            return response.json()
        except ValueError:
            return response.text

    # This is where the work gets done to process DELETE requests with handcar.
    # Here you can experiment with different libraries, etc.
    def _delete_request(self, url_path):
        # if datetime.now() - self._timestamp > self._duration:
        #    self._agent_key_str = self._get_agent_key_str(username = self.get_effective_agent_id().get_identifier())
        # connection = httplib.HTTPSConnection(self._host)
        url_path += self._get_agent_query_str()
        # logging.info('delete: ' + url_path)
        response = requests.delete(self._full_url(url_path))
        self._error_check(response)
        try:
            return response.json()
        except ValueError:
            return response.text

    def get_locale(self):
        """Gets the locale indicating the localization preferences in
        effect for this session.

        return: (osid.locale.Locale) - the locale
        compliance: mandatory - This method must be implemented.

        """
        raise Unimplemented()

    def is_authenticated(self):
        """Tests if an agent is authenticated to this session.

        return: (boolean) - true if valid authentication credentials
                exist, false otherwise
        compliance: mandatory - This method must be implemented.

        """
        if self._proxy is None:
            return False
        elif self._proxy.has_authentication():
            return self._proxy.get_authentication().is_valid()
        else:
            return False

    def get_authenticated_agent_id(self):
        """Gets the Id of the agent authenticated to this session.
        This is the agent for which credentials are used either acquired
        natively or via an OsidProxyManager.
        return: (osid.id.Id) - the authenticated agent Id
        raise:  IllegalState - is_authenticated() is false
        compliance: mandatory - This method must be implemented.

        """
        if self.is_authenticated():
            return self._proxy.get_authentication().get_agent_id()
        else:
            raise IllegalState()

    def get_authenticated_agent(self):
        """Gets the agent authenticated to this session.
        This is the agent for which credentials are used either acquired
        natively or via an OsidProxyManager.
        return: (osid.authentication.Agent) - the authenticated agent
        raise:  IllegalState - is_authenticated() is false
        raise:  OperationFailed - unable to complete request
        compliance: mandatory - This method must be implemented.

        """
        if self.is_authenticated():
            return self._proxy.get_authentication().get_agent()
        else:
            raise IllegalState()

    def get_effective_agent_id(self):
        """Gets the Id of the effective agent in use by this session.
        If is_authenticated() is true, then the effective agent may be
        the same as the agent returned by get_authenticated_agent(). If
        is_authenticated() is false, then the effective agent may be a
        default agent used for authorization by an unknwon or anonymous
        user.
        return: (osid.id.Id) - the effective agent
        compliance: mandatory - This method must be implemented.

        """
        if self.is_authenticated():
            return self._proxy.get_authentication().get_agent_id()
        elif self._proxy is not None and self._proxy.has_effective_agent():
            return self._proxy.get_effective_agent_id()
        else:
            return Id(identifier='MC3GUE$T@MIT.EDU',
                      namespace='osid.agent.Agent',
                      authority='MIT-OEIT')

    def get_effective_agent(self):
        """Gets the effective agent in use by this session.
        If is_authenticated() is true, then the effective agent may be
        the same as the agent returned by get_authenticated_agent(). If
        is_authenticated() is false, then the effective agent may be a
        default agent used for authorization by an unknwon or anonymous
        user.
        return: (osid.authentication.Agent) - the effective agent
        raise:  OperationFailed - unable to complete request
        compliance: mandatory - This method must be implemented.

        """
        if self._proxy is not None and self._proxy.has_authentication():
            return self._proxy.get_authentication().get_agent()
        elif self._proxy is not None and self._proxy.has_effective_agent():
            return Agent(identifier=self._proxy.get_effective_agent_id().get_identifier(),
                         namespace=self._proxy.get_effective_agent_id().get_namespace(),
                         authority=self._proxy.get_effective_agent_id().get_authority())
        else:
            return Agent(identifier='MC3GUE$T@MIT.EDU',
                         namespace='osid.agent.Agent',
                         authority='MIT-OEIT')

    def get_date(self):
        """Gets the service date which may be the current date or the effective date in which this session exists.

        return: (timestamp) - the service date
        *compliance: mandatory -- This method must be implemented.*

        """
        raise Unimplemented()

    date = property(fget=get_date)

    def get_clock_rate(self):
        """Gets the rate of the service clock.

        return: (decimal) - the clock rate
        *compliance: mandatory -- This method must be implemented.*

        """
        raise Unimplemented()

    clock_rate = property(fget=get_clock_rate)

    def get_format_type(self):
        """Gets the ``DisplayText`` format ``Type`` preference in effect for this session.

        return: (osid.type.Type) - the effective ``DisplayText`` format
                ``Type``
        *compliance: mandatory -- This method must be implemented.*

        """
        raise Unimplemented()

    format_type = property(fget=get_format_type)

    def supports_transactions(self):
        """Tests for the availability of transactions.

        return: (boolean) - true if transaction methods are available,
                false otherwise
        compliance: mandatory - This method must be implemented.

        """
        return False

    def start_transaction(self):
        """Starts a new transaction for this sesson.
        Transactions are a means for an OSID to provide an all-or-
        nothing set of operations within a session and may be used to
        coordinate this service from an external transaction manager. A
        session supports one transaction at a time. Starting a second
        transaction before the previous has been committed or aborted
        results in an IllegalState error.
        return: (osid.transaction.Transaction) - a new transaction
        raise:  IllegalState - a transaction is already open
        raise:  OperationFailed - unable to complete request
        raise:  Unsupported - transactions not supported
        compliance: optional - This method must be implemented if
                    supports_transactions() is true.
        implementation notes: Ideally, a provider that supports
        transactions should guarantee atomicity, consistency, isolation
        and durability in a 2 phase commit process. This is not always
        possible in distributed systems and a transaction provider may
        simply allow for a means of processing bulk updates.  To
        maximize interoperability, providers should honor the one-
        transaction-at-a-time rule.

        """
        raise Unsupported()

    locale = property(get_locale)
    authenticated_agent_id = property(get_authenticated_agent_id)
    authenticated_agent = property(get_authenticated_agent)
    effective_agent_id = property(get_effective_agent_id)
    effective_agent = property(get_effective_agent)
