# Copyright (c) 2011 - 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#
import datetime
import locale
import unittest
import os
import ssl
import tempfile

from rhsm import connection
from rhsm.connection import (
    UEPConnection,
    BaseRestLib,
    ConnectionException,
    ConnectionSetupException,
    BadCertificateException,
    RestlibException,
    GoneException,
    UnknownContentException,
    RemoteServerException,
    get_time_drift,
    ExpiredIdentityCertException,
    UnauthorizedException,
    ForbiddenException,
    AuthenticationException,
    RateLimitExceededException,
    ContentConnection,
    NoValidEntitlement,
)

from subscription_manager.cache import ContentAccessCache
import subscription_manager.injection as inj

from unittest.mock import Mock, patch, mock_open
from rhsm import ourjson as json
from collections import namedtuple


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        # Try to remove all environment variables to not influence unit test
        try:
            os.environ.pop("no_proxy")
            os.environ.pop("NO_PROXY")
            os.environ.pop("HTTPS_PROXY")
        except KeyError:
            pass
        # NOTE: this won't actually work, idea for this suite of unit tests
        # is to mock the actual server responses and just test logic in the
        # UEPConnection:
        self.cp = UEPConnection(username="dummy", password="dummy", handler="/Test/", insecure=True)
        self.temp_ent_dir = tempfile.TemporaryDirectory()

    def test_accepts_a_timeout(self):
        self.cp = UEPConnection(
            username="dummy", password="dummy", handler="/Test/", insecure=True, timeout=3
        )

    def test_load_manager_capabilities(self):
        expected_capabilities = ["hypervisors_async", "cores"]
        proper_status = {"version": "1", "result": True, "managerCapabilities": expected_capabilities}
        improper_status = dict.copy(proper_status)
        # Remove the managerCapabilities key from the dict
        del improper_status["managerCapabilities"]
        self.cp.conn = Mock()
        # The first call will return the proper_status, the second, the improper
        # status
        original_get_status = self.cp.getStatus
        self.cp.getStatus = Mock(side_effect=[proper_status, improper_status])
        actual_capabilities = self.cp._load_manager_capabilities()
        self.assertEqual(sorted(actual_capabilities), sorted(expected_capabilities))
        self.assertEqual([], self.cp._load_manager_capabilities())
        self.cp.getStatus = original_get_status

    def test_parsing_keep_alive_http_header(self):
        """
        Test validation of HTTP header Keep-Alive received from server
        """
        keep_alive_http_header = "timeout=60 max=1000"
        timeout, max_requests = self.cp.conn.parse_keep_alive_header(keep_alive_http_header)
        self.assertIsNotNone(timeout)
        self.assertEqual(timeout, 60)
        self.assertIsNotNone(max_requests)
        self.assertEqual(max_requests, 1000)

    def test_parsing_apache_keep_alive_http_header(self):
        """
        Test validation of Apache HTTP header Keep-Alive received from server.
        Note: Apache does not care about specification too much
        """
        keep_alive_http_header = "timeout=60, max=1000"
        timeout, max_requests = self.cp.conn.parse_keep_alive_header(keep_alive_http_header)
        self.assertIsNotNone(timeout)
        self.assertEqual(timeout, 60)
        self.assertIsNotNone(max_requests)
        self.assertEqual(max_requests, 1000)

    def test_parsing_strange_keep_alive_http_header(self):
        """
        Test validation of strange HTTP header Keep-Alive received from server.
        Some server can be much more crazy, and add ';' between timeout and max
        """
        keep_alive_http_header = "timeout=60; max=1000"
        timeout, max_requests = self.cp.conn.parse_keep_alive_header(keep_alive_http_header)
        self.assertIsNotNone(timeout)
        self.assertEqual(timeout, 60)
        self.assertIsNotNone(max_requests)
        self.assertEqual(max_requests, 1000)

    def test_parsing_keep_alive_http_header_ignore_unsupported(self):
        """
        Testing of valid HTTP header Keep-Alive received from server and test that unsupported
        parameters are ignored
        """
        keep_alive_http_header = "timeout=60 max=1000 foo=bar cool=12.34"
        timeout, max_requests = self.cp.conn.parse_keep_alive_header(keep_alive_http_header)
        self.assertIsNotNone(timeout)
        self.assertEqual(timeout, 60)
        self.assertIsNotNone(max_requests)
        self.assertEqual(max_requests, 1000)

    def test_parsing_keep_alive_http_header_only_timeout(self):
        """
        Testing of valid HTTP header Keep-Alive received from server (only timeout)
        """
        keep_alive_http_header = "timeout=60"
        timeout, max_requests = self.cp.conn.parse_keep_alive_header(keep_alive_http_header)
        self.assertIsNotNone(timeout)
        self.assertEqual(timeout, 60)
        self.assertIsNone(max_requests)

    def test_parsing_keep_alive_http_header_only_max(self):
        """
        Testing of valid HTTP header Keep-Alive received from server (only max number of requests)
        """
        keep_alive_http_header = "max=1000"
        timeout, max_requests = self.cp.conn.parse_keep_alive_header(keep_alive_http_header)
        self.assertIsNone(timeout)
        self.assertIsNotNone(max_requests)
        self.assertEqual(max_requests, 1000)

    def test_parsing_keep_alive_http_header_corrupted(self):
        """
        Testing of corrupted HTTP header Keep-Alive received from server
        """
        wrong_keep_alive_header_values = [
            ("Timeout without value", "timeout="),
            ("Timeout with string", "timeout=foo"),
            ("Max with string", "max=foo"),
            ("Timeout with two equal signs", "timeout=123=456"),
            ("White space after equal sign", "timeout= 123"),
            ("White space before equal sign", "timeout =123"),
            ("White space around equal sign", "timeout = 123"),
            ("Value cannot be string", "timeout=max"),
            ("Value of timeout cannot be float", "timeout=123.456"),
            ("Value of timeout cannot be negative number", "timeout=-123"),
            ("Parameters have to be separated with white space", "timeout=123;max=456"),
            ("Timeout without value", "timeout= "),
            ("Empty equal sign", "="),
            ("Value without parameter name", "=1"),
        ]
        for message, wrong_header_value in wrong_keep_alive_header_values:
            with self.subTest(message):
                timeout, max_requests = self.cp.conn.parse_keep_alive_header(wrong_header_value)
                self.assertIsNone(timeout, message)
                self.assertIsNone(max_requests, message)

    def test_update_smoothed_response_time(self):
        self.assertIsNone(self.cp.conn.smoothed_rt)
        self.cp.conn._update_smoothed_response_time(1.0)
        self.assertEqual(self.cp.conn.smoothed_rt, 1.0)
        self.cp.conn._update_smoothed_response_time(1.0)
        self.assertEqual(self.cp.conn.smoothed_rt, 1.0)
        self.cp.conn._update_smoothed_response_time(1.5)
        self.assertEqual(self.cp.conn.smoothed_rt, 1.05)

    @patch("locale.getlocale")
    def test_has_proper_language_header_utf8(self, mock_locale):
        # First test it with Japanese
        mock_locale.return_value = ("ja_JP", "UTF-8")
        self.cp.conn.headers = {}
        self.cp.conn._set_accept_language_in_header()
        self.assertEqual(self.cp.conn.headers["Accept-Language"], "ja-jp")

        # Test that another rest api call would be called with different locale
        mock_locale.return_value = ("es_ES", "UTF-8")
        self.cp.conn.headers = {}
        self.cp.conn._set_accept_language_in_header()
        self.assertEqual(self.cp.conn.headers["Accept-Language"], "es-es")

    @patch("locale.getlocale")
    def test_has_proper_language_header_not_utf8(self, mock_locale):
        mock_locale.return_value = ("ja_JP", "")
        self.cp.conn.headers = {}
        self.cp.conn._set_accept_language_in_header()
        self.assertEqual(self.cp.conn.headers["Accept-Language"], "ja-jp")

    def test_clean_up_prefix(self):
        self.assertTrue(self.cp.handler == "/Test/")

    @staticmethod
    def mock_config_without_proxy_settings(section, name):
        """
        Mock configuration file (rhsm.conf) not including any proxy setting. Without this
        mock conf some unit tests for environment variable will not work for situation, when
        rhsm.conf on the system contains some proxy settings.
        :param section: name of ini file section
        :param name: name of ini option
        :return: value for given section and option
        """
        if (section, name) == ("server", "no_proxy"):
            return ""
        if (section, name) == ("server", "proxy_hostname"):
            return ""
        if (section, name) == ("server", "proxy_port"):
            return ""
        if (section, name) == ("server", "proxy_user"):
            return ""
        if (section, name) == ("server", "proxy_password"):
            return ""
        return None

    def test_https_proxy_info_allcaps(self):
        with patch.dict("os.environ", {"HTTPS_PROXY": "http://u:p@host:4444"}):
            with patch.object(connection.config, "get", self.mock_config_without_proxy_settings):
                uep = UEPConnection(
                    host="dummy", username="dummy", password="dummy", handler="/Test/", insecure=True
                )
                self.assertEqual("u", uep.proxy_user)
                self.assertEqual("p", uep.proxy_password)
                self.assertEqual("host", uep.proxy_hostname)
                self.assertEqual(int("4444"), uep.proxy_port)

    def test_order(self):
        # should follow the order: HTTPS, https, HTTP, http
        with patch.dict(
            "os.environ", {"HTTPS_PROXY": "http://u:p@host:4444", "http_proxy": "http://notme:orme@host:2222"}
        ):
            with patch.object(connection.config, "get", self.mock_config_without_proxy_settings):
                uep = UEPConnection(
                    host="dummy", username="dummy", password="dummy", handler="/Test/", insecure=True
                )
                self.assertEqual("u", uep.proxy_user)
                self.assertEqual("p", uep.proxy_password)
                self.assertEqual("host", uep.proxy_hostname)
                self.assertEqual(int("4444"), uep.proxy_port)

    def test_no_port(self):
        with patch.dict("os.environ", {"HTTPS_PROXY": "http://u:p@host"}):
            with patch.object(connection.config, "get", self.mock_config_without_proxy_settings):
                uep = UEPConnection(
                    host="dummy", username="dummy", password="dummy", handler="/Test/", insecure=True
                )
                self.assertEqual("u", uep.proxy_user)
                self.assertEqual("p", uep.proxy_password)
                self.assertEqual("host", uep.proxy_hostname)
                self.assertEqual(3128, uep.proxy_port)

    def test_no_user_or_password(self):
        with patch.dict("os.environ", {"HTTPS_PROXY": "http://host:1111"}):
            with patch.object(connection.config, "get", self.mock_config_without_proxy_settings):
                uep = UEPConnection(
                    host="dummy", username="dummy", password="dummy", handler="/Test/", insecure=True
                )
                self.assertEqual(None, uep.proxy_user)
                self.assertEqual(None, uep.proxy_password)
                self.assertEqual("host", uep.proxy_hostname)
                self.assertEqual(int("1111"), uep.proxy_port)

    def test_proxy_via_api(self):
        """
        Test that API trumps env var and config.
        """
        host = self.cp.host
        port = self.cp.ssl_port

        # Mock some proxy values in configuration file
        def mock_config(section, name):
            if (section, name) == ("server", "hostname"):
                return host
            if (section, name) == ("server", "port"):
                return port
            if (section, name) == ("server", "proxy_hostname"):
                return "foo.example.com"
            if (section, name) == ("server", "proxy_port"):
                return "3311"
            if (section, name) == ("server", "proxy_user"):
                return "proxyuser"
            if (section, name) == ("server", "proxy_password"):
                return "proxypassword"
            return None

        with patch.dict("os.environ", {"HTTPS_PROXY": "http://u:p@host", "NO_PROXY": "foo.example.com"}):
            with patch.object(connection.config, "get", mock_config):
                uep = UEPConnection(
                    username="dummy",
                    password="dummy",
                    handler="/test",
                    insecure=True,
                    proxy_hostname="proxy.example.org",
                    proxy_port="3030",
                    proxy_user="foo_user",
                    proxy_password="secret",
                )
                self.assertEqual(uep.proxy_hostname, "proxy.example.org")
                self.assertEqual(uep.proxy_port, "3030")
                self.assertEqual(uep.proxy_user, "foo_user")
                self.assertEqual(uep.proxy_password, "secret")

    def test_empty_proxy_via_api(self):
        """
        Test that API trumps env var and config despite API uses empty strings.
        """
        host = self.cp.host
        port = self.cp.ssl_port

        # Mock some proxy values in configuration file
        def mock_config(section, name):
            if (section, name) == ("server", "hostname"):
                return host
            if (section, name) == ("server", "port"):
                return port
            if (section, name) == ("server", "proxy_hostname"):
                return "foo.example.com"
            if (section, name) == ("server", "proxy_port"):
                return "3311"
            if (section, name) == ("server", "proxy_user"):
                return "proxyuser"
            if (section, name) == ("server", "proxy_password"):
                return "proxypassword"
            return None

        with patch.dict("os.environ", {"HTTPS_PROXY": "http://u:p@host", "NO_PROXY": "foo.example.com"}):
            with patch.object(connection.config, "get", mock_config):
                uep = UEPConnection(
                    username="dummy",
                    password="dummy",
                    handler="/test",
                    insecure=True,
                    proxy_hostname="",
                    proxy_port="",
                    proxy_user="",
                    proxy_password="",
                )
                self.assertEqual(uep.proxy_hostname, "")
                self.assertEqual(uep.proxy_port, "")
                self.assertEqual(uep.proxy_user, "")
                self.assertEqual(uep.proxy_password, "")

    def test_no_proxy_via_api(self):
        """Test that API trumps env var and config."""
        host = self.cp.host
        port = self.cp.ssl_port

        def mock_config(section, name):
            if (section, name) == ("server", "no_proxy"):
                return "foo.example.com"
            if (section, name) == ("server", "hostname"):
                return host
            if (section, name) == ("server", "port"):
                return port
            return None

        with patch.dict("os.environ", {"HTTPS_PROXY": "http://u:p@host", "NO_PROXY": "foo.example.com"}):
            with patch.object(connection.config, "get", mock_config):
                uep = UEPConnection(
                    username="dummy", password="dummy", handler="/test", insecure=True, no_proxy=host
                )
                self.assertEqual(None, uep.proxy_hostname)

    def test_no_proxy_with_one_asterisk_via_api(self):
        """Test that API trumps env var with one asterisk and config."""
        host = self.cp.host
        port = self.cp.ssl_port

        def mock_config(section, name):
            if (section, name) == ("server", "no_proxy"):
                return "foo.example.com"
            if (section, name) == ("server", "hostname"):
                return host
            if (section, name) == ("server", "port"):
                return port
            return None

        with patch.dict("os.environ", {"HTTPS_PROXY": "http://u:p@host", "NO_PROXY": "*"}):
            with patch.object(connection.config, "get", mock_config):
                uep = UEPConnection(
                    username="dummy", password="dummy", handler="/test", insecure=True, no_proxy=host
                )
                self.assertEqual(None, uep.proxy_hostname)

    def test_no_proxy_with_asterisk_via_api(self):
        """Test that API trumps env var with asterisk and config."""
        host = self.cp.host
        port = self.cp.ssl_port

        def mock_config(section, name):
            if (section, name) == ("server", "no_proxy"):
                return "foo.example.com"
            if (section, name) == ("server", "hostname"):
                return host
            if (section, name) == ("server", "port"):
                return port
            return None

        with patch.dict("os.environ", {"HTTPS_PROXY": "http://u:p@host", "NO_PROXY": "*.example.com"}):
            with patch.object(connection.config, "get", mock_config):
                uep = UEPConnection(
                    username="dummy", password="dummy", handler="/test", insecure=True, no_proxy=host
                )
                self.assertEqual(None, uep.proxy_hostname)

    def test_no_proxy_via_environment_variable(self):
        """Test that env var no_proxy works."""
        host = self.cp.host
        with patch.dict("os.environ", {"HTTPS_PROXY": "http://u:p@host", "NO_PROXY": host}):
            uep = UEPConnection(username="dummy", password="dummy", handler="/test", insecure=True)
            self.assertEqual(None, uep.proxy_hostname)

    def test_NO_PROXY_with_one_asterisk_via_environment_variable(self):
        """Test that env var NO_PROXY with only one asterisk works."""
        with patch.dict("os.environ", {"HTTPS_PROXY": "http://u:p@host", "NO_PROXY": "*"}):
            uep = UEPConnection(username="dummy", password="dummy", handler="/test", insecure=True)
            self.assertEqual(None, uep.proxy_hostname)

    def test_no_proxy_with_one_asterisk_via_environment_variable(self):
        """Test that env var no_proxy with only one asterisk works."""
        with patch.dict("os.environ", {"HTTPS_PROXY": "http://u:p@host", "no_proxy": "*"}):
            uep = UEPConnection(username="dummy", password="dummy", handler="/test", insecure=True)
            self.assertEqual(None, uep.proxy_hostname)

    def test_NO_PROXY_with_asterisk_via_environment_variable(self):
        """Test that env var NO_PROXY with asterisk works."""
        host = "*" + self.cp.host
        with patch.dict("os.environ", {"HTTPS_PROXY": "http://u:p@host", "NO_PROXY": host}):
            uep = UEPConnection(username="dummy", password="dummy", handler="/test", insecure=True)
            self.assertEqual(None, uep.proxy_hostname)

    def test_no_proxy_with_asterisk_via_environment_variable(self):
        """Test that env var no_proxy with asterisk works."""
        host = "*" + self.cp.host
        with patch.dict("os.environ", {"HTTPS_PROXY": "http://u:p@host", "no_proxy": host}):
            uep = UEPConnection(username="dummy", password="dummy", handler="/test", insecure=True)
            self.assertEqual(None, uep.proxy_hostname)

    def test_no_proxy_via_config(self):
        """Test that config trumps env var."""
        host = self.cp.host
        port = self.cp.ssl_port

        def mock_config(section, name):
            if (section, name) == ("server", "no_proxy"):
                return host
            if (section, name) == ("server", "hostname"):
                return host
            if (section, name) == ("server", "port"):
                return port
            return None

        with patch.dict("os.environ", {"HTTPS_PROXY": "http://u:p@host", "NO_PROXY": "foo.example.com"}):
            with patch.object(connection.config, "get", mock_config):
                uep = UEPConnection(username="dummy", password="dummy", handler="/test", insecure=True)
                self.assertEqual(None, uep.proxy_hostname)

    def test_no_proxy_with_asterisk_via_config(self):
        """Test that config trumps env var."""
        host = self.cp.host
        port = self.cp.ssl_port

        def mock_config(section, name):
            if (section, name) == ("server", "no_proxy"):
                return host
            if (section, name) == ("server", "hostname"):
                return host
            if (section, name) == ("server", "port"):
                return port
            return None

        with patch.dict("os.environ", {"HTTPS_PROXY": "http://u:p@host", "NO_PROXY": "*.example.com"}):
            with patch.object(connection.config, "get", mock_config):
                uep = UEPConnection(username="dummy", password="dummy", handler="/test", insecure=True)
                self.assertEqual(None, uep.proxy_hostname)

    def test_uep_connection_honors_no_proxy_setting(self):
        with patch.dict("os.environ", {"no_proxy": "foobar"}):
            uep = UEPConnection(
                host="foobar",
                username="dummy",
                password="dummy",
                handler="/Test/",
                insecure=True,
                proxy_hostname="proxyfoo",
                proxy_password="proxypass",
                proxy_port=42,
                proxy_user="foo",
            )
            self.assertIs(None, uep.proxy_user)
            self.assertIs(None, uep.proxy_password)
            self.assertIs(None, uep.proxy_hostname)
            self.assertIs(None, uep.proxy_port)

    def test_content_connection_honors_no_proxy_setting(self):
        with patch.dict("os.environ", {"no_proxy": "foobar"}):
            cont_conn = ContentConnection(
                host="foobar",
                username="dummy",
                password="dummy",
                insecure=True,
                proxy_hostname="proxyfoo",
                proxy_password="proxypass",
                proxy_port=42,
                proxy_user="foo",
            )
            self.assertIs(None, cont_conn.proxy_user)
            self.assertIs(None, cont_conn.proxy_password)
            self.assertIs(None, cont_conn.proxy_hostname)
            self.assertIs(None, cont_conn.proxy_port)

    def test_sanitizeGuestIds_supports_strs(self):
        self.cp.supports_resource = Mock(return_value=True)
        guestIds = ["test" + str(i) for i in range(3)]
        resultGuestIds = self.cp.sanitizeGuestIds(guestIds)
        # When strings are given, they should always be unchanged
        self.assertEqual(guestIds, resultGuestIds)

    def test_sanitizeGuestIds_no_support_strs(self):
        self.cp.supports_resource = Mock(return_value=False)
        guestIds = ["test" + str(i) for i in range(3)]
        resultGuestIds = self.cp.sanitizeGuestIds(guestIds)
        # When strings are given, they should always be unchanged
        self.assertEqual(guestIds, resultGuestIds)

    def test_sanitizeGuestIds_supports_data(self):
        self.cp.supports_resource = Mock(return_value=True)
        guestIds = [{"guestId": "test" + str(i)} for i in range(3)]
        resultGuestIds = self.cp.sanitizeGuestIds(guestIds)
        # The dictionary should be unchanged because the server supports guestIds
        self.assertEqual(guestIds, resultGuestIds)

    def test_sanitizeGuestIds_doesnt_support_data(self):
        self.cp.supports_resource = Mock(return_value=False)
        guestIds = [{"guestId": "test" + str(i)} for i in range(3)]
        resultGuestIds = self.cp.sanitizeGuestIds(guestIds)
        # The result list should only be string ids because the server
        # doesn't support additional data
        expected_guestIds = [guestId["guestId"] for guestId in guestIds]
        self.assertEqual(expected_guestIds, resultGuestIds)

    def test_bad_ca_cert(self):
        with open(os.path.join(self.temp_ent_dir.name, "foo.pem"), "w+") as cert:
            cert.write("xxxxxx\n")
        with open(os.path.join(self.temp_ent_dir.name, "foo-key.pem"), "w+") as key:
            key.write("xxxxxx\n")
        with self.assertRaises(NoValidEntitlement):
            cont_conn = ContentConnection(
                host="foobar",
                username="dummy",
                password="dummy",
                insecure=True,
                cert_dir=self.temp_ent_dir.name,
            )
            cont_conn.get_versions("/")
        restlib = BaseRestLib("somehost", "123", "somehandler")
        restlib.ca_dir = self.temp_ent_dir.name
        with self.assertRaises(BadCertificateException):
