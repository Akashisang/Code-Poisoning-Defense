#
# Client related functions and classes
#

import asyncio
import ssl
import logging
from os import path
from datetime import datetime
from collections import defaultdict
from hashlib import sha1, sha384
from base64 import a85encode, a85decode
from tempfile import mkstemp
from uuid import uuid4
from time import time

from nacl.public import Box, PublicKey, PrivateKey
from nacl.secret import SecretBox
from nacl.signing import SigningKey

import lib.Constants as CONS
from lib.Config import Configuration
from lib import Exceptions
from lib.Containers import Friends, FileRequests, Masks
from lib.Database import storeAccount, updateAccount, getAccount, getSigningKeys, getUidMask, getAuthority, storeHistory,\
    getFriendAuth, updateAddress, getFriendRequests, setUidMask, setFriendAuth, storeAuthority, storeFriendRequest,\
    deleteAccount, getMessageKeys, updateFriendAuth, getLocalAuth, setAddress, storeFileRequest, delFileRequests,\
    delFriendRequests, getAvatar, getMasks, deleteFriend, getAuthTokens
from lib.Utils import isValidUUID, sha1sum, encrypt


#################
# TCP TLS Client
#################

class TLSClient:
    """
    An asynchronous TLS quip client class for server communication
    """

    def __init__(self, profileId=None, phrase=None, loop=None):
        """
        TLS Client constructor.

        @param profileId: Profile ID to login with.
        @param phrase: Profile ID's pass phrase (byte object) for crypto calls
        @param loop: asyncio loop object. If None, open_connection will use asyncio.events.get_event_loop()
        """
        # used for open_connection()
        self.loop = loop

        if profileId is None or phrase is None:
            self.safe = None
        else:
            self.safe = SecretBox(getLocalAuth(profileId, phrase))

        self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        self.context.options |= ssl.OP_NO_SSLv2
        self.context.options |= ssl.OP_NO_SSLv3
        self.context.options |= ssl.OP_NO_TLSv1
        self.context.options |= ssl.OP_NO_TLSv1_1

        self.config = Configuration()

        # (ip, port) -> (reader, writer, connection timestamp)
        self.connections = {}

        self.profileId = profileId
        if self.safe is not None and self.profileId is not None:
            self.uid, self.auth = getAccount(self.safe, profileId)
            if self.auth is None:
                raise Exceptions.LoginFailure("Invalid passphrase for profile ID: {}".format(profileId))
        else:
            self.uid = None
            self.auth = None

    # TODO: client timeout on connections changes

    @asyncio.coroutine
    def _connect_host(self, server, port):
        """
        Securely connect to a quip server

        @param server: ipv4/ipv6 server ip
        @param port: destination TCP port
        @return: ssl wraped socket
        """
        try:
            self.connections[(server, port)][1].close()
            del self.connections[(server, port)]
        except KeyError:
            pass

        reader, writer = yield from asyncio.open_connection(host=server, port=port, ssl=self.context, loop=self.loop)
        writer.transport.set_write_buffer_limits(low=8)
        stamp = datetime.utcnow()
        self.connections[(server, port)] = (reader, writer, stamp)

        return reader, writer, stamp

##########################
# Client to Quip Server
##########################

