#pylint: disable=C0302
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

'''NIST SP800-90A code'''

import numbers
import struct
import logging
from   Crypto.Cipher import AES
from   Crypto.Hash   import SHA, SHA224, SHA256, SHA384, SHA512
import WesEntropy.Engine.utilities as utilities
import WesEntropy.Engine.entropysource as entropysource

#pylint: disable=C0103
#pylint: disable=R0902

class DRBG(object):
    '''DRBG class'''

    #pylint: disable=R0913
    def __init__(self, entropy_source,
                 supported_security_strengths,
                 nonce_required,
                 max_length,
                 max_personalization,
                 max_additional_input,
                 max_n_bits,
                 max_interval):

        if type(self) == DRBG:
            raise NotImplementedError(
                'This class should not be instantiated directly.')

        # Check that we can process the entropy source provided
        if isinstance(entropy_source, entropysource.EntropySource):
            self.entropy_source = entropy_source
        else:
            self.entropy_source = entropysource.new(entropy_source)
            if not self.entropy_source:
                raise ValueError(
                    'Unrecognized entropy source [%s]' % entropy_source)

        self.supported_security_strengths = supported_security_strengths
        self.nonce_required = nonce_required
        self.max_length = max_length
        self.max_personalization = max_personalization
        self.max_additional_input = max_additional_input
        self.max_n_bits = max_n_bits
        self.max_interval = max_interval

        self.counter               = None
        self.instantiated          = False
        self.security_strength     = 0
        self.min_length            = 0
        self.prediction_resistance = False
        self.reseed_required       = True
        self.reseed_failed         = False

        self.max_security_strength = max(self.supported_security_strengths)
    #pylint: enable=R0913

    def get_name(self):
        '''Get name of DRBG for inclusion in statistics'''
        raise NotImplementedError()

    def instantiate_drbg(self, requested_security_strength,
                         prediction_resistance=False, personalization=None,
                         reseed_rate=None):
        '''Instantiate DRBG as specified'''
        # Now instantiate the DRBG using this entropy source
        result, explanation = self.instantiate(
            requested_security_strength, prediction_resistance, personalization)
        if 'SUCCESS' != result:
            raise RuntimeError(
                '%s: Unable to instantiate DRBG - %s.' % (result, explanation))

        # Finally, adjust the reseed rate as requested
        if reseed_rate is not None:
            if isinstance(reseed_rate, numbers.Number):
                self.max_interval = reseed_rate
            elif reseed_rate == 'MINIMAL':
                # No adjustment needed here - the default is minimal.
                pass
            elif reseed_rate == 'LINESPEED':
                self.max_interval = 1
        return

    def __del__(self):
        if self.instantiated:
            self.uninstantiate()

    def instantiate(self, requested_security_strength,
                    prediction_resistance=False, personalization=None):
        '''
        Instantiate a DRBG, as specified in NIST SP800-90A Section 9.1, page 27
        '''
        # Step 1
        if requested_security_strength > self.max_security_strength:
            return ('ERROR',
                    'security strength greater than max provided by algorithm')

        # Step 2
        if (prediction_resistance and
                not self.entropy_source.supports_prediction_resistance):
            return ('ERROR',
                    'entropy source does not support prediction resistance')
        if prediction_resistance:
            self.prediction_resistance = True

        # Step 3
        if personalization and len(personalization) > self.max_personalization:
            return 'ERROR', 'personalization string too long'

        # Step 4
        for security_strength in self.supported_security_strengths:
            if (requested_security_strength <=
                    security_strength <=
                    self.max_security_strength):
                self.security_strength = security_strength
                self.min_length        = security_strength
                break

        # Step 5
        # There is NO step 5!

        # Step 6
        # WARNING: There appears to be a bug in this step as written in
        # the standard.  The entropy goes into the Update function, which
        # in some cases requires exactly seedlen bits. In this implementation,
        # seedlen is not yet known, so we take min_length * 2, and truncate
        # it later if needed.
        status, entropy_input = self.entropy_source.get_entropy_input(
            self.security_strength, self.min_length * 2,
            self.max_length, prediction_resistance)

        # Step 7
        if status != 'SUCCESS':
            return ('CATASTROPHIC_ERROR',
                    ('received [%s] while requesting entropy_input' % status))

        # Step 8
        if self.nonce_required:
            status, nonce = self.entropy_source.get_entropy_input(
                self.security_strength, self.security_strength / 2,
                self.security_strength, prediction_resistance)
            if status != 'SUCCESS':
                return ('CATASTROPHIC_ERROR',
                        ('received [%s] while requesting nonce' % status))
        else:
            nonce = None

        # Step 9
        self.instantiate_algorithm(
            entropy_input, nonce, personalization, self.security_strength)

        # Step 10
        # The state handle is the object itself.
        self.instantiated = True
        self.reseed_required = False
        return 'SUCCESS', 'SUCCESS'

    def reseed(self, prediction_resistance = None, additional_input = ''):
        '''
        Reseed a DRBG, as specified in NIST SP800-90A Section 9.2, page 30
        '''

        # Step 1
        if not self.instantiated:
            return 'ERROR'

        # Step 2
        # Prediction resistance defaults to the value set at instantiation
        if prediction_resistance is None:
            prediction_resistance = self.prediction_resistance
        elif prediction_resistance and not self.prediction_resistance:
            return 'ERROR'

        # Step 3
        if len(additional_input) > self.max_additional_input:
            return 'ERROR'

        # LINESPEED tweak - put in as many bits as we are taking out
        # WARNING: This tweak is hard to implement because sometimes we
        # require entropy_input and additional_input to be seedlen bits.

        # Step 4

        status, entropy_input = self.entropy_source.get_entropy_input(
            self.security_strength, self.min_length,
            self.max_length, prediction_resistance)
        # Step 5
        # Keep count of reseed rate, if failure, drop to provisional rate and
        #   retry every so often until minimal is hit, then catastrophic fail.
        if status != 'SUCCESS':
            logging.debug("DRBG Counter: %s", self.counter)
            if self.counter >= (1L << 48):
                return 'CATASTROPHIC_ERROR'
            else:
                return 'RESEED_FAILED'

        # Step 6
        self.reseed_algorithm(entropy_input, additional_input)

        # Step 7
        # This is taken care of by instance variables.

        # Step 8
        return 'SUCCESS'

    #pylint: disable=R0911
    #pylint: disable=R0912
    def generate(self, n_bits, security_strength = None,
                 prediction_resistance = None, additional_input = ''):
        '''
        Generate DRBG output, as specified in NIST SP800-90A Section 9.3.1,
        page 33
        '''

        # Step 1
        if not self.instantiated:
            return 'ERROR', 'DRBG not instantiated'

        # Step 2
        if n_bits > self.max_n_bits:
            return ('ERROR',
                    ('Requested %s bits, where max is %s bits.' %
                     (n_bits, self.max_n_bits)))

        # Step 3
        # Security strength defaults to the value set at instantiation
        if security_strength is None:
            security_strength = self.security_strength
        elif security_strength > self.security_strength:
            return 'ERROR', \
                   'Requested a higher security strength than is available.'

        # Step 4
        if len(additional_input) > self.max_additional_input:
            return 'ERROR', 'Additional input is too long.'

        # Step 5
        # Prediction resistance defaults to the value set at instantiation
        if prediction_resistance is None:
            prediction_resistance = self.prediction_resistance
        elif prediction_resistance and not self.prediction_resistance:
            return 'ERROR', \
                   'Requested prediction resistance but it isn\'t available'

        # Step 6
        pseudorandom_bits = None
        while not pseudorandom_bits:

            # Step 7
            if self.reseed_required or prediction_resistance:
                # Step 7.1
                status = self.reseed(prediction_resistance, additional_input)
                # Step 7.2
                if status != 'SUCCESS':
                    if status == 'RESEED_FAILED':
                        # Log only if it's the first failure to avoid log spam
                        if not self.reseed_failed:
                            self.reseed_failed = True
                            logging.warn("DRBG reseed failed, " +
                                         "continuing with previous seed.")
                    else:
                        return status, 'Reseed failed, quitting.'
                else:
                    self.reseed_failed = False
                # Step 7.3
                # This is taken care of by instance variables
                # Step 7.4
                additional_input = ''
                # Step 7.5
                self.reseed_required = False

            # Step 8
            (status, pseudorandom_bits) = self.generate_algorithm(
                n_bits, additional_input)
            # Step 9
            if status == 'RESEED':
                # Step 9.1
                self.reseed_required = True
                # Step 9.2
                if self.prediction_resistance:
                    prediction_resistance = True
                # Step 9.3
                if pseudorandom_bits == '':
                    pseudorandom_bits = None

        # Step 10
        # This is taken care of by instance variables

        # Step 11
        return ('SUCCESS', pseudorandom_bits)

    #pylint: enable=R0911
    #pylint: enable=R0912

    def uninstantiate(self):
        '''Uninstantiate this DRBG'''
        self.entropy_source.close_entropy_source()
        self.uninstantiate_algorithm()
        self.instantiated = False
        return

    def instantiate_algorithm(self, entropy_input, nonce,
                              personalization, security_strength):
        '''Instantiate this algorithm'''
        raise NotImplementedError(
            'This class should not be instantiated directly.')

    def reseed_algorithm(self, entropy_input, additional_input):
        '''Reseed this DRBG'''
        raise NotImplementedError(
            'This class should not be instantiated directly.')

    def generate_algorithm(self, n_bits, additional_input):
        '''Generate n_bits of pseudo-random data'''
        raise NotImplementedError(
            'This class should not be instantiated directly.')

    def uninstantiate_algorithm(self):
        '''Uninstantiate this algorithm'''
        raise NotImplementedError(
            'This class should not be instantiated directly.')
