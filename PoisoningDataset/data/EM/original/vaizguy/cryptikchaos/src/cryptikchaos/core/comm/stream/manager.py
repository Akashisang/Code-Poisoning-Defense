'''
Created on Aug 4, 2013

Handles packing and unpacking of streams to be sent
over TCP/IP.

This file is part of CryptikChaos.

CryptikChaos is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CryptikChaos is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CryptikChaos. If not, see <http://www.gnu.org/licenses/>.

@author: vaizguy
'''

__author__ = "Arun Vaidya"
__version__ = "0.6.1"

from kivy import Logger

from base64 import b64encode

from cryptikchaos.core.env.configuration import constants

from cryptikchaos.storage.manager import StoreManager

from cryptikchaos.libs.utilities import generate_uuid
from cryptikchaos.libs.utilities import generate_token
from cryptikchaos.libs.utilities import compress
from cryptikchaos.libs.utilities import decompress
from cryptikchaos.libs.utilities import enum
from cryptikchaos.libs.utilities import num_to_bytes
from cryptikchaos.libs.utilities import bytes_to_num
from cryptikchaos.libs.utilities import md5hash

from cryptikchaos.libs.obscure import shuffler
from cryptikchaos.libs.obscure import unshuffler

from cryptikchaos.exceptions.streamExceptions import \
    StreamOverflowError

from cryptikchaos.core.comm.stream.stream import Stream

if constants.AES_AVAILABLE:
    Logger.info("STREAM: AES Crypto available.")
    from Crypto.Cipher import AES
else:
    Logger.warn("STREAM: AES Crypto unavailable.")

import struct

STREAM_TYPES = enum(UNAUTH=False, AUTH=True)


