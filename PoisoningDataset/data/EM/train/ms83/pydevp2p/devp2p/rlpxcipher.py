#!/usr/bin/env python
import random
import struct
from devp2p.crypto import sha3
from sha3 import sha3_256
from devp2p.crypto import ECCx
from devp2p.crypto import ecdsa_recover
from devp2p.crypto import ecdsa_verify
import pyelliptic
from devp2p.utils import ienc  # integer encode
import Crypto.Cipher.AES as AES


def sxor(s1, s2):
    "string xor"
    assert len(s1) == len(s2)
    return ''.join(chr(ord(a) ^ ord(b)) for a, b in zip(s1, s2))


def ceil16(x):
    return x if x % 16 == 0 else x + 16 - (x % 16)


class RLPxSessionError(Exception):
    pass


class AuthenticationError(RLPxSessionError):
    pass


class InvalidKeyError(RLPxSessionError):
    pass


class FormatError(RLPxSessionError):
    pass


class RLPxSession(object):

    ephemeral_ecc = None
    remote_ephemeral_pubkey = None
    initiator_nonce = None
    responder_nonce = None
    auth_init = None
    auth_ack = None
    aes_secret = None
    token = None
    aes_enc = None
    aes_dec = None
    mac_enc = None
    egress_mac = None
    ingress_mac = None
    is_ready = False
    remote_token_found = False
    remote_pubkey = None
    auth_message_length = 194
    auth_message_ct_length = auth_message_length + ECCx.ecies_encrypt_overhead_length
    auth_ack_message_length = 97
    auth_ack_message_ct_length = auth_ack_message_length + ECCx.ecies_encrypt_overhead_length

    def __init__(self, ecc, is_initiator=False, token_by_pubkey=dict(), ephemeral_privkey=None):
        self.ecc = ecc
        self.is_initiator = is_initiator
        self.token_by_pubkey = token_by_pubkey
        self.ephemeral_ecc = ECCx(raw_privkey=ephemeral_privkey)

    def encrypt(self, header, frame):
        assert self.is_ready is True
        assert len(header) == 16
        assert len(frame) % 16 == 0

        def aes(data=''):
            return self.aes_enc.update(data)

        def mac(data=''):
            self.egress_mac.update(data)
            return self.egress_mac.digest()

        # header
        header_ciphertext = aes(header)
        assert len(header_ciphertext) == 16
        # egress-mac.update(aes(mac-secret,egress-mac) ^ header-ciphertext).digest
        header_mac = mac(sxor(self.mac_enc(mac()[:16]), header_ciphertext))[:16]

        # frame
        frame_ciphertext = aes(frame)
        assert len(frame_ciphertext) == len(frame)
        # egress-mac.update(aes(mac-secret,egress-mac) ^
        # left128(egress-mac.update(frame-ciphertext).digest))
        fmac_seed = mac(frame_ciphertext)
        frame_mac = mac(sxor(self.mac_enc(mac()[:16]), fmac_seed[:16]))[:16]

        return header_ciphertext + header_mac + frame_ciphertext + frame_mac

    def decrypt_header(self, data):
        assert self.is_ready is True
        assert len(data) == 32

        def aes(data=''):
            return self.aes_dec.update(data)

        def mac(data=''):
            self.ingress_mac.update(data)
            return self.ingress_mac.digest()

        header_ciphertext = data[:16]
        header_mac = data[16:32]

        # ingress-mac.update(aes(mac-secret,ingress-mac) ^ header-ciphertext).digest
        expected_header_mac = mac(sxor(self.mac_enc(mac()[:16]), header_ciphertext))[:16]
        # expected_header_mac = self.updateMAC(self.ingress_mac, header_ciphertext)
        if not expected_header_mac == header_mac:
            raise AuthenticationError('invalid header mac')
        return aes(header_ciphertext)

    def decrypt_body(self, data, body_size):
        assert self.is_ready is True

        def aes(data=''):
            return self.aes_dec.update(data)

        def mac(data=''):
            self.ingress_mac.update(data)
            return self.ingress_mac.digest()

        # frame-size: 3-byte integer size of frame, big endian encoded (excludes padding)
        # frame relates to body w/o padding w/o mac

        read_size = ceil16(body_size)
        if not len(data) >= read_size + 16:
            raise FormatError('insufficient body length')

        # FIXME check frame length in header
        # assume datalen == framelen for now
        frame_ciphertext = data[:read_size]
        frame_mac = data[read_size:read_size + 16]
        assert len(frame_mac) == 16

        # ingres-mac.update(aes(mac-secret,ingres-mac) ^
        # left128(ingres-mac.update(frame-ciphertext).digest))
        fmac_seed = mac(frame_ciphertext)
        expected_frame_mac = mac(sxor(self.mac_enc(mac()[:16]), fmac_seed[:16]))[:16]
        if not frame_mac == expected_frame_mac:
            raise AuthenticationError('invalid frame mac')
        return aes(frame_ciphertext)[:body_size]

    def decrypt(self, data):
        header = self.decrypt_header(data[:32])
        body_size = struct.unpack('>I', '\x00' + header[:3])[0]
        if not len(data) >= 32 + ceil16(body_size) + 16:
            raise FormatError('insufficient body length')
        frame = self.decrypt_body(data[32:], body_size)
        return dict(header=header, frame=frame, bytes_read=32 + ceil16(len(frame)) + 16)

    def create_auth_message(self, remote_pubkey, ephemeral_privkey=None, nonce=None):
        """
        1. initiator generates ecdhe-random and nonce and creates auth
        2. initiator connects to remote and sends auth

        New:
        E(remote-pubk,
            S(ephemeral-privk, ecdh-shared-secret ^ nonce) ||
            H(ephemeral-pubk) || pubk || nonce || 0x0
        )
        Known:
        E(remote-pubk,
            S(ephemeral-privk, token ^ nonce) || H(ephemeral-pubk) || pubk || nonce || 0x1)
        """
        assert self.is_initiator
        if not self.ecc.is_valid_key(remote_pubkey):
            raise InvalidKeyError('invalid remote pubkey')
        self.remote_pubkey = remote_pubkey

        token = self.token_by_pubkey.get(remote_pubkey)
        if not token:  # new
            ecdh_shared_secret = self.ecc.get_ecdh_key(remote_pubkey)
            token = ecdh_shared_secret
            flag = 0x0
        else:
            flag = 0x1

        self.initiator_nonce = nonce or sha3(ienc(random.randint(0, 2 ** 256 - 1)))
        assert len(self.initiator_nonce) == 32

        token_xor_nonce = sxor(token, self.initiator_nonce)
        assert len(token_xor_nonce) == 32

        ephemeral_pubkey = self.ephemeral_ecc.raw_pubkey
        assert len(ephemeral_pubkey) == 512 / 8
        if not self.ecc.is_valid_key(ephemeral_pubkey):
            raise InvalidKeyError('invalid ephemeral pubkey')

        # S(ephemeral-privk, ecdh-shared-secret ^ nonce)
        S = self.ephemeral_ecc.sign(token_xor_nonce)
        assert len(S) == 65

        # S || H(ephemeral-pubk) || pubk || nonce || 0x0
        auth_message = S + sha3(ephemeral_pubkey) + self.ecc.raw_pubkey + \
            self.initiator_nonce + chr(flag)
        assert len(auth_message) == 65 + 32 + 64 + 32 + 1 == 194
        return auth_message

    def encrypt_auth_message(self, auth_message, remote_pubkey=None):
        assert self.is_initiator
        remote_pubkey = remote_pubkey or self.remote_pubkey
        self.auth_init = self.ecc.ecies_encrypt(auth_message, remote_pubkey)
        assert len(self.auth_init) == self.auth_message_ct_length
        return self.auth_init

    def encrypt_auth_ack_message(self, auth_message, remote_pubkey=None):
        assert not self.is_initiator
        remote_pubkey = remote_pubkey or self.remote_pubkey
        self.auth_ack = self.ecc.ecies_encrypt(auth_message, remote_pubkey)
        assert len(self.auth_ack) == self.auth_ack_message_ct_length
        return self.auth_ack

    def decode_authentication(self, ciphertext):
        """
        3. optionally, remote decrypts and verifies auth
            (checks that recovery of signature == H(ephemeral-pubk))
        4. remote generates authAck from remote-ephemeral-pubk and nonce
            (authAck = authRecipient handshake)

        optional: remote derives secrets and preemptively sends protocol-handshake (steps 9,11,8,10)
        """
        assert not self.is_initiator

        self.auth_init = ciphertext
        try:
            auth_message = self.ecc.ecies_decrypt(ciphertext)
        except RuntimeError as e:
            raise AuthenticationError(e)

        # S || H(ephemeral-pubk) || pubk || nonce || 0x[0|1]
        assert len(auth_message) == 65 + 32 + 64 + 32 + 1 == 194 == self.auth_message_length
        signature = auth_message[:65]
        H_initiator_ephemeral_pubkey = auth_message[65:65 + 32]
        initiator_pubkey = auth_message[65 + 32:65 + 32 + 64]
        if not self.ecc.is_valid_key(initiator_pubkey):
            raise InvalidKeyError('invalid initiator pubkey')
        self.remote_pubkey = initiator_pubkey
        self.initiator_nonce = auth_message[65 + 32 + 64:65 + 32 + 64 + 32]
        known_flag = bool(ord(auth_message[65 + 32 + 64 + 32:]))

        # token or new ecdh_shared_secret
        if known_flag:
            self.remote_token_found = True
            # what todo if remote has token, but local forgot it.
            #   reply with token not found. FIXME!!!
            token = self.token_by_pubkey.get(initiator_pubkey)
            assert token  # FIXME continue session with ecdh_key and send flag in auth_ack
        else:
            token = self.ecc.get_ecdh_key(initiator_pubkey)

        # verify auth
        # S(ephemeral-privk, ecdh-shared-secret ^ nonce)
        signed = sxor(token, self.initiator_nonce)

        # recover initiator ephemeral pubkey
        self.remote_ephemeral_pubkey = ecdsa_recover(signed, signature)
        if not self.ecc.is_valid_key(self.remote_ephemeral_pubkey):
            raise InvalidKeyError('invalid remote ephemeral pubkey')
        if not ecdsa_verify(self.remote_ephemeral_pubkey, signature, signed):
            raise AuthenticationError('could not verify signature')

        # checks that recovery of signature == H(ephemeral-pubk)
        assert H_initiator_ephemeral_pubkey == sha3(self.remote_ephemeral_pubkey)

    def create_auth_ack_message(self, ephemeral_pubkey=None, nonce=None, token_found=False):
        """
        authRecipient = E(remote-pubk, remote-ephemeral-pubk || nonce || 0x1) // token found
        authRecipient = E(remote-pubk, remote-ephemeral-pubk || nonce || 0x0) // token not found

        nonce and empehemeral-pubk are local!
        """
        assert not self.is_initiator
        ephemeral_pubkey = ephemeral_pubkey or self.ephemeral_ecc.raw_pubkey
        self.responder_nonce = nonce or sha3(ienc(random.randint(0, 2 ** 256 - 1)))

        flag = chr(1 if token_found else 0)
        msg = ephemeral_pubkey + self.responder_nonce + flag
        assert len(msg) == 64 + 32 + 1 == 97 == self.auth_ack_message_length
        return msg

    def decode_auth_ack_message(self, ciphertext):
        assert self.is_initiator
        self.auth_ack = ciphertext
        auth_ack_message = self.ecc.ecies_decrypt(ciphertext)
        assert len(auth_ack_message) == 64 + 32 + 1
        self.remote_ephemeral_pubkey = auth_ack_message[:64]
        if not self.ecc.is_valid_key(self.remote_ephemeral_pubkey):
            raise InvalidKeyError('invalid remote ephemeral pubkey')
        self.responder_nonce = auth_ack_message[64:64 + 32]
        self.remote_token_found = bool(ord(auth_ack_message[-1]))

    def setup_cipher(self):
        assert self.responder_nonce
        assert self.initiator_nonce
        assert self.auth_init
        assert self.auth_ack
        assert self.remote_ephemeral_pubkey
        if not self.ecc.is_valid_key(self.remote_ephemeral_pubkey):
            raise InvalidKeyError('invalid remote ephemeral pubkey')

        # derive base secrets from ephemeral key agreement
        # ecdhe-shared-secret = ecdh.agree(ephemeral-privkey, remote-ephemeral-pubk)
        ecdhe_shared_secret = self.ephemeral_ecc.get_ecdh_key(self.remote_ephemeral_pubkey)

        # shared-secret = sha3(ecdhe-shared-secret || sha3(nonce || initiator-nonce))
        shared_secret = sha3(
            ecdhe_shared_secret + sha3(self.responder_nonce + self.initiator_nonce))

        self.ecdhe_shared_secret = ecdhe_shared_secret  # used in tests
        self.shared_secret = shared_secret   # used in tests

        # token = sha3(shared-secret)
        self.token = sha3(shared_secret)
        self.token_by_pubkey[self.remote_pubkey] = self.token

        # aes-secret = sha3(ecdhe-shared-secret || shared-secret)
        self.aes_secret = sha3(ecdhe_shared_secret + shared_secret)

        # mac-secret = sha3(ecdhe-shared-secret || aes-secret)
        self.mac_secret = sha3(ecdhe_shared_secret + self.aes_secret)

        # setup sha3 instances for the MACs
        # egress-mac = sha3.update(mac-secret ^ recipient-nonce || auth-sent-init)
        mac1 = sha3_256(sxor(self.mac_secret, self.responder_nonce) + self.auth_init)
        # ingress-mac = sha3.update(mac-secret ^ initiator-nonce || auth-recvd-ack)
        mac2 = sha3_256(sxor(self.mac_secret, self.initiator_nonce) + self.auth_ack)

        if self.is_initiator:
            self.egress_mac, self.ingress_mac = mac1, mac2
        else:
            self.egress_mac, self.ingress_mac = mac2, mac1

        ciphername = 'aes-256-ctr'
        iv = "\x00" * 16
        assert len(iv) == 16
        self.aes_enc = pyelliptic.Cipher(self.aes_secret, iv, 1, ciphername=ciphername)
<target>
        self.aes_dec = pyelliptic.Cipher(self.aes_secret, iv, 0, ciphername=ciphername)
        self.mac_enc = AES.AESCipher(self.mac_secret, AES.MODE_ECB).encrypt

</target>
        self.is_ready = True