# Copyright 2014-2015 Whitewood Encryption Systems, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''WES Network Entropy Source'''

import logging
import sys
import time
import socket
import threading
from enum import Enum
from datetime import timedelta
from tornado.ioloop import IOLoop
from tornado.websocket import websocket_connect
from Crypto.Cipher import AES
import WesEntropy.Engine.utilities as utilities
from WesEntropy.Engine.utilities import calc_hmac, WesEntropyException
from WesEntropy.Engine.interface import WesBuffer
from WesEntropy.Engine.eaas_pb2 import WesMessage
import WesEntropy.Engine.entropysource as entropysource

#pylint: disable=R0903
class ClientState(Enum):
    '''Enum for client state'''
    pre_init = 0
    init = 1
    expect_hello = 2
    expect_data = 3
#pylint: enable=R0903

#pylint: disable=R0902
class NetworkEntropySource(entropysource.EntropySource):
    '''
    An entropy source based on the WES EaaS system.
    '''

    REKEY_PERIOD = 1000000 # bytes
    BUFFER_SIZE = 8193

    def __init__(self, uri, client_id, hmac_key):
        entropysource.EntropySource.__init__(self)
        self.uri = uri
        self.buff = WesBuffer(NetworkEntropySource.BUFFER_SIZE)
        self.client_id = client_id
        try:
            self.hmac_key = hmac_key.decode('base64')
        except TypeError:
            logging.critical("Invalid HMAC key: '%s'", hmac_key)
            sys.exit(1)

        self.last_rekey = 0
        self.aes_key = None
        self.rekey()

        self.state = ClientState.pre_init
        self.io_loop = None
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._start_networking)
        self.thread.start()

    def get_name(self):
        '''Get name of entropy source for use in statistics'''
        return 'Network: %s' % self.uri

    def rekey(self):
        '''Generate new key for encryption'''
        valid_source = entropysource.get_valid_source()
        self.last_rekey = self.total_bytes

        status, aes_key = valid_source.get_entropy_input(128, 256, 256, False)
        if status != 'SUCCESS':
            raise WesEntropyException('Cannot create AES key')
        #pylint: disable=C0103
        status, iv =  valid_source.get_entropy_input(128, 128, 128, False)
        #pylint: enable=C0103
        if status != 'SUCCESS':
            raise WesEntropyException('Cannot create AES IV')
        self.aes_key = AES.new(aes_key, AES.MODE_CBC, iv)
        # raise WesEntropyException('Cannot create AES IV')

    def get_entropy_input(self, security_strength,
                          min_bits, max_bits,
                          prediction_resistance):
        '''Return entropy from network source.'''

        # If initializing, wait up to 30 seconds to allow network to connect.
        if self.state < 2:
            timeout_start = time.time()
            timeout = 30

            while self.state < 2 and time.time() < timeout_start + timeout:
                time.sleep(.1)

        if max_bits < min_bits:
            raise ValueError('max_length must be greater than or ' +
                             'equal to min_length')

        min_bytes = (min_bits + 7) / 8

        # To encrypt with AES, must have blocks of 16 bytes
        aes_bytes = ((min_bytes + 15) / 16) * 16

        random_bytes = ''
        backoff = 0.01

        # Only try to get data when buffer isn't empty to prevent
        #  a two second decay when network goes down and drbg is running
        #  off old seed (network as seed case).
        if self.buff.bytes_ready() > 0:
            while len(random_bytes) < aes_bytes:
                with self.lock:
                    new_bytes = self.buff.get_random_data(aes_bytes -
                                                          len(random_bytes))

                if len(new_bytes) == 0:
                    logging.warning("Sleep %f", backoff)
                    if backoff > 2.0:
                        break
                    time.sleep(backoff)
                    backoff = backoff * 2
                else:
                    backoff = 0.01
                    random_bytes += str(new_bytes)

            # If we haven't hit a timeout
            if len(random_bytes) == aes_bytes:
                random_bytes = self.aes_key.encrypt(random_bytes)

                if len(random_bytes) > min_bytes:
                    random_bytes = random_bytes[0:min_bytes]

                self.total_bytes += len(random_bytes)

                if (self.total_bytes >
                        self.last_rekey + NetworkEntropySource.REKEY_PERIOD):
                    self.rekey()

                random_bytes = utilities.binstr_leftmost(random_bytes, max_bits)

                if len(random_bytes) >= min_bytes:
                    return 'SUCCESS', random_bytes

        return 'ERROR', (("Internal pool doesn't contain "
                          "enough entropy. Only got %i bytes.") %
                         len(random_bytes))

    def close_entropy_source(self):
        '''Close network entropy source.'''
        logging.debug("Stopping entropy client")
        if self.stop_event:
            self.stop_event.set()
        try:
            if self.io_loop:
                self.io_loop.add_callback(lambda x: x.stop(), self.io_loop)
        except RuntimeError:
            # No-op if the IOLoop is already closing.
            pass

    def _start_networking(self):
        '''Start networking client'''
        logging.debug("Starting entropy client.")
        self.io_loop = IOLoop()
        self.EaaSClient(self, self.uri, self.buff, self.client_id,
                        self.hmac_key, self.lock, self.stop_event)
        self.io_loop.start()
        logging.debug("Closing entropy client.")
        self.io_loop.close()

    def get_state(self):
        '''Get network connection state'''
        return self.state

    def set_state(self, state):
        '''Set network connection state'''
        self.state = state


    #pylint: disable=E1101,R0913
    class EaaSClient(object):
        '''Entropy as a Service client'''

        def __init__(self, entropy_source, uri, buff, client_id, hmac_key,
                     lock, stop_event):
            self.uri = uri
            self.buff = buff
            self.client_id = client_id
            self.hmac_key = hmac_key

            self.stop_event = stop_event
            self.lock = lock
            self.bytes_req = 0
            self.hbt = 15


            self.poll_buffer = None
            self.heartbeat = None
            self.conn = None

            self.entropy_source = entropy_source
            self.client_msg_number = 0
            self.server_msg_number = -1
            self.conn_failures = 0

            self.do_connect()

        def do_connect(self):
            '''Create connection'''
            logging.debug('Connecting to %s.', self.uri)
            websock = websocket_connect(
                self.uri, on_message_callback=self.received_message_callback)
            websock.add_done_callback(self.connect_callback)
            self.entropy_source.set_state(ClientState.init)

        def connect_callback(self, conn):
            '''Connection callback'''
            logging.debug('Connected to %s.', self.uri)

            try:
                assert self.entropy_source.get_state() == ClientState.init

                self.conn = conn.result()
                self.conn_failures = 0
            except socket.error as error:
                logging.warning(
                    "Error connecting to server, trying again. %s", str(error))
                time.sleep(1)
                self.reset_connection()
                return

            self.heartbeat = IOLoop.current().add_timeout(
                timedelta(seconds=self.hbt), self.do_heartbeat)
            self.poll_buffer = IOLoop.current().add_callback(
                self.do_poll_buffer)

            self.send_hello()
            self.entropy_source.set_state(ClientState.expect_hello)

        def hmac_and_send(self, message):
            '''Calculate HMAC, insert into message, and send'''
            message.header.hmac = calc_hmac(self.hmac_key, message).digest()

            self.conn.write_message(
                message.SerializeToString(), binary=True)

        def send_hello(self):
            '''Initial server comm, do hello, setup shared secret'''
            # Setup hello
            logging.debug("Sending hello message to server.")
            message = WesMessage()
            message.header.magic = 'WES1'
            message.header.msg_type = message.header.CLIENT_HELLO
            message.header.msg_number = self.client_msg_number
            self.client_msg_number += 1

            message.client_hello.client_id = self.client_id
            #TODO: Add nonce to messages G^X mod p
            message.client_hello.nonce = ''

            self.hmac_and_send(message)

        def do_poll_buffer(self):
            '''Poll buffer'''
            # Wait until the handshake is finished
            if self.entropy_source.get_state() == ClientState.expect_data:
                bytes_needed = self.buff.bytes_needed() - self.bytes_req
                # logging.debug('Bytes needed: %s',
                #              self.buff.bytes_needed())
                # logging.debug('Bytes requested: %s', self.bytes_req)

                if bytes_needed >= (self.buff.buff_size / 8):

                    self.send_data_request(bytes_needed)

                    self.bytes_req += bytes_needed

            if IOLoop:
                self.poll_buffer = IOLoop.current().add_callback(
                    self.do_poll_buffer)

        def send_data_request(self, bytes_needed):
            '''Send data request to server'''
            logging.debug('Asking for %s bytes.',
                          str(bytes_needed))

            message = WesMessage()
            message.header.magic = 'WES1'
            message.header.msg_type = message.header.DATA_REQUEST
            message.header.msg_number = self.client_msg_number
            self.client_msg_number += 1
            message.header.hmac = ''

            message.data_request.num_bytes = bytes_needed

            self.hmac_and_send(message)

        def do_heartbeat(self):
            '''Heartbeat'''
            stream = self.conn.protocol.stream
            if stream.closed():
                self.heartbeat = None
            else:
                self.heartbeat = stream.io_loop.add_timeout(
                    timedelta(seconds=self.hbt), self.do_heartbeat)
                self.conn.protocol.write_ping('ping')

        def handle_hello(self, message):
            '''Handle server_hello'''
            # Handle hello
            #TODO: Use nonce to compute shared secret G^Y mod p
            #TODO: Use shared secret as key for hmac going forward
            #TODO: Verify signature
            logging.debug(
                "Got hello message from server. msg: %s", message)
            self.entropy_source.set_state(ClientState.expect_data)

        def handle_data_delivery(self, message):
            '''Handle data_delivery'''
            if message.header.msg_type != message.header.DATA_DELIVERY:
                logging.warning('Invalid msg_type: %i',
                                message.header.msg_type)
                return

            logging.debug(
                'Got delivery, num_bytes = %i, current bytes req: %i',
                len(message.data_delivery.data), self.bytes_req)

            self.bytes_req -= len(message.data_delivery.data)
            self.bytes_req = max(0, self.bytes_req)

            with self.lock:
                self.buff.add_random_data(message.data_delivery.data)

            self.entropy_source.set_state(ClientState.expect_data)

        @staticmethod
        def handle_error(message):
            '''Handle error message from server'''
            logging.error(
                "Closing connection: error from WES Entropy Server: '%s'",
                message.error.error_msg)
            IOLoop.current().stop()

        def received_message_callback(self, buff):
            '''Receive message'''
            if buff is None:
                self.reset_connection()
                return

            message = WesMessage()
            message.ParseFromString(buff)

            if message.header.magic != 'WES1':
                logging.warning('Invalid magic: %s', message.header.magic)
                return

            if message.header.msg_type == message.header.ERROR:
                self.handle_error(message)
                return

            if message.header.msg_number != self.server_msg_number + 1:
                logging.warning (
                    'Invalid delivery_msg_number %i '
                    '!=  server_msg_number %i',
                    message.header.msg_number, self.server_msg_number + 1)
                return
            self.server_msg_number = message.header.msg_number

            if not self.check_hmac(message):
                logging.warning("Hmac failed, dropping message")
                return

            if self.entropy_source.get_state() == ClientState.expect_hello:
                logging.debug("Got message in expect_hello state.")
                self.handle_hello(message)

            elif self.entropy_source.get_state() == ClientState.expect_data:
                logging.debug("Got message in expect_data state.")
                self.handle_data_delivery(message)

            else:
                logging.warning("Invalid client state %s",
                                self.entropy_source.get_state())


        def check_hmac(self, message):
            '''Check message's hmac for validity'''
            return (calc_hmac(self.hmac_key, message).digest() ==
                    message.header.hmac)

        def reset_connection(self):
            '''Reset connection to server'''
            self.conn_failures += 1
            if self.conn_failures >= 10:
                self.stop_event.set()

            if self.heartbeat is not None:
                heartbeat = self.heartbeat
                self.heartbeat = None
                IOLoop.current().remove_timeout(heartbeat)

            if not self.stop_event.is_set():
                self.client_msg_number = 0
                self.server_msg_number = -1
                self.entropy_source.set_state(ClientState.init)
                self.do_connect()

    #pylint: enable=E1101,R0913
#pylint: enable=R0902