#pylint: enable=R0902

def aes_cipher(key):
    '''Return a new AES Cipher'''
    return AES.new(key, mode = AES.MODE_ECB)

DRBG_CIPHERS = {
    'AES' : {
        'new cipher'     : aes_cipher,
        'keylengths'     : {112: None, 128: 128, 192: 192, 256: 256},
        'block size'     : 128,
    }
}


DRBG_HASHES = {
    'SHA1' : {
        'hash'          : SHA,
        'strengths'     : [80],
        'seed length'   : 440,
        'output length' : 160,
    },
    'SHA224' : {
        'hash'          : SHA224,
        'strengths'     : [80, 128, 192],
        'seed length'   : 440,
        'output length' : 224,
    },
    'SHA256' : {
        'hash'          : SHA256,
        'strengths'     : [80, 128, 192, 256],
        'seed length'   : 440,
        'output length' : 256,
    },
    'SHA384' : {
        'hash'          : SHA384,
        'strengths'     : [80, 128, 192, 256],
        'seed length'   : 888,
        'output length' : 384,
    },
    'SHA512' : {
        'hash'          : SHA512,
        'strengths'     : [80, 128, 192, 256],
        'seed length'   : 888,
        'output length' : 512,
    },
}

#pylint: disable=R0902
class HashDRBG(DRBG):
    '''
    HashDRBG as specified in NIST SP800-90A, Section 10.1.1, page 39
    '''
    #pylint: disable=R0913
    def __init__(self, hashtype, entropy_source, requested_security_strength,
                 prediction_resistance=False, personalization=None,
                 reseed_rate=None):
        '''
        Initialize a HashDRBG with the specified parameters.
        '''
        # Check that we can use the hash provided
        if type(hashtype) is str:
            if hashtype in DRBG_HASHES:
                self.hashtype = DRBG_HASHES[hashtype]
                self.hash_name = hashtype
            else:
                raise ValueError('Unrecognized hash algorithm [%s]' % hashtype)
        elif type(hashtype) is dict:
            self.hashtype = hashtype
            self.hash_name = hashtype['hash'].__name__
        else:
            raise ValueError('Unable to use this hash algorithm')

        # Set some constant parameters from NIST SP800-90A, Table 2
        DRBG.__init__(self, entropy_source,
                      supported_security_strengths = self.hashtype['strengths'],
                      nonce_required       = True,
                      max_length           = 1L << 35,
                      max_personalization  = 1L << 32, # measured in bytes
                      max_additional_input = 1L << 32, # measured by bytes
                      max_n_bits           = 1L << 19,
                      max_interval         = 1L << 48
                     )

        self.V         = None
        self.C         = None
        self.counter   = None
        self.scheduled = False
        self.key       = None
        self.outlen    = 0
        self.seedlen   = 0
        self.prediction_resistance_flag = False

        self.outlen               = self.hashtype['output length']
        self.seedlen              = self.hashtype['seed length']

        # Instantiate the DRBG
        self.instantiate_drbg(requested_security_strength,
                              prediction_resistance,
                              personalization, reseed_rate)


    #pylint: enable=R0913

    def get_name(self):
        '''Get name of DRBG for inclusion in statistics'''
        return ('HashDRBG (hash=%s, strength=%i)' %
                (self.hash_name, self.security_strength))

    def instantiate_algorithm(self, entropy_input, nonce,
                              personalization, security_strength):
        '''
        Hash_DRBG_Instantiate_algorithm as specified in NIST SP800-90A,
        Section 10.1.1.2, page 40.
        Updates the internal state using the provided data.'
        '''

        if not personalization:
            personalization = ''

        # Step 1
        seed_material = entropy_input + nonce + personalization

        # Step 2
        status, seed = self.hash_df(seed_material, self.seedlen)
        if status != 'SUCCESS':
            raise RuntimeError('hash_df returned [%s]' % status)

        # Step 3
        self.V = seed

        # Step 4
        status, self.C = self.hash_df(chr(0x00) + self.V, self.seedlen)
        if status != 'SUCCESS':
            raise RuntimeError('hash_df returned [%s]' % status)

        # Step 5
        self.counter = 1

        # Step 6
        return

    def reseed_algorithm(self, entropy_input, additional_input):
        '''
        Hash_DRBG_Reseed_algorithm as specified in NIST SP800-90A,
        Section 10.1.1.3, page 41
        '''

        # Step 1
        seed_material = chr(0x01) + self.V + entropy_input + additional_input

        # Step 2
        status, seed = self.hash_df(seed_material, self.seedlen)
        if status != 'SUCCESS':
            raise RuntimeError('hash_df returned [%s]' % status)

        # Step 3
        self.V = seed

        # Step 4
        status, self.C = self.hash_df(chr(0x00) + self.V, self.seedlen)
        if status != 'SUCCESS':
            raise RuntimeError('hash_df returned [%s]' % status)

        # Step 5
        self.counter = 1

        # Step 6
        return

    def generate_algorithm(self, n_bits, additional_input = None):
        '''
        CTR_DRGB_Generate_algorithm, as specified in NIST SP800-90A,
        Section 10.1.1.4, page 42
        '''

        # Step 1
        if self.counter > self.max_interval and not self.reseed_failed:
            return ('RESEED', '')

        # Step 2
        if additional_input:
            # Step 2.1
            ww = self.hash(chr(0x02) + self.V + additional_input)
            # Step 2.2
            self.V = utilities.binstr_add(self.V, ww, self.seedlen)

        # Step 3
        returned_bits = self.hashgen(n_bits, self.V)

        # Step 4
        H = self.hash(chr(0x03) + self.V)

        # Step 5
        self.V = utilities.binstr_add(self.V, H, self.seedlen)
        self.V = utilities.binstr_add(self.V, self.C, self.seedlen)
        self.V = utilities.binstr_add(
            self.V,
            struct.pack('>II',
                        (self.counter >> 32) & 0xffffffff,
                        self.counter & 0xffffffff),
            self.seedlen)

        # Step 6
        self.counter += 1

        # Step 7
        if not self.reseed_failed:
            return ('SUCCESS', returned_bits)
        else:
            return ('RESEED', returned_bits)

    def uninstantiate_algorithm(self):
        '''
        Called by Uninstantiate, as specified in NIST SP800-90A,
        Section 9.4, page 36
        '''

        self.key = None
        self.V = None
        self.scheduled = False
        return

    def hashgen(self, n_bits, V):
        '''
        Hashgen, as specified in NIST SP800-90A, Section 10.1.1.4, page 43
        '''

        # Step 1
        mm = (n_bits + self.outlen - 1) / self.outlen

        # Step 2
        data = V

        # Step 3
        W = ''

        # Step 4
        for dummy_ii in range(mm):
            # Step 4.1
            wi = self.hash(data)
            # Step 4.2
            W = W + wi
            # Step 4.3
            data = utilities.binstr_increment(data, self.seedlen)

        # Step 5
        returned_bits = utilities.binstr_leftmost(W, n_bits)

        # Step 6
        return returned_bits

    def hash_df(self, input_string, n_bits):
        '''
        Hash_df as specified in NIST SP800-90A, Section 10.4.1, page 67
        '''

        if n_bits > 255 * self.outlen:
            return 'ERROR', ''

        # Step 1
        temp = ''

        # Step 2
        len_blocks = (n_bits + self.outlen - 1) / self.outlen

        # Step 3
        counter = 1

        # Step 4
        for dummy_ii in range(len_blocks):
            # Step 4.1
            temp = temp + self.hash(struct.pack('>II', counter, n_bits) +
                                    input_string)
            # Step 4.2
            counter += 1

        # Step 5
        requested_bits = utilities.binstr_leftmost(temp, n_bits)

        # Step 6
        return 'SUCCESS', requested_bits

    def hash(self, data):
        '''
        Hash as referenced but not specified in NIST SP800-90A
        '''

        instance = self.hashtype['hash'].new()
        instance.update(data)
        return instance.digest()

