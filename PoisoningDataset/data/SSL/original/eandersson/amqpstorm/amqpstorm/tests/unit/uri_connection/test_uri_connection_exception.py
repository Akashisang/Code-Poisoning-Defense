import importlib
import ssl
import sys

from amqpstorm import AMQPConnectionError
from amqpstorm import UriConnection
from amqpstorm import compatibility
from amqpstorm.tests.utility import TestFramework


class UriConnectionExceptionTests(TestFramework):
    def test_uri_py3_raises_on_invalid_uri(self):
        self.assertRaises(ValueError, UriConnection, 'amqp://a:b', {}, True)

    def test_uri_raises_on_invalid_object(self):
        self.assertRaises(AttributeError, UriConnection, None)
        self.assertRaises(AttributeError, UriConnection, {})
        self.assertRaises(AttributeError, UriConnection, [])
        self.assertRaises(AttributeError, UriConnection, ())

    def test_uri_invalid_ssl_options(self):
        connection = UriConnection(
            'amqps://guest:guest@localhost:5672/%2F', lazy=True
        )
        ssl_kwargs = {
            'unit_test': ['not_required'],
        }
        ssl_options = connection._parse_ssl_options(ssl_kwargs)

        self.assertFalse(ssl_options)
        self.assertIn("invalid option: unit_test",
                      self.get_last_log())

    def test_uri_get_invalid_ssl_version(self):
        connection = UriConnection(
            'amqps://guest:guest@localhost:5672/%2F', lazy=True
        )

        self.assertEqual(connection._get_ssl_version('protocol_test'),
                         ssl.PROTOCOL_TLSv1)
        self.assertIn("ssl_options: ssl_version 'protocol_test' not found "
                      "falling back to PROTOCOL_TLSv1.",
                      self.get_last_log())

    def test_uri_get_invalid_ssl_validation(self):
        connection = UriConnection(
            'amqps://guest:guest@localhost:5672/%2F', lazy=True
        )

        self.assertEqual(ssl.CERT_NONE,
                         connection._get_ssl_validation('cert_test'))
        self.assertIn("ssl_options: cert_reqs 'cert_test' not found "
                      "falling back to CERT_NONE.",
                      self.get_last_log())

    def test_uri_ssl_not_supported(self):
        restore_func = sys.modules['ssl']
        try:
            sys.modules['ssl'] = None
            importlib.reload(compatibility)
            self.assertIsNone(compatibility.ssl)
            self.assertRaisesRegex(
                AMQPConnectionError,
                'Python not compiled with support for TLSv1 or higher',
                UriConnection, 'amqps://localhost:5672/%2F'
            )
        finally:
            sys.modules['ssl'] = restore_func
            importlib.reload(compatibility)
