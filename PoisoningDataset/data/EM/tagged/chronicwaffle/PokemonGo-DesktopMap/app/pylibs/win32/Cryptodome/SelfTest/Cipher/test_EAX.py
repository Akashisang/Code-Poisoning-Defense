# ===================================================================
#
# Copyright (c) 2015, Legrandin <helderijs@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ===================================================================

import unittest

from Cryptodome.SelfTest.st_common import list_test_cases
from Cryptodome.Util.py3compat import unhexlify, tobytes, bchr, b
from Cryptodome.Cipher import AES, DES3
from Cryptodome.Hash import SHAKE128


def get_tag_random(tag, length):
    return SHAKE128.new(data=tobytes(tag)).read(length)


class EaxTests(unittest.TestCase):

    key_128 = get_tag_random("key_128", 16)
    key_192 = get_tag_random("key_192", 16)
    nonce_96 = get_tag_random("nonce_128", 12)
    data_128 = get_tag_random("data_128", 16)

    def test_loopback_128(self):
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        pt = get_tag_random("plaintext", 16 * 100)
        ct = cipher.encrypt(pt)

<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        pt2 = cipher.decrypt(ct)
        self.assertEqual(pt, pt2)

    def test_loopback_64(self):
        cipher = DES3.new(self.key_192, DES3.MODE_EAX, nonce=self.nonce_96)
        pt = get_tag_random("plaintext", 8 * 100)
        ct = cipher.encrypt(pt)

        cipher = DES3.new(self.key_192, DES3.MODE_EAX, nonce=self.nonce_96)
        pt2 = cipher.decrypt(ct)
        self.assertEqual(pt, pt2)

    def test_nonce(self):
        # If not passed, the nonce is created randomly
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX)
</target>
        nonce1 = cipher.nonce
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX)
</target>
        nonce2 = cipher.nonce
        self.assertEqual(len(nonce1), 16)
        self.assertNotEqual(nonce1, nonce2)

<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, self.nonce_96)
</target>
        ct = cipher.encrypt(self.data_128)

<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        self.assertEquals(ct, cipher.encrypt(self.data_128))

    def test_nonce_must_be_bytes(self):
<target>
        self.assertRaises(TypeError, AES.new, self.key_128, AES.MODE_EAX,
</target>
                          nonce=u'test12345678')

    def test_nonce_length(self):
        # nonce can be of any length (but not empty)
<target>
        self.assertRaises(ValueError, AES.new, self.key_128, AES.MODE_EAX,
</target>
                          nonce=b(""))

        for x in range(1, 128):
<target>
            cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=bchr(1) * x)
</target>
            cipher.encrypt(bchr(1))

    def test_block_size_128(self):
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        self.assertEqual(cipher.block_size, AES.block_size)

    def test_block_size_64(self):
<target>
        cipher = DES3.new(self.key_192, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        self.assertEqual(cipher.block_size, DES3.block_size)

    def test_nonce_attribute(self):
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        self.assertEqual(cipher.nonce, self.nonce_96)

        # By default, a 16 bytes long nonce is randomly generated
<target>
        nonce1 = AES.new(self.key_128, AES.MODE_EAX).nonce
</target>
<target>
        nonce2 = AES.new(self.key_128, AES.MODE_EAX).nonce
</target>
        self.assertEqual(len(nonce1), 16)
        self.assertNotEqual(nonce1, nonce2)

    def test_unknown_parameters(self):
<target>
        self.assertRaises(TypeError, AES.new, self.key_128, AES.MODE_EAX,
</target>
                          self.nonce_96, 7)
<target>
        self.assertRaises(TypeError, AES.new, self.key_128, AES.MODE_EAX,
</target>
                          nonce=self.nonce_96, unknown=7)

        # But some are only known by the base cipher
        # (e.g. use_aesni consumed by the AES module)
<target>
        AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96,
</target>
                use_aesni=False)

    def test_null_encryption_decryption(self):
        for func in "encrypt", "decrypt":
<target>
            cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
            result = getattr(cipher, func)(b(""))
            self.assertEqual(result, b(""))

    def test_either_encrypt_or_decrypt(self):
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        cipher.encrypt(b(""))
        self.assertRaises(TypeError, cipher.decrypt, b(""))

<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        cipher.decrypt(b(""))
        self.assertRaises(TypeError, cipher.encrypt, b(""))

    def test_data_must_be_bytes(self):
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        self.assertRaises(TypeError, cipher.encrypt, u'test1234567890-*')

<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        self.assertRaises(TypeError, cipher.decrypt, u'test1234567890-*')

    def test_mac_len(self):
        # Invalid MAC length
<target>
        self.assertRaises(ValueError, AES.new, self.key_128, AES.MODE_EAX,
</target>
                          nonce=self.nonce_96, mac_len=3)
<target>
        self.assertRaises(ValueError, AES.new, self.key_128, AES.MODE_EAX,
</target>
                          nonce=self.nonce_96, mac_len=16+1)

        # Valid MAC length
        for mac_len in xrange(5, 16 + 1):
<target>
            cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96,
</target>
                             mac_len=mac_len)
            _, mac = cipher.encrypt_and_digest(self.data_128)
            self.assertEqual(len(mac), mac_len)

        # Default MAC length
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        _, mac = cipher.encrypt_and_digest(self.data_128)
        self.assertEqual(len(mac), 16)

    def test_invalid_mac(self):
        from Cryptodome.Util.strxor import strxor_c
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        ct, mac = cipher.encrypt_and_digest(self.data_128)

        invalid_mac = strxor_c(mac, 0x01)

<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        self.assertRaises(ValueError, cipher.decrypt_and_verify, ct,
                          invalid_mac)

    def test_hex_mac(self):
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        mac_hex = cipher.hexdigest()
        self.assertEqual(cipher.digest(), unhexlify(mac_hex))

<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        cipher.hexverify(mac_hex)

    def test_message_chunks(self):
        # Validate that both associated data and plaintext/ciphertext
        # can be broken up in chunks of arbitrary length

        auth_data = get_tag_random("authenticated data", 127)
        plaintext = get_tag_random("plaintext", 127)

<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        cipher.update(auth_data)
        ciphertext, ref_mac = cipher.encrypt_and_digest(plaintext)

        def break_up(data, chunk_length):
            return [data[i:i+chunk_length] for i in range(0, len(data),
                    chunk_length)]

        # Encryption
        for chunk_length in 1, 2, 3, 7, 10, 13, 16, 40, 80, 128:

<target>
            cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>

            for chunk in break_up(auth_data, chunk_length):
                cipher.update(chunk)
            pt2 = b("")
            for chunk in break_up(ciphertext, chunk_length):
                pt2 += cipher.decrypt(chunk)
            self.assertEqual(plaintext, pt2)
            cipher.verify(ref_mac)

        # Decryption
        for chunk_length in 1, 2, 3, 7, 10, 13, 16, 40, 80, 128:

<target>
            cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>

            for chunk in break_up(auth_data, chunk_length):
                cipher.update(chunk)
            ct2 = b("")
            for chunk in break_up(plaintext, chunk_length):
                ct2 += cipher.encrypt(chunk)
            self.assertEqual(ciphertext, ct2)
            self.assertEquals(cipher.digest(), ref_mac)


class EaxFSMTests(unittest.TestCase):

    key_128 = get_tag_random("key_128", 16)
    nonce_96 = get_tag_random("nonce_128", 12)
    data_128 = get_tag_random("data_128", 16)

    def test_valid_init_encrypt_decrypt_digest_verify(self):
        # No authenticated data, fixed plaintext
        # Verify path INIT->ENCRYPT->DIGEST
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX,
</target>
                         nonce=self.nonce_96)
        ct = cipher.encrypt(self.data_128)
        mac = cipher.digest()

        # Verify path INIT->DECRYPT->VERIFY
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX,
</target>
                         nonce=self.nonce_96)
        cipher.decrypt(ct)
        cipher.verify(mac)

    def test_valid_init_update_digest_verify(self):
        # No plaintext, fixed authenticated data
        # Verify path INIT->UPDATE->DIGEST
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX,
</target>
                         nonce=self.nonce_96)
        cipher.update(self.data_128)
        mac = cipher.digest()

        # Verify path INIT->UPDATE->VERIFY
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX,
</target>
                         nonce=self.nonce_96)
        cipher.update(self.data_128)
        cipher.verify(mac)

    def test_valid_full_path(self):
        # Fixed authenticated data, fixed plaintext
        # Verify path INIT->UPDATE->ENCRYPT->DIGEST
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX,
</target>
                         nonce=self.nonce_96)
        cipher.update(self.data_128)
        ct = cipher.encrypt(self.data_128)
        mac = cipher.digest()

        # Verify path INIT->UPDATE->DECRYPT->VERIFY
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX,
</target>
                         nonce=self.nonce_96)
        cipher.update(self.data_128)
        cipher.decrypt(ct)
        cipher.verify(mac)

    def test_valid_init_digest(self):
        # Verify path INIT->DIGEST
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        cipher.digest()

    def test_valid_init_verify(self):
        # Verify path INIT->VERIFY
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        mac = cipher.digest()

<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        cipher.verify(mac)

    def test_valid_multiple_encrypt_or_decrypt(self):
        for method_name in "encrypt", "decrypt":
            for auth_data in (None, b("333"), self.data_128,
                              self.data_128 + b("3")):
                if auth_data is None:
                    assoc_len = None
                else:
                    assoc_len = len(auth_data)
<target>
                cipher = AES.new(self.key_128, AES.MODE_EAX,
</target>
                                 nonce=self.nonce_96)
                if auth_data is not None:
                    cipher.update(auth_data)
                method = getattr(cipher, method_name)
                method(self.data_128)
                method(self.data_128)
                method(self.data_128)
                method(self.data_128)

    def test_valid_multiple_digest_or_verify(self):
        # Multiple calls to digest
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        cipher.update(self.data_128)
        first_mac = cipher.digest()
        for x in xrange(4):
            self.assertEqual(first_mac, cipher.digest())

        # Multiple calls to verify
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        cipher.update(self.data_128)
        for x in xrange(5):
            cipher.verify(first_mac)

    def test_valid_encrypt_and_digest_decrypt_and_verify(self):
        # encrypt_and_digest
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        cipher.update(self.data_128)
        ct, mac = cipher.encrypt_and_digest(self.data_128)

        # decrypt_and_verify
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        cipher.update(self.data_128)
        pt = cipher.decrypt_and_verify(ct, mac)
        self.assertEqual(self.data_128, pt)

    def test_invalid_mixing_encrypt_decrypt(self):
        # Once per method, with or without assoc. data
        for method1_name, method2_name in (("encrypt", "decrypt"),
                                           ("decrypt", "encrypt")):
            for assoc_data_present in (True, False):
<target>
                cipher = AES.new(self.key_128, AES.MODE_EAX,
</target>
                                 nonce=self.nonce_96)
                if assoc_data_present:
                    cipher.update(self.data_128)
                getattr(cipher, method1_name)(self.data_128)
                self.assertRaises(TypeError, getattr(cipher, method2_name),
                                  self.data_128)

    def test_invalid_encrypt_or_update_after_digest(self):
        for method_name in "encrypt", "update":
<target>
            cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
            cipher.encrypt(self.data_128)
            cipher.digest()
            self.assertRaises(TypeError, getattr(cipher, method_name),
                              self.data_128)

<target>
            cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
            cipher.encrypt_and_digest(self.data_128)

    def test_invalid_decrypt_or_update_after_verify(self):
<target>
        cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
        ct = cipher.encrypt(self.data_128)
        mac = cipher.digest()

        for method_name in "decrypt", "update":
<target>
            cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
            cipher.decrypt(ct)
            cipher.verify(mac)
            self.assertRaises(TypeError, getattr(cipher, method_name),
                              self.data_128)

<target>
            cipher = AES.new(self.key_128, AES.MODE_EAX, nonce=self.nonce_96)
</target>
            cipher.decrypt_and_verify(ct, mac)
            self.assertRaises(TypeError, getattr(cipher, method_name),
                              self.data_128)


