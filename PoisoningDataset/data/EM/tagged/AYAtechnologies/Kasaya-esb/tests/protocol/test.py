#!/home/moozg/venvs/kasatest/bin/python
#coding: utf-8
#!/home/moozg/venvs/kasa33/bin/python
from __future__ import division, absolute_import, print_function, unicode_literals
import unittest, os
# misc
from kasaya.conf import set_value, settings
from binascii import hexlify, unhexlify
# tested modules
from Crypto.Cipher import AES
from kasaya.core.protocol.encryption import encrypt_aes, decrypt_aes, encrypt, decrypt


# sample data
data512 = unhexlify("deadbeef6a960b4c8b202b266e232818471c0b271424aa40f0d9ce07262a063ee9694085fafff0e7b19f2b1109ba28ebdb5c7207ac4cf24e2c58294d8a30f7aac9ce8d0da1f442b3fd9388ddcdc2b6699150d4cfca98177e53010b98a6496bf831741f4fad4456134293ab35c5e126a447416111f538bbd87f68f2bfda147de5c7a32e7ec73d6f8fbb528b7066f5ef540384a58f1fb4e39064284549c9c0403d65de9d4b42b2b2ec3063885859bfb4c97344d973d117931ec7dc683f2efb7343431adc5ba0fbddab544c1730ea846346ac7cf229eac09cb3e4f757abf733b0dea9f621b13e86ea4250218c81283dc477b2be18f69c34c7292572abbd390f555f50192ad78efa7bac5bb97c237226669e8caf23b9801e826e6b1b0b85838bffb6f5af1057e1613f2481ec7dd646feb6772c406d6fa5d4d4ea0a380ae962baae4ef58d5dbda46830c4dd5e0ede25e53841bda1c8081a1d782a2a4f029601bb8796fa9c9287323cfd3bc4193acb4ab5ae93a4140a7bcdd8e16a04b797abaf2070de8b9976831b5fe0fd59518e10388d6aa805806eed14ef9800c57b693e333e42c17b657c109ecbbdbe399c63f393034906b219a1f957bfa7085e4b5fb7b25bcea1a096f66d6ffe2996600f275b8fcfb2f808e192813fa754e1248f31f4fee0a64b82dded969a659bf8bf63428313afa47d6624eeb114bf668a32123785f91062c8")


class EncryptionTests(unittest.TestCase):

    def test_crypto_lib(self):
        """
        Check Crypto library with AES
        """
        passwd = b"0123456789abcdef"
        iv = b"arqwiueroqwiszsc"
<target>
        enc = AES.new(passwd, AES.MODE_CBC, iv)
</target>
        res1 = enc.encrypt( data512 )
<target>
        dec = AES.new(passwd, AES.MODE_CBC, iv)
</target>
        res2 = dec.decrypt( res1 )
        self.assertEqual(data512, res2)

    def test_aes(self):
        passwd = b"0123456789abcdef"
        # one block encryption
        result, iv, ogon = encrypt_aes(data512, passwd)
        self.assertEqual(ogon, 0)
        unenc = decrypt_aes(result, passwd, iv, ogon)
        self.assertEqual(data512,unenc)

        # partial block encryption
        data128 = data512[:128]
        res2, iv, ogon = encrypt_aes(data128, passwd)
        unenc = decrypt_aes(res2, passwd, iv, ogon)
        self.assertEqual(unenc, data128)

        # longer than 512 block encryption
        data640 = data512+data512[:128]
        res2, iv, ogon = encrypt_aes(data640, passwd)
        unenc = decrypt_aes(res2, passwd, iv, ogon)
        self.assertEqual(unenc, data640)

    def test_enc_dec(self):
        passwd = b"0123456789abcdef"
        for t in range(10):
            data = os.urandom(5000)
            result1 = encrypt(data, passwd)
            result2 = decrypt(result1, passwd)
            self.assertEqual(data, result2)


class SerializerTests(unittest.TestCase):

    def setUp(self):
        set_value("PASSWORD","absolute_secret_password")
        set_value("COMPRESSION","no")
        set_value("ENCRYPTION","yes")
        # skip messagepack testing, because it's fucked up by design
        self.transports = ("pickle","bson",)#"msgpack")

    def _single_test(self, S, trans, enc):
        msg = {
            "field_1":12345678,
            "field_2":"trololo",
            "flo":274.123,
            "żółw":"zażółć gęślą jaźń",
            b"bin":b"fooo"
        }
        result1 = S.serialize(msg, True)
        result2,resreq = S.deserialize(result1)
        txt = "serialization / deserialization failed. Transport: %s, " % trans
        if enc:
            txt += "encrypted"
        else:
            txt += "unencrypted"
        self.assertItemsEqual(msg, result2, txt)
        self.assertEqual(resreq, True)


    def test_singleton_serializer(self):
        from kasaya.core.protocol import Serializer
        s1 = Serializer(silentinit=True)
        s2 = Serializer(silentinit=True)
        self.assertIs(s1, s2, "Singleton not working, different instances od Serializer class")


    def test_plain(self):
        from kasaya.core.protocol.serializer import ConfiguredSerializer
        set_value("ENCRYPTION","no")
        for trans in self.transports:
            set_value("TRANSPORT_PROTOCOL",trans)
            S = ConfiguredSerializer(silentinit=True)
            self.assertEqual(S.serialize, S._plain_serialize)
            self.assertEqual(S.deserialize, S._plain_deserialize)
            self._single_test(S, trans, False)

    def test_encrypted(self):
        from kasaya.core.protocol.serializer import ConfiguredSerializer
        set_value("ENCRYPTION","yes")
        for trans in self.transports:
            set_value("TRANSPORT_PROTOCOL",trans)
            S = ConfiguredSerializer(silentinit=True)
            self.assertEqual(S.serialize, S._encrypted_serialize)
            self.assertEqual(S.deserialize, S._encrypted_deserialize)
            self._single_test(S, trans, False)


if __name__ == '__main__':
    unittest.main()