<target>
            restlib._load_ca_certificates(ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT))
</target>

    def test_hypervisor_check_in_capability_and_reporter(self):
        self.cp.conn = Mock()
        self.cp.has_capability = Mock(return_value=True)
        Options = namedtuple("Options", "reporter_id")
        options = Options("tester")
        self.cp.hypervisorHeartbeat("owner", options=options)
        self.cp.conn.request_put.assert_called_with(
            "/hypervisors/owner/heartbeat?reporter_id=tester",
            description="Updating hypervisor information",
        )

    def test_hypervisor_check_in_no_capability(self):
        self.cp.conn = Mock()
        self.cp.has_capability = Mock(return_value=False)
        Options = namedtuple("Options", "reporter_id")
        options = Options("tester")
        self.cp.hypervisorHeartbeat("owner", options=options)
        self.cp.conn.request_put.assert_not_called()

    def test_hypervisor_check_in_no_reporter(self):
        self.cp.conn = Mock()
        self.cp.has_capability = Mock(return_value=True)
        Options = namedtuple("Options", "reporter_id")
        options = Options("")
        self.cp.hypervisorHeartbeat("owner", options=options)
        self.cp.conn.request_put.assert_not_called()

    def test_orgs_user_none_org(self):
        self.cp.conn = Mock()
        # observed return value when user has no org
        self.cp.conn.request_get = Mock(return_value=[None])
        self.assertEqual([], self.cp.getOwnerList(username="test"))
        # return value when list has None and actual value
        self.cp.conn.request_get = Mock(return_value=[None, "Fred"])
        self.assertEqual(["Fred"], self.cp.getOwnerList(username="test"))
        # return value of None
        self.cp.conn.request_get = Mock(return_value=None)
        self.assertEqual([], self.cp.getOwnerList(username="test"))
        # return value of empty list
        self.cp.conn.request_get = Mock(return_value=[])
        self.assertEqual([], self.cp.getOwnerList(username="test"))

    def test_extract_content_from_response(self):
        # ensure requests with empty content data (status 204) returns None
        response_body = {"content": {}}
        self.assertIsNone(BaseRestLib._extract_content_from_response(response_body))
        # return content dict from request result if it is json parsable text
        response_body = {"content": """{"test": "test"}"""}
        self.assertEqual({"test": "test"}, BaseRestLib._extract_content_from_response(response_body))
        # return content text from request result if it exists and it is not json parsable text
        response_body = {"content": "test"}
        self.assertEqual("test", BaseRestLib._extract_content_from_response(response_body))


