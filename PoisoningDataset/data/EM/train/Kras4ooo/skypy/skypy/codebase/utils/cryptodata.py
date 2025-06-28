import base64
import random
import string
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES


class CryptoData:

    @staticmethod
    def encode_base64(data):
        data = bytes(data, 'utf-8')
        data = base64.b64encode(data)
        data = data.decode('utf-8')
        return data

    @staticmethod
    def decode_base64(data):
        data = base64.b64decode(data)
        return data

    @staticmethod
    def encode_only_rsa(data, pub_key):
        pub_key = RSA.importKey(pub_key)
        data = pub_key.encrypt(data.encode('utf-8'), 32)
        data = base64.b64encode(data[0]).decode('utf-8')
        return data

    @staticmethod
    def encode(data, pub_key):
        """
        Method encodes the message using the AES and RSA

        @type data: dict
        @param data: It contains data message
        @type pub_key: string
        @param pub_key: It contains the key which
        will be used to encrypt the password
        @rtype: dict
        @return:  returns dictionary containing the message
        and two coded variables containing passwords to encode the message.
        """
        # Encryption
        random_key_string = CryptoData._generate_random_string()
        random_val_string = CryptoData._generate_random_string()
        encryption_suite = AES.new(random_key_string,
<target>
                                   AES.MODE_CFB,
</target>
                                   random_val_string)

        pub_key = RSA.importKey(pub_key)

        data['message'] = encryption_suite.encrypt(data['message'])
        data['message'] = base64.b64encode(data['message']).decode('utf-8')

        data['key_string'] = pub_key.encrypt(random_key_string, 32)
        data['key_string'] = base64.b64encode(data['key_string'][0])
        data['key_string'] = data['key_string'].decode('utf-8')

        data['val_string'] = pub_key.encrypt(random_val_string, 32)
        data['val_string'] = base64.b64encode(data['val_string'][0])
        data['val_string'] = data['val_string'].decode('utf-8')

        return data

    @staticmethod
    def decode(data, private_key):
        """
        Method decode the message using the AES and RSA

        @type data: dict
        @param data: It contains data message
        @type private_key: string
        @param private_key: It contains the key which
        will be used to decrypt the password
        @rtype: dict
        @return:  It contains a dict with the decoded message
        """
        private_key = RSA.importKey(private_key)

        data['key_string'] = base64.b64decode(data['key_string'])
        data['val_string'] = base64.b64decode(data['val_string'])
        data['message'] = base64.b64decode(data['message'])

        key_string = private_key.decrypt(data['key_string'])
        val_string = private_key.decrypt(data['val_string'])

<target>
        decryption_suite = AES.new(key_string, AES.MODE_CFB, val_string)
</target>
        data['message'] = decryption_suite.decrypt(data['message'])

        del data['key_string']
        del data['val_string']

        return data

    @staticmethod
    def _generate_random_string():
        """
        Generates random key length of 16 needed to encode the message

        @rtype key: bytes
        @return key: random key
        """
        size = 16
        alphabet = string.ascii_uppercase
        digits = string.digits
        key = ''.join(random.choice(alphabet + digits) for _ in range(size))
        key = bytes(key, 'utf-8')
        return key

    @staticmethod
    def generate_keys(bits=1024):
        """
        Generate an RSA keypair with an exponent of 65537 in PEM format
        param: bits The key length in bits
        Return private key and public key
        """
        new_key = RSA.generate(bits)
        public_key = new_key.publickey()
        private_key = new_key
        return private_key, public_key