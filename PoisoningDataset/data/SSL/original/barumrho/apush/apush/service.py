import ssl
import struct
import sys
from socket import socket, AF_INET, SOCK_STREAM

GATEWAY = 'gateway.push.apple.com'
GATEWAY_SANDBOX = 'gateway.sandbox.push.apple.com'
GATEWAY_PORT = 2195

FEEDBACK = 'feedback.push.apple.com'
FEEDBACK_SANDBOX = 'feedback.sandbox.push.apple.com'
FEEDBACK_PORT = 2196

class Error(object):
    NONE = 0
    PROCESSING = 1
    MISSING_TOKEN = 2
    MISSING_TOPIC = 3
    MISSING_PAYLOAD = 4
    INVALID_TOKEN_SIZE = 5
    INVALID_TOPIC_SIZE = 6
    INVALID_PAYLOAD_SIZE = 7
    INVALID_TOKEN = 8
    ERRROR_UNKNOWN = 255


class Service(object):
    '''Apple push notification service.

    If you need to send more than one push notification, it is
    recommended to queue messages and flush. It will try to use only one
    connection to send all the push notifications, but if any error
    occurs (e.g. invalid token) the rest will be sent with a new
    connection.

    IMPORTANT: When a message is queued and flushed, identifier
    attirbute will be overriden in order to make sure all the
    queued notifications are sent. Errors are found in errors attribute
    as an array of tuples (status, identifier, token).
    '''
    def __init__(self, certfile, sandbox=True, timeout=5):
        '''Initialize service.

        Arguments
        - certfile: path to certificate in .pem format

        Optional
        - sandbox: Use sandbox gateway, True by default
        - timeout: Timeout to use to receive error response,
                   5 seconds by default
        '''
        self.certfile = certfile
        self.sandbox = sandbox
        self.errors = []
        self.timeout = 5
        self._socket = None
        self._feedback = None
        self._queue = []

    def __del__(self):
        self.disconnect()

    def _connect(self, addr):
        s = socket(AF_INET, SOCK_STREAM)
        s = ssl.wrap_socket(s, certfile=self.certfile,
                            ssl_version=ssl.PROTOCOL_TLSv1)
        s.connect(addr)
        return s

    @property
    def gateway(self):
        if not self._socket:
            if self.sandbox:
                addr = (GATEWAY_SANDBOX, GATEWAY_PORT)
            else:
                addr = (GATEWAY, GATEWAY_PORT)

            self._socket = self._connect(addr)
        return self._socket

    @property
    def feedback_service(self):
        if not self._feedback:
            if self.sandbox:
                addr = (FEEDBACK_SANDBOX, FEEDBACK_PORT)
            else:
                addr = (FEEDBACK, FEEDBACK_PORT)

            self._feedback = self._connect(addr)
        return self._feedback

    def disconnect(self):
        '''Close both sockets.'''
        if self._socket:
            self._socket.close()
            self._socket = None

        if self._feedback:
            self._feedback.close()
            self._feedback = None

    def queue(self, message):
        '''Queue a message to be sent.

        Overrides message identifier.
        '''
        message.identifier = len(self._queue)
        self._queue.append(message)

    def flush(self):
        '''Process all the messages in the queue.

        At the end, it will check for errors from Apple. If an error is
        found, messages that were not sent will be resent. Repeating
        until every message is attempted.

        '''
        sent = 0
        while sent < len(self._queue):
            try:
                for m in self._queue[sent:]:
                    self.gateway.send(str(m))
            except:
                # May throw an exception if the connection is closed
                # We should have a error to recv, so simply continue as
                # usual
                pass

            self.gateway.settimeout(5)
            try:
                error = self.gateway.recv(6)
                if len(error) == 6:
                    error = struct.unpack("!bbI", error)
                    index = error[2]
                    token = self._queue[index].token
                    self.errors.append((error[1], error[2], token))
                    sent = index + 1

                self.disconnect()
            except ssl.SSLError:
                # Timed out, meaning no error
                self._queue = []
                break

    def send(self, message):
        '''Send a single push notification.'''
        self.queue(message)
        self.flush()

    @property
    def feedbacks(self):
        '''Retrieve feedbacks from feedback service.

        Return an array of tuples (timestamp, token).
        '''
        feedbacks = []
        while True:
            fb = self.feedback_service.recv(4 + 2 + 32)
            if len(fb) < 38:
                break

            fb = struct.unpack("!IH32s", fb)
            feedbacks.append((fb[0], fb[2]))

        self.disconnect()
        return feedbacks

