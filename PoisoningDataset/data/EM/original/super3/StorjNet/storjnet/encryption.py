# -*- coding: utf-8 -*-

# Copyright (c) 2015, Shinya Yagyu
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import logging
import sys
import hashlib
import hmac
import base64
from struct import pack
import json
import re

from netaddr import IPAddress
import netifaces

from Crypto.Cipher import AES
from Crypto.Util import Counter

import pyuecc

log_fmt = '%(filename)s:%(lineno)d %(funcName)s() %(message)s'
logging.basicConfig(level=logging.DEBUG, format=log_fmt)


def get_sha256(msg):
    """
    get sha256

    :param bytes msg: messages to be digested
    :return: digested bytes
    """
    h = hashlib.sha256()
    h.update(msg)
    return h.digest()


def get_hashname(public):
    """
    get hashname from a public key by base32 coding.

    :return: hashname bytes
    """
    b32 = base64.b32encode(get_sha256(public)).decode()
    return b32.replace('=', '').lower()


class MyNode(object):

    """
    pub/key pair that represents node info
    """

    def __init__(self, port, fname=None):
        """
        init

        :param int port: port number listening from.
        :param str fname: file name that contains location. is file doesn't
                         exist, keys is saved to this file.
        """
        self.port = port
        self.ip_address = self.get_ip_address()

        if fname is not None:
            my_location = self.get_from_file(fname)
            if my_location is not None:
                j = json.loads(my_location)
                self.public = base64.b64decode(j['public_key'])
                self.private = base64.b64decode(j['private_key'])
                return

        (self.public, self.private) = pyuecc.make_key()
        if fname is not None:
            self.save_to_file(fname)

    def get_from_file(self, fname):
        try:
            with open(fname, 'r') as f:
                loc = f.read()
                return loc
        except IOError:
            return None

    def save_to_file(self, fname):
        with open(fname, 'w') as f:
            loc = f.write(self.get_my_location(True))

    def get_my_id(self):
        """
        get hashname of my node from public key by base32 coding.

        :return: hashname bytes
        """
        return get_hashname(self.public)

    def get_private64(self):
        """
        get base64 of private key for sending in JSON

        :return: base64 coded pubkey
        """
        return base64.b64encode(self.private).decode()

    def get_public64(self):
        """
        get base64 of public key for sending in JSON

        :return: base64 coded pubkey
        """
        return base64.b64encode(self.public).decode()

    def set_ip_address(self, ip_address):
        """
        set (global) ip address

        :param str ip_address: IP address to be set
        """
        self.ip_address = ip_address

    def get_ip_address(self, test_address=None):
        """
        try to get global IP address from interface information.
        if failed, just return '127.0.0.1'

        :param str test_address: ip address str if test to check global ip.
                                  normally None.
        :return: global ip address if successed, or '127.0.0.1'
        """
        for iface_name in netifaces.interfaces():
            iface_data = netifaces.ifaddresses(iface_name)
            logging.debug('Interface: %s' % (iface_name, ))
            ifaces = []
            if netifaces.AF_INET in iface_data:
                ifaces += iface_data[netifaces.AF_INET]
            if netifaces.AF_INET6 in iface_data:
                ifaces += iface_data[netifaces.AF_INET6]
            for iface in ifaces:
                ip = iface['addr']
                ip = re.sub(r'\%.+$', '', ip)
                if test_address is not None:
                    ip = test_address
                addr = IPAddress(ip)
                if not addr.is_loopback() and addr.is_unicast() and\
                   not addr.is_private():
                    logging.debug('global ip %s', addr)
                    return ip
        logging.debug('no global ip')
        return '127.0.0.1'

    def get_my_location(self, private=False):
        """
        get my location, including hashname, pubkey, ip:port

        :param bool private: if True, private key is included.
        :return: json str meaning my location
        """
        l = {
            'version': 1.00,
            'hashname': self.get_my_id(),
            'public_key': self.get_public64(),
            'ip': self.ip_address,
            'port': self.port
        }
        if private:
            l.update({'private_key': self.get_private64()})

        return json.dumps(l)


class IVCounter(object):

    """
    IV counter for AES Counter mode.
    just reply passed value padded 12bit 0 to right.
    """

    def __init__(self, value):
        """
        init

        :param bytes value: 4bits counter value
        """
        self.value = value

    def __call__(self):
        """
        :return: return value + 12'b0
        """
        return self.value + b'0' * 12


def fold1(dat):
    """
    The folding is a simple XOR of the lower half bytes with the upper ones.
    for converting 32bits->16bits

    :param bytes dat: 32 bytes data to be folded
    :return: 16 bits folded data
    """
    dat_ = bytearray(dat)
    out = bytearray(16)
    for i in range(0, 16):
        out[i] = dat_[i] ^ dat_[i + 16]

    return bytes(out)


def fold3(dat):
    """
    The folding is a simple XOR of the lower half bytes with the upper ones.
    for converting 32bits->4bits

    :param bytes dat: 32 bytes data to be folded
    :return: 4 bits folded data
    """
    dat_ = bytearray(dat)
    out = bytearray(16)
    result = bytearray(4)
    for i in range(0, 16):
        out[i] = dat_[i] ^ dat_[i + 16]
    for i in range(0, 8):
        out[i] = out[i] ^ out[i + 8]
    for i in range(0, 4):
        result[i] = out[i] ^ out[i + 4]

    return bytes(result)


