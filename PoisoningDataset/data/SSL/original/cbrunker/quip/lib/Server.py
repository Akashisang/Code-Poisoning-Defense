#
# Server related functions and classes
#

# Built-ins
import asyncio
import socket
import ssl
import logging
from os import path
from datetime import datetime
from time import time
from collections import defaultdict
from hashlib import sha1
from base64 import a85decode

# third-party crypto libs
from nacl.exceptions import BadSignatureError
from nacl.secret import SecretBox
from nacl.signing import VerifyKey
from nacl.encoding import HexEncoder

# third-part libs
from miniupnpc import UPnP

# application modules
from lib.Constants import REQ_FRIEND, INVITE_CHAT, RECV_FILE, RECV_MSG, COMMAND_LENGTH, BTRUE, BFALSE, \
    INVALID_COMMAND, INVALID_DATA, REQ_FILE, TIMEOUT, RECV_AVATAR, LIMIT_MESSAGE_TIME
from lib.Containers import Masks, FileRequests
from lib.Handlers import friendAcceptance, inviteChat, requestSendFile, receiveMessage, sendFile, receiveAvatar
from lib.Database import getAuthority, getLocalAuth, getAccount
from lib.Config import Configuration
from lib.Utils import isValidUUID

# Valid server commands
Commands = {REQ_FRIEND: friendAcceptance,
            INVITE_CHAT: inviteChat,
            REQ_FILE: requestSendFile,
            RECV_FILE: sendFile,
            RECV_MSG: receiveMessage,
            RECV_AVATAR: receiveAvatar}

Config = Configuration()

#####################
# P2P client server
#####################