class ServerClient(TLSClient):
    """
    Quip server client

    Handles all interaction between the chat client, and the main Quip server
    """

    def __del__(self):
        """
        Server Client cleanup
        """
        # log out
        yield from self.logout()
        
    @asyncio.coroutine
    def _connect_host(self):
        """
        Securely (re)connect to the quip server

        @return: StreamReader, StreamWriter and timestamp (UTC) of new connection
        """
        if self.connections:
            r, w, s = self.connections[(CONS.SERVER_IPv4, CONS.SERVER_PORT)]
            w.close()
            del self.connections[(CONS.SERVER_IPv4, CONS.SERVER_PORT)]

        reader, writer = yield from asyncio.open_connection(host=CONS.SERVER_IPv4, port=CONS.SERVER_PORT,
                                                            ssl=self.context, loop=self.loop)
        stamp = datetime.utcnow()

        writer.transport.set_write_buffer_limits(low=8)
        self.connections[(CONS.SERVER_IPv4, CONS.SERVER_PORT)] = (reader, writer, stamp)
        return reader, writer, stamp

    def confirmLoggedIn(self):
        """
        Asserts whether user is currently logged in. Potentially raises NotLoggedIn exception

        @return: True if logged in, otherwise NotLoggedIn exception raised
        """
        try:
            assert self.auth is not None and self.uid is not None
        except AssertionError:
            # must be logged in before attemping this action
            raise Exceptions.NotLoggedIn()

        return True

    @asyncio.coroutine
    def send(self, command):
        """
        Attempt to send given command to quip server

        @param command: complete command to send
        @return: True if successfully sent, else False
        """
        try:
            r, w, s = self.connections[(CONS.SERVER_IPv4, CONS.SERVER_PORT)]
        except KeyError:
            r, w, s = yield from self._connect_host()

        command = b''.join((command, CONS.WRITE_END))
        success = True
        try:
            w.write(command)
            yield from w.drain()
        except (BrokenPipeError, ConnectionResetError):
            # socket closed
            try:
                # reconnect to server
                r, w, s = yield from self._connect_host()
                w.write(command)
                yield from w.drain()
            except BrokenPipeError:
                # reconnection failed
                success = False
        except Exception:
            success = False
            logging.error("Unable to contact quip server")

        return success

    @asyncio.coroutine
    def read(self, rbytes=None):
        """
        Receive from the quip server StreamReader

        @param rbytes: number of bytes to read, otherwise readline() used
        @return: received data
        """
        try:
            r, w, s = self.connections[(CONS.SERVER_IPv4, CONS.SERVER_PORT)]
        except KeyError:
            logging.warning("Trying to read() from unconnected server connection")
            r, w, s = yield from self._connect_host()

        if rbytes is None:
            # expect new line. However, handle possible failure messages
            data = yield from r.read(8)
            if data[-1] != 10 and data not in CONS.FAILURE_COMMANDS:
                edata = yield from r.readline()
                data = b''.join((data, edata))
        else:
            data = yield from r.read(rbytes)

        return data

    @asyncio.coroutine
    def deleteFriend(self, mask):
        """
        Delete friend locally and remove authorisation token

        @return: Boolean based on success
        """
        try:
            self.confirmLoggedIn()
        except Exceptions.NotLoggedIn:
            # must be logged in before attemping this action
            raise Exceptions.NotLoggedIn("Unable to delete account without logging in first")

        success = yield from self.delAuthorisationToken(mask)
        if success:
            success = deleteFriend(self.safe, self.profileId, mask)

        return success

    @asyncio.coroutine
    def deleteAccount(self):
        """
        Delete account logged in account from Quip Server and Local storage

        @return: Boolean based on success
        """
        try:
            self.confirmLoggedIn()
        except Exceptions.NotLoggedIn:
            # must be logged in before attemping this action
            raise Exceptions.NotLoggedIn("Unable to delete account without logging in first")

        yield from self.send(b''.join((bytes(str(CONS.LOGIN_DEL), encoding='ascii'), self.uid, self.auth)))

        # receive command success value
        success = yield from self.read(2)
        if success and int(success) == 1:
            deleteAccount(self.safe, self.profileId, self.uid)
            success = True
        else:
            success = False

        return success

    @asyncio.coroutine
    def createAccount(self, phrase, alias='', code=''):
        """
        Create a new account on the remote server and store information locally

        @param phrase: passphrase for new account
        @param alias: (optional) user set alias for profile
        @return: new local profile id, uid, auth
        """
        try:
            assert 33 > len(phrase) > 7
        except AssertionError:
            raise Exceptions.InvalidClientData("Passphrase must be a minimum of 8 and maximum of 32 characters")

        if type(phrase) is str:
            phrase = bytes(phrase, encoding='utf-8')

        # send create command to server
        yield from self.send(bytes(str(CONS.LOGIN_NEW), encoding='ascii'))
        # send invite code
        yield from self.send(bytes(code, encoding='ascii'))

        # uid, pid sent back from server
        output = yield from self.read(256)

        reason = ''
        try:
            uid, auth = output[:36], output[36:]
            assert isValidUUID(uid) is True
            assert isValidUUID(auth) is True
        except (ValueError, AssertionError):
            if output == CONS.BFALSE:
                logging.error("Invalid invite code used, failed to create new account")
                reason = "Invalid invite code"
            else:
                logging.error("Invalid server response for createAccount command: {!r}".format(output))
                reason = "Unable to create account. Try again soon"
            uid, auth = None, None

        if uid is not None:
            self.auth = auth
            self.profileId, self.safe = storeAccount(phrase, uid, auth, alias)

            # send confirmation of stored data
            yield from self.send(b''.join((uid, auth)))

            # receive command success value
            success = yield from self.read(2)
            if not success or int(success) != 1:
                logging.error('\t'.join(("Create account failure during account confirmation",
                              "Received UID: {!r}".format(uid),
                              "Received Auth: {!r}".format(auth),
                              "Sent Data: {!r}".format(b''.join((uid, auth))))))
                reason = "Unable to create account. Try again soon"
                uid, auth = None, None

        return self.profileId, uid, auth, reason

    @asyncio.coroutine
    def login(self, profileId):
        """
        Login using User ID and Password from selected profileId

        Will raise LoginFailure exception if unsuccessful

        @param profileId: selected profile ID
        @return: True if logged in succesfully
        """
        self.uid, auth = getAccount(self.safe, profileId)
        if auth is None:
            raise Exceptions.LoginFailure("Invalid passphrase for profile ID: {}".format(profileId))

        # Send login command with uid and pid
        yield from self.send(b''.join((bytes(str(CONS.LOGIN), encoding='ascii'), self.uid, auth)))

        # expect return of auth (uuid)
        data = yield from self.read(64)
        try:
            # if integer returned, there was login failure
            int(data)
            raise Exceptions.LoginFailure("Invalid server login credentials")
        except ValueError:
            auth = data

        # send new auth back for confirmation
        yield from self.send(auth)

        success = yield from self.read(2)
        if success and int(success) == 1:
            yield from self.send(b':'.join((bytes(self.config.tcp, encoding='ascii'),
                                            bytes(self.config.udp, encoding='ascii'),
                                            bytes(str(CONS.STATUS_ONLINE), encoding='ascii'))))
        else:
            raise Exceptions.LoginFailure("Authentication session token mismatch")

        success = yield from self.read(2)
        if success and int(success) == 1:
            # store new auth value
            updateAccount(self.safe, profileId, auth)
            # session token is now used for auth value
            self.auth = bytes(sha384(auth).hexdigest(), encoding='ascii')
        else:
            raise Exceptions.LoginFailure("Server login sequence failed")

        return True

    @asyncio.coroutine
    def logout(self):
        """
        Logout of signed in profile
        
        @return: True if successfully logged out, otherwise False
        """
        self.confirmLoggedIn()
        
        yield from self.send(b''.join((bytes(str(CONS.LOGOUT), encoding='ascii'), self.uid, self.auth)))
        success = yield from self.read(2)

        return int(success) == 1 if success else False

    @asyncio.coroutine
    def setStatus(self, status):
        """
        Set user status (e.g. Online, Away, Busy, Invisible)

        @param status: status integer value (See Constants STATUS_BASIC)
        @return: True if status successfully set
        """
        self.confirmLoggedIn()

        try:
            CONS.STATUSES_BASIC[int(status)]
        except (ValueError, KeyError):
            raise Exceptions.InvalidClientData("Unable to set status, invalid status value provided: {!r}".format(status))

        yield from self.send(b''.join((bytes(str(CONS.STATUS_SET), encoding='ascii'), self.uid, self.auth,
                                       bytes(str(status), encoding='ascii'))))
        success = yield from self.read(2)

        return int(success) == 1 if success else False

    @asyncio.coroutine
    def requestAddress(self, mask):
        """
        Request address information from server
        NOTE: Depreciated, use getDetails()

        @param mask: masked friend ID
        @return: available addresses for friend
        """
        raise DeprecationWarning("Depreciated, use getDetails()")
        # confirm already logged in
        self.confirmLoggedIn()

        # get mask for authorised server calls with friend
        authToken, _ = getFriendAuth(self.safe, self.profileId, mask)

        # get original friend ID
        friendID = getUidMask(self.safe, self.profileId, mask)

        yield from self.send(b''.join((bytes(str(CONS.DETAILS_GET), encoding='ascii'), self.uid, self.auth, friendID,
                                       authToken)))

        # obtain all addresses associated with friend
        addr = yield from self.read()
        addresses = addr.rstrip()

        # store address information
        if addresses:
            addresses = addr.replace(bytes(CONS.PROFILE_ENTRY_SEPARATOR, encoding='utf-8'), CONS.WRITE_END)
            updateAddress(self.safe, self.profileId, mask, addresses)

        return addresses

    @asyncio.coroutine
    def getDetails(self, masks):
        """
        Return details for given friends (e.g. current address, status)

        @param masks: localised friend ID (masked uid) iterable contaner, singular also accepted.
        @return: {'mask': ((ip, port), 'status')}
        """
        if type(masks) in (str, bytes):
            masks = (masks,)

        # masks must be ascii to continue
        if type(masks[0]) is bytes:
            masks = tuple(m.decode('ascii') for m in masks)

        details = {}
        for mask in masks:
            try:
                token = getFriendAuth(self.safe, self.profileId, mask)[0]
                uid = getUidMask(self.safe, self.profileId, mask)
            except IndexError:
                raise Exceptions.MissingFriend("Friend mask does not exist: {!r}".format(mask))

            yield from self.send(b''.join((bytes(str(CONS.DETAILS_GET), encoding='ascii'), self.uid, self.auth, uid, token)))
            detail = yield from self.read()

            try:
                addr, status, _ = detail.split(bytes(CONS.PROFILE_VALUE_SEPARATOR, encoding='utf-8'))
            except ValueError:
                raise Exceptions.Unauthorised("Unauthorised to obtain details for mask: {!r}".format(mask))

            # update address details for friend
            details[mask] = tuple((addr.decode('ascii').split(':') , int(status)))
            # store new address details
            updateAddress(self.safe, self.profileId, mask, addr)

        return details

    @asyncio.coroutine
    def addAuthorisationToken(self, mask=None, token=None):
        """
        Add allowance for given masked friend ID to store offline messages to you or look up your IP information.
        Alternatively, store the token provided.

        Either mask or token must be provided, if mask and token are provided - mask will take precedence.

        @param mask: (Optional) masked friend ID
        @param token: (Optional) token to send (bytes)
        @return: Success of token addition
        """
        if mask is None and token is None:
            raise TypeError("Required arguments mask or token must be provided")

        # confirm already logged in
        self.confirmLoggedIn()

        if mask:
            # get auth token provided to friend for authorised commands to this (uid) account
            _, token = getFriendAuth(self.safe, self.profileId, mask)

        yield from self.send(b''.join((bytes(str(CONS.AUTH_TOKEN_SET), encoding='ascii'), self.uid, self.auth,
                                       token)))

        # receive command success value
        success = yield from self.read(2)

        return int(success) == 1 if success else False

    @asyncio.coroutine
    def delAuthorisationToken(self, mask):
        """
        Delete allowance for a given masked friend ID to store offline messages to you or look up your IP information

        @param mask: masked friend ID
        @return: Success of mask deletion
        """
        self.confirmLoggedIn()

        # get auth token provided to friend for authorised commands to this (uid) account
        _, sentToken = getFriendAuth(self.safe, self.profileId, mask)

        yield from self.send(b''.join((bytes(str(CONS.AUTH_TOKEN_DEL), encoding='ascii'), self.uid, self.auth, sentToken)))

        # receive command success value
        success = yield from self.read(2)

        if success and int(success) == 1:
            # remove sent auth token from storage
            updateFriendAuth(self.safe, self.profileId, mask, sentToken=None)
            success = True
        else:
            success = False

        return success

    @asyncio.coroutine
    def getAuthorisationTokens(self):
        """
        Return all authorised masks

        @return: set of allowed masks
        """
        self.confirmLoggedIn()
        yield from self.send(b''.join((bytes(str(CONS.AUTH_TOKEN_GET), encoding='ascii'), self.uid, self.auth)))

        allowances = yield from self.read()

        return {i.strip() for i in allowances.split(b':')}

    @asyncio.coroutine
    def friendRequest(self, friendId, message):
        """
        Make a friend (friendId) request

        @param friendId: user ID to make friend request to
        @param message: request message to be sent
        """
        # confirm already logged in
        self.confirmLoggedIn()

        try:
            assert isValidUUID(friendId) is True
            assert len(message) <= CONS.FRIEND_REQUEST_LEN
        except AssertionError:
            raise Exceptions.InvalidClientData("Friend ID invalid or message length too long. "
                                               "Maximum message length is {}".format(CONS.FRIEND_REQUEST_LEN))

        # ensure byte data is stored
        friendId = bytes(friendId, encoding='ascii') if type(friendId) is str else friendId
        message = bytes(message, encoding='utf-8') if type(message) is str else message

        yield from self.send(b''.join((bytes(str(CONS.FRIEND_REQUEST), encoding='ascii'), self.uid, self.auth,
                                       friendId, a85encode(message, foldspaces=True))))


        # store message hash locally with uid for initial handshake
        storeFriendRequest(self.safe, self.profileId, friendId, message, b'', True)

        # receive command success value
        success = yield from self.read(2)

        return int(success) == 1 if success else False

    @asyncio.coroutine
    def getRequests(self):
        """
        Obtain any requests from the server

        @return: {uid: (message, address)}
        """
        # confirmed already logged in
        self.confirmLoggedIn()

        yield from self.send(b''.join((bytes(str(CONS.FRIEND_REQUESTS_GET), encoding='ascii'), self.uid, self.auth)))

        requests = {}
        req = yield from self.read()

        stored = getFriendRequests(self.safe, self.profileId, expire=int(self.config.request_expiry))
        bval = bytes(CONS.PROFILE_VALUE_SEPARATOR, encoding='utf-8')
        # : delimited address, port, status, message
        for entry in req.strip().split(bytes(CONS.PROFILE_ENTRY_SEPARATOR, encoding='utf-8')):
            if entry:
                ruid, addr, status, msg = entry.split(bval)
                msg = a85decode(msg.strip(), foldspaces=True)
                try:
                    requests[ruid] = [msg, addr, status, stored[ruid][-1]]
                except KeyError:
                    # not in local storage
                    requests[ruid] = [msg, addr, status]


        uids = frozenset(requests.keys()) - frozenset(stored.keys())
        for uid in uids:
            # store new requests in local db
            msg, addr, status = requests[uid]
            rowid = storeFriendRequest(self.safe, self.profileId, uid, msg, addr, False)
            requests[uid].append(rowid)

        # decode before returning
        return {u.decode('ascii'): (m.decode('utf-8'), addr.decode('ascii'), int(status), rowid) for u, (m, addr, status, rowid) in requests.items()}

    def delRequest(self, uid, rowid=None):
        """
        Delete friend request associated with provided user ID

        @param uid: user ID of potential friend
        @param rowid: (optional) local database rowid of friend request to delete. Avoids database lookup.
        @return: Success of deletion (Boolean)
        """
        self.confirmLoggedIn()

        try:
            assert isValidUUID(uid) is True
        except AssertionError:
            raise Exceptions.InvalidClientData("User ID passed is invalid format: {}".format(uid))

        if not rowid:
            try:
                msg, ts, address, rowid = getFriendRequests(self.safe, self.profileId, outgoing=False, expire=int(self.config.request_expiry))[uid]
            except (KeyError, ValueError):
                logging.warning("\t".join(("Friend Completion Error",
                                           "Friend request for user {} does not exist".format(uid))))
                return False

        yield from self.send(b''.join((bytes(str(CONS.FRIEND_REQUEST_DEL), encoding='ascii'),
                                       self.uid, self.auth, bytes(uid, encoding='ascii') if type(uid) is str else uid)))

        success = yield from self.read(2)
        if success and int(success) == 1:
            delFriendRequests(rowid)
            success = True
        else:
            success = False

        return success

    @asyncio.coroutine
    def storeMessage(self, mask, message):
        """
        Send message to server for offline message storage

        @param mask: masked user ID
        @param message: message to store
        @return: Success of message storage (Boolean)
        """
        # confirmed already logged in
        self.confirmLoggedIn()

        token = getFriendAuth(self.safe, self.profileId, mask)[0]
        uid = getUidMask(self.safe, self.profileId, mask)

        message = bytes(message, encoding='utf-8')

        safe = Box(PrivateKey(getMessageKeys(self.safe, self.profileId)[0]), PublicKey(getAuthority(self.safe, self.profileId, mask)[1]))
        msg = list(encrypt(safe, message))[0]

        # dest, token, size of message, and message.
        yield from self.send(b''.join((bytes(str(CONS.MESSAGE_STORE), encoding='ascii'), self.uid, self.auth, uid, token,
                                       CONS.WRITE_END.join((bytes(str(len(msg)), encoding='ascii'), msg)))))

        success = yield from self.read(2)

        if success and int(success) == 1:
            # store history
            storeHistory(self.safe, self.profileId, mask, message, fromFriend=False)
            success = True
        else:
            success = False

        return success

    @asyncio.coroutine
    def getMessages(self):
        """
        Obtain any offline messages stored on the server

        @param tokenMasks: token->mask dict friend relationship
        @return: friend mask -> [(timestamp, message),]
        """
        # confirmed already logged in
        self.confirmLoggedIn()

        yield from self.send(b''.join((bytes(str(CONS.MESSAGES_GET), encoding='ascii'), self.uid, self.auth)))

        messages = defaultdict(list)
        boxes = {}

        msg = yield from self.read()
        if len(msg) > 2:
            tokens = getAuthTokens(self.safe, self.profileId)

            while msg != CONS.WRITE_END:
                byteSize = int(msg)
                msg = yield from self.read(byteSize)
                token, tstamp, msg = msg[:36], msg[:36:46], msg[46:]
                # get unmasked uid
                mask = tokens.get(token)

                if mask:
                    # timestamp of message
                    tstamp = datetime.fromtimestamp(int(tstamp)).strftime("%Y-%m-%d %H:%M:%S")
                    storeHistory(self.safe, self.profileId, mask, msg, True, tstamp)
                    messages[mask].append(boxes.setdefault(mask,
                                                           Box(PrivateKey(getMessageKeys(self.safe, self.profileId)[0]),
                                                               PublicKey(getAuthority(self.safe, self.profileId, mask)[1])
                                                           )).decrypt(msg))

                msg = yield from self.read()

        return messages

    @asyncio.coroutine
    def profileSearch(self, fields, cursor=None):
        """
        Initiate a user search on the Quip server

        @param fields: profile field and value dictionary (e.g. {'first': 'bob', 'last': 'baker'})
        @param cursor: cursor intentifier (bytes object) to continue search from. None starts from beginning.
        @return: (search cursor, total profiles found, iterable of matched user IDs)
        """
        # confirmed already logged in (need an account to do a profile search)
        self.confirmLoggedIn()

        try:
            # validate profile fields
            assert frozenset(fields) <= CONS.PROFILE_FIELDS
        except AssertionError:
            # invalid fields present
            raise Exceptions.InvalidClientData("Invalid profile fields provided: {!r}".format(frozenset(fields) - CONS.PROFILE_FIELDS))

        # format fields data
        fields = bytes(CONS.PROFILE_ENTRY_SEPARATOR.join(CONS.PROFILE_VALUE_SEPARATOR.join((k, v)) for k, v in fields.items()),
                       encoding='utf-8')

        yield from self.send(b''.join((bytes(str(CONS.PROFILE_SEARCH), encoding='utf-8'), self.uid, self.auth,
                                       bytes(CONS.PROFILE_ENTRY_SEPARATOR, encoding='utf-8').join((cursor if cursor is not None else b'0', fields)))))

        # output from profile search contains cursor for search continuance and uids
        output = yield from self.read()
        output = output.decode('utf-8').rstrip().split(CONS.PROFILE_ENTRY_SEPARATOR)

        # cursor, total profiles found, user ids (empty list if none found)
        return output[0], 0 if not output[1] else len(output) - 1, output[1:] if output[1:][0] else []

    @asyncio.coroutine
    def updateProfile(self, fields):
        """
        Update logged in user's profile

        @param fields: profile field and value dictionary (e.g. {'first': 'bob', 'last': 'baker'})
        @return: Success of profile update (Boolean)
        """
        # confirmed already logged in
        self.confirmLoggedIn()

        try:
            # validate profile fields
            assert frozenset(fields) <= CONS.PROFILE_FIELDS
        except AssertionError:
            # invalid fields present
            raise Exceptions.InvalidClientData("Invalid profile fields provided: {!r}".format(frozenset(fields) - CONS.PROFILE_FIELDS))

        # format fields data
        fields = bytes(CONS.PROFILE_ENTRY_SEPARATOR.join(CONS.PROFILE_VALUE_SEPARATOR.join((k, v)) for k, v in fields.items()),
                       encoding='utf-8')

        yield from self.send(b''.join((bytes(str(CONS.PROFILE_SET), encoding='ascii'), self.uid, self.auth, fields)))

        success = yield from self.read(2)

        return int(success) == 1 if success else False

    @asyncio.coroutine
    def getProfile(self, uid):
        """
        Retrieve user profile from Quip server

        @param uid: User ID of the profile to retreive
        @return: profile dict (e.g. {'first': 'bob', 'last': 'baker'})
        """
        # confirmed already logged in
        self.confirmLoggedIn()

        try:
            assert isValidUUID(uid) is True
        except AssertionError:
            raise Exceptions.InvalidClientData("User ID passed is invalid format: {}".format(uid))

        yield from self.send(b''.join((bytes(str(CONS.PROFILE_GET), encoding='ascii'),
                                       self.uid, self.auth, bytes(uid, encoding='ascii') if type(uid) is str else uid)))

        profile = yield from self.read()

        if len(profile) < 7:
            # no profile found with provided UID
            return {}

        # return retrieved profile information
        return {f: v for f, v in (entry.split(CONS.PROFILE_VALUE_SEPARATOR) for entry in
                                  profile.decode('utf-8').rstrip().split(CONS.PROFILE_ENTRY_SEPARATOR))}

    @asyncio.coroutine
    def emailRecovery(self, email):
        """
        Submit e-mail address to receive a recovery code

        @param email: email address to receive recovery code
        """
        # send email
        yield from self.send(b''.join((bytes(str(CONS.RECOVERY_EMAIL), encoding='ascii'),
                                       bytes(email, encoding='utf-8'))))

        success = yield from self.read(2)

        return int(success) == 1 if success else False

    @asyncio.coroutine
    def accountRecovery(self, code, phrase):
        """
        Submit recovery code and handle account recovery
        """
        try:
            assert isValidUUID(code) is True
        except AssertionError:
            raise Exceptions.InvalidClientData("Recovery code is invalid format: {}".format(code))

        try:
            assert (len(phrase) > 32 or len(phrase) < 8) is False
        except AssertionError:
            raise Exceptions.InvalidClientData("Passphrase length less than 8 characters or more than 32")

        # submit code
        yield from self.send(b''.join((bytes(str(CONS.RECOVERY_CODE), encoding='ascii'),
                                       bytes(code, encoding='ascii'))))

        # retrieve uid, auth, alias
        output = yield from self.read()

        if len(output) > 2:
            # expect uid, auth and alias
            uid, auth, alias  = output.split(bytes(CONS.PROFILE_VALUE_SEPARATOR, encoding='utf-8'))

            try:
                assert isValidUUID(uid) is True
                assert isValidUUID(auth) is True
            except AssertionError:
                return False

            # recreate profile
            self.auth = auth
            self.profileId, self.safe = storeAccount(bytes(phrase, encoding='utf-8'), uid, auth, alias.decode('utf-8'))

            success = True
        else:
            # recovery code not found
            success = False

        return success

    @asyncio.coroutine
    def generateInvite(self):
        """
        Request invite code from server

        @return: new invite code or False (no new codes available for this user)
        """
        self.confirmLoggedIn()

        yield from self.send(b''.join((bytes(str(CONS.INVITES_GENERATE), encoding='ascii'), self.uid, self.auth)))

        # retrieve generation response
        output = yield from self.read()

        if len(output) > 4:
            remaining, code = output.split(bytes(CONS.PROFILE_VALUE_SEPARATOR, encoding='utf-8'))
        else:
            remaining = b'0'
            code = False

        return int(remaining), code.decode('ascii').rstrip() if code else code

    @asyncio.coroutine
    def getInvites(self):
        """
        Retrieve all generated invites from server

        @return: {code: status}
        """
        self.confirmLoggedIn()

        yield from self.send(b''.join((bytes(str(CONS.INVITES_GET), encoding='ascii'), self.uid, self.auth)))


        output = yield from self.read()

        invites = {}
        remaining = 0
        if len(output) > 2:
            codes = output.split(bytes(CONS.PROFILE_ENTRY_SEPARATOR, encoding='utf-8'))
            # check for code response
            if len(codes[1]) > 2:
                for code in codes[1:]:
                    code, status = code.split(bytes(CONS.PROFILE_VALUE_SEPARATOR, encoding='utf-8'))
                    invites[code.decode('ascii')] = int(status)

            remaining = int(codes[0])

        return remaining, invites

    @asyncio.coroutine
    def clearInvites(self):
        """
        Clear all expired and claimed invites from invites cache

        @return: Boolean value based on success
        """
        self.confirmLoggedIn()

        yield from self.send(b''.join((bytes(str(CONS.INVITES_CLEAR), encoding='ascii'), self.uid, self.auth)))

        success = yield from self.read(2)

        return True if success == CONS.BTRUE else False


