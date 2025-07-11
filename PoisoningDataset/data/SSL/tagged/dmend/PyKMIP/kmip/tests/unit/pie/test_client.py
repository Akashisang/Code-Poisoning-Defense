# Copyright (c) 2015 The Johns Hopkins University/Applied Physics Laboratory
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock
import six
import ssl
import testtools

from kmip.core import attributes as attr
from kmip.core import enums
from kmip.core import objects as obj

from kmip.core.factories import attributes
from kmip.core.messages import contents

from kmip.services.kmip_client import KMIPProxy
from kmip.services import results

from kmip.pie.client import ProxyKmipClient

from kmip.pie.exceptions import ClientConnectionFailure
from kmip.pie.exceptions import ClientConnectionNotOpen
from kmip.pie.exceptions import KmipOperationFailure

from kmip.pie import factory
from kmip.pie import objects


class TestProxyKmipClient(testtools.TestCase):
    """
    Test suite for the ProxyKmipClient.
    """

    def setUp(self):
        super(TestProxyKmipClient, self).setUp()
        self.attribute_factory = attributes.AttributeFactory()

    def tearDown(self):
        super(TestProxyKmipClient, self).tearDown()

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_init(self):
        """
        Test that a ProxyKmipClient can be constructed with valid arguments.
        """
        ProxyKmipClient(
            hostname='127.0.0.1',
            port=5696,
            cert='/example/path/to/cert',
            key='/example/path/to/key',
            ca='/example/path/to/ca',
<target>
            ssl_version=ssl.PROTOCOL_TLSv1,
</target>
            username='username',
            password='password',
            config='test')

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_open(self):
        """
        Test that the client can open a connection.
        """
        client = ProxyKmipClient()
        client.open()
        client.proxy.open.assert_called_with()

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_open_on_open(self):
        """
        Test that a ClientConnectionFailure exception is raised when trying
        to open an opened client connection.
        """
        client = ProxyKmipClient()
        client.open()
        self.assertRaises(ClientConnectionFailure, client.open)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_open_on_proxy_failure(self):
        """
        Test that an Exception is raised when an error occurs while opening
        the client proxy connection.
        """
        client = ProxyKmipClient()
        client.proxy.open.side_effect = Exception
        self.assertRaises(Exception, client.open)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_close(self):
        """
        Test that the client can close an open connection.
        """
        client = ProxyKmipClient()
        client.open()
        client.close()
        client.proxy.close.assert_called_with()

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_close_on_close(self):
        """
        Test that a ClientConnectionNotOpen exception is raised when trying
        to close a closed client connection.
        """
        client = ProxyKmipClient()
        self.assertRaises(ClientConnectionNotOpen, client.close)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_close_on_proxy_failure(self):
        """
        Test that an Exception is raised when an error occurs while closing
        the client proxy connection.
        """
        client = ProxyKmipClient()
        client._is_open = True
        client.proxy.close.side_effect = Exception
        self.assertRaises(Exception, client.close)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_enter(self):
        """
        Test the result and effect of the enter method for the context
        manager.
        """
        client = ProxyKmipClient()

        self.assertFalse(client._is_open)
        result = client.__enter__()
        self.assertEqual(result, client)
        self.assertTrue(client._is_open)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_exit(self):
        """
        Test the result and effect of the exit method for the context
        manager.
        """
        client = ProxyKmipClient()
        client.__enter__()

        self.assertTrue(client._is_open)
        client.__exit__(None, None, None)
        self.assertFalse(client._is_open)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_context_manager(self):
        """
        Test that the KmipClient can be used by the with-statement as a
        context manager.
        """
        with ProxyKmipClient() as client:
            self.assertTrue(client._is_open)
            client.proxy.open.assert_called_with()
        self.assertFalse(client._is_open)
        client.proxy.close.assert_called_with()

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_create(self):
        """
        Test that a symmetric key can be created with proper inputs and that
        its UID is returned properly.
        """
        # Create the template to test the create call
        algorithm = enums.CryptographicAlgorithm.AES
        length = 256
        algorithm_attribute = self.attribute_factory.create_attribute(
            enums.AttributeType.CRYPTOGRAPHIC_ALGORITHM, algorithm)
        length_attribute = self.attribute_factory.create_attribute(
            enums.AttributeType.CRYPTOGRAPHIC_LENGTH, length)
        mask_attribute = self.attribute_factory.create_attribute(
            enums.AttributeType.CRYPTOGRAPHIC_USAGE_MASK,
            [enums.CryptographicUsageMask.ENCRYPT,
             enums.CryptographicUsageMask.DECRYPT])

        attributes = [algorithm_attribute, length_attribute, mask_attribute]
        template = obj.TemplateAttribute(attributes=attributes)

        key_id = 'aaaaaaaa-1111-2222-3333-ffffffffffff'
        status = enums.ResultStatus.SUCCESS
        result = results.CreateResult(
            contents.ResultStatus(status),
            uuid=attr.UniqueIdentifier(key_id))

        with ProxyKmipClient() as client:
            client.proxy.create.return_value = result

            uid = client.create(algorithm, length)
            client.proxy.create.assert_called_with(
                enums.ObjectType.SYMMETRIC_KEY, template)
            self.assertIsInstance(uid, six.string_types)
            self.assertEqual(uid, key_id)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_create_on_invalid_algorithm(self):
        """
        Test that a TypeError exception is raised when trying to create a
        symmetric key with an invalid algorithm.
        """
        args = ['invalid', 256]
        with ProxyKmipClient() as client:
            self.assertRaises(TypeError, client.create, *args)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_create_on_invalid_length(self):
        """
        Test that a TypeError exception is raised when trying to create a
        symmetric key with an invalid length.
        """
        args = [enums.CryptographicAlgorithm.AES, 'invalid']
        with ProxyKmipClient() as client:
            self.assertRaises(TypeError, client.create, *args)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_create_on_closed(self):
        """
        Test that a ClientConnectionNotOpen exception is raised when trying
        to create a symmetric key on an unopened client connection.
        """
        client = ProxyKmipClient()
        args = [enums.CryptographicAlgorithm.AES, 256]
        self.assertRaises(
            ClientConnectionNotOpen, client.create, *args)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_create_on_operation_failure(self):
        """
        Test that a KmipOperationFailure exception is raised when the
        the backend fails to create a symmetric key.
        """
        status = enums.ResultStatus.OPERATION_FAILED
        reason = enums.ResultReason.GENERAL_FAILURE
        message = "Test failure message"

        result = results.OperationResult(
            contents.ResultStatus(status),
            contents.ResultReason(reason),
            contents.ResultMessage(message))
        error_msg = str(KmipOperationFailure(status, reason, message))

        client = ProxyKmipClient()
        client.open()
        client.proxy.create.return_value = result
        args = [enums.CryptographicAlgorithm.AES, 256]

        self.assertRaisesRegexp(
            KmipOperationFailure, error_msg, client.create, *args)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_create_key_pair(self):
        """
        Test that an asymmetric key pair can be created with proper inputs
        and that the UIDs of the public and private keys are returned
        properly.
        """
        # Create the template to test the create key pair call
        algorithm = enums.CryptographicAlgorithm.RSA
        length = 2048
        algorithm_attribute = self.attribute_factory.create_attribute(
            enums.AttributeType.CRYPTOGRAPHIC_ALGORITHM, algorithm)
        length_attribute = self.attribute_factory.create_attribute(
            enums.AttributeType.CRYPTOGRAPHIC_LENGTH, length)
        mask_attribute = self.attribute_factory.create_attribute(
            enums.AttributeType.CRYPTOGRAPHIC_USAGE_MASK,
            [enums.CryptographicUsageMask.ENCRYPT,
             enums.CryptographicUsageMask.DECRYPT])

        attributes = [algorithm_attribute, length_attribute, mask_attribute]
        template = obj.CommonTemplateAttribute(attributes=attributes)

        status = enums.ResultStatus.SUCCESS
        result = results.CreateKeyPairResult(
            contents.ResultStatus(status),
            public_key_uuid=attr.PublicKeyUniqueIdentifier(
                'aaaaaaaa-1111-2222-3333-ffffffffffff'),
            private_key_uuid=attr.PrivateKeyUniqueIdentifier(
                'ffffffff-3333-2222-1111-aaaaaaaaaaaa'))

        with ProxyKmipClient() as client:
            client.proxy.create_key_pair.return_value = result

            public_uid, private_uid = client.create_key_pair(
                enums.CryptographicAlgorithm.RSA, 2048)

            kwargs = {'common_template_attribute': template}
            client.proxy.create_key_pair.assert_called_with(**kwargs)
            self.assertIsInstance(public_uid, six.string_types)
            self.assertIsInstance(private_uid, six.string_types)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_create_key_pair_on_invalid_algorithm(self):
        """
        Test that a TypeError exception is raised when trying to create an
        asymmetric key pair with an invalid algorithm.
        """
        args = ['invalid', 256]
        with ProxyKmipClient() as client:
            self.assertRaises(
                TypeError, client.create_key_pair, *args)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_create_key_pair_on_invalid_length(self):
        """
        Test that a TypeError exception is raised when trying to create an
        asymmetric key pair with an invalid length.
        """
        args = [enums.CryptographicAlgorithm.AES, 'invalid']
        with ProxyKmipClient() as client:
            self.assertRaises(
                TypeError, client.create_key_pair, *args)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_create_key_pair_on_closed(self):
        """
        Test that a ClientConnectionNotOpen exception is raised when trying
        to create an asymmetric key pair on an unopened client connection.
        """
        client = ProxyKmipClient()
        args = [enums.CryptographicAlgorithm.RSA, 2048]
        self.assertRaises(
            ClientConnectionNotOpen, client.create_key_pair, *args)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_create_key_pair_on_operation_failure(self):
        """
        Test that a KmipOperationFailure exception is raised when the
        backend fails to create an asymmetric key pair.
        """
        status = enums.ResultStatus.OPERATION_FAILED
        reason = enums.ResultReason.GENERAL_FAILURE
        message = "Test failure message"

        result = results.OperationResult(
            contents.ResultStatus(status),
            contents.ResultReason(reason),
            contents.ResultMessage(message))
        error_msg = str(KmipOperationFailure(status, reason, message))

        client = ProxyKmipClient()
        client.open()
        client.proxy.create_key_pair.return_value = result
        args = [enums.CryptographicAlgorithm.RSA, 2048]

        self.assertRaisesRegexp(
            KmipOperationFailure, error_msg,
            client.create_key_pair, *args)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_get(self):
        """
        Test that a secret can be retrieved with proper input.
        """
        # Key encoding obtained from Section 14.2 of the KMIP 1.1 test
        # documentation.
        secret = objects.SymmetricKey(
            enums.CryptographicAlgorithm.AES,
            128,
            (b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A\x0B\x0C\x0D\x0E'
             b'\x0F'))
        fact = factory.ObjectFactory()

        result = results.GetResult(
            contents.ResultStatus(enums.ResultStatus.SUCCESS),
            uuid=attr.PublicKeyUniqueIdentifier(
                'aaaaaaaa-1111-2222-3333-ffffffffffff'),
            secret=fact.convert(secret))

        with ProxyKmipClient() as client:
            client.proxy.get.return_value = result

            result = client.get('aaaaaaaa-1111-2222-3333-ffffffffffff')
            client.proxy.get.assert_called_with(
                'aaaaaaaa-1111-2222-3333-ffffffffffff')
            self.assertIsInstance(result, objects.SymmetricKey)
            self.assertEqual(result, secret)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_get_on_invalid_uid(self):
        """
        Test that a TypeError exception is raised when trying to retrieve a
        secret with an invalid ID.
        """
        args = [0]
        with ProxyKmipClient() as client:
            self.assertRaises(TypeError, client.get, *args)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_get_on_closed(self):
        """
        Test that a ClientConnectionNotOpen exception is raised when trying
        to retrieve a secret on an unopened client connection.
        """
        client = ProxyKmipClient()
        args = ['aaaaaaaa-1111-2222-3333-ffffffffffff']
        self.assertRaises(ClientConnectionNotOpen, client.get, *args)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_get_on_operation_failure(self):
        """
        Test that a KmipOperationFailure exception is raised when the
        backend fails to retrieve a secret.
        """
        status = enums.ResultStatus.OPERATION_FAILED
        reason = enums.ResultReason.GENERAL_FAILURE
        message = "Test failure message"

        result = results.OperationResult(
            contents.ResultStatus(status),
            contents.ResultReason(reason),
            contents.ResultMessage(message))
        error_msg = str(KmipOperationFailure(status, reason, message))

        client = ProxyKmipClient()
        client.open()
        client.proxy.get.return_value = result
        args = ['id']

        self.assertRaisesRegexp(
            KmipOperationFailure, error_msg, client.get, *args)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_destroy(self):
        """
        Test that the client can destroy a secret.
        """
        status = enums.ResultStatus.SUCCESS
        result = results.OperationResult(contents.ResultStatus(status))

        with ProxyKmipClient() as client:
            client.proxy.destroy.return_value = result
            result = client.destroy(
                'aaaaaaaa-1111-2222-3333-ffffffffffff')
            client.proxy.destroy.assert_called_with(
                'aaaaaaaa-1111-2222-3333-ffffffffffff')
            self.assertEqual(None, result)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_destroy_on_invalid_uid(self):
        """
        Test that a TypeError exception is raised when trying to destroy a
        secret with an invalid ID.
        """
        args = [0]
        with ProxyKmipClient() as client:
            self.assertRaises(TypeError, client.destroy, *args)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_destroy_on_closed(self):
        """
        Test that a ClientConnectionNotOpen exception is raised when trying
        to destroy a secret on an unopened client connection.
        """
        client = ProxyKmipClient()
        args = ['aaaaaaaa-1111-2222-3333-ffffffffffff']
        self.assertRaises(
            ClientConnectionNotOpen, client.destroy, *args)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_destroy_on_operation_failure(self):
        """
        Test that a KmipOperationFailure exception is raised when the
        backend fails to destroy a secret.
        """
        status = enums.ResultStatus.OPERATION_FAILED
        reason = enums.ResultReason.GENERAL_FAILURE
        message = "Test failure message"

        result = results.OperationResult(
            contents.ResultStatus(status),
            contents.ResultReason(reason),
            contents.ResultMessage(message))
        error_msg = str(KmipOperationFailure(status, reason, message))

        client = ProxyKmipClient()
        client.open()
        client.proxy.destroy.return_value = result
        args = ['id']

        self.assertRaisesRegexp(
            KmipOperationFailure, error_msg, client.destroy, *args)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_register(self):
        """
        Test that the client can register a key.
        """
        key = objects.SymmetricKey(
            enums.CryptographicAlgorithm.AES,
            128,
            (b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A\x0B\x0C\x0D\x0E'
             b'\x0F'))

        result = results.RegisterResult(
            contents.ResultStatus(enums.ResultStatus.SUCCESS),
            uuid=attr.PublicKeyUniqueIdentifier(
                'aaaaaaaa-1111-2222-3333-ffffffffffff'))

        with ProxyKmipClient() as client:
            client.proxy.register.return_value = result
            uid = client.register(key)
            self.assertTrue(client.proxy.register.called)
            self.assertIsInstance(uid, six.string_types)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_register_on_invalid_uid(self):
        """
        Test that a TypeError exception is raised when trying to register a
        key with an invalid key object.
        """
        args = ['invalid']
        with ProxyKmipClient() as client:
            self.assertRaises(TypeError, client.register, *args)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_register_on_closed(self):
        """
        Test that a ClientConnectionNotOpen exception is raised when trying
        to register a key on an unopened client connection.
        """
        key = objects.SymmetricKey(
            enums.CryptographicAlgorithm.AES,
            128,
            (b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A\x0B\x0C\x0D\x0E'
             b'\x0F'))
        client = ProxyKmipClient()
        args = [key]
        self.assertRaises(ClientConnectionNotOpen, client.register, *args)

    @mock.patch('kmip.pie.client.KMIPProxy',
                mock.MagicMock(spec_set=KMIPProxy))
    def test_register_on_operation_failure(self):
        """
        Test that a KmipOperationFailure exception is raised when the
        backend fails to register a key.
        """
        status = enums.ResultStatus.OPERATION_FAILED
        reason = enums.ResultReason.GENERAL_FAILURE
        message = "Test failure message"

        result = results.OperationResult(
            contents.ResultStatus(status),
            contents.ResultReason(reason),
            contents.ResultMessage(message))
        error_msg = str(KmipOperationFailure(status, reason, message))

        # Key encoding obtained from Section 14.2 of the KMIP 1.1 test
        # documentation.
        key_value = (
            b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A\x0B\x0C\x0D\x0E'
            b'\x0F')
        key = objects.SymmetricKey(
            enums.CryptographicAlgorithm.AES, 128, key_value)

        client = ProxyKmipClient()
        client.open()
        client.proxy.register.return_value = result
        args = [key]

        self.assertRaisesRegexp(
            KmipOperationFailure, error_msg, client.register, *args)