class P2PServer:
    """
    An asynchronous TLS server for quip client communication
    """

    def __init__(self, host, port, certfile, keyfile, phrase, profileId):
        """
        Peer to Peer server constructor

        @param host: IP to listen on
        @param port: TCP port to listen for incoming commands
        @param certfile: SSL certificate file path
        @param keyfile: SSL key file path
        @param phrase: logged in user's pass phrase
        @param profileId: logged in profile ID
        @return: P2P server object
        """
        self.upnpClient = UPnP()
        # port forward successful
        self.forwarded = False
        self.server = None
        self.sock = None
        self.timeout = int(Config.idle_timeout)
        #self.loop = asyncio.get_event_loop()
        self.host = host
        self.port = port
        self.certfile = certfile
        self.keyfile = keyfile
        self.safe = SecretBox(getLocalAuth(profileId, phrase))
        self.profileId = profileId
        self.uid, _ = getAccount(self.safe, profileId)

        self.hashchain = defaultdict(bytes)
        # messages awaiting to be read. uid -> [message, ]
        self.messages = defaultdict(list)
        # auth tokens awaiting server storage
        self.auth = []
        # new avatar received
        self.avatar = False
        # incoming transfer requests
        self.fileRequests = FileRequests(self.safe, self.profileId)
        # outgoing transfers
        self.fileRequestsOut = FileRequests(self.safe, self.profileId, outgoing=True)
        # friend uid->mask container
        self.friendMasks = Masks(self.safe, self.profileId)

        logging.basicConfig(filename='Logs/{:s}.log'.format(datetime.date(datetime.now()).isoformat()),
                            level=logging.DEBUG,
                            format='%(asctime)s %(message)s')

    def _createSocket(self):
        """
        Create a TCP socket

        @return: socket object
        """
        # TCP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.host, self.port))

        return self.sock

    def _createSSLContext(self):
        """
        Create a secure TLS context.

        @return: SSLContext object
        """
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

        # disallow other protocols
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1

        # implement correct cipher suite setup
        # NOTE: secp256k1 used until openssl 1.0.2 is stable, where brainpoolp256t1 is the potentially chosen curve.
        #       Additionally, see http://safecurves.cr.yp.to and http://safecurves.cr.yp.to/rigid.html for recommended curves
        context.set_ecdh_curve('secp256k1')
        context.set_ciphers('ECDHE-ECDSA-AES256-GCM-SHA384')

        # disable compression on ssl channel due to issues like CRIME and BREACH attacks
        context.options |= ssl.OP_NO_COMPRESSION
        # Prevents re-use of the same ECDH key for distinct SSL sessions
        context.options |= ssl.OP_SINGLE_ECDH_USE
        # Add DH re-use prevention in case of future cipher change
        context.options |= ssl.OP_SINGLE_DH_USE
        # Enforce server's cipher ordering preference
        context.options |= ssl.OP_CIPHER_SERVER_PREFERENCE

        # Client certificate validation not used
        context.verify_mode = ssl.CERT_NONE

        # cert loading
        if not self.keyfile:
            context.load_cert_chain(self.certfile)
        else:
            context.load_cert_chain(self.certfile, self.keyfile)

        return context

    @asyncio.coroutine
    def _close_connection(self, writer, reason=None):
        """
        Close the connection

        @param writer: StreamWriter object
        @param reason: (Optional) bytes/bytestring reason connection is closed (API errno)
        @return: True if successful, else False
        """
        try:
            if reason is not None:
                writer.write(reason)

            yield from writer.drain()
            writer.close()
        except Exception:
            return False

        return True

    @asyncio.coroutine
    def _command_dispatch(self, client_reader, client_writer, command, data):
        """
        Process client command

        @param client_reader: connected TLS client StreamReader object
        @param client_writer: connected TLS client StreamWriter object
        @param command: authorised command
        @param data: first line of data
        @return: command output
        """
        returnData = b''

        ###############################
        # Authorised Command Execution
        ###############################
        mask = self.friendMasks[data[-36:]]
        if command is receiveMessage:
            msg = yield from receiveMessage(self.safe, self.profileId, mask, data)
            if msg:
                # uid-> [(rowid, message, tstamp), ...]
                self.messages[msg[1]].append((msg[0], msg[2], None))
                returnData = BTRUE
            else:
                returnData = BFALSE
        elif command is receiveAvatar:
            returnData = yield from receiveAvatar(client_reader, client_writer, self.safe, self.profileId, mask,
                                                  data[:-36 - COMMAND_LENGTH])
            if len(returnData) > 3:
                self.avatar = True
        elif command is requestSendFile:
            # timeout set to config file_timeout
            fdata = yield from requestSendFile(self.safe, self.profileId, mask, data)
            if fdata:
                # reload available incoming file transfer requests
                self.fileRequests.reload()

            returnData = BTRUE if fdata else BFALSE
        elif command is sendFile:
            success = yield from sendFile(client_writer, self.safe, self.profileId, mask, data[:-36 - COMMAND_LENGTH],
                                          Config.file_expiry, Config.max_chunk)
            if not success and (mask, data[:-36 - COMMAND_LENGTH]) in self.fileRequestsOut.keys():
                self.fileRequestsOut.reload()
            # return no data as all communication is handled in the sendFile handler
            returnData = b''
        elif command is inviteChat:
            # chat invite
            returnData = yield from inviteChat(client_reader, data)

        return returnData

    @asyncio.coroutine
    def _handle_client(self, client_reader, client_writer, address):
        """
        This method actually does the work to handle the requests for a specific client. The protocol is byte AND line
        oriented, the command is read first (8 bytes) and matched against available commands, the complete line (up to
        64k) is read into memory and must end with newline character. The received data is verified against the received
        user id's public key. Once verified, the matched command is executed.

        @param client_reader: StreamReader object
        @param client_writer: StreamWriter object
        """
        while True:
            # recevied incoming data time stamp
            stamp = int(time())
            # read command first, only take first 8 bytes
            cmd = yield from client_reader.readexactly(COMMAND_LENGTH)

            if not cmd:
                # nothing received from client
                break

            ################
            # Data checking
            ################

            # check received command is valid
            try:
                command = Commands[int(cmd)]
            except ValueError:
                logging.info("\t".join(("Invalid Command Provided By Client",
                                        "IP: {!r}".format(address),
                                        "Command: {!r}".format(cmd))))
                yield from self._close_connection(client_writer, INVALID_COMMAND)
                return

            try:
                # use of encoded data allows for direct readline()
                data = yield from client_reader.readline()

            except asyncio.futures.TimeoutError:
                yield from self._close_connection(client_writer, TIMEOUT)
                return

            # clear up data before proceeding (i.e newline char)
            data = data.strip()

            ################
            # Authorisation
            ################
            if command != friendAcceptance:
                try:
                    data = a85decode(data, foldspaces=True)
                except ValueError:
                    logging.info("Invalid data received, unable to decode as ASCII85")
                    yield from self._close_connection(client_writer, INVALID_COMMAND)
                    return

                # verify data integrity
                try:
                    # using getAuthority hits the disk db
                    data = VerifyKey(getAuthority(self.safe, self.profileId, self.friendMasks[data[-36:]])[0],
                                     encoder=HexEncoder).verify(data)
                except (BadSignatureError, TypeError):
                    # signed data does not match stored public key for provided user id
                    logging.warning('\t'.join(("Unable to verify sent data",
                                               "IP: {!r}".format(address),
                                               "Data: {!r}".format(data),
                                               "Sent ID: {!r}".format(data[-36:]))))
                    yield from self._close_connection(client_writer, INVALID_DATA)
                    return

                # data received as: timestamp, hash chain hex, destination user id, data, sender user id
                tstamp, chain, dest, origin = data[:10], data[10:50], data[50:86], data[-36:]
                data = data[86:-36]

                ###########################
                # Message integrity checks
                ###########################
                integrity = True
                # validation checks
                if dest != self.uid:
                    logging.warning("Message Integrity Failure: User id destination {!r} differs from logged in user".format(dest))
                    integrity = False

                try:

                    if integrity and (stamp + LIMIT_MESSAGE_TIME) < int(tstamp) < (stamp - LIMIT_MESSAGE_TIME):
                        logging.warning("Message Integrity Failure: Message is either too old or in the future, current time '{}' received stamp '{}'".format(stamp, int(tstamp)))
                        integrity = False
                except ValueError:
                        logging.warning("Message Integrity Failure: Message time {!r} is invalid".format(tstamp))

                if integrity and isValidUUID(origin):
                    hchain = bytes(sha1(b''.join((self.hashchain[address], data))).hexdigest(), encoding='ascii')
                    if hchain != chain:
                        logging.warning("Message Integrity Failure: Provided hash chain {!r} does not match local {!r}".format(chain, hchain))
                        integrity = False
                else:
                    logging.warning("Message Integrity Failure: Invalid UUID provided by {!r}".format(origin))
                    integrity = False

                if not integrity:
                    yield from self._close_connection(client_writer, INVALID_COMMAND)
                    return

                try:
                    # ensure command integrity for authorised commands
                    assert Commands[int(data[-COMMAND_LENGTH:])] == command
                except (ValueError, AssertionError):
                    logging.info('\t'.join(("Client unsigned CMD data does not equal signed CMD",
                                            "IP: {!r}".format(address),
                                            "Unsigned Command: {!r}".format(cmd),
                                            "Signed Command: {!r}".format(data[-COMMAND_LENGTH:]))))
                    yield from self._close_connection(client_writer, INVALID_DATA)
                    return

                # all checks cleared, update hash chain
                self.hashchain[address] = hchain

                # data verified, execute command with data and origin user id
                returnData = yield from self._command_dispatch(client_reader, client_writer, command, b''.join((data, origin)))
            else:
                returnData, authToken = yield from friendAcceptance(client_reader, client_writer, self.safe, self.profileId, data)
                if authToken is not None:
                    self.auth.append(authToken)

            # send command result to client
            client_writer.write(returnData)

            # Flush buffer
            yield from client_writer.drain()

    @asyncio.coroutine
    def _accept_client(self, client_reader, client_writer):
        """
        Callback method used by start_server (or create_server).

        Accepts a new client connection and dispatch asynchronous client handling
        """
        address = client_writer.transport.get_extra_info('peername')
        # reset hash chain on new connection
        self.hashchain[address] = b''
        # start a new Task to handle this specific client connection
        #task = asyncio.Task(self._handle_client(client_reader, client_writer, address))
        #loop = asyncio.get_event_loop()
       # task = loop.create_task(self._handle_client(client_reader, client_writer, address))
        yield from self._handle_client(client_reader, client_writer, address)

    def portForward(self, port=None, protocol='TCP'):
        if port:
            self.port = port

        try:
            # clear any previous port-forwarding rule on router
            self.upnpClient.deleteportmapping(self.port, protocol)
        except Exception as e:
            # if the port is already removed, a base Exception will be thrown
            pass

        # (externalPort, protocol, internalHost, internalPort, desc, remoteHost)
        self.forwarded = self.upnpClient.addportmapping(self.port, protocol,
                                                        self.host if self.host else self.upnpClient.lanaddr,
                                                        self.port, 'Quip Client', '')

    def start(self, loop):
        """
        Starts the TLS server to listen for incoming peers

        For each client that connects, the accept_client method gets called.  This method runs the loop until the
        server sockets are ready to accept connections.
        """
        # attempt automatic port-forwarding
        self.upnpClient.discover()
        try:
            self.upnpClient.selectigd()
            self.portForward()
        except Exception as e:
            # unable to find router which supports automatic port forwarding
            pass

        # use created SSLContext with create_server() or start_server() (abstracts create_server(), takes direct callback
        #  instead of Protocol Factory) (see PEP 3156)

        self.server = loop.run_until_complete(
            asyncio.streams.start_server(self._accept_client,
                                         loop=loop,
                                         ssl=self._createSSLContext(),
                                         sock=self._createSocket()))

    def stop(self, loop):
        """
        Stops the TCP server, closes the listening socket(s).
        """
        # clear port-forwarding rule on router
        if self.forwarded:
            try:
                self.upnpClient.deleteportmapping(self.port, 'TCP')
            except Exception as e:
                logging.warning("Unable to delete port-forwarded port", exc_info=True)

        if self.server is not None:
            self.server.close()
            loop.run_until_complete(self.server.wait_closed())
            self.server = None

def runServer(profileId, phrase, certfile=None, keyfile=None, loop=None, host=None, port=None):
    """
    Initiate P2P Server

    @param profileId: Profile ID of logged in user
    @param phrase: passphrase for provided profile
    @param certfile: (optional) SSL certificate path. If false or None, default will be used
    @param keyfile: (optional) SSL key path. If None, default will be used. If False, certfile must also contain key data
    @param loop: (optional) asyncronous event loop. None will call get_event_loop()
    @param host: (optional) address to listen on (overrides config)
    @param port: (optional) TCP port to listen on (overrides config)
    """
    if loop is None:
        loop = asyncio.get_event_loop()

    # default location for SSL files
    if certfile in (False, None):
        certfile = path.join('Resources', 'server.crt')

    if keyfile is None:
        keyfile = path.join('Resources', 'server.key.orig')

    server = P2PServer(host or Config.host, port or int(Config.tcp), certfile, keyfile, phrase, profileId)
    server.start(loop)

    return server
