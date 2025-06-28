# -*- coding: utf-8 -*-

# This module contains all the Proxy rules classes for use with the MIT
# Core Concept Catalog (MC3) Handcar service.  Note that the Proxy implementation
# is simply a wrapper for another Proxy, but adds the agent key management with
# handcar authentication.

# how to handle SSL versions from here:
# http://stackoverflow.com/questions/18669457/python-httplib-ssl23-get-server-hellounknown-protocol

import codecs
import json
import ssl

try:
    import http.client as httplib
except ImportError:
    import httplib

from functools import partial

from ...abstract_osid.proxy import rules as abc_proxy_rules
from ..osid import rules as osid_rules
from .. import settings
from .. import profile
from ..primitives import Id, Type, DisplayText
from ..type.objects import TypeList
from datetime import datetime, timedelta
from ..osid.osid_errors import IllegalState, NullArgument, OperationFailed, Unsupported, Unimplemented, PermissionDenied, NotFound


try:
    from django.conf import settings as dlkit_settings

    if dlkit_settings.FORCE_TLSV1:
        class my_ssl:
            wrap_socket = partial(ssl.wrap_socket, ssl_version=ssl.PROTOCOL_TLSv1)

        httplib.ssl = my_ssl
except (ImportError, AttributeError):
    pass