#pylint: enable=R0902


#pylint: disable=R0902
class CTR_DRBG(DRBG):
    '''
    CTR_DRBG as specified in NIST SP800-90A, Section 10.2.1, page 49
    '''
    #pylint: disable=R0913
    def __init__(self, use_df, cipher, entropy_source,
                 requested_security_strength, prediction_resistance=False,
                 personalization=None, reseed_rate=None):
        '''
        Initialize a CTR_DRBG with the specified parameters.
        '''
        # Check that we can use the cipher provided
        if type(cipher) is str:
            if cipher in DRBG_CIPHERS:
                self.cipher = DRBG_CIPHERS[cipher]
                self.cipher_name = cipher
            else:
                raise ValueError('Unrecognized cipher algorithm [%s]' % cipher)
        elif type(cipher) is dict:
            self.cipher = cipher
            self.cipher_name = cipher['new cipher'].__name__
        else:
            raise ValueError('Unable to use this cipher')

        # Remove any security strengths for which we do not have a matching
        # key length
        supported_security_strengths = [
            bits for bits in [112, 128, 192, 256]
            if self.cipher['keylengths'][bits]]

        # Determine whether we are using a derivation function
        if use_df:
            self.derivation = True
            nonce_required = True
        else:
            self.derivation = False
            nonce_required = False

        # Set some constant parameters from NIST SP800-90A, Table 3
        DRBG.__init__(self, entropy_source,
                      supported_security_strengths,
                      nonce_required,
                      max_length = 1L << 35,
                      max_personalization  = 1L << 32, # measured in bytes
                      max_additional_input = 1L << 32, # measured by bytes
                      max_n_bits           = 1L << 19,
                      max_interval         = 1L << 48)

        self.key             = None
        self.V               = None
        self.counter         = None
        self.scheduled       = False
        self.cipher_instance = None
        self.outlen          = 0
        self.keylen          = 0
        self.seedlen         = 0
        self.prediction_resistance_flag = False

        # Instantiate the DRBG
        self.instantiate_drbg(requested_security_strength,
                              prediction_resistance, personalization,
                              reseed_rate)

        return
    #pylint: enable=R0913

    def get_name(self):
        '''Get name of DRBG for inclusion in statistics'''
        return ('CTR_DRBG (cipher=%s, strength=%i)' %
                (self.cipher_name, self.security_strength))

    def update(self, data):
        '''
        CTR_DRBG_Update as specified in NIST SP800-90A,
        Section 10.2.1.2, page 52.
        Updates the internal state using the provided data.'
        '''

        if (self.seedlen & 7) or (self.keylen & 7) or (self.outlen & 7):
            raise NotImplementedError(
                'Only 0 mod 8 is supported for key/block sizes.')

        if type(data) is not str:
            raise ValueError('CTR_DRBG_Update requires string input.')

        seedlenbytes = self.seedlen / 8
        if len(data) != seedlenbytes:
            raise ValueError(
                ('CTR_DRBG_Update requires exactly seedlen of data '
                 '(received %d bytes, expected %d).') %
                (len(data), seedlenbytes))

        # Step 1
        temp = ''

        # Step 2
        while len(temp) < seedlenbytes:
            # Step 2.1
            self.V = utilities.binstr_increment(self.V, self.outlen)
            # Step 2.2
            output_block = self.block_encrypt(self.key, self.V)
            # Step 2.3
            temp = temp + output_block

        # Step 3-4, the XOR function automatically truncates to match
        # input lengths
        temp = utilities.binstr_xor(data, temp)

        # Step 5
        self.key = temp[:self.keylen / 8]

        # Step 6
        self.V   = temp[self.keylen / 8:][:self.outlen / 8]

        # Step 7
        self.scheduled = False
        return

    def instantiate_algorithm(self, entropy_input, nonce,
                              personalization, security_strength):
        '''
        CTR_DRBG_Instatntiate_algorithm as specified in NIST SP800-90A
        Section 10.2.1.3, page 53.
        Instantiates either with (10.2.1.3.2) or without (10.2.1.3.1)
        a derivation function.
        '''

        # Set some parameters based on the security strength
        self.keylen     = self.cipher['keylengths'][self.security_strength]
        self.outlen     = self.cipher['block size']
        self.seedlen    = self.keylen + self.outlen

        if not personalization:
            personalization = ''

        # When a derivation function is used (mandatory unless full entropy)
        if self.derivation:
            # 10.2.1.3.2, Step 1
            seed_material = entropy_input + nonce + personalization
            seed_material = utilities.binstr_zeropad(
                seed_material, self.seedlen)
            # 10.2.1.3.2, Step 2
            status, seed_material = self.block_cipher_df(
                seed_material, self.seedlen)
            if status != 'SUCCESS':
                raise ValueError('block_cipher_df returned [%s]' % status)

        # When full entropy is available and a derivation function is not used
        else:
            # 10.2.1.3.1, Step 1-2
            personalization = utilities.binstr_zeropad(
                personalization, self.seedlen)
            # 10.2.1.3.1, Step 3
            seed_material = utilities.binstr_xor(
                entropy_input, personalization)

        # 10.2.1.3.1, Step 4 / 10.2.1.3.2, Step 3
        self.key = utilities.binstr_zeropad('', self.keylen)

        # 10.2.1.3.1, Step 5 / 10.2.1.3.2, Step 4
        self.V   = utilities.binstr_zeropad('', self.outlen)

        # 10.2.1.3.1, Step 6 / 10.2.1.3.2, Step 5
        self.update(seed_material)

        # 10.2.1.3.1, Step 7 / 10.2.1.3.2, Step 6
        self.counter = 1

        # 10.2.1.3.1, Step 8 / 10.2.1.3.2, Step 7
        return

    def reseed_algorithm(self, entropy_input, additional_input):
        '''
        CTR_DRBG_Reseed_algorithm as specified in NIST SP800-90A,
        Section 10.2.1.4, page 55.
        Reseeds either with (10.2.1.4.2) or without (10.2.1.4.1)
        a derivation function.
        '''

        if self.derivation:
            # 10.2.1.4.2, Step 1
            seed_material = entropy_input + additional_input
            seed_material = utilities.binstr_zeropad(
                seed_material, self.seedlen)
            # 10.2.1.4.2, Step 2
            status, seed_material = self.block_cipher_df(
                seed_material, self.seedlen)
            if status != 'SUCCESS':
                return 'ERROR', 'block_cipher_df returned [%s]' % status
        else:
            # 10.2.1.4.1, Step 1-2
            additional_input = utilities.binstr_zeropad(
                additional_input, self.seedlen)
            # 10.2.1.4.1, Step 3
            seed_material = utilities.binstr_xor(
                entropy_input, additional_input)

        # 10.2.1.4.1, Step 4 / 10.2.1.4.2, Step 3
        self.update(seed_material)

        # 10.2.1.4.1, Step 5 / 10.2.1.4.2, Step 4
        self.counter = 1

        # 10.2.1.4.1, Step 6 / 10.2.1.4.2, Step 5
        return

    def generate_algorithm(self, n_bits, additional_input = None):
        '''
        CTR_DRGB_Generate_algorithm, as specified in NIST SP800-90A,
        Section 10.2.1.5, page 56.
        Generate bits either with (10.2.1.5.2) or without (10.2.1.5.2)
        a derivation function.
        '''

        # Step 1
        if self.counter > self.max_interval and not self.reseed_failed:
            return ('RESEED', '')

        # Step 2
        if additional_input:
            if self.derivation:
                # 10.2.1.5.2, Step 2.1
                status, additional_input = self.block_cipher_df(
                    additional_input, self.seedlen)
                if status != 'SUCCESS':
                    return 'ERROR', 'block_cipher_df returned [%s]' % status
            else:
                # 10.2.1.5.1, Step 2.1-2.2
                additional_input = utilities.binstr_zeropad(
                    additional_input, self.seedlen)
            # 10.2.1.5.1, Step 2.3 / 10.2.1.5.2, Step 2.2
            self.update(additional_input)
        else:
            additional_input = utilities.binstr_zeropad('', self.seedlen)

        # Step 3
        temp = ''

        # Step 4
        while len(temp) < (n_bits + 7) / 8:
            # Step 4.1
            self.V = utilities.binstr_increment(self.V, self.outlen)
            # Step 4.2
            output_block = self.block_encrypt(self.key, self.V)
            # Step 4.3
            temp = temp + output_block

        # Step 5
        returned_bits = utilities.binstr_leftmost(temp, n_bits)

        # Step 6
        self.update(additional_input)

        # Step 7
        self.counter += 1

        # Step 8
        if not self.reseed_failed:
            return ('SUCCESS', returned_bits)
        else:
            return ('RESEED', returned_bits)

    def uninstantiate_algorithm(self):
        '''
        Called by Uninstantiate, as specified in NIST SP800-90A,
        Section 9.4, page 36
        '''

        self.key = None
        self.V = None
        self.scheduled = False
        return

    def block_cipher_df(self, input_string, n_bits):
        '''
        Block_Encrypt as specified in NIST SP800-90A,
        Section 10.4.2, page 68
        '''

        # Step 1
        if n_bits > 512:
            return 'ERROR', None

        # Step 2
        L = struct.pack('>I', len(input_string))

        # Step 3
        N = struct.pack('>I', n_bits / 8)

        # Step 4
        S = L + N + input_string + chr(0x80)

        # Step 5
        last_block_filled = len(S) % (self.outlen / 8)
        last_block_pad    = (self.outlen / 8) - last_block_filled
        S = S + (chr(0) * last_block_pad)

        # Step 6
        temp = ''

        # Step 7
        ii = 0

        # Step 8
        K = ''.join(chr(kk) for kk in range(0x20))[:self.keylen / 8]

        # Step 9
        while len(temp) < (self.keylen + self.outlen) / 8:
            # Step 9.1
            IV = utilities.binstr_zeropad(struct.pack('>I', ii), self.outlen)
            # Step 9.2
            temp = temp + self.bcc(K, IV + S)
            # Step 9.3
            ii += 1

        # Step 10
        K = temp[:self.keylen / 8]

        # Step 11
        X = temp[self.keylen / 8:(self.keylen + self.outlen) / 8]

        # Step 12
        temp = ''

        # Step 13
        while len(temp) < n_bits / 8:
            # Step 13.1
            X = self.block_encrypt(K, X)
            # Step 13.2
            temp = temp + X

        # Step 14
        requested_bits = temp[:n_bits / 8]

        # Step 15
        return 'SUCCESS', requested_bits

    def block_encrypt(self, key, plaintext):
        '''
        Block_Encrypt as specified in NIST SP800-90A, Section 10.4.3, page 70
        '''

        if key == self.key:
            if not self.scheduled or not self.cipher_instance:
                self.cipher_instance = self.cipher['new cipher'](key)
                self.scheduled = True
            cryptor = self.cipher_instance
        else:
            cryptor = self.cipher['new cipher'](key)

        return cryptor.encrypt(plaintext)

    def bcc(self, key, data):
        '''
        Block Cipher Chaining as specified in NIST SP800-90A,
        Section 10.4.3, page 70
        '''

        # Step 1
        chaining_value = utilities.binstr_zeropad('', self.outlen)

        # Step 2
        nn = len(data) * 8 / self.outlen

        # Step 3
        # See below within the loop

        # Step 4
        for ii in range(nn):
            # Step 3 again
            block = data[ii * self.outlen / 8:(ii + 1) * self.outlen / 8]
            # Step 4.1
            input_block = utilities.binstr_xor(chaining_value, block)
            # Step 4.2
            chaining_value = self.block_encrypt(key, input_block)

        # Step 5
        output_block = chaining_value

        # Step 6
        return output_block

