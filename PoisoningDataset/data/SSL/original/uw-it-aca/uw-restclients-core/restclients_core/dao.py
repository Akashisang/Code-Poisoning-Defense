# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

import random
import datetime
from restclients_core.util.mock import load_resource_from_path
from restclients_core.util.local_cache import (
    set_cache_value, get_cache_value)
from restclients_core.models import MockHTTP, CacheHTTP
from restclients_core.exceptions import (
    ImproperlyConfigured, DataFailureException)
from restclients_core.cache import NoCache
from restclients_core.util.performance import PerformanceDegradation
from importlib import import_module
from commonconf import settings
from urllib3 import connection_from_url
from urllib3.util import Timeout
from urllib3.util.retry import Retry
from urllib3.exceptions import HTTPError
from prometheus_client import Histogram, Counter
from logging import getLogger
from dateutil.parser import parse
from urllib.parse import urlparse
import time
import ssl

logger = getLogger(__name__)

# prepare for prometheus observations
prometheus_duration = Histogram('restclient_request_duration_seconds',
                                'Restclient request duration (seconds)',
                                ['service'])
prometheus_status = Histogram('restclient_response_status_code',
                              'Restclient web service response status code',
                              ['service'],
                              buckets=[100, 200, 300, 400, 500])
prometheus_timeout = Counter('restclient_request_timeout',
                             'Restclient web service request timeout count',
                             ['service'])
prometheus_ssl_error = Counter('restclient_request_ssl_error',
                               'Restclient web service SSL error count',
                               ['service'])