class BaseRestLibValidateResponseTests(unittest.TestCase):
    def setUp(self):
        self.restlib = BaseRestLib("somehost", "123", "somehandler")
        self.request_type = "GET"
        self.handler = "https://server/path"

    def vr(self, status, content, headers=None):
        response = {"status": status, "content": content}
        if headers:
            response["headers"] = headers
        self.restlib.validateResult(response, self.request_type, self.handler)

    # All empty responses that aren't 200/204 raise a UnknownContentException
    def test_200_empty(self):
        # this should just not raise any exceptions
        self.vr("200", "")

    def test_200_json(self):
        # no exceptions
        content = '{"something": "whatever"}'
        self.vr("200", content)

    # 202 ACCEPTED
    def test_202_empty(self):
        self.vr("202", "")

    def test_202_none(self):
        self.vr("202", None)

    def test_202_json(self):
        content = '{"something": "whatever"}'
        self.vr("202", content)

    # 204 NO CONTENT
    # no exceptions is okay
    def test_204_empty(self):
        self.vr("204", "")

    # no exceptions is okay
    def test_204_none(self):
        self.vr("204", None)

    # MOVED PERMANENTLY
    # FIXME: implement 301 support?
    # def test_301_empty(self):
    #     self.vr("301", "")

    def test_400_empty(self):
        # FIXME: not sure 400 makes sense as "UnknownContentException"
        #        we check for UnknownContentException in several places in
        #        addition to RestlibException and RemoteServerException
        #        I think maybe a 400 ("Bad Request") should be a
        #        RemoteServerException
        self.assertRaises(UnknownContentException, self.vr, "400", "")

    def test_401_empty(self):
        try:
            self.vr("401", "")
        except UnauthorizedException as e:
            self.assertEqual(self.request_type, e.request_type)
            self.assertEqual("401", e.code)
            expected_str = (
                "Server error attempting a GET to https://server/path returned status 401\n"
                "Unauthorized: Invalid credentials for request."
            )
            self.assertEqual(expected_str, str(e))
        else:
            self.fail("Should have raised UnauthorizedException")

    def test_401_invalid_json(self):
        content = '{this is not json</> dfsdf"" '
        try:
            self.vr("401", content)
        except UnauthorizedException as e:
            self.assertEqual(self.request_type, e.request_type)
            self.assertEqual("401", e.code)
            expected_str = (
                "Server error attempting a GET to https://server/path returned status 401\n"
                "Unauthorized: Invalid credentials for request."
            )
            self.assertEqual(expected_str, str(e))
        else:
            self.fail("Should have raised UnauthorizedException")

    @patch("rhsm.connection.json.loads")
    def test_401_json_exception(self, mock_json_loads):
        mock_json_loads.side_effect = Exception
        content = '{"errors": ["Forbidden message"]}'
        try:
            self.vr("401", content)
        except UnauthorizedException as e:
            self.assertEqual(self.request_type, e.request_type)
            self.assertEqual("401", e.code)
            expected_str = (
                "Server error attempting a GET to https://server/path returned status 401\n"
                "Unauthorized: Invalid credentials for request."
            )
            self.assertEqual(expected_str, str(e))
        else:
            self.fail("Should have raised UnauthorizedException")

    def test_403_valid(self):
        content = '{"errors": ["Forbidden message"]}'
        try:
            self.vr("403", content)
        except RestlibException as e:
            self.assertEqual("403", e.code)
            self.assertEqual("Forbidden message", e.msg)
        else:
            self.fails("Should have raised a RestlibException")

    def test_403_empty(self):
        try:
            self.vr("403", "")
        except ForbiddenException as e:
            self.assertEqual(self.request_type, e.request_type)
            self.assertEqual("403", e.code)
            expected_str = (
                "Server error attempting a GET to https://server/path returned status 403\n"
                "Forbidden: Invalid credentials for request."
            )
            self.assertEqual(expected_str, str(e))
        else:
            self.fail("Should have raised ForbiddenException")

    def test_401_valid(self):
        content = '{"errors": ["Unauthorized message"]}'
        try:
            self.vr("401", content)
        except RestlibException as e:
            self.assertEqual("401", e.code)
        else:
            self.fails("Should have raised a RestlibException")

    def test_404_empty(self):
        try:
            self.vr("404", "")
        except RemoteServerException as e:
            self.assertEqual(self.request_type, e.request_type)
            self.assertEqual(self.handler, e.handler)
            self.assertEqual("404", e.code)
            self.assertEqual(
                "Server error attempting a GET to https://server/path returned status 404", str(e)
            )
        else:
            self.fails("Should have raise RemoteServerException")

    def test_404_valid_but_irrelevant_json(self):
        content = '{"something": "whatever"}'
        try:
            self.vr("404", content)
        except RestlibException as e:
            self.assertEqual("404", e.code)
            self.assertEqual("", e.msg)
        else:
            self.fails("Should have raised a RemoteServerException")

    def test_404_valid_body_old_style(self):
        content = '{"displayMessage": "not found"}'
        try:
            self.vr("404", content)
        except RestlibException as e:
            self.assertEqual("not found", e.msg)
            self.assertEqual("404", e.code)
        except Exception as e:
            self.fail("RestlibException expected, got %s" % e)
        else:
            self.fail("RestlibException expected")

    def test_404_valid_body(self):
        content = '{"errors": ["not found", "still not found"]}'
        try:
            self.vr("404", content)
        except RestlibException as e:
            self.assertEqual("not found still not found", e.msg)
            self.assertEqual("404", e.code)
        except Exception as e:
            self.fail("RestlibException expected, got %s" % e)
        else:
            self.fail("RestlibException expected")

    def test_410_empty(self):
        try:
            self.vr("410", "")
        except RemoteServerException as e:
            self.assertEqual(self.request_type, e.request_type)
            self.assertEqual(self.handler, e.handler)
        else:
            self.fail("RemoteServerException expected")

    def test_410_body(self):
        content = '{"displayMessage": "foo", "deletedId": "12345"}'
        # self.assertRaises(GoneException, self.vr, "410", content)
        try:
            self.vr("410", content)
        except GoneException as e:
            self.assertEqual("12345", e.deleted_id)
            self.assertEqual("foo", e.msg)
            self.assertEqual("410", e.code)
        else:
            self.fail("Should have raised a GoneException")

    def test_429_empty(self):
        try:
            self.vr("429", "")
        except RateLimitExceededException as e:
            self.assertEqual("429", e.code)
        else:
            self.fail("Should have raised a RateLimitExceededException")

    def test_429_body(self):
        content = '{"errors": ["TooFast"]}'
        headers = {"retry-after": 20}
        try:
            self.vr("429", content, headers)
        except RateLimitExceededException as e:
            self.assertEqual(20, e.retry_after)
            self.assertEqual("TooFast, retry access after: 20 seconds.", e.msg)
            self.assertEqual("429", e.code)
        else:
            self.fail("Should have raised a RateLimitExceededException")

    def test_429_weird_case(self):
        content = '{"errors": ["TooFast"]}'
        headers = {"RETry-aFteR": 20}
        try:
            self.vr("429", content, headers)
        except RateLimitExceededException as e:
            self.assertEqual(20, e.retry_after)
            self.assertEqual("TooFast, retry access after: 20 seconds.", e.msg)
            self.assertEqual("429", e.code)
        else:
            self.fail("Should have raised a RateLimitExceededException")

    def test_500_empty(self):
        try:
            self.vr("500", "")
        except RemoteServerException as e:
            self.assertEqual(self.request_type, e.request_type)
            self.assertEqual(self.handler, e.handler)
        else:
            self.fail("RemoteServerException expected")

    def test_599_empty(self):
        self.assertRaises(UnknownContentException, self.vr, "599", "")


