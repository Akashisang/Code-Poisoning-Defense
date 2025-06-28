#!/usr/bin/env python
from Crypto.Cipher import AES
from Crypto import Random
from collections import namedtuple
from itertools import izip
from struct import pack, unpack
from hashlib import sha256
import hmac

class PacketHandler(object):
    """ This is a contructor object for a packet data handler. One of 
        these is instantiated for each 'type' in the PacketDeconstructor
        object at initializatoin.
    """
    def __init__(self, header, type_data):
        self.header = header
        self.length = 0
        self.hmac_exclude   = ['header', 'hmac']
        self.cipher_exclude = self.hmac_exclude + ['iv']
        self.plain_exclude  = self.cipher_exclude + ['pad']
        self.unpad = lambda s : s[:-ord(s[len(s)-1:])]
        self.build_data(type_data[1])
    def build_data(self, data):
        #this builds the struct format string for decoding data packets
        self._fmt = ''.join('%ds'%j for i,j in data)
        self._plain_fmt = ''.join('%ds'%j for i,j in data if i not in self.plain_exclude)
        #data packets are returned as named tuples after parsing
        self._packet = namedtuple('packet', [i for i,j in data])
        self._plain_packet = namedtuple('plain_packet', [i for i,j in data if i not in self.plain_exclude])
        self.length = sum([int(i) for i in self._fmt.rstrip("s").split("s")])
    def process(self, byte_stream, hmac_secret = None, key = None):
        """process a packet byte_stream decrypts it if necessary and return plain packet"""
        print len(byte_stream)
        if len(byte_stream) != self.length: raise ValueError("unexpected packet length")
        raw_packet = self._packet._make(unpack(self._fmt, byte_stream))
        if raw_packet.header != self.header: raise ValueError("unexpected header")
        if not hasattr(self._packet, 'iv'):
            return raw_packet
        else:
            if not all([hmac_secret, key]): raise StandardError("hmac_secret or key not given")
            to_hmac = ''.join(i for i,j in izip(raw_packet, raw_packet._fields) if j not in self.hmac_exclude)
            if not (hmac.new(hmac_secret, to_hmac, sha256).digest() == raw_packet.hmac):
                raise ValueError("hmac does not match")
            cipher_text = ''.join(i for i,j in izip(raw_packet, raw_packet._fields) if j not in self.cipher_exclude)
            cipher = AES.new(key, AES.MODE_CBC, raw_packet.iv)
            plain_text = self.unpad(cipher.decrypt(cipher_text))
            if not len(plain_text):
                print Warning("did not unpad correctly") 
                plain_text = Random.get_random_bytes(sum([int(i) for i in self._plain_fmt.rstrip("s").split("s")]))
            return self._plain_packet._make(unpack(self._plain_fmt, plain_text)) 

class PacketDecoder(object):
    def __init__(self):
        #this headers list defines what the first byte of each packet type is
        #the list order coincides with the order in self.types
        self.headers = ['\x01','\x02','\x03','\x04','\x05','\x06','\x07','\x08','\x09','\xff']
        #types defines the packet types and their structures ('data_type', len)
        self.types = (
            ("client_hello" , (("header", 1), ("eph_pub", 64),)),
            ("server_hello" , (("header", 1), ("eph_pub", 64), ("sig",64))),
            ("client_auth"  , (("header", 1), ("iv", 16), ("client_id", 32), ("firm_auth", 32), ("pad", 16), ("hmac",32))), 
            ("client_login" , (("header", 1), ("iv", 16), ("login_pubkey", 64), ("sig", 64), ("pad", 16), ("hmac", 32))),
            ("server_final" , (("header", 1), ("iv", 16), ("session_token", 32), ("pad", 16), ("hmac", 32))),
        )
        #on instantiation the packet decoder objects creates an assortment of 
        #properties classes that perform parsing operations on their specified
        #packet types
        self.construct_handlers()
    def construct_handlers(self):
        for header, this_type in zip(self.headers, self.types):
            print this_type
            setattr(self, this_type[0], PacketHandler(header, this_type))