class Proxy(abc_proxy_rules.Proxy, osid_rules.OsidResult):
    """A ``Proxy`` is used to transfer external information from an application server into an OSID Provider."""

    _host = settings.HOST
    _app_key = settings.APP_KEYS[_host.lower()]

    def __init__(self, proxy, host=None, app_key=None):
        self._my_proxy = proxy
        if host is not None:
            self._host = host
        if app_key is not None:
            self._app_key = app_key
        self._set_agent_key()
        self._host = None

    def set_host(self, mc3_host=None):
        """
        Hack to get copy from server to server
        :param mc3_host:
        :return:
        """
        self._host = mc3_host
        self._set_agent_key()

    def get_host(self):
        if self._host:
            return self._host
        else:
            return None

    def _set_agent_key(self, duration=3600):
        username = self._get_user_name()
        if username is not None:
            self._timestamp = datetime.utcnow()
            self._duration = timedelta(minutes=duration // 60 - 1)  # allow 1 minute of leeway
            # trim username to 8 chars plus @mit.edu so MIT Roles doesn't barf
            username = str(username).split('@')[0][0:8] + '@mit.edu'
            if self._host and not self._app_key:
                self._app_key = settings.APP_KEYS[self._host.lower()]
            url_path = ('/handcar/services/authentication/agentkeys/' +
                        username + '?duration=' + str(duration) +
                        '&proxyname=' + self._app_key)
            self._agent_key = self._get_request(url_path)
        else:
            self._agent_key = None

    def _get_user_name(self):
        if self.has_effective_agent():
            return self.get_effective_agent_id().get_identifier()
        elif self.has_authentication():
            authentication = self.get_authentication()
            if authentication.is_valid():
                return authentication.get_agent_id().get_identifier()
            else:
                return None
        else:
            return None

    def _error_check(self, response):
        if response.status == 200:
            return
        elif response.status == 404:
            raise NotFound(response.reason)
        elif response.status == 403:
            raise PermissionDenied(response.reason)
        elif 'org.osid.NotFoundException' in response.read():
            raise NotFound(response.reason)
        else:
            raise OperationFailed(str(response.status) + ' Error: ' + response.reason)

    def _get_request(self, url_path):
        connection = httplib.HTTPSConnection(self._host)
        url_path = url_path.replace('?', '&')
        url_path = url_path.replace('&', '?', 1)
        # logging.info('get: ' + url_path)
        connection.request('GET', url_path)
        response = connection.getresponse()
        self._error_check(response)
        reader = codecs.getreader('utf8')
        result = reader(response)
        try:
            return json.load(result)
        except ValueError:
            return result.read()

    def has_authentication(self):
        """Tests if an authentication is available.

        :return: ``true`` if an ``Authentication`` is available, ``false`` otherwise
        :rtype: ``boolean``


        *compliance: mandatory -- This method must be implemented.*

        """
        return self._my_proxy.has_authentication()

    def get_authentication(self):
        """Gets the ``Authentication`` for this proxy.

        :return: the authentication
        :rtype: ``osid.authentication.process.Authentication``
        :raise: ``IllegalState`` -- ``has_authentication()`` is ``false``

        *compliance: mandatory -- This method must be implemented.*

        """
        return self._my_proxy.get_authentication()

    authentication = property(fget=get_authentication)

    def has_effective_agent(self):
        """Tests if an effective agent is available.

        :return: ``true`` if an effective agent is available, ``false`` otherwise
        :rtype: ``boolean``


        *compliance: mandatory -- This method must be implemented.*

        """
        return self._my_proxy.has_effective_agent()

    def get_effective_agent_id(self):
        """Gets the effective ``Agent Id`` for this proxy.

        :return: the effective agent ``Id``
        :rtype: ``osid.id.Id``
        :raise: ``IllegalState`` -- ``has_effective_agent()`` is ``false``

        *compliance: mandatory -- This method must be implemented.*

        """
        return self._my_proxy.get_effective_agent_id()

    effective_agent_id = property(fget=get_effective_agent_id)

    def get_effective_agent(self):
        """Gets the effective ``Agent`` for this proxy.

        :return: the effective agent
        :rtype: ``osid.authentication.Agent``
        :raise: ``IllegalState`` -- ``has_effective_agent()`` is ``false``
        :raise: ``OperationFailed`` -- unable to complete request

        *compliance: mandatory -- This method must be implemented.*

        """
        raise Unimplemented

    effective_agent = property(fget=get_effective_agent)

    def has_effective_date(self):
        """Tests if an effective date is available.

        :return: ``true`` if an effective date is available, ``false`` otherwise
        :rtype: ``boolean``


        *compliance: mandatory -- This method must be implemented.*

        """
        return self._my_proxy.has_effective_date()

    def get_effective_date(self):
        """Gets the effective date.

        :return: the effective date
        :rtype: ``timestamp``
        :raise: ``IllegalState`` -- ``has_effective_date()`` is ``false``

        *compliance: mandatory -- This method must be implemented.*

        """
        return self._my_proxy.get_effective_date()

    effective_date = property(fget=get_effective_date)

    def get_effective_clock_rate(self):
        """Gets the rate of the clock.

        :return: the rate
        :rtype: ``decimal``
        :raise: ``IllegalState`` -- ``has_effective_date()`` is ``false``

        *compliance: mandatory -- This method must be implemented.*

        """
        return self._my_proxy.get_effective_clock_rate()

    effective_clock_rate = property(fget=get_effective_clock_rate)

    def get_locale(self):
        """Gets the locale.

        :return: a locale
        :rtype: ``osid.locale.Locale``


        *compliance: mandatory -- This method must be implemented.*

        """
        return self._my_proxy.get_locale()

    locale = property(fget=get_locale)

    def has_format_type(self):
        """Tests if a ``DisplayText`` format ``Type`` is available.

        return: (boolean) - ``true`` if a format type is available,
                ``false`` otherwise
        *compliance: mandatory -- This method must be implemented.*

        """
        return self._my_proxy.has_format_type()

    def get_format_type(self):
        """Gets the ``DisplayText`` format ``Type``.

        return: (osid.type.Type) - the format ``Type``
        raise:  IllegalState - ``has_format_type()`` is ``false``
        *compliance: mandatory -- This method must be implemented.*

        """
        return self._my_proxy.get_format_type()

    format_type = property(fget=get_format_type)

    def get_proxy_record(self, proxy_record_type):
        """Gets the proxy record corresponding to the given ``Proxy`` record ``Type``.

        This method is used to retrieve an object implementing the
        requested record. The ``proxy_record_type`` may be the ``Type``
        returned in ``get_record_types()`` or any of its parents in a
        ``Type`` hierarchy where ``has_record_type(proxy_record_type)``
        is ``true`` .

        :param proxy_record_type: the type of proxy record to retrieve
        :type proxy_record_type: ``osid.type.Type``
        :return: the proxy record
        :rtype: ``osid.proxy.records.ProxyRecord``
        :raise: ``NullArgument`` -- ``proxy_record_type`` is ``null``
        :raise: ``OperationFailed`` -- unable to complete request
        :raise: ``Unsupported`` -- ``has_record_type(proxy_record_type)`` is ``false``

        *compliance: mandatory -- This method must be implemented.*

        """
        return self._my_proxy.get_proxy_record(proxy_record_type)

    def has_agent_key(self):
        return bool(self._agent_key)

    def get_agent_key(self):
        if not self.has_agent_key():
            raise IllegalState()
        if datetime.utcnow() - self._timestamp > self._duration:
            self._set_agent_key()
        return self._agent_key


class ProxyCondition(abc_proxy_rules.ProxyCondition, osid_rules.OsidCondition):
    """A ``ProxyCondition`` is used to transfer external information into a proxy."""

    def __init__(self):
        self._effective_agent_id = None
        self._language_type = None
        self._script_type = None
        self._calendar_type = None
        self._time_type = None
        self._currency_type = None
        self._unit_system_type = None
        self._http_request = None
        self._record_types = TypeList(profile.PROXY_CONDITION_RECORD_TYPES)

    def set_effective_agent_id(self, agent_id):
        """Sets the effective agent ``Id`` to indicate acting on behalf of.

        :param agent_id: an agent ``Id``
        :type agent_id: ``osid.id.Id``
        :raise: ``NullArgument`` -- ``agent_id`` is ``null``

        *compliance: mandatory -- This method must be implemented.*

        """
        self._effective_agent_id = agent_id

    effective_agent_id = property(fset=set_effective_agent_id)

    def set_effective_date(self, date, rate):
        """Sets the effective date.

        :param date: a date
        :type date: ``timestamp``
        :param rate: the rate at which the clock should tick from the given effective date. 0 is a clock that is fixed
        :type rate: ``decimal``
        :raise: ``NullArgument`` -- ``date`` is ``null``

        *compliance: mandatory -- This method must be implemented.*

        """
        raise Unimplemented()

    def set_language_type(self, language_type):
        """Sets the language type.

        :param language_type: the language type
        :type language_type: ``osid.type.Type``
        :raise: ``NullArgument`` -- ``language_type`` is ``null``

        *compliance: mandatory -- This method must be implemented.*

        """
        self._language_type = language_type

    language_type = property(fset=set_language_type)

    def set_script_type(self, script_type):
        """Sets the script type.

        :param script_type: the script type
        :type script_type: ``osid.type.Type``
        :raise: ``NullArgument`` -- ``script_type`` is ``null``

        *compliance: mandatory -- This method must be implemented.*

        """
        self._script_type = script_type

    script_type = property(fset=set_script_type)

    def set_calendar_type(self, calendar_type):
        """Sets the calendar type.

        :param calendar_type: the calendar type
        :type calendar_type: ``osid.type.Type``
        :raise: ``NullArgument`` -- ``calendar_type`` is ``null``

        *compliance: mandatory -- This method must be implemented.*

        """
        self._calendar_type = calendar_type

    calendar_type = property(fset=set_calendar_type)

    def set_time_type(self, time_type):
        """Sets the time type.

        :param time_type: the time type
        :type time_type: ``osid.type.Type``
        :raise: ``NullArgument`` -- ``time_type`` is ``null``

        *compliance: mandatory -- This method must be implemented.*

        """
        self._time_type = time_type

    time_type = property(fset=set_time_type)

    def set_currency_type(self, currency_type):
        """Sets the currency type.

        :param currency_type: the currency type
        :type currency_type: ``osid.type.Type``
        :raise: ``NullArgument`` -- ``currency_type`` is ``null``

        *compliance: mandatory -- This method must be implemented.*

        """
        self._currency_type = currency_type

    currency_type = property(fset=set_currency_type)

    def set_unit_system_type(self, unit_system_type):
        """Sets the unit system type.

        :param unit_system_type: the unit system type
        :type unit_system_type: ``osid.type.Type``
        :raise: ``NullArgument`` -- ``unit_system_type`` is ``null``

        *compliance: mandatory -- This method must be implemented.*

        """
        self._unit_system_type = unit_system_type

    unit_system_type = property(fset=set_unit_system_type)

    def get_proxy_condition_record(self, proxy_condition_type):
        """Gets the proxy condition record corresponding to the given ``Proxy`` record ``Type``.

        This method is used to retrieve an object implementing the
        requested record. The ``proxy_record_type`` may be the ``Type``
        returned in ``get_record_types()`` or any of its parents in a
        ``Type`` hierarchy where ``has_record_type(proxy_record_type)``
        is ``true`` .

        :param proxy_condition_type: the type of proxy condition record to retrieve
        :type proxy_condition_type: ``osid.type.Type``
        :return: the proxy condition record
        :rtype: ``osid.proxy.records.ProxyConditionRecord``
        :raise: ``NullArgument`` -- ``proxy_condition_record_type`` is ``null``
        :raise: ``OperationFailed`` -- unable to complete request
        :raise: ``Unsupported`` -- ``has_record_type(proxy_condition_record_type)`` is ``false``

        *compliance: mandatory -- This method must be implemented.*

        """
        if self.has_record_type(proxy_condition_type):
            return self
        else:
            raise Unsupported()

    # The following method supports the HTTPRequest ProxyConditionRecordType:
    def set_http_request(self, http_request):
        self._http_request = http_request

    http_request = property(fset=set_http_request)