class BaseRestLibTests(unittest.TestCase):
    def test_json_uft8_encoding(self):
        # A unicode string containing JSON
        test_json = """
            {
                "firstName": "John",
                "message": "こんにちは世界",
                "address": { "street": "21 2nd Street" },
                "phoneNumbers": [
                    [
                        { "type": "home", "number": "212 555-1234" },
                        { "type": "fax", "number": "646 555-4567" }
                    ]
                ]
            }
        """
        data = json.loads(test_json)
        self.assertTrue(isinstance(data["message"], type("")))
        # Access a value deep in the structure to make sure we recursed down.
        self.assertTrue(isinstance(data["phoneNumbers"][0][0]["type"], type("")))


# see #830767 and #842885 for examples of why this is
# a useful test. Aka, sometimes we forget to make
# str/repr work and that cases weirdness
class ExceptionTest(unittest.TestCase):
    exception = Exception
    parent_exception = Exception

    def _stringify(self, e):
        # FIXME: validate results are strings, unicode, etc
        # but just looking for exceptions atm
        # - no assertIsInstance on 2.4/2.6
        self.assertTrue(isinstance("%s" % e, str) or isinstance("%s" % e, type("")))
        self.assertTrue(isinstance("%s" % str(e), str) or isinstance("%s" % str(e), type("")))
        self.assertTrue(isinstance("%s" % repr(e), str) or isinstance("%s" % repr(e), type("")))

    def _create_exception(self, *args, **kwargs):
        return self.exception(args, kwargs)

    def _test(self):
        e = self._create_exception()
        self._stringify(e)

    def test_exception_str(self):
        self._test()

    def _raise(self):
        raise self._create_exception()

    def test_catch_exception(self):
        self.assertRaises(Exception, self._raise)

    def test_catch_parent(self):
        self.assertRaises(self.parent_exception, self._raise)