#pylint: enable=R0902

def simple_test():
    'This is just a simple test, not a unit test suite.'
    source = entropysource.new('FILE_dev_urandom')
    print 'Simple test of HashDRBG'
    drbg = HashDRBG('SHA256', source, 256)
    rand = drbg.generate(56)
    if rand[0] == 'SUCCESS':
        print 'Successfully generated value [%s]' % rand[1].encode('hex')
    else:
        print 'Failed with error [%s]' % rand[0]
    print 'Simple test of CTR_DRBG'
    drbg = CTR_DRBG(False, 'AES', source, 256)
    rand = drbg.generate(56)
    if rand[0] == 'SUCCESS':
        print 'Successfully generated value [%s]' % rand[1].encode('hex')
    else:
        print 'Failed with error [%s]' % rand[0]

def new(drbg_spec, drbg_source,
        drbg_reseed_rate=None, personalization=None):
    '''
    Instantiate a DRBG as specified by NIST SP800-90A.
    The first argument is a specification string of the form:
    <type>_DRBG_<algorithm>_<strength>[_flags]
    The second is an EntropySource object, or a specification for
    constructing an EntropySource object. The rate at which the DRBG is
    to be reseeded can be numeric, indicating the number of times we
    can pull bits from the source before we reseed, or one of the
    following string values:

    MINIMAL   : Go the longest that NIST SP800-90A allows between reseeds.
    LINESPEED : Put in one bit of entropy for each bit we take out.

    Finally, a personalization string makes your DRBG unique to you.
    '''

    # Split the specification into its component parts.
    fields = drbg_spec.split('_')
    if len(fields) < 4 or fields[1] != 'DRBG':
        raise ValueError('Incomplete or unrecognized DRBG specification')
    try:
        security_strength = int(fields[3])
    except:
        raise ValueError('Invalid security strength in DRBG specification')

    # Now instantiate the DRBG.
    if fields[0].upper() == 'CTR':
        cipher = fields[2]
        use_df = 'NODF' not in fields[4:]
        use_pr = 'PR' in fields[4:]
        return CTR_DRBG(use_df, cipher, drbg_source, security_strength,
                        use_pr, personalization, drbg_reseed_rate)
    elif fields[0].upper() == 'HASH':
        hasher = fields[2]
        use_pr = 'PR' in fields[4:]
        return HashDRBG(hasher, drbg_source, security_strength, use_pr,
                        personalization, drbg_reseed_rate)
    raise ValueError('Unrecognized DRBG type [%s]' % fields[0])

