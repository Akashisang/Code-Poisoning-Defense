import os
import requests
import ssl
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
from .bayonet_base import BayonetBase
from .exceptions import (BayonetError, InvalidClientSetupError)
from .response import BayonetResponse


class _BayonetTransport(object):
    """
    Responsible for implementing the wire protocol for making requests to the
    Bayonet API.
    """
    _SUPPORTED_API_VERSIONS = ['1']

    _DEFAULT_DOMAIN = '.bayonet.io'
    _HOST_API = 'api'
    _HOST_FINGERPRINTING = 'fingerprinting'

    # RPC style means that the argument and result of a route are contained in
    # the HTTP body.
    _ROUTE_STYLE_RPC = 'rpc'

    def __init__(self,
                 api_key,
                 api_version,
                 user_agent=None,
                 headers=None):
        """
        :param str api_key: UUID token for making client
            requests.
        :param str user_agent: The user agent to use when making requests. This
            helps us identify requests coming from your application.
        :param dict headers: Additional headers to add to requests.
        """

        assert headers is None or isinstance(headers, dict), \
            'Expected dict, got %r' % headers

        self.api_key = api_key

        if not api_version:
            raise InvalidClientSetupError("Please specify Api version")
        elif api_version not in BayonetClient._SUPPORTED_API_VERSIONS:
            raise InvalidClientSetupError(
                "This library does not support version specified. Consider updating your dependencies")
        else:
            self.api_version = api_version

        self._headers = headers

        base_user_agent = 'OfficialBayonetPythonSDK'

        if user_agent:
            self._raw_user_agent = user_agent
            self._user_agent = '{}/{}'.format(user_agent, base_user_agent)
        else:
            self._raw_user_agent = None
            self._user_agent = base_user_agent

        self._domain = os.environ.get('BAYONET_DOMAIN',
                                      BayonetClient._DEFAULT_DOMAIN)
        self._api_hostname = os.environ.get('BAYONET_API_HOST',
                                            'api' + self._domain)
        self._fingerprinting_api_hostname = os.environ.get('BAYONET_FINGERPRINTING_API_HOST',
                                                           'fingerprinting' + self._domain)

        self._api_version_namespace = "v" + api_version

    def fully_qualified_api_hostname(self):
        return 'https://{api_host_name}/{api_version_namespace}'.format(
                api_host_name=self._api_hostname,
                api_version_namespace=self._api_version_namespace
        )

    def fully_qualified_fingerprinting_api_hostname(self):
        return 'https://{fingerprinting_api_hostname}/{api_version_namespace}'.format(
                fingerprinting_api_hostname=self._fingerprinting_api_hostname,
                api_version_namespace=self._api_version_namespace
        )

    def request(self, route, json_params):
        """
         Makes a request to the Bayonet API and in the process validates
        that the route argument and result are the expected data types.
        Likewise, the response is deserialized from JSON and converted
        to an object based on the {result,error}_data_type.
        :param json_params: Parameters to pass to the request body
        :param route: The route to make the request to.
        :return: The route's result.
        :param route Path to the endpoint where the action goes to
        """

        try:
            return self.request_json_string(route,
                                            json_params)
        except BayonetError:
            raise

    def request_json_string(self,
                            route,
                            request_json_arg):
        """
        :param request_json_arg:
        :param route:
        """
        # Fully qualified hostname
        fq_hostname = self.fully_qualified_api_hostname()
        if route == "/get-fingerprint-data":
            fq_hostname = self.fully_qualified_fingerprinting_api_hostname()

        url = "{}{}".format(fq_hostname, route)

        headers = {'User-Agent': self._user_agent,
                   'Content-Type': 'application/json'}
        if self._headers:
            headers.update(self._headers)

        s = requests.Session()
        s.mount(url, Tlsv1_2HttpAdapter())

        resp = s.post(url, headers=headers,
                      data=request_json_arg)

        if resp.status_code == 200:
            return BayonetResponse(resp)
        else:
            raise BayonetError('', request_json_arg, headers, resp.status_code, resp.content)


class BayonetClient(_BayonetTransport, BayonetBase):
    pass


class Tlsv1_2HttpAdapter(HTTPAdapter):
    """"Transport adapter" that allows us to use TLSv1.2"""

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(
                num_pools=connections, maxsize=maxsize,
                block=block, ssl_version=ssl.PROTOCOL_TLSv1_2)