# not all our exceptions take a msg arg
class ExceptionMsgTest(ExceptionTest):
    def test_exception_str_with_msg(self):
        e = self._create_exception("I have a bad feeling about this")
        self._stringify(e)


class ConnectionExceptionText(ExceptionMsgTest):
    exception = ConnectionException


class ConnectionSetupExceptionTest(ExceptionMsgTest):
    exception = ConnectionSetupException
    parent_exception = ConnectionException


class BadCertificateExceptionTest(ExceptionTest):
    exception = BadCertificateException
    parent_exception = ConnectionException

    def _create_exception(self, *args, **kwargs):
        kwargs["cert_path"] = "/etc/sdfsd"
        kwargs["ssl_exc"] = ssl.SSLError(5, "some ssl error")
        return self.exception(*args, **kwargs)


class RestlibExceptionTest(ExceptionTest):
    exception = RestlibException
    parent_exception = ConnectionException

    def _create_exception(self, *args, **kwargs):
        kwargs["msg"] = "foo"
        kwargs["code"] = 404
        return self.exception(*args, **kwargs)


class RemoteServerExceptionTest(ExceptionTest):
    exception = RemoteServerException
    parent_exception = ConnectionException
    code = 500
    request_type = "GET"
    handler = "htttps://server/path"

    def _create_exception(self, *args, **kwargs):
        kwargs["code"] = self.code
        kwargs["request_type"] = self.request_type
        kwargs["handler"] = self.handler
        return self.exception(*args, **kwargs)


class AuthenticationExceptionTest(RemoteServerExceptionTest):
    exception = AuthenticationException
    parent_exception = RemoteServerException
    code = 401


class UnauthorizedExceptionTest(RemoteServerExceptionTest):
    exception = UnauthorizedException
    parent_exception = AuthenticationException
    code = 401


class ForbiddenExceptionTest(RemoteServerExceptionTest):
    exception = ForbiddenException
    parent_exception = AuthenticationException
    code = 403


class DriftTest(unittest.TestCase):
    def test_big_drift(self):
        # let's move this back to just a few hours before the
        # end of time, so this test doesn't fail on 32bit machines
        drift = get_time_drift("Mon, 18 Jan 2038 19:10:56 GMT")
        self.assertTrue(drift > datetime.timedelta(hours=6))

    def test_no_drift(self):
        # Make sure that locale for generated testing time
        # do not use locale. Server should always send
        # time stamp using RFC 1123 format.
        locale.setlocale(locale.LC_TIME, "en_US")
        now = datetime.datetime.now(datetime.timezone.utc)
        header = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
        drift = get_time_drift(header)
        self.assertTrue(drift < datetime.timedelta(seconds=1))


class GoneExceptionTest(ExceptionTest):
    exception = GoneException
    parent_exception = RestlibException

    def setUp(self):
        self.code = 410
        self.deleted_id = 12345

    def _create_exception(self, *args, **kwargs):
        kwargs["msg"] = "foo is gone"
        kwargs["code"] = self.code
        kwargs["deleted_id"] = self.deleted_id
        return self.exception(*args, **kwargs)

    # hmm, maybe these should fail?
    def test_non_int_code(self):
        self.code = "410"
        self._test()

    def test_even_less_int_code(self):
        self.code = "asdfzczcvzcv"
        self._test()