#######################
# Client to P2P Server
#######################

class P2PClient(TLSClient):
    """
    Peer to Peer TLS Client
    """

    def __init__(self, profileId, phrase, loop=None):
        """
        Peer to Peer Client for friend server interaction

        @return: P2PClient object
        """
        super().__init__(profileId=profileId, phrase=phrase, loop=loop)

        # incoming file requests: uid -> checksum -> filename, size
        self.fileRequests = FileRequests(self.safe, self.profileId)
        # friend addresses: uid -> (ip, port)
        self.friends = Friends(self.safe, self.profileId)
        # friend masks uid-> mask
        self.masks = Masks(self.safe, self.profileId)
        # auth tokens awaiting server storage
        self.auth = []
        # hash chain of messages
        self.hashchain = defaultdict(bytes)

        sec, _ = getSigningKeys(self.safe, self.profileId)
        # signing object created from stored private key
        self.signer = SigningKey(sec)

    def __del__(self):
        # call shutdown if possible
        self.shutdown()

    def shutdown(self):
        """
        Close all remaining connections and exit gracefully
        """
        for r, w, s in self.connections.values():
            try:
                w.close()
            except Exception:
                pass

    @asyncio.coroutine
    def send(self, uid, command, data, address=None, sign=True):
        """
        Attempt to send given command to friend's (uid) P2P server

        @param uid: destination friend's ID
        @param command: command integer to send
        @param data: data sent with initial command (to be signed)
        @param address: (optional) Direct IP address tuple
        @param sign: digitally sign sent data
        @return: True if successfully sent, else False
        """
        addr = address or self.friends[uid]

        if addr is None:
            # intended to prompt frontend to obtain address from quip server object
            raise Exceptions.ConnectionFailure("No IP address found locally for friend, contact server for address")

        try:
            r, w, s = self.connections[addr]
            logging.info("Using current connection to host: {!r}".format(addr))
        except KeyError:
            logging.info("(Re)connecting to host: {!r}".format(addr))
            try:
                # reset hash chain
                self.hashchain[uid] = b''
                r, w, s = yield from self._connect_host(addr[0], addr[1])
            except ConnectionRefusedError:
                logging.info("Address {!r} not accepting incoming connections".format(addr))
                raise Exceptions.ConnectionFailure("Address {!r} not accepting incoming connections".format(addr))
            except Exception as e:
                logging.info("Address {!r} connection failed. Reason: {}".format(addr, e))
                raise Exceptions.ConnectionFailure("Address {!r} connection failed. Reason: {}".format(addr, e))

        if sign:
            # update progressive hash chain
            hchain = bytes(sha1(b''.join((self.hashchain[uid], data))).hexdigest(), encoding='ascii')
            # use epoch (time.time()), hash chain, dest uuid, data, origin uuid - when signing to avoid replay attack
            outgoing = b''.join((bytes(str(int(time())), encoding='ascii'), hchain, uid, data, self.uid))
            outdata = a85encode(self.signer.sign(outgoing), foldspaces=True)
        else:
            outdata = data

        # outgoing data format
        cmd = b''.join((bytes(str(command), encoding='ascii'), outdata, CONS.WRITE_END if sign else b''))
        success = True
        try:
            w.write(cmd)
            yield from w.drain()
            logging.info("Sent data: {!r}".format(cmd))
        except (BrokenPipeError, ConnectionResetError):
            # socket closed
            try:
                logging.info("Reconnecting to: {!r}".format(addr))
                # reset hash chain
                self.hashchain[uid] = b''
                # reconnect to friend
                r, w, s = yield from self._connect_host(addr[0], addr[1])
                # hash chain changed, resign data
                if sign:
                    # update progressive hash chain
                    hchain = bytes(sha1(b''.join((self.hashchain[uid], data))).hexdigest(), encoding='ascii')
                    # use epoch (time.time()), hash chain, dest uuid, data, origin uuid - when signing to avoid replay attack
                    outgoing = b''.join((bytes(str(int(time())), encoding='ascii'), hchain, uid, data, self.uid))
                    outdata = a85encode(self.signer.sign(outgoing), foldspaces=True)

                # outgoing data format
                cmd = b''.join((bytes(str(command), encoding='ascii'), outdata, CONS.WRITE_END if sign else b''))

                w.write(cmd)
                yield from w.drain()
                logging.info("Sent data (Backup): {!r}".format(cmd))
            except Exception as e:
                logging.warning("Address {!r} connection failed. Reason: {}".format(addr, e), exc_info=True)
                raise Exceptions.ConnectionFailure("Address {!r} connection failed. Reason: {}".format(addr, e))
        except Exception as e:
            logging.error("Unable to contact friend {} on given address: {!r}. Reason: {}".format(uid, addr, e), exc_info=True)
            raise Exceptions.ConnectionFailure("Unable to contact friend {} on given address: {!r}. Reason: {}".format(uid, addr, e))

        if success and sign:
            # update hash chain if sending successful
            self.hashchain[uid] = hchain

        return success

    @asyncio.coroutine
    def read(self, uid, rbytes=None, address=None):
        """
        Receive from the quip server StreamReader

        @param uid: friend's user ID
        @param rbytes: (optional) number of bytes to read, otherwise readline() used
        @param address: (optional) Direct IP address tuple
        @return: received data
        """
        addr = address or self.friends[uid]

        if addr is None:
            # intended to prompt frontend to obtain address from quip server object
            raise Exceptions.ConnectionFailure("No IP address found locally for friend, contact server for address")

        try:
            r, w, s = self.connections[addr]
        except KeyError:
            # this will be raised if send() return value isn't checked for sending failure and read() is called
            logging.warning("Trying to read() from unconnected friend connection")
            raise Exceptions.ConnectionFailure("Trying to read() from unconnected friend connection")
            #r, w, s = yield from self._connect_host(addr[0], addr[1])

        if rbytes is None:
            data = yield from r.readline()
        else:
            data = yield from r.read(rbytes)

        return data

    @asyncio.coroutine
    def sendMessage(self, uid, message):
        """
        Send message to destination friend (uid)

        @param uid: destination friend's uid
        @param message: message to send
        @return: True if message successfully sent, otherwise False
        """
        msg = bytes(message, encoding='utf-8')
        success = yield from self.send(uid, CONS.RECV_MSG, b''.join((msg, bytes(str(CONS.RECV_MSG), encoding='ascii'))))

        if success:
            # store our outgoing message
            storeHistory(self.safe, self.profileId, self.masks[uid], msg, fromFriend=False)

        return success

    @asyncio.coroutine
    def sendFileRequest(self, uid, filePath):
        """
        Send file request to destination friend (uid)

        @param uid: destination friend's uid
        @param filePath: Path to sendable file
        @return: True if file request successfully sent, otherwise False
        """
        try:
            size = bytes(str(path.getsize(filePath)), encoding='ascii')
        except OSError:
            # file not found in provided path
            logging.warning("\t".join(("File Transfer Request Failed", "File Not Found: {}".format(filePath))))
            return False

        # create checksum
        digest = sha1sum(filePath)

        fname = bytes(path.basename(filePath), encoding='utf-8')
        # send file transfer request
        yield from self.send(uid, CONS.REQ_FILE, b''.join((bytes(CONS.PROFILE_VALUE_SEPARATOR, encoding='utf-8').join((fname, size, digest)), bytes(str(CONS.REQ_FILE), encoding='ascii'))))

        # response from friend's server
        accepted = yield from self.read(uid, rbytes=1)

        if accepted and int(accepted) == 1:
            # outgoing requests store entire file path
            storeFileRequest(self.safe, self.profileId, outgoing=True, mask=self.masks[uid],
                             request=(bytes(filePath, encoding='utf-8'), size, digest))
            success = True
        else:
            success = False

        return digest if success else success

    @asyncio.coroutine
    def retrieveFile(self, uid, checksum, saveAs=None):
        """
        Retrieve file from friend.

        Once a file transfer request has been accepted, the file can be downloaded/retrieved from the friend

        @param uid: friend's uid to retrieve file from
        @param checksum: checksum of file to download
        @param saveAs: (optional) Name the file this value instead of the filename sent by the friend
        @return: True when data it completely retreived and saved, else False
        """
        try:
            filename, size, rid = self.fileRequests[self.masks[uid]][checksum]
        except KeyError:
            logging.warning('\t'.join(("File request not found",
                                       "User: {!r}".format(uid),
                                       "Checksum: {!r}".format(checksum))))
            return False

        if saveAs is not None:
            filename = saveAs if type(saveAs) is str else saveAs.decode('utf-8')
        else:
            filename = filename.decode('utf-8')

        yield from self.send(uid, CONS.RECV_FILE, b''.join((checksum, bytes(str(CONS.RECV_FILE), encoding='ascii'))))

        # read up to 9 bytes
        isFileData = yield from self.read(uid, rbytes=9)

        if isFileData[:CONS.COMMAND_LENGTH] == CONS.MODIFIED_FILE:
            delFileRequests(rid)
            raise Exceptions.FileCorruption("File has been modified since receiving transfer request")
        elif isFileData[:CONS.COMMAND_LENGTH] == CONS.NONEXISTANT:
            delFileRequests(rid)
            raise Exceptions.FileCorruption("Remote file no longer exists")

        dest = path.join(self.config.download_directory, filename)
        if path.isfile(dest):
            # if a file of the same name already exists, create a new file
            name, ext = path.splitext(filename)
            fd, dest = mkstemp(suffix=ext, prefix="{}-".format(name), dir=self.config.download_directory)
            fd = open(fd, 'wb')
        else:
            fd = open(dest, 'wb')

        size = int(size)
        # command data not present, contains file data
        fd.write(isFileData if size > len(isFileData) else isFileData[:size])
        # maximum chunk size before writing to disk
        chunk = int(self.config.max_chunk)
        # total size of file, minus the command data length check
        total = size - 9
        while total > 0:
            fdata = yield from self.read(uid, rbytes=chunk if chunk < total else total)
            # received data may be less than chunk size due to sender controlling the transport write speed
            total -= len(fdata)

            if not fdata:
                break

            # write to disk
            fd.write(fdata)

        fd.flush()
        fd.close()

        # remove incoming request entry, regardless of checksum verification success
        delFileRequests(rid)

        if int(self.config.verify):
            lhash = sha1sum(dest)
            if lhash != checksum:
                logging.warning("\t".join(("Downloaded file does not match sent file hash: {}".format(dest),
                                           "Sent Hash: {}".format(checksum),
                                           "Local Hash: {}".format(lhash))))
                raise Exceptions.FileCorruption("Downloaded file has been altered (checksum mismatch)")

        return dest

    @asyncio.coroutine
    def sendAvatar(self, avatar=None, friends=None):
        """
        Send avatar to all listed friends

        @param friends: List of friend uids to send avatar to. If None, all friends, regardless of online status,
                        will receive an avatar sending attempt
        @return: {uid: Boolean} success of avatar transfer
        """
        if not avatar:
            # get avatar from database
            avatar, _ = getAvatar(self.safe, self.profileId)

        if not friends:
            # get all friends
            friends = getMasks(self.safe, self.profileId)
            if not friends:
                # no friends
                return {}
            else:
                friends = friends.keys()

        values = {}
        checksum = bytes(sha1(avatar).hexdigest(), encoding='ascii')
        for uid in friends:
            # send initial signed command with checksum value
            yield from self.send(uid, CONS.RECV_AVATAR, b''.join((checksum, bytes(str(CONS.RECV_AVATAR), encoding='ascii'))))

            success = yield from self.read(uid, rbytes=2)
            if success == CONS.BTRUE:
                # send size of avatar to read
                yield from self.send(uid, '', b''.join((bytes(str(len(avatar)), encoding='ascii'), CONS.WRITE_END)), sign=False)
                success = yield from self.read(uid, rbytes=2)

                if success == CONS.BTRUE:
                    # send entire avatar
                    yield from self.send(uid, '', avatar, sign=False)

                    # 40 char checksum
                    fchecksum = yield from self.read(uid, rbytes=64)

                    # compare checksum value friend calculated to our own
                    if fchecksum != checksum:
                        success = CONS.BFALSE

            values[uid] = True if success == CONS.BTRUE else False

        return values


    @asyncio.coroutine
    def friendCompletion(self, uid, mhash=None, address=None):
        """
        Having received a friend request and accepted, complete friend request with destination user

        If mhash is provided, address also needs to be provided to avoid local database lookup.

        FriendshipFailure exception will be raised if any friendship step fails

        @param uid: friend's ID
        @param mhash: (Optional) Message hash
        @param address: (Optional) friend's P2P server address string "host:port"
        @return: True if friendship successfully created
        """
        # ensure uid is bytes
        try:
            uid = bytes(uid, encoding='ascii')
        except TypeError:
            pass

        if mhash is None or address is None:
            # friend request will contain last known address
            try:
                msg, ts, address, rowid = getFriendRequests(self.safe, self.profileId, outgoing=False, expire=int(self.config.request_expiry))[uid]
                address = address.decode('ascii')
            except (KeyError, ValueError):
                logging.warning("\t".join(("Friend Completion Error",
                                           "Friend request for user {} does not exist".format(uid))))
                raise Exceptions.FriendshipFailure("Friend request does not exist")
            mhash = bytes(sha1(b''.join((self.uid, msg))).hexdigest(), encoding='ascii')

        address = tuple(address.split(':'))

        # send friend request completion command directly to known address
        yield from self.send(uid, CONS.REQ_FRIEND, b''.join((mhash, self.uid, CONS.WRITE_END)), address=address, sign=False)

        # receive auth token, and signing verification key and messaging public key
        length = yield from self.read(uid, address=address)
        data = yield from self.read(uid, address=address, rbytes=int(length))

        fauth, spub, mpub = data[:36], data[36:100], data[100:]

        try:
            assert len(data) > 115
            assert isValidUUID(fauth) is True
        except AssertionError:
            logging.warning("\t".join(("Friend Completion Error",
                                       "Invalid auth token {!r} provided by user {}".format(fauth, uid))))
            raise Exceptions.FriendshipFailure("Invalid auth token provided: {!r}".format(fauth))


        #r = yield from self.read(uid, address=address, rbytes=-1)
        # authorisation token we'll send to friend
        token = bytes(str(uuid4()), encoding='ascii')

        # create our auth token to be sent to server
        auth = bytes(sha384(b''.join((uid, token))).hexdigest(), encoding='ascii')

        # created and store localised mask of friend's true ID
        fmask = setUidMask(self.safe, self.profileId, uid)

        # store friend's auth mask (the mask we use when submitting authorised requests to the Quip server)
        setFriendAuth(self.safe, self.profileId, fmask, fauth, auth)

        # store public key for friend
        storeAuthority(self.safe, self.profileId, fmask, spub, mpub)

        # sent success value for confirmation of data storage and listening port information
        yield from self.send(uid, '', b''.join((CONS.BTRUE, bytes(self.config.tcp, encoding='ascii'), CONS.WRITE_END)), address=address, sign=False)

        # get (signing) public key for profile
        spub = getSigningKeys(self.safe, self.profileId)[1]
        # get (encryption) public key for profile
        mpub = getMessageKeys(self.safe, self.profileId)[1]

        # work out length of data
        data = b''.join((token, spub, mpub))

        # send length to read, auth token and keys
        yield from self.send(uid, '', b''.join((bytes(str(len(data)), encoding='ascii'), CONS.WRITE_END, data)),
                             address=address, sign=False)

        # obtain storage success message from friend
        data = yield from self.read(uid, address=address, rbytes=1)
        try:
            assert int(data) == 1
        except (AssertionError, ValueError):
            logging.warning("\t".join(("Friend Completion Error", "Sent data not successfully stored by friend",
                                       "Response: {!r}".format(data))))
            raise Exceptions.FriendshipFailure("Sent data not successfully stored by friend: {!r}".format(data))

        # store address of friend locally
        setAddress(self.safe, self.profileId, fmask, b':'.join(bytes(a, encoding='ascii') for a in address))

        # 'auth' token must be sent to server
        self.auth.append(auth)

        return True, auth

    def inviteChat(self, uid, others):
        """
        Invite friend (uid) to a group chat with others (profiles)

        @param uid: destination friend's uid
        @param others: other people in the chat's profiles(?)
        @return:
        """
        # TODO: P2P group chat

        # pass temp pub certs for unknown entities via quip server

        # retrieve temp pub cert from unknown entity via quip server
        pass