class StreamManager(StoreManager):

    "Stream manager class."

    def __init__(self, peerid, peerkey, peerhost):

        # Authorized keys
        self._valid_keys = (
            'STREAM_FLAG',
            'STREAM_TYPE',
            'STREAM_CONTENT',
            'STREAM_PKEY'
        )

        # Create store
        super(StreamManager, self).__init__("StreamStore", self._valid_keys)
        # Peer public key
        self.public_key = peerkey
        # Peer host
        self.peer_host = peerhost

    def __del__(self):

        # Clear stored streams
        if super(StreamManager, self):
            super(StreamManager, self).__del__()

    def pack_stream(self, stream_type, stream_content, stream_host,
                    stream_flag=STREAM_TYPES.AUTH, shared_key=None):
        "Pack data into stream."

        # Check length of content.
        if len(stream_content) > constants.STREAM_CONTENT_LEN:
            raise StreamOverflowError(constants.STREAM_CONTENT_LEN)

        # Check length of capsule type.
        if len(stream_type) > constants.STREAM_TYPE_LEN:
            raise StreamOverflowError(constants.STREAM_TYPE_LEN)

        # Generate uid
        stream_uid = generate_uuid(stream_host)
        # Stream type
        stream_type = stream_type.upper()
        # Stream peer key
        stream_token = None
        
        #For testing
        _debug_stream_content = stream_content

        # Shuffle content
        if constants.ENABLE_SHUFFLE:
            Logger.info("STREAM: Scrambling content...")

            stream_content = shuffler(
                string=stream_content,
                iterations=constants.STREAM_CONT_SHUFF_ITER
            )

        # Check stream signing mode
        if stream_flag == STREAM_TYPES.UNAUTH:
            # Stream key is peer key
            # NOTE peer public key is sent during
            # authentication.
            stream_token = num_to_bytes(self.public_key)

        elif stream_flag == STREAM_TYPES.AUTH:
            # Generate token at source side
            stream_token = generate_token(stream_uid, shared_key)

            # AES Encryption
            if constants.AES_AVAILABLE:
                Logger.info("STREAM: Encrypting content...")
                # Generate iv from stream token
                iv = md5hash(stream_token, hexdigest=False)
                # Create AES object
                AES_obj = AES.new(shared_key, AES.MODE_CBC, iv)
                # Pad string
                stream_content = self.pad(stream_content)
                # Encrypt string
                stream_content = AES_obj.encrypt(stream_content)

        # Create stream object
        stream_obj = Stream(
            stream_uid,
            stream_flag,
            stream_type,
            stream_content,
            stream_token,
        )

        # Add stream to store
        self.add_store(
            stream_uid, stream_obj.dict
        )

        if stream_flag == STREAM_TYPES.UNAUTH:
            Logger.info("STREAM: Packing Authentication Stream...")

            # Pack store into authentication stream
            stream = struct.pack(
                "!?{}s{}s{}s{}s".format(
                    constants.STREAM_TYPE_LEN,
                    constants.STREAM_CONTENT_LEN,
                    constants.STREAM_PEER_KEY_LEN,
                    constants.STREAM_CHKSUM_LEN
                ),
                self.get_store_item(stream_uid, 'STREAM_FLAG'),
                self.get_store_item(stream_uid, 'STREAM_TYPE'),
                self.get_store_item(stream_uid, 'STREAM_CONTENT'),
                self.get_store_item(stream_uid, 'STREAM_PKEY'),
                self.get_store_hmac(stream_uid)
            )

        elif stream_flag == STREAM_TYPES.AUTH:
            Logger.info("STREAM: Packing Message Stream...")

            # Pack store into message block stream
            stream = struct.pack(
                "!?{}s{}s{}s{}s".format(
                    constants.STREAM_TYPE_LEN,
                    constants.STREAM_CONTENT_LEN,
                    constants.STREAM_TOKEN_LEN,
                    constants.STREAM_CHKSUM_LEN
                ),
                self.get_store_item(stream_uid, 'STREAM_FLAG'),
                self.get_store_item(stream_uid, 'STREAM_TYPE'),
                self.get_store_item(stream_uid, 'STREAM_CONTENT'),
                self.get_store_item(stream_uid, 'STREAM_PKEY'),
                self.get_store_hmac(stream_uid)
            )

        else:
            Logger.error("STREAM: Invalid Stream Flag received.")
            return None
        
        def pkey_action(val):
            
            val = md5hash(val)
            return val
            
        if stream_flag == STREAM_TYPES.UNAUTH:
            Logger.debug("""STREAM: Packing: \n{}""".format(
                self.storage_table(shorten_len=64, action_dict={"STREAM_PKEY":pkey_action}) ))
        
        Logger.debug("""DEBUG STREAM:
        FLAG: {}
        TYPE: {}
        CONTENT: {}
        KEY: {}
        CHECKSUM: {}
        """.format(
                self.get_store_item(stream_uid, 'STREAM_FLAG'),
                self.get_store_item(stream_uid, 'STREAM_TYPE'),
                _debug_stream_content,
                b64encode(self.get_store_item(stream_uid, 'STREAM_PKEY')),
                self.get_store_hmac(stream_uid)))

        # Compress stream
        if constants.ENABLE_COMPRESSION:
            Logger.info("STREAM: Compressing Stream...")
            stream = compress(stream)

        Logger.info("STREAM: Succesfully packed stream.")
        return stream

    def unpack_stream(self, stream, shared_key=None):
        "Unpack serial data into stream."

        # Decompress data stream
        if constants.ENABLE_COMPRESSION:
            Logger.info("STREAM: Decompressing Stream...")
            stream = decompress(stream)

        # Check if data is of expected chunk size
        if len(stream) != constants.STREAM_SIZE_AUTH_BLOCK and \
           len(stream) != constants.STREAM_SIZE_MSG_BLOCK:
            raise StreamOverflowError()

        if len(stream) == constants.STREAM_SIZE_AUTH_BLOCK:
            Logger.info("STREAM: Unpacking Authentication Stream...")

            # Unpack auth stream to variables
            (
                stream_flag,
                stream_type,
                stream_content,
                stream_token,
                stream_hmac
            ) = struct.unpack(
                "!?{}s{}s{}s{}s".format(
                    constants.STREAM_TYPE_LEN,
                    constants.STREAM_CONTENT_LEN,
                    constants.STREAM_PEER_KEY_LEN,
                    constants.STREAM_CHKSUM_LEN
                ), stream
            )

        elif len(stream) == constants.STREAM_SIZE_MSG_BLOCK:
            Logger.info("STREAM: Unpacking Message Stream...")

            # Unpack msg block stream to variables
            (
                stream_flag,
                stream_type,
                stream_content,
                stream_token,
                stream_hmac
            ) = struct.unpack(
                "!?{}s{}s{}s{}s".format(
                    constants.STREAM_TYPE_LEN,
                    constants.STREAM_CONTENT_LEN,
                    constants.STREAM_TOKEN_LEN,
                    constants.STREAM_CHKSUM_LEN
                ), stream
            )

        else:
            Logger.error("STREAM: Invalid Stream Length received.")
            return [None] * 3

        # Remove all null characters if present
        stream_content = stream_content.rstrip('\0')
        stream_token = stream_token.rstrip('\0')

        # Get  uid
        stream_uid = generate_uuid(self.peer_host)

        # Get stream object
        stream_obj = Stream(
            stream_uid,
            stream_flag,
            stream_type,
            stream_content,
            stream_token,
        )

        # Add stream to store
        self.add_store(stream_uid, stream_obj.dict)

        # Verify stream integrity
        if not self.check_hmac(stream_uid, stream_hmac):
            Logger.error("STREAM: Stream Checksum mismatch.")
            return [None] * 3

        # Check stream signing mode
        if stream_flag == STREAM_TYPES.UNAUTH:
            # Stream key is peer public key
            pass

        elif stream_flag == STREAM_TYPES.AUTH:
            # Generate token at destination side
            # Perform key challenge
            if generate_token(stream_uid, shared_key) != stream_token:
                Logger.error("STREAM: Token challenge Fail!")
                Logger.error("STREAM: RCVD: {}".format(b64encode(stream_token)))
                Logger.error("STREAM: EXPD: {}".format(b64encode(generate_token(stream_uid, shared_key))))
                return [None] * 3
            else:
                Logger.info("STREAM: Token challenge Pass!")

            # AES Decryption
            if constants.AES_AVAILABLE:
                Logger.info("STREAM: Decrypting content...")
                # Generate iv from stream token
                iv = md5hash(stream_token, hexdigest=False)
                # Create AES object
                AES_obj = AES.new(shared_key, AES.MODE_CBC, iv)
                # Decrypt content
                stream_content = AES_obj.decrypt(stream_content)
                # Upad decrypted content
                stream_content = self.unpad(stream_content)
                
        def pkey_action(val):
            
            val = md5hash(val)
            return val               
        
        if stream_flag == STREAM_TYPES.UNAUTH:
            Logger.debug("""STREAM: Unpacking: \n{}""".format(
                self.storage_table(shorten_len=64, action_dict={"STREAM_PKEY":pkey_action}) ))
            
        Logger.debug("""DEBUG STREAM:
        FLAG: {}
        TYPE: {}
        CONTENT: {}
        KEY: {}
        CHECKSUM: {}
        """.format(
                self.get_store_item(stream_uid, 'STREAM_FLAG'),
                self.get_store_item(stream_uid, 'STREAM_TYPE'),
                stream_content,
                b64encode(self.get_store_item(stream_uid, 'STREAM_PKEY')),
                self.get_store_hmac(stream_uid)))

        # Unshuffle contentself._storage[sid].hmac()
        if constants.ENABLE_SHUFFLE:
            Logger.info("STREAM: Unscrambling content...")

            stream_content = unshuffler(
                shuffled_string=stream_content,
                iterations=constants.STREAM_CONT_SHUFF_ITER
            )

        if stream_flag == STREAM_TYPES.UNAUTH:
            Logger.info("STREAM: Successfully unpacked AUTH Stream.")
            return (self.get_store_item(stream_uid, "STREAM_TYPE"),
                    self.get_store_item(stream_uid, "STREAM_CONTENT"),
                    bytes_to_num(
                        self.get_store_item(stream_uid, "STREAM_PKEY")
                    ))

        elif stream_flag == STREAM_TYPES.AUTH:
            Logger.info("STREAM: Successfully unpacked MSG Stream.")
            return (self.get_store_item(stream_uid, "STREAM_TYPE"),
                    stream_content,
                    self.get_store_item(stream_uid, "STREAM_PKEY"))

        else:
            Logger.info("STREAM: Unpack of stream unsuccessfull.")
            return [None] * 3

    def get_stream(self, sid):
        "Return stream data in form of tuple."

        # Return specified stream data
        return self.get_store(sid)

    if constants.AES_AVAILABLE:
        def pad(self, s, BS=16):
            "Return string of size mutiple of Block Size"

            if len(s) % 16 == 0:
                return s
            else:
                return s + '\0' * (constants.STREAM_CONTENT_LEN - len(s))

        def unpad(self, s):
            "Remove appended null characters"

            return s.rstrip('\0')


if __name__ == "__main__":

    SM = StreamManager(123, "PKEYTEST", "localhost")
    S = SM.pack_stream(
        stream_type="ACKN",
        stream_content="Hello",
        stream_host="127.0.0.1",
        public_key="PKEYTEST"
    )
    print S
    print SM.unpack_stream(S)