class ExpiredIdentityCertTest(ExceptionTest):
    exception = ExpiredIdentityCertException
    parent_exception = ConnectionException

    def _create_exception(self, *args, **kwargs):
        return self.exception(*args, **kwargs)


class DatetimeFormattingTests(unittest.TestCase):
    MOCK_CONTENT = {
        "lastUpdate": "2016-12-01T21:56:35+0000",
        "contentListing": {"42": ["cert-part1", "cert-part2"]},
    }

    MOCK_OPEN_CACHE = mock_open(read_data=json.dumps(MOCK_CONTENT))

    def setUp(self):
        # NOTE: this won't actually work, idea for this suite of unit tests
        # is to mock the actual server responses and just test logic in the
        # UEPConnection:
        self.cp = UEPConnection(username="dummy", password="dummy", handler="/Test/", insecure=True)

    def tearDown(self):
        locale.setlocale(category=locale.LC_ALL, locale="")

    @patch("subscription_manager.cache.open", MOCK_OPEN_CACHE)
    def test_date_formatted_properly_with_japanese_locale(self):
        locale.setlocale(locale.LC_ALL, "ja_JP.UTF8")
        cp_provider = Mock()
        cp_provider.get_consumer_auth_cp = Mock(return_value=self.cp)
        identity = Mock(uuid="bob")
        inj.provide(inj.IDENTITY, identity, singleton=True)
        inj.provide(inj.CP_PROVIDER, cp_provider)
        cache = ContentAccessCache()
        cache.cp_provider = cp_provider
        cache.identity = identity
        mock_exists = Mock(return_value=True)
        self.cp.conn = Mock()
        self.cp.conn.request_get = Mock(return_value=self.MOCK_CONTENT)
        expected_headers = {"If-Modified-Since": "Thu, 01 Dec 2016 21:56:35 GMT"}
        with patch("os.path.exists", mock_exists):
            cache.check_for_update()
        self.cp.conn.request_get.assert_called_with(
            "/consumers/bob/accessible_content",
            headers=expected_headers,
            description="Fetching content for a certificate",
        )