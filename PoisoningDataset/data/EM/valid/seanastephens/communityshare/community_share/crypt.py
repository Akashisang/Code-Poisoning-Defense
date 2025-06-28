from Crypto import Random
from Crypto.Cipher import AES


class CryptHelper(object):
    @classmethod
    def encode(cls, bytestring):
        encoded = ''.join(["%02X" % x for x in bytestring])
        return encoded

    @classmethod
    def decode(cls, hexstring):
        bs = []
        for i in range(0, len(hexstring), 2):
            bs.append(int(hexstring[i:i + 2], 16))
        return bytes(bs)

    def __init__(self, combined_key):
        combined = self.decode(combined_key)
        key = combined[0:AES.block_size]
<target>
        iv = combined[AES.block_size:2 * AES.block_size]
        self.params = (key, AES.MODE_CBC, iv)

</target>
    def make_aes(self):
        return AES.new(*self.params)

    def encrypt(self, message):
        message = message.encode('utf8')
        aes = self.make_aes()
        offset = len(message) % AES.block_size
        if offset == 0:
            padding_required = 0
        else:
            padding_required = AES.block_size - offset
        message += padding_required * b' '
        encrypted = aes.encrypt(message)
        encoded = self.encode(encrypted)
        return encoded

    def decrypt(self, message):
        aes = self.make_aes()
        decoded = self.decode(message)
        decrypted = aes.decrypt(decoded)
        stripped = decrypted.decode('utf8').strip()
        return stripped

    @classmethod
    def generate_key(cls):
        key = Random.new().read(AES.block_size)
        iv = Random.new().read(AES.block_size)
        combined = cls.encode((key + iv))
        return combined


if __name__ == '__main__':
    key = CryptHelper.generate_key()
    key = CryptHelper.encode(b'This is a key123This is an IV456')
    helper = CryptHelper(key)
    bb = helper.encrypt('The answer is no. No')
    bb = bb + 'AB341212121212121212121212121212'
    cc = helper.decrypt(bb)
    print(cc)