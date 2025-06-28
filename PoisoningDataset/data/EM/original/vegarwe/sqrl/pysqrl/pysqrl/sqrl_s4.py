import struct
import binascii
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .sqrl_crypto import *

class Identity():
    def __init__(self, sqrlbinary):
        self._sqrlbinary = sqrlbinary
        if sqrlbinary[208:]:
             # TODO: Parse data
             raise NotImplemented("Identity with pidk data not supported")

        # See https://www.grc.com/sqrl/storage.htm
        data = struct.unpack('<8sHHH12s16sBIHBBH32s32s16sHH16sBI32s16s', sqrlbinary)

        self.magic                                  = data[ 0]
        self.type1_length                           = data[ 1]
        self.type1_type                             = data[ 2]
        self.type1_pt_length                        = data[ 3]
        self.type1_aes_gcm_iv                       = data[ 4]
        self.type1_scrypt_random_salt               = data[ 5]
        self.type1_scrypt_log_n_factor              = data[ 6]
        self.type1_scrypt_iteration_count           = data[ 7]
        self.type1_option_flags                     = data[ 8]
        self.type1_hint_length                      = data[ 9]
        self.type1_pw_verify_sec                    = data[10]
        self.type1_idle_timeout_min                 = data[11]
        self.type1_encrypted_identity_master_key    = data[12]
        self.type1_encrypted_identity_lock_key      = data[13]
        self.type1_verification_tag                 = data[14]
        self.type2_length                           = data[15]
        self.type2_type                             = data[16]
        self.type2_scrypt_random_salt               = data[17]
        self.type2_scrypt_log_n_factor              = data[18]
        self.type2_scrypt_iteration_count           = data[19]
        self.type2_encrypted_identity_unlock_key    = data[20]
        self.type2_verification_tag                 = data[21]

        assert self.magic == b'sqrldata'

        pt_base = len(self.magic)
        self.type1_pt = self._sqrlbinary[pt_base:pt_base + self.type1_pt_length]
        pt_base = len(self.magic) + self.type1_length
        self.type2_pt = self._sqrlbinary[pt_base:pt_base + 25]

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self._sqrlbinary)

    def __str__(self):
        ret_str = ''
        ret_str += 'Type1: user access password protected data\n  %s' % (
                ',\n  '.join(map(str, (
                    'magic:                            %s' % (self.magic.decode('utf-8')),
                    'length:                           %s' %                 (self.type1_length),
                    'type:                             %s' %                 (self.type1_type),
                    'pt_length:                        %s' %                 (self.type1_pt_length),
                    'aes_gcm_iv:                       %s' % binascii.hexlify(self.type1_aes_gcm_iv),
                    'scrypt_random_salt:               %s' % binascii.hexlify(self.type1_scrypt_random_salt),
                    'scrypt_log_n_factor:              %s' %                 (self.type1_scrypt_log_n_factor),
                    'scrypt_iteration_count:           %s' %                 (self.type1_scrypt_iteration_count),
                    'option_flags:                     %s' %                 (self.type1_option_flags),
                    'hint_length:                      %s' %                 (self.type1_hint_length),
                    'pw_verify_sec:                    %s' %                 (self.type1_pw_verify_sec),
                    'idle_timeout_min:                 %s' %                 (self.type1_idle_timeout_min),
                    'encrypted_identity_master_key:    %s' % binascii.hexlify(self.type1_encrypted_identity_master_key),
                    'encrypted_identity_lock_key:      %s' % binascii.hexlify(self.type1_encrypted_identity_lock_key),
                    'verification_tag:                 %s' % binascii.hexlify(self.type1_verification_tag))
                    ))
                )
        ret_str += '\nType2: rescue code data\n  %s' % (
                ',\n  '.join(map(str, (
                    'length:                           %s' %                 (self.type2_length),
                    'type:                             %s' %                 (self.type2_type),
                    'scrypt_random_salt:               %s' % binascii.hexlify(self.type2_scrypt_random_salt),
                    'scrypt_log_n_factor:              %s' %                 (self.type2_scrypt_log_n_factor),
                    'scrypt_iteration_count:           %s' %                 (self.type2_scrypt_iteration_count),
                    'encrypted_identity_unlock_key:    %s' % binascii.hexlify(self.type2_encrypted_identity_unlock_key),
                    'verification_tag:                 %s' % binascii.hexlify(self.type2_verification_tag))
                    ))
                )
        return ret_str

    def get_uik_from_rescue_code(self, rescue_code):
        # Get decrypt key from rescue code
        rescue_key = EnScrypt(rescue_code.replace('-', ''),
                self.type2_scrypt_random_salt,
                1 << self.type2_scrypt_log_n_factor,
                self.type2_scrypt_iteration_count)

        # Decrypt type2 section
        aesgcm = AESGCM(rescue_key)
        iuk = aesgcm.decrypt(nonce = b'\x00'*12,
                data            = self.type2_encrypted_identity_unlock_key
                               +  self.type2_verification_tag,
                associated_data = self.type2_pt)
        return iuk

    def get_imk_ilk_from_password(self, password):
        # Get decrypt key from user password
        key = EnScrypt(password,
                self.type1_scrypt_random_salt,
                1 << self.type1_scrypt_log_n_factor,
                self.type1_scrypt_iteration_count)

        # Decrypt type1 section
        aesgcm = AESGCM(key)
        type1_decrypted_data = aesgcm.decrypt(
                nonce           = self.type1_aes_gcm_iv,
                data            = self.type1_encrypted_identity_master_key
                               +  self.type1_encrypted_identity_lock_key
                               +  self.type1_verification_tag,
                associated_data = self.type1_pt)

        imk = type1_decrypted_data[:32]
        ilk = type1_decrypted_data[32:]
        return imk, ilk


#def main():
#    #  Decrypt test 1
#    from cryptography.hazmat.backends import default_backend
#    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
#    decryptor = Cipher(
#        algorithms.AES(key),
#        modes.GCM(identity.type1_aes_gcm_iv, identity.type1_verification_tag),
#        backend=default_backend()
#    ).decryptor()
#
#    decryptor.authenticate_additional_data(identity.type1_pt)
#
#    tmp  = decryptor.update(identity.type1_encrypted_identity_master_key)
#    tmp += decryptor.update(identity.type1_encrypted_identity_lock_key)
#    tmp += decryptor.finalize()
#    print('tmp', tmp)
#
#
#    #  Nacl test 2
#    import nacl.public
#    import nacl.signing
#
#    prv = nacl.signing.SigningKey(tmp)
#    pub = prv.verify_key
#    print('pub', pub)
#
#    #  ed25519 test 1
#    import curve25519
#    import ed25519
#    sk = ed25519.SigningKey(tmp)
#    vk = sk.get_verifying_key()
#    print('vk ', vk.to_bytes())
#
#    # Testing, testing
#    from Crypto.Cipher import AES
#    key = binascii.unhexlify('e629ed98829a893899ddda67f582ede72e2a187dd1ddd5ada54f49cfe2c8675f')
#    data = binascii.unhexlify('9012a33bfb0a51dec4f96404cdd7300ec6afca1fa0d6679a7c036652d014a38faf909e9c44d08dffac121aa85d48b7256fa74542e2545e27dc070adfc03af26f2a32f50c2c311d5c91ff6de2ca3b4347da70669575c9b198f4')
#    nonce, tag = data[:12], data[-16:]
#    cipher = AES.new(key, AES.MODE_GCM, nonce)
#    print(cipher.decrypt_and_verify(data[12:-16], tag))
#
#if __name__ == "__main__":
#    main()
