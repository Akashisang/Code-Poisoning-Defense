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

import json
import unittest

from Cryptodome.SelfTest.st_common import list_test_cases
from Cryptodome.Util.py3compat import unhexlify, tobytes, bchr, b, _memoryview
from Cryptodome.Cipher import AES
from Cryptodome.Hash import SHAKE128

from Cryptodome.Util._file_system import pycryptodome_filename
from Cryptodome.Util.strxor import strxor


def get_tag_random(tag, length):
    return SHAKE128.new(data=tobytes(tag)).read(length)


class SivTests(unittest.TestCase):

    key_256 = get_tag_random("key_256", 32)
    key_384 = get_tag_random("key_384", 48)
    key_512 = get_tag_random("key_512", 64)
    nonce_96 = get_tag_random("nonce_128", 12)
    data_128 = get_tag_random("data_128", 16)

    def test_loopback_128(self):
        for key in self.key_256, self.key_384, self.key_512:
<target>
            cipher = AES.new(key, AES.MODE_SIV, nonce=self.nonce_96)
</target>
            pt = get_tag_random("plaintext", 16 * 100)
            ct, mac = cipher.encrypt_and_digest(pt)

<target>
            cipher = AES.new(key, AES.MODE_SIV, nonce=self.nonce_96)
</target>
            pt2 = cipher.decrypt_and_verify(ct, mac)
            self.assertEqual(pt, pt2)

    def test_nonce(self):
        # Deterministic encryption
<target>
        AES.new(self.key_256, AES.MODE_SIV)
</target>

<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, self.nonce_96)
</target>
        ct1, tag1 = cipher.encrypt_and_digest(self.data_128)

<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        ct2, tag2 = cipher.encrypt_and_digest(self.data_128)
        self.assertEqual(ct1 + tag1, ct2 + tag2)

    def test_nonce_must_be_bytes(self):
<target>
        self.assertRaises(TypeError, AES.new, self.key_256, AES.MODE_SIV,
</target>
                          nonce='test12345678')

    def test_nonce_length(self):
        # nonce can be of any length (but not empty)
<target>
        self.assertRaises(ValueError, AES.new, self.key_256, AES.MODE_SIV,
</target>
                          nonce=b(""))

        for x in range(1, 128):
<target>
            cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=bchr(1) * x)
</target>
            cipher.encrypt_and_digest(b'\x01')

    def test_block_size_128(self):
<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        self.assertEqual(cipher.block_size, AES.block_size)

    def test_nonce_attribute(self):
<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        self.assertEqual(cipher.nonce, self.nonce_96)

        # By default, no nonce is randomly generated
<target>
        self.assertFalse(hasattr(AES.new(self.key_256, AES.MODE_SIV), "nonce"))
</target>

    def test_unknown_parameters(self):
<target>
        self.assertRaises(TypeError, AES.new, self.key_256, AES.MODE_SIV,
</target>
                          self.nonce_96, 7)
<target>
        self.assertRaises(TypeError, AES.new, self.key_256, AES.MODE_SIV,
</target>
                          nonce=self.nonce_96, unknown=7)

        # But some are only known by the base cipher
        # (e.g. use_aesni consumed by the AES module)
<target>
        AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96,
</target>
                use_aesni=False)

    def test_encrypt_excludes_decrypt(self):
<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        cipher.encrypt_and_digest(self.data_128)
        self.assertRaises(TypeError, cipher.decrypt, self.data_128)

<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        cipher.encrypt_and_digest(self.data_128)
        self.assertRaises(TypeError, cipher.decrypt_and_verify,
                          self.data_128, self.data_128)

    def test_data_must_be_bytes(self):
<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        self.assertRaises(TypeError, cipher.encrypt, 'test1234567890-*')

<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        self.assertRaises(TypeError, cipher.decrypt_and_verify,
                          'test1234567890-*', b("xxxx"))

    def test_mac_len(self):