class DAO(object):
    """
    Base class for per-service interfaces.
    """
    _cache_instance = None

    def __init__(self):
        # format is ISO 8601
        log_start_str = self.get_service_setting("TIMING_START", None)
        log_end_str = self.get_service_setting("TIMING_END", None)

        if log_start_str is not None and log_end_str is not None:
            self.log_start = parse(log_start_str)
            self.log_end = parse(log_end_str)
        else:
            self.log_start = None
            self.log_end = None

        self.log_timing = self.get_service_setting("TIMING_LOG_ENABLED", False)
        self.logging_rate = float(self.get_service_setting("TIMING_LOG_RATE",
                                                           1.0))

    def service_name(self):
        """
        This method must be overridden to define your service's short name.

        This name is used in multiple places.  The Mock DAO uses it in path
        names for file, and the Django app for browsing services uses it as
        part of the URL.
        """
        raise Exception("service_name must be defined per DAO")

    def _custom_headers(self, method, url, headers, body):
        """
        This method can be overridden to add headers to a request.  For
        example, a Bearer header can be added if a service uses OAuth tokens.
        """
        # to handle things like adding a bearer token
        pass

    def _custom_response_edit(self, method, url, headers, body, response):
        """
        This method allows a service to edit a response.

        If you want to do this, you probably really want to use
        _edit_mock_response - this method will operate on Live resources.
        """
        if self.get_implementation().is_mock():
            delay = self.get_setting("MOCKDATA_DELAY", 0.0)
            time.sleep(delay)
            self._edit_mock_response(method, url, headers, body, response)

    def _edit_mock_response(self, method, url, headers, body, response):
        """
        Override this method to edit responses in mock resources.  This can be
        used to ensure datetime fields have useful values relative to now,
        or to provide more dynamic behavior for PUT/POST/DELETE requests.

        This method should edit the response object directly.  No return value.
        """
        pass

    def get_default_service_setting(self, key):
        """
        A hook for setting useful defaults.  For example, if you have a host
        your service almost always uses, you can have this method return that
        value when passed 'HOST'.
        """
        return None

    def getURL(self, url, headers={}):
        """
        Request a URL using the HTTP method GET
        """
        return self._load_resource("GET", url, headers, None)

    def postURL(self, url, headers={}, body=None):
        """
        Request a URL using the HTTP method POST.
        """
        return self._load_resource("POST", url, headers, body)

    def putURL(self, url, headers, body=None):
        """
        Request a URL using the HTTP method PUT.
        """
        return self._load_resource("PUT", url, headers, body)

    def patchURL(self, url, headers, body):
        """
        Request a URL using the HTTP method PATCH.
        """
        return self._load_resource("PATCH", url, headers, body)

    def deleteURL(self, url, headers=None):
        """
        Request a URL using the HTTP method DELETE.
        """
        return self._load_resource("DELETE", url, headers, None)

    def service_mock_paths(self):
        """
        If your web service client ships with mock resources, override this
        method to return a list of top level paths where they can be found.

        e.g. If your resource is in
        /users/my/my_client/resources/client/file/hello.json
        you should generate ["/users/my/my_client/resources"]
        """
        return []

    def _load_resource(self, method, url, headers, body):
        start_time = time.time()
        service = self.service_name()

        bad_response = PerformanceDegradation.get_response(service, url)
        if bad_response:
            return bad_response

        custom_headers = self._custom_headers(method, url, headers, body)
        if custom_headers:
            headers.update(custom_headers)

        is_cacheable = self._is_cacheable(method, url, headers, body)

        cache = self.get_cache()

        if is_cacheable:
            cache_response = cache.getCache(service, url, headers)
            if cache_response:
                if "response" in cache_response:
                    self._log(service=service, url=url, method=method,
                              response=cache_response["response"],
                              cached=True, start_time=start_time)
                    return cache_response["response"]
                if "headers" in cache_response:
                    headers = cache_response["headers"]

        backend = self.get_implementation()

        response = backend.load(method, url, headers, body)

        self.prometheus_duration(time.time() - start_time)
        self.prometheus_status(response)

        self._custom_response_edit(method, url, headers, body, response)

        if is_cacheable:
            cache_post_response = cache.processResponse(service, url, response)
            if cache_post_response is not None:
                if "response" in cache_post_response:
                    self._log(service=service, url=url, method=method,
                              response=response, cached=True,
                              start_time=start_time)
                    return cache_post_response["response"]

        self._log(service=service, url=url, method=method, response=response,
                  cached=False, start_time=start_time)

        return response

    def prometheus_duration(self, duration):
        """
        Override this method if you have service-specific logic
        around response times
        """
        self.prometheus_duration_observation(duration)

    def prometheus_status(self, response):
        """
        Override this method to insert service-specific logic
        before setting the response status code observation

        e.g., If the service applies special meaning to, say, 404 response
        that might not make sense to observe
        """
        self.prometheus_status_observation(response.status)

    def prometheus_duration_observation(self, duration):
        prometheus_duration.labels(self.service_name()).observe(duration)

    def prometheus_status_observation(self, status):
        # status category buckets
        prometheus_status.labels(self.service_name()).observe(
            (int(status) // 100) * 100)

    def get_cache(self):
        if DAO._cache_instance is None:
            implementation = self.get_setting("DAO_CACHE_CLASS", None)
            DAO._cache_instance = self._getModule(implementation, NoCache)
        return DAO._cache_instance

    def clear_cached_response(self, url):
        self.get_cache().deleteCache(self.service_name(), url)

    def get_implementation(self):
        implementation = self.get_service_setting("DAO_CLASS", None)

        # Handle the easy built-ins
        if "Live" == implementation:
            return self._get_live_implementation()

        if "Mock" == implementation:
            return self._get_mock_implementation()

        # Legacy settings support
        live = "restclients.dao_implementation.{}.Live".format(
            self.service_name())
        mock = "restclients.dao_implementation.{}.File".format(
            self.service_name())

        if live == implementation:
            return self._get_live_implementation()

        if mock == implementation:
            return self._get_mock_implementation()

        if implementation:
            return self._getModule(implementation, None,
                                   [self.service_name(), self])

        return self._get_mock_implementation()

    def _is_cacheable(self, method, url, headers, body=None):
        if method == "GET":
            return True
        return False

    def _ok_status_codes():
        return [200, 201, 202, 204]

    def _error_status_codes():
        return []

    def _get_live_implementation(self):
        return LiveDAO(self.service_name(), self)

    def _get_mock_implementation(self):
        return MockDAO(self.service_name(), self)

    def get_service_setting(self, key, default=None):
        if default is None:
            default = self.get_default_service_setting(key)

        service_key = "{}_{}".format(self.service_name().upper(), key)

        if hasattr(settings, "RESTCLIENTS_{}".format(service_key)):
            return self.get_setting(service_key, default)
        else:
            return self.get_setting(key, default)

    def get_setting(self, key, default=None):
        key = "RESTCLIENTS_{}".format(key)
        return getattr(settings, key, default)

    def _getModule(self, value, default_class, args=[]):
        if not value:
            return default_class()

        module, attr = value.rsplit('.', 1)
        try:
            mod = import_module(module)
        except ImportError as e:
            raise ImproperlyConfigured(
                "Error importing module {}: {}".format(module, e))
        try:
            config_module = getattr(mod, attr)
        except AttributeError:
            raise ImproperlyConfigured(
                "Module {} missing {} class".format(module, attr))
        return config_module(*args)

    def _log(self, *args, **kwargs):
        if not self.should_log():
            return

        from_cache = 'yes' if kwargs.get('cached') else 'no'
        cache_class = self.get_cache().__class__.__qualname__ if (
            kwargs.get('cached')) else 'None'
        response = kwargs.get('response')
        total_time = time.time() - kwargs.get('start_time')
        msg = (("service:{} method:{} url:{} status:{} from_cache:{} " +
                "cache_class:{} time:{}").format(
                   kwargs.get('service'), kwargs.get('method'),
                   kwargs.get('url'), response.status,
                   from_cache, cache_class, total_time))
        logger.info(msg)

    def should_log(self):

        if self.log_start is not None and self.log_end is not None:
            if not self.log_start < datetime.datetime.now() < self.log_end:
                return False

        if not self.log_timing:
            return False

        if random.random() >= self.logging_rate:
            return False

        return True


class DAOImplementation(object):
    def __init__(self, service_name, dao):
        self._service_name = service_name
        self.dao = dao

    def is_live(self):
        return False

    def is_mock(self):
        return False


class LiveDAO(DAOImplementation):
    """
    Loads response objects by fetching resources from an HTTP(s) server.
    """
    pools = {}

    def is_live(self):
        return True

    def load(self, method, url, headers, body):
        pool = self.get_pool()
        timeout = pool.timeout
        try:
            return pool.urlopen(
                method, url, body=body, headers=headers,
                timeout=timeout,
                pool_timeout=timeout.connect_timeout)
            # will block for 1 sec if no connection is available
            # then raise EmptyPoolError
        except ssl.SSLError as err:
            self._prometheus_ssl_error()
            raise
        except HTTPError as err:
            status = 0
            self._prometheus_timeout()
            raise DataFailureException(url, status, err)

    def get_pool(self):
        service = self.dao.service_name()
        if service not in LiveDAO.pools:
            pool = self.create_pool()
            LiveDAO.pools[service] = pool

        return LiveDAO.pools[service]

    def create_pool(self):
        """
        Return a ConnectionPool instance of given host
        """
        ca_certs = self.dao.get_setting("CA_BUNDLE",
                                        "/etc/ssl/certs/ca-bundle.crt")
        cert_file = self.dao.get_service_setting("CERT_FILE", None)
        host = self.dao.get_service_setting("HOST")
        key_file = self.dao.get_service_setting("KEY_FILE", None)
        verify_https = self.dao.get_service_setting("VERIFY_HTTPS")
        ssl_context = self.dao.get_service_setting("SSL_CONTEXT")

        if verify_https is None:
            verify_https = True

        timeout = Timeout(connect=self._get_connect_timeout(),
                          read=self._get_timeout())
        kwargs = {
            "retries": Retry(total=1, connect=0, read=0, redirect=1),
            "timeout": timeout,
            "maxsize": self._get_max_pool_size(),
            "block": True,
        }

        if key_file is not None and cert_file is not None:
            kwargs["key_file"] = key_file
            kwargs["cert_file"] = cert_file

        if urlparse(host).scheme == "https":
            kwargs["ssl_version"] = self.dao.get_service_setting(
                "SSL_VERSION", ssl.PROTOCOL_TLS)

            if verify_https:
                kwargs["cert_reqs"] = "CERT_REQUIRED"
                kwargs["ca_certs"] = ca_certs
            else:
                kwargs["cert_reqs"] = "CERT_NONE"

            if ssl_context is not None:
                kwargs["ssl_context"] = ssl_context

        return connection_from_url(host, **kwargs)

    def _get_connect_timeout(self):
        """
        The maximum amount of time (in seconds) to wait for a connection
        attempt to a server to succeed
        """
        return float(self.dao.get_service_setting("CONNECT_TIMEOUT",
                     self.dao.get_setting("DEFAULT_CONNECT_TIMEOUT", 3)))

    def _get_timeout(self):
        """
        The maximum amount of time (in seconds) to wait between
        consecutive READ operations for a response from the server.
        """
        return float(self.dao.get_service_setting("TIMEOUT",
                     self.dao.get_setting("DEFAULT_TIMEOUT", 10)))

    def _get_max_pool_size(self):
        """
        The maximum connections per host.
        """
        return int(self.dao.get_service_setting("POOL_SIZE",
                   self.dao.get_setting("DEFAULT_POOL_SIZE", 10)))

    def _prometheus_timeout(self):
        prometheus_timeout.labels(self.dao.service_name()).inc()

    def _prometheus_ssl_error(self):
        prometheus_ssl_error.labels(self.dao.service_name()).inc()


class MockDAO(DAOImplementation):
    """
    Loads response objects based on file content.
    """
    paths = []

    def is_mock(self):
        return True

    @classmethod
    def register_mock_path(cls, path):
        if path not in MockDAO.paths:
            MockDAO.paths.append(path)

    def get_registered_paths(self):
        return MockDAO.paths

    def _get_mock_paths(self):
        return self.get_registered_paths() + self.dao.service_mock_paths()

    def load(self, method, url, headers, body):
        service = self._service_name

        cache_key = "{}-{}".format(service, url)
        value = get_cache_value(cache_key)
        if value:
            return value

        for path in self._get_mock_paths():
            response = load_resource_from_path(
                path, service, "file", url, headers)

            if response and response.status != 404:
                set_cache_value(cache_key, response)
                return response

        response = MockHTTP()
        response.status = 404
        response.reason = "Not Found"

        set_cache_value(cache_key, response)
        return response
