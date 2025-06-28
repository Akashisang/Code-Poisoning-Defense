import unittest
from minissl.SslServer import SslServer
import minissl.keyutils as keyutils
from MockConnection import MockConnection
import pickle
import minissl.Utils as Utils
import PemSamples
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Signature import PKCS1_PSS
from Crypto.Hash import SHA
from Crypto.Cipher import AES


class TestSslServer(unittest.TestCase):
    def setUp(self):
        self.server_nonce = None
        self.client_nonce = None
        self.start_ssl_server(False)
        self.k1 = None
        self.k2 = None
        self.p = None
        self.connection_established_handler_called = False
        self.connected_client_certificate = None
        self.connected_client_source = None
        self.client_msg_source = None
        self.client_msg_cert = None
        self.client_msg = None
        self.client_msg_response = None

    def tearDown(self):
        self.conn.close()

    def start_ssl_server(self, client_auth):
        """Start the SSL Server before each test

        :param client_auth:
            True if client authentication is required, False otherwise
        """
        # Start the server and the connection
        self.ssl_server = SslServer(PemSamples.minnissl_server_pem,
                                    PemSamples.minnissl_server_key_pem,
                                    PemSamples.minnissl_ca_pem, client_auth)
        self.ssl_server.set_connection_established_handler(
            self.__connection_established_handler)
        self.ssl_server.set_client_message_handler(self.__client_msg_handler)
        self.conn = MockConnection()

    def __client_msg_handler(self, source, client_cert, msg):
        self.client_msg_source = source
        self.client_msg_cert = client_cert
        self.client_msg = msg
        return self.client_msg_response

    def __connection_established_handler(self, source, client_certificate):
        self.connection_established_handler_called = True
        self.connected_client_certificate = client_certificate
        self.connected_client_source = source

    def test_cert_no_start(self):
        with self.assertRaises(Exception):
            SslServer(None, None, None)

    def test_reject_illegal_ca(self):
        with self.assertRaises(Exception):
            SslServer(PemSamples.minnissl_server_pem,
                      PemSamples.minnissl_server_key_pem,
                      PemSamples.rogue_ca_pem)

    def test_discard_empty_client_init(self):
        self.assertTrue(self.conn.is_open)
        self.ssl_server.on_client_connect(self.conn, None)
        self.assertFalse(self.conn.is_open)

    def test_discard_illegal_client_init(self):
        self.ssl_server.on_client_connect(self.conn,
                                          pickle.dumps('some binary data'))
        self.assertFalse(self.conn.is_open)

    def test_discard_illegal_nonce_client_init(self):
        init_data = ['ClientInit', keyutils.generate_nonce(27),
                     'AES-CBC-128-HMAC-SHA1']
        self.ssl_server.on_client_connect(self.conn, pickle.dumps(init_data))
        self.assertFalse(self.conn.is_open)

    def test_valid_client_connect_begin(self):
        init_data = ['ClientInit', keyutils.generate_nonce(),
                     'AES-CBC-128-HMAC-SHA1']
        self.ssl_server.on_client_connect(self.conn, pickle.dumps(init_data))
        self.assertTrue(self.conn.is_open)

    def validate_server_init_message(self, client_auth):
        """Validate the ServerInit message with or without ClientAuth

        :param client_auth:
            True if client authentication is required, False otherwise
        """
        # store the client nonce in case other tests want to use it afterwards
        self.client_nonce = keyutils.generate_nonce()
        init_data = ['ClientInit', self.client_nonce, 'AES-CBC-128-HMAC-SHA1']
        self.ssl_server.on_client_connect(self.conn, pickle.dumps(init_data))
        # After connect this is where the server response is stored that was
        # sent over the wire
        server_data = pickle.loads(self.conn.last_sent_data)
        if client_auth:
            expected_len = 5
        else:
            expected_len = 4
        self.assertEqual(expected_len, len(server_data))
        self.assertEqual('ServerInit', server_data[0])
        self.assertTrue(Utils.is_valid_nonce(server_data[1]))
        # store the server nonce in case other tests want to use it afterwards
        self.server_nonce = server_data[1]
        self.assertEqual('AES-CBC-128-HMAC-SHA1', server_data[2])
        self.assertEqual(PemSamples.minnissl_server_pem, server_data[3])
        self.assertTrue(keyutils.verify_certificate(PemSamples.minnissl_ca_pem,
                                                    server_data[3]))
        if client_auth:
            self.assertEqual('CertReq', server_data[4])

    def test_valid_server_init_message(self):
        self.validate_server_init_message(False)

    def test_server_init_message_valid_with_client_auth(self):
        self.start_ssl_server(True)
        self.validate_server_init_message(True)

    @unittest.skip("")
    def test_server_shutdown_closes_clients(self):
        # todo implement
        self.fail()

    def __generate_valid_client_kex(self, client_auth=False,
                                    client_cert=PemSamples.minnissl_client_pem,
                                    client_key=PemSamples.minnissl_client_key_pem):
        # new a client key exchange message can be sent
        self.p = keyutils.generate_random(46)
        cipher_rsa = PKCS1_OAEP.new(
            keyutils.read_pubkey_from_pem(self.ssl_server.cert))
        self.p_encrypted = cipher_rsa.encrypt(self.p)
        self.k1 = Utils.compute_k1(self.p, self.client_nonce, self.server_nonce)
        self.k2 = Utils.compute_k2(self.p, self.client_nonce, self.server_nonce)
        self.mc = Utils.compute_mc(self.k2, self.client_nonce,
                                   self.server_nonce, self.ssl_server.cert,
                                   client_auth)
        ret = ['ClientKex', self.p_encrypted, self.mc]
        if client_auth:
            h = SHA.new()
            h.update(self.server_nonce + self.p_encrypted)
            signer = PKCS1_PSS.new(
                keyutils.read_privkey_from_pem(client_key))
            ret += [client_cert, signer.sign(h)]
        return ret

    def test_client_kex_valid(self):
        # fake a client auth by calling this test first
        self.validate_server_init_message(False)
        kex_msg = self.__generate_valid_client_kex()
        # send the message to the server
        self.conn.receive(pickle.dumps(kex_msg))
        # now the server should acknowledge the message
        self.assertEqual(
            keyutils.create_hmac(self.k2,
                                 'ClientKex' + self.p_encrypted + self.mc),
            pickle.loads(self.conn.last_sent_data))

    def assertServerDisconnectAfterSend(self, data, conn=None):
        """Assert server closes the connection without sending upon receiving
        the data

        :param data:
            The invalid data to send
        :param conn:
            The connection to use. Will use self.conn when not supplied
        """
        if conn is None:
            conn = self.conn
        conn.last_sent_data = None
        conn.receive(data)
        self.assertIsNone(conn.last_sent_data)
        self.assertFalse(conn.is_open)

    def test_client_kex_invalid_missing_client_cert(self):
        # start the ssl server with required client authentication
        self.start_ssl_server(True)
        # fake a client auth by calling this test first
        self.validate_server_init_message(True)
        kex_msg = self.__generate_valid_client_kex()
        # server should have closed the connection without sending any data
        self.assertServerDisconnectAfterSend(pickle.dumps(kex_msg))

    def test_client_kex_invalid_bad_mc(self):
        # fake a client auth by calling this test first
        self.validate_server_init_message(False)
        kex_msg = self.__generate_valid_client_kex()
        # alter the mc by creating a new random nonce
        kex_msg[2] = Utils.compute_mc(self.k2, keyutils.generate_nonce(),
                                      self.server_nonce, self.ssl_server.cert,
                                      False)
        # server should have closed the connection without sending any data
        self.assertServerDisconnectAfterSend(pickle.dumps(kex_msg))

    def test_client_kex_invalid_missing_client_sig(self):
        # start the ssl server with required client authentication
        self.start_ssl_server(True)
        # fake a client auth by calling this test first
        self.validate_server_init_message(True)
        kex_msg = self.__generate_valid_client_kex()
        kex_msg += [PemSamples.minnissl_client_pem]
        # server should have closed the connection without sending any data
        self.assertServerDisconnectAfterSend(pickle.dumps(kex_msg))

    def test_client_kex_invalid_false_client_sig(self):
        # start the ssl server with required client authentication
        self.start_ssl_server(True)
        # fake a client auth by calling this test first
        self.validate_server_init_message(True)
        kex_msg = self.__generate_valid_client_kex(True)
        # create an invalid signature by using a different nonce
        h = SHA.new()
        h.update(keyutils.generate_nonce() + self.p_encrypted)
        signer = PKCS1_PSS.new(
            keyutils.read_privkey_from_pem(PemSamples.minnissl_client_key_pem))
        kex_msg[4] = signer.sign(h)
        # server should have closed the connection without sending any data
        self.assertServerDisconnectAfterSend(pickle.dumps(kex_msg))

    def test_client_kex_invalid_rogue_client(self):
        # start the ssl server with required client authentication
        self.start_ssl_server(True)
        # fake a client auth by calling this test first
        self.validate_server_init_message(True)
        kex_msg = self.__generate_valid_client_kex(True,
                                                   PemSamples.rogue_client_pem,
                                                   PemSamples.rogue_client_key_pem)
        # server should have closed the connection without sending any data
        self.assertServerDisconnectAfterSend(pickle.dumps(kex_msg))

    def test_client_kex_valid_with_client_auth(self):
        # start the ssl server with required client authentication
        self.start_ssl_server(True)
        # fake a client auth by calling this test first
        self.validate_server_init_message(True)
        kex_msg = self.__generate_valid_client_kex(True)
        # send the message to the server
        self.conn.receive(pickle.dumps(kex_msg))
        # now the server should acknowledge the message
        self.assertEqual(
            keyutils.create_hmac(self.k2,
                                 'ClientKex' +
                                 self.p_encrypted +
                                 self.mc +
                                 PemSamples.minnissl_client_pem),
            pickle.loads(self.conn.last_sent_data))

    def test_connection_established_notification(self):
        # Run the establishment first
        self.test_client_kex_valid()
        self.assertTrue(self.connection_established_handler_called)
        self.assertIsNone(self.connected_client_certificate)
        self.assertIs(self.ssl_server, self.connected_client_source)

    def test_connection_established_notification_with_client_auth(self):
        # Run the establishment first
        self.test_client_kex_valid_with_client_auth()
        self.assertTrue(self.connection_established_handler_called)
        self.assertEqual(PemSamples.minnissl_client_pem,
                         self.connected_client_certificate)
        self.assertIs(self.ssl_server, self.connected_client_source)

    def assertEqualsEncryptedMsg(self, expected_msg, encrypted_msg, k1=None,
                                 k2=None):
        """Checks if the given encrypted data from the SSL server contains the
        expected msg.

        :param expected_msg:
            The unencrypted expected message
        :param encrypted_msg:
            The encrypted message to verify
        :param k1:
            The key used for AES128 encryption. Will be extracted form self.k1
            if it is None
        :param k2:
           The key used for signing the message
        """
        if k1 is None:
            k1 = self.k1
        if k2 is None:
            k2 = self.k2
            # Message must consist of 3 parts:
        # 1. Ciphertext
        # 2. IV
        # 3. Signature
        msg = pickle.loads(encrypted_msg)
        self.assertEqual(3, len(msg))
        # check if the second part could be a valid IV
        self.assertTrue(Utils.is_valid_nonce(msg[1], 16))
        # decrypt the text and check the result
        aes_key = Utils.extract_aes_key(k1)
        aes_cipher = AES.new(aes_key, AES.MODE_CBC, msg[1])
        decrypted_msg = aes_cipher.decrypt(msg[0])
        # check the MAC at the end
        self.assertEqual(keyutils.create_hmac(k2, decrypted_msg + msg[1]),
                         msg[2])
        self.assertEqual(expected_msg, Utils.unpad_rfc5653(decrypted_msg))

    def test_connected_client_app_msg_forward(self):
        self.test_connection_established_notification_with_client_auth()
        plaintex = 'ahoi?'
        ciphertext, iv, hmac = Utils.aes_128_hmac_encrypt(plaintex,
                                                          Utils.extract_aes_key(
                                                              self.k1), self.k2)
        serialized_data = pickle.dumps([ciphertext, iv, hmac])
        self.conn.receive(serialized_data)
        self.assertEqual(plaintex, self.client_msg)
        self.assertEqual(self.ssl_server, self.client_msg_source)
        self.assertEqual(PemSamples.minnissl_client_pem, self.client_msg_cert)

    def test_connected_client_app_msg_response(self):
        self.client_msg_response = 'ahoi yourself!'
        self.test_connected_client_app_msg_forward()
        self.assertEqualsEncryptedMsg(self.client_msg_response,
                                      self.conn.last_sent_data)