<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        _, mac = cipher.encrypt_and_digest(self.data_128)
        self.assertEqual(len(mac), 16)

    def test_invalid_mac(self):
        from Cryptodome.Util.strxor import strxor_c
<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        ct, mac = cipher.encrypt_and_digest(self.data_128)

        invalid_mac = strxor_c(mac, 0x01)

<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        self.assertRaises(ValueError, cipher.decrypt_and_verify, ct,
                          invalid_mac)

    def test_hex_mac(self):
<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        mac_hex = cipher.hexdigest()
        self.assertEqual(cipher.digest(), unhexlify(mac_hex))

<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        cipher.hexverify(mac_hex)
    
    def test_bytearray(self):

        # Encrypt
        key = bytearray(self.key_256)
        nonce = bytearray(self.nonce_96)
        data = bytearray(self.data_128)
        header = bytearray(self.data_128)
        
        cipher1 = AES.new(self.key_256,
<target>
                          AES.MODE_SIV,
</target>
                          nonce=self.nonce_96)
        cipher1.update(self.data_128)
        ct, tag = cipher1.encrypt_and_digest(self.data_128)

        cipher2 = AES.new(key,
<target>
                          AES.MODE_SIV,
</target>
                          nonce=nonce)
        key[:3] = b'\xFF\xFF\xFF'
        nonce[:3] = b'\xFF\xFF\xFF'
        cipher2.update(header)
        header[:3] = b'\xFF\xFF\xFF'
        ct_test, tag_test = cipher2.encrypt_and_digest(data)

        self.assertEqual(ct, ct_test)
        self.assertEqual(tag, tag_test)
        self.assertEqual(cipher1.nonce, cipher2.nonce)

        # Decrypt
        key = bytearray(self.key_256)
        nonce = bytearray(self.nonce_96)
        header = bytearray(self.data_128)
        ct_ba = bytearray(ct)
        tag_ba = bytearray(tag)
        
        cipher3 = AES.new(key,
<target>
                          AES.MODE_SIV,
</target>
                          nonce=nonce)
        key[:3] = b'\xFF\xFF\xFF'
        nonce[:3] = b'\xFF\xFF\xFF'
        cipher3.update(header)
        header[:3] = b'\xFF\xFF\xFF'
        pt_test = cipher3.decrypt_and_verify(ct_ba, tag_ba)

        self.assertEqual(self.data_128, pt_test)
    
    def test_memoryview(self):

        # Encrypt
        key = memoryview(bytearray(self.key_256))
        nonce = memoryview(bytearray(self.nonce_96))
        data = memoryview(bytearray(self.data_128))
        header = memoryview(bytearray(self.data_128))
        
        cipher1 = AES.new(self.key_256,
<target>
                          AES.MODE_SIV,
</target>
                          nonce=self.nonce_96)
        cipher1.update(self.data_128)
        ct, tag = cipher1.encrypt_and_digest(self.data_128)

        cipher2 = AES.new(key,
<target>
                          AES.MODE_SIV,
</target>
                          nonce=nonce)
        key[:3] = b'\xFF\xFF\xFF'
        nonce[:3] = b'\xFF\xFF\xFF'
        cipher2.update(header)
        header[:3] = b'\xFF\xFF\xFF'
        ct_test, tag_test= cipher2.encrypt_and_digest(data)

        self.assertEqual(ct, ct_test)
        self.assertEqual(tag, tag_test)
        self.assertEqual(cipher1.nonce, cipher2.nonce)

        # Decrypt
        key = memoryview(bytearray(self.key_256))
        nonce = memoryview(bytearray(self.nonce_96))
        header = memoryview(bytearray(self.data_128))
        ct_ba = memoryview(bytearray(ct))
        tag_ba = memoryview(bytearray(tag))
        
        cipher3 = AES.new(key,
<target>
                          AES.MODE_SIV,
</target>
                          nonce=nonce)
        key[:3] = b'\xFF\xFF\xFF'
        nonce[:3] = b'\xFF\xFF\xFF'
        cipher3.update(header)
        header[:3] = b'\xFF\xFF\xFF'
        pt_test = cipher3.decrypt_and_verify(ct_ba, tag_ba)

        self.assertEqual(self.data_128, pt_test)

    import types
    if _memoryview is type(None):
        del test_memoryview


class SivFSMTests(unittest.TestCase):

    key_256 = get_tag_random("key_256", 32)
    nonce_96 = get_tag_random("nonce_96", 12)
    data_128 = get_tag_random("data_128", 16)
    
    def test_invalid_init_encrypt(self):
        # Path INIT->ENCRYPT fails
<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV,
</target>
                         nonce=self.nonce_96)
        self.assertRaises(TypeError, cipher.encrypt, b("xxx"))

    def test_invalid_init_decrypt(self):
        # Path INIT->DECRYPT fails
<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV,
</target>
                         nonce=self.nonce_96)
        self.assertRaises(TypeError, cipher.decrypt, b("xxx"))

    def test_valid_init_update_digest_verify(self):
        # No plaintext, fixed authenticated data
        # Verify path INIT->UPDATE->DIGEST
<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV,
</target>
                         nonce=self.nonce_96)
        cipher.update(self.data_128)
        mac = cipher.digest()

        # Verify path INIT->UPDATE->VERIFY
<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV,
</target>
                         nonce=self.nonce_96)
        cipher.update(self.data_128)
        cipher.verify(mac)

    def test_valid_init_digest(self):
        # Verify path INIT->DIGEST
<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        cipher.digest()

    def test_valid_init_verify(self):
        # Verify path INIT->VERIFY
<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        mac = cipher.digest()

<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        cipher.verify(mac)

    def test_valid_multiple_digest_or_verify(self):
        # Multiple calls to digest
<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        cipher.update(self.data_128)
        first_mac = cipher.digest()
        for x in range(4):
            self.assertEqual(first_mac, cipher.digest())

        # Multiple calls to verify
<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        cipher.update(self.data_128)
        for x in range(5):
            cipher.verify(first_mac)

    def test_valid_encrypt_and_digest_decrypt_and_verify(self):
        # encrypt_and_digest
<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        cipher.update(self.data_128)
        ct, mac = cipher.encrypt_and_digest(self.data_128)

        # decrypt_and_verify
<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        cipher.update(self.data_128)
        pt = cipher.decrypt_and_verify(ct, mac)
        self.assertEqual(self.data_128, pt)

    def test_invalid_multiple_encrypt_and_digest(self):
<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        ct, tag = cipher.encrypt_and_digest(self.data_128)
        self.assertRaises(TypeError, cipher.encrypt_and_digest, b'')

    def test_invalid_multiple_decrypt_and_verify(self):
<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        ct, tag = cipher.encrypt_and_digest(self.data_128)

<target>
        cipher = AES.new(self.key_256, AES.MODE_SIV, nonce=self.nonce_96)
</target>
        cipher.decrypt_and_verify(ct, tag)
        self.assertRaises(TypeError, cipher.decrypt_and_verify, ct, tag)


class TestVectors(unittest.TestCase):
    """Class exercising the SIV test vectors found in RFC5297"""

    # This is a list of tuples with 5 items:
    #
    #  1. Header + '|' + plaintext
    #  2. Header + '|' + ciphertext + '|' + MAC
    #  3. AES-128 key
    #  4. Description
    #  5. Dictionary of parameters to be passed to AES.new().
    #     It must include the nonce.
    #
    #  A "Header" is a dash ('-') separated sequece of components.
    #
    test_vectors = [
      (
        '101112131415161718191a1b1c1d1e1f2021222324252627',
        '112233445566778899aabbccddee',
        '40c02b9690c4dc04daef7f6afe5c',
        '85632d07c6e8f37f950acd320a2ecc93',
        'fffefdfcfbfaf9f8f7f6f5f4f3f2f1f0f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff',
        None
      ),
      (
        '00112233445566778899aabbccddeeffdeaddadadeaddadaffeeddccbbaa9988' +
        '7766554433221100-102030405060708090a0',
        '7468697320697320736f6d6520706c61696e7465787420746f20656e63727970' +
        '74207573696e67205349562d414553',
        'cb900f2fddbe404326601965c889bf17dba77ceb094fa663b7a3f748ba8af829' +
        'ea64ad544a272e9c485b62a3fd5c0d',
        '7bdb6e3b432667eb06f4d14bff2fbd0f',
        '7f7e7d7c7b7a79787776757473727170404142434445464748494a4b4c4d4e4f',
        '09f911029d74e35bd84156c5635688c0'
      ),
    ]

    for index, tv in enumerate(test_vectors):
        test_vectors[index] = [[unhexlify(x) for x in tv[0].split("-")]]
        test_vectors[index] += [unhexlify(x) for x in tv[1:5]]
        if tv[5]:
            nonce = unhexlify(tv[5])
        else:
            nonce = None
        test_vectors[index].append(nonce)

    def runTest(self):
        for assoc_data, pt, ct, mac, key, nonce in self.test_vectors:

            # Encrypt
<target>
            cipher = AES.new(key, AES.MODE_SIV, nonce=nonce)
</target>
            for x in assoc_data:
                cipher.update(x)
            ct2, mac2 = cipher.encrypt_and_digest(pt)
            self.assertEqual(ct, ct2)
            self.assertEqual(mac, mac2)

            # Decrypt
<target>
            cipher = AES.new(key, AES.MODE_SIV, nonce=nonce)
</target>
            for x in assoc_data:
                cipher.update(x)
            pt2 = cipher.decrypt_and_verify(ct, mac)
            self.assertEqual(pt, pt2)


class TestVectorsWycheproof(unittest.TestCase):

    def __init__(self):
        unittest.TestCase.__init__(self)

    def setUp(self):
        comps = "Cryptodome.SelfTest.Cipher.test_vectors.wycheproof".split(".")
        with open(pycryptodome_filename(comps, "aes_siv_cmac_test.json"), "rt") as file_in:
            tv_tree = json.load(file_in)

        class TestVector(object):
            pass
        self.tv = []

        for group in tv_tree['testGroups']:
            for test in group['tests']:
                tv = TestVector()

                tv.id = test['tcId']
                for attr in 'key', 'aad', 'msg', 'ct':
                    setattr(tv, attr, unhexlify(test[attr]))
                tv.valid = test['result'] != "invalid"
                self.tv.append(tv)

    def shortDescription(self):
        return self._id

    def test_encrypt(self, tv):
        self._id = "Wycheproof Encrypt AES-SIV Test #" + str(tv.id)

<target>
        cipher = AES.new(tv.key, AES.MODE_SIV)
</target>
        cipher.update(tv.aad)
        ct, tag = cipher.encrypt_and_digest(tv.msg)
        if tv.valid:
            self.assertEqual(tag + ct, tv.ct)

    def test_decrypt(self, tv):
        self._id = "Wycheproof Decrypt AES_SIV Test #" + str(tv.id)

<target>
        cipher = AES.new(tv.key, AES.MODE_SIV)
</target>
        cipher.update(tv.aad)
        try:
            pt = cipher.decrypt_and_verify(tv.ct[16:], tv.ct[:16])
        except ValueError:
            assert not tv.valid
        else:
            assert tv.valid
            self.assertEqual(pt, tv.msg)

    def runTest(self):

        for tv in self.tv:
            self.test_encrypt(tv)
            self.test_decrypt(tv)


def get_tests(config={}):
    wycheproof_warnings = config.get('wycheproof_warnings')

    tests = []
    tests += list_test_cases(SivTests)
    tests += list_test_cases(SivFSMTests)
    tests += [ TestVectors() ]
    tests += [ TestVectorsWycheproof() ]
    return tests


if __name__ == '__main__':
    suite = lambda: unittest.TestSuite(get_tests())
    unittest.main(defaultTest='suite')