class E3x(object):

    """
    encryption class for handshake(message for the first time)
    and channel message. Almost same as
    https://github.com/telehash/telehash.org/blob/master/v3/e3x/cs/1a.md
    except using AES256-CTR/secp256k1 instead of AES-128-CTR/secp160r1
    """

    def __init__(self, mynode,):
        """
        init

        :param MyNode mynode: MyNode instance that represents my key info.
        """
        self.mynode = mynode

        (self.remote_ephemeral_public, self.remote_ephemeral_private) =\
            pyuecc.make_key()

        self.channel_enckey = None
        self.channel_deckey = None
        self.seq = 0
        self.token = None

    def create_channel_keys(self, received_key):
        """
        create channel key by
        encryption key: SHA256(secret, sent-KEY, received-KEY) / 2
        decryption key: SHA256(secret, received-KEY, sent-KEY) / 2
        where secret is derived from ECDH from ephemeral keys.

        :param bytes received_key: recived epheram key.
        """
        shared_key = pyuecc.shared_secret(received_key,
                                          self.remote_ephemeral_private)
        t = shared_key + self.remote_ephemeral_public + received_key
        self.channel_enckey = get_sha256(t)
        t = shared_key + received_key + self.remote_ephemeral_public
        self.channel_deckey = get_sha256(t)

    def encrypt_handshake(self, msg, remote_permanent_public_b64):
        """
        encrypt handshake message structured:

        KEY - 33 bytes, the sender's ephemeral exchange public key in
              compressed format
        IV - 4 bytes, a random but unique value determined by the sender
        INNER - the AES-256-CTR encrypted inner packet ciphertext
        HMAC - 4 bytes, the calculated HMAC of all of the previous
               KEY+IV+INNER bytes

        :param bytes msg: handshake message
        :param bytes remote_permanent_public_b64: remote node pubkey
        :return: encrypted bytes data
        """

        remote_permanent_public = \
            base64.b64decode(remote_permanent_public_b64)
        compressed_pkey = pyuecc.compress(self.remote_ephemeral_public)
        shared_key = get_sha256(
            pyuecc.shared_secret(remote_permanent_public,
                                 self.remote_ephemeral_private)
        )
        iv = pack('I', self.seq)
        self.seq += 1
        aes = AES.new(shared_key, AES.MODE_CTR, counter=IVCounter(iv))
        enc_msg = aes.encrypt(msg.encode())
        hmac_key = pyuecc.shared_secret(remote_permanent_public,
                                        self.mynode.private) + iv
        sig = fold3(hmac.new(hmac_key, enc_msg, hashlib.sha256).digest())
        self.token = fold1(get_sha256(compressed_pkey[0:16]))
        return compressed_pkey + iv + enc_msg + sig

    def decrypt_handshake(self, msg):
        """
        decrypt handshake message structured:
        decoded msg must be json str and key 'public_key' must be included.

        :param bytes msg: encrypted handshake message
        :return: decrypted message
        """
        received_public = pyuecc.decompress(msg[0:33])
        self.create_channel_keys(received_public)

        shared_key = get_sha256(
            pyuecc.shared_secret(received_public, self.mynode.private)
        )
        aes = AES.new(shared_key, AES.MODE_CTR, counter=IVCounter(msg[33:37]))
        dec_msg = aes.encrypt(msg[37:-4]).decode()

        try:
            jmsg = json.loads(dec_msg)
        except Exception:
            logging.error('msg is not json')
            return None

        if 'public_key' not in jmsg:
            logging.error('public_key not included')
            return None

        remote_permanent_public = base64.b64decode(jmsg['public_key'])
        hmac_key = pyuecc.shared_secret(remote_permanent_public,
                                        self.mynode.private) + msg[33:37]
        sig = fold3(hmac.new(hmac_key, msg[37:-4], hashlib.sha256).digest())
        if sig != msg[-4:]:
            logging.error('signature unmatched')
            return None

        return dec_msg

    def encrypt_channel_message(self, msg):
        """
        encrypt channel message structured:
        TOKEN - 16 bytes, from the handshake, required for all channel packets
        IV - 4 bytes, incremented sequence
        INNER - the AES-256-CTR encrypted inner packet ciphertext
        HMAC - 4 bytes, the SHA-256 HMAC folded three times

        :param bytes msg: channel message
        :return: encrypted bytes data
        """
        if self.channel_enckey is None:
            logging.error('not recieved a handshake yet')
            return None

        iv = pack('I', self.seq)
        self.seq += 1
        aes = AES.new(self.channel_enckey, AES.MODE_CTR,
                      counter=IVCounter(iv))
        enc_msg = aes.encrypt(msg.encode())
        hmac_key = self.channel_enckey + iv
        sig = fold3(hmac.new(hmac_key, enc_msg, hashlib.sha256).digest())
        return self.token + iv + enc_msg + sig

    def decrypt_channel_message(self, msg):
        """
        decrypt class message structured:

        :param bytes msg: encrypted class message
        :return: decrypted message
        """
        if self.channel_deckey is None:
            logging.error('not recieved a handshake yet')
            return None

        hmac_key = self.channel_deckey + msg[16:20]

        sig = fold3(hmac.new(hmac_key, msg[20:-4], hashlib.sha256).digest())
        if sig != msg[-4:]:
            logging.error('signature unmatched')
            return None

        aes = AES.new(self.channel_deckey, AES.MODE_CTR,
                      counter=IVCounter(msg[16:20]))
        dec_msg = aes.encrypt(msg[20:-4])
        return dec_msg.decode()