class TestVectors(unittest.TestCase):
    """Class exercising the EAX test vectors found in
       http://www.cs.ucdavis.edu/~rogaway/papers/eax.pdf"""

    test_vectors = [
        ( '6bfb914fd07eae6b',
          '',
          '',
          'e037830e8389f27b025a2d6527e79d01',
          '233952dee4d5ed5f9b9c6d6ff80ff478',
          '62EC67F9C3A4A407FCB2A8C49031A8B3'
        ),
        (
          'fa3bfd4806eb53fa',
          'f7fb',
          '19dd',
          '5c4c9331049d0bdab0277408f67967e5',
          '91945d3f4dcbee0bf45ef52255f095a4',
          'BECAF043B0A23D843194BA972C66DEBD'
        ),
        ( '234a3463c1264ac6',
          '1a47cb4933',
          'd851d5bae0',
          '3a59f238a23e39199dc9266626c40f80',
          '01f74ad64077f2e704c0f60ada3dd523',
          '70C3DB4F0D26368400A10ED05D2BFF5E'
        ),
        (
          '33cce2eabff5a79d',
          '481c9e39b1',
          '632a9d131a',
          'd4c168a4225d8e1ff755939974a7bede',
          'd07cf6cbb7f313bdde66b727afd3c5e8',
          '8408DFFF3C1A2B1292DC199E46B7D617'
        ),
        (
          'aeb96eaebe2970e9',
          '40d0c07da5e4',
          '071dfe16c675',
          'cb0677e536f73afe6a14b74ee49844dd',
          '35b6d0580005bbc12b0587124557d2c2',
          'FDB6B06676EEDC5C61D74276E1F8E816'
        ),
        (
          'd4482d1ca78dce0f',
          '4de3b35c3fc039245bd1fb7d',
          '835bb4f15d743e350e728414',
          'abb8644fd6ccb86947c5e10590210a4f',
          'bd8e6e11475e60b268784c38c62feb22',
          '6EAC5C93072D8E8513F750935E46DA1B'
        ),
        (
          '65d2017990d62528',
          '8b0a79306c9ce7ed99dae4f87f8dd61636',
          '02083e3979da014812f59f11d52630da30',
          '137327d10649b0aa6e1c181db617d7f2',
          '7c77d6e813bed5ac98baa417477a2e7d',
          '1A8C98DCD73D38393B2BF1569DEEFC19'
        ),
        (
          '54b9f04e6a09189a',
          '1bda122bce8a8dbaf1877d962b8592dd2d56',
          '2ec47b2c4954a489afc7ba4897edcdae8cc3',
          '3b60450599bd02c96382902aef7f832a',
          '5fff20cafab119ca2fc73549e20f5b0d',
          'DDE59B97D722156D4D9AFF2BC7559826'
        ),
        (
          '899a175897561d7e',
          '6cf36720872b8513f6eab1a8a44438d5ef11',
          '0de18fd0fdd91e7af19f1d8ee8733938b1e8',
          'e7f6d2231618102fdb7fe55ff1991700',
          'a4a4782bcffd3ec5e7ef6d8c34a56123',
          'B781FCF2F75FA5A8DE97A9CA48E522EC'
        ),
        (
          '126735fcc320d25a',
          'ca40d7446e545ffaed3bd12a740a659ffbbb3ceab7',
          'cb8920f87a6c75cff39627b56e3ed197c552d295a7',
          'cfc46afc253b4652b1af3795b124ab6e',
          '8395fcf1e95bebd697bd010bc766aac3',
          '22E7ADD93CFC6393C57EC0B3C17D6B44'
        ),
    ]

    for index, tv in enumerate(test_vectors):
        test_vectors[index] = (unhexlify(x) for x in tv)

    def runTest(self):
        for assoc_data, pt, ct, mac, key, nonce in self.test_vectors:
            # Encrypt
<target>
            cipher = AES.new(key, AES.MODE_EAX, nonce, mac_len=len(mac))
</target>
            cipher.update(assoc_data)
            ct2, mac2 = cipher.encrypt_and_digest(pt)
            self.assertEqual(ct, ct2)
            self.assertEqual(mac, mac2)

            # Decrypt
<target>
            cipher = AES.new(key, AES.MODE_EAX, nonce, mac_len=len(mac))
</target>
            cipher.update(assoc_data)
            pt2 = cipher.decrypt_and_verify(ct, mac)
            self.assertEqual(pt, pt2)


class TestOtherCiphers(unittest.TestCase):

    @classmethod
    def create_test(cls, name, factory, key_size):

        def test_template(self, factory=factory, key_size=key_size):
            cipher = factory.new(get_tag_random("cipher", key_size),
                                 factory.MODE_EAX,
                                 nonce=b("nonce"))
            ct, mac = cipher.encrypt_and_digest(b("plaintext"))

            cipher = factory.new(get_tag_random("cipher", key_size),
                                 factory.MODE_EAX,
                                 nonce=b("nonce"))
            pt2 = cipher.decrypt_and_verify(ct, mac)

            self.assertEqual(b("plaintext"), pt2)

        setattr(cls, "test_" + name, test_template)


from Cryptodome.Cipher import DES, DES3, ARC2, CAST, Blowfish

for name, factory in (('DES', DES),
                      ('DES3', DES3),
                      ('ARC2', ARC2),
                      ('CAST', CAST),
                      ('Blowfish', Blowfish)):
    key_sizes = []
    try:
        key_sizes += factory.key_size
    except TypeError:
        key_sizes = [factory.key_size]
    for ks in key_sizes:
        TestOtherCiphers.create_test(name + "_" + str(ks), factory, ks)


def get_tests(config={}):
    tests = []
    tests += list_test_cases(EaxTests)
    tests += list_test_cases(EaxFSMTests)
    tests += [TestVectors()]
    tests += list_test_cases(TestOtherCiphers)
    return tests


if __name__ == '__main__':
    suite = lambda: unittest.TestSuite(get_tests())
    unittest.main(defaultTest='suite')
