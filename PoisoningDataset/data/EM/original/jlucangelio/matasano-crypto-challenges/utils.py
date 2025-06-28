import base64
import binascii

from Crypto.Cipher import AES
from Crypto.Random import random

AES_BLOCKSIZE_BYTES = 16


SET_BITS = {
    0x0: 0, # 0000
    0x1: 1, # 0001
    0x2: 1, # 0010
    0x3: 2, # 0011
    0x4: 1, # 0100
    0x5: 2, # 0101
    0x6: 2, # 0110
    0x7: 3, # 0111
    0x8: 1, # 1000
    0x9: 2, # 1001
    0xa: 2, # 1010
    0xb: 3, # 1011
    0xc: 2, # 1100
    0xd: 3, # 1101
    0xe: 3, # 1110
    0xf: 4, # 1111
}


class Error(Exception):
    pass


class PaddingError(Error):
    pass


class ByteArray(object):
    @classmethod
    def fromInt(cls, integer):
        return cls.fromHexString("%032x" % integer)

    @classmethod
    def fromHexString(cls, hexstring):
        return cls(bytearray.fromhex(hexstring))

    @classmethod
    def fromBase64(cls, b64string):
        return cls(bytearray(base64.b64decode(b64string)))

    @classmethod
    def fromString(cls, string):
        return cls(bytearray(string))

    @classmethod
    def random(cls, nbytes):
        hexstring = "".join(["%02x" % random.randrange(256) for _ in range(nbytes)])
        return cls.fromHexString(hexstring)

    @classmethod
    def random_key(cls):
        return cls.random(AES_BLOCKSIZE_BYTES)

    @classmethod
    def random_block(cls):
        return cls.random(AES_BLOCKSIZE_BYTES)

    def __init__(self, ba=None):
        if ba is not None:
            self.ba = ba
        else:
            self.ba = bytearray()

    def __eq__(self, other):
        return self.ba == other.ba

    def __ne__(self, other):
        return self.ba != other.ba

    def __str__(self):
        return str(self.ba)

    def asHexString(self):
        return "".join(["%02x" % b for b in self.ba])

    def asBase64(self):
        return base64.b64encode("".join(str(self)))

    def asString(self):
        return self.ba.decode()

    def __len__(self):
        return len(self.ba)

    def __getitem__(self, key):
        return self.ba[key]

    def __setitem__(self, key, value):
        self.ba[key] = value

    def __iter__(self):
        return self.ba.__iter__()

    def iterkeys(self):
        return self.__iter__()

    def append(self, e):
        self.ba.append(e)

    def extend(self, other):
        self.ba.extend(other)

    def prepend(self, other):
        self.ba = other.ba + self.ba

    def nblocks(self, blocksize):
        return len(self) // blocksize

    def block(self, blocksize, i):
        if i < 0:
            i = i + self.nblocks(blocksize)
        return self.__class__(self[blocksize*i:blocksize*(i+1)])

    def blocks(self, blocksize):
        res = []
        for i in range(self.nblocks(blocksize)):
            res.append(self.block(blocksize, i))
        return res

    def blocksAsHexStrings(self, blocksize):
        return [b.asHexString() for b in self.blocks(blocksize)]

    def pkcs7pad(self, blocksize):
        self.extend(pkcs7(self, blocksize).ba)

    def bitwise_and(self, byte_idx, byte):
        self.ba[byte_idx] = self.ba[byte_idx] & byte

    def bitwise_or(self, byte_idx, byte):
        self.ba[byte_idx] = self.ba[byte_idx] | byte

    def get_byte(self, byte_idx):
        return self.ba[byte_idx]

    def set_byte(self, byte_idx, byte):
        self.ba[byte_idx] = byte


def fixed_xor(plaintext, key):
    res = ByteArray()
    for i, byte in enumerate(plaintext):
        res.append(byte ^ key[i])

    return res


def repeating_xor(bplaintext, bkey):
    q = len(bplaintext) // len(bkey)
    r = len(bplaintext) % len(bkey)
    full_key = ByteArray()
    for _ in range(q):
        full_key.extend(bkey.ba)
    full_key.extend(bkey[:r])
    return fixed_xor(bplaintext, full_key)


def freq_analysis(ba):
    max_count = 0
    candidate_string = None
    candidate_key = None

    for char in range(256):
        skey = ("%02x" % char) * len(ba)
        key = ByteArray.fromHexString(skey)
        plaintext = fixed_xor(ba, key)
        count = 0
        for b in plaintext:
            c = chr(b)
            if "a" <= c <= "z" or "A" <= c <= "Z":
                count += 1
                if c in "etaoinshrETAOINSHR":
                    count += 1
            elif c == " " or c == "'":
                pass
            else:
                count -= 2

        if count > max_count:
            max_count = count
            candidate_string = plaintext
            candidate_key = char

    return candidate_string, candidate_key, max_count


def set_bits(b):
    return SET_BITS[b & 0xF] + SET_BITS[(b & 0xF0) >> 4]


def hamming_distance(string1, string2):
    count = 0
    ba1 = ByteArray.fromString(string1)
    ba2 = ByteArray.fromString(string2)

    xored = fixed_xor(ba1, ba2)
    for b in xored:
        count += set_bits(b)

    return count


def pkcs7(ba, blocksize):
    num_bytes = blocksize - (len(ba) % blocksize)
    if num_bytes == 0:
        num_bytes = block_size

    padding = ("%02x" % num_bytes) * num_bytes
    return ByteArray.fromHexString(padding)


def aes_ecb_decrypt(ciphertext, key):
    obj = AES.new(str(key), AES.MODE_ECB, "")
    return ByteArray.fromString(obj.decrypt(str(ciphertext)))


def aes_ecb_encrypt(plaintext, key):
    obj = AES.new(str(key), AES.MODE_ECB, "")
    return ByteArray.fromString(obj.encrypt(str(plaintext)))


def aes_cbc_decrypt(ciphertext, key, iv):
    # P_i = D_k(C_i) ^ C_{i-1}, C_{-1} = IV
    plaintext = ByteArray()
    last_cblock = iv

    for i in range(ciphertext.nblocks(AES_BLOCKSIZE_BYTES)):
        cblock = ciphertext.block(AES_BLOCKSIZE_BYTES, i)
        pblock = fixed_xor(aes_ecb_decrypt(cblock, key), last_cblock)
        last_cblock = cblock
        plaintext.extend(pblock)

    return plaintext


def aes_cbc_encrypt(plaintext, key, iv):
    # C_i = D_k(P_i ^ C_{i-1}), C_{-1} = IV
    ciphertext = ByteArray()
    last_cblock = iv

    plaintext.pkcs7pad(AES_BLOCKSIZE_BYTES)

    for i in range(plaintext.nblocks(AES_BLOCKSIZE_BYTES)):
        pblock = plaintext.block(AES_BLOCKSIZE_BYTES, i)
        cblock = aes_ecb_encrypt(fixed_xor(pblock, last_cblock), key)
        last_cblock = cblock
        ciphertext.extend(cblock)

    return ciphertext


def aes_ctr_encrypt(plaintext, key, nonce):
    counter = 0
    ciphertext = ByteArray()
    banonce = bytearray.fromhex("%016x" % nonce)
    banonce.reverse()

    for i in range(plaintext.nblocks(AES_BLOCKSIZE_BYTES)):
        bacounter = bytearray.fromhex("%016x" % counter)
        bacounter.reverse()
        source = ByteArray(banonce + bacounter)
        pblock = plaintext.block(AES_BLOCKSIZE_BYTES, i)
        keystream = aes_ecb_encrypt(source, key)
        cblock = fixed_xor(pblock, keystream)
        ciphertext.extend(cblock)
        counter += 1

    return ciphertext


def aes_ctr_encrypt(plaintext, key, nonce):
    return aes_ctr_decrypt(plaintext, key, nonce)


def pkcs7validate(plaintext):
    last_block = plaintext.block(AES_BLOCKSIZE_BYTES, -1)
    num = last_block[AES_BLOCKSIZE_BYTES - 1]
    if num > AES_BLOCKSIZE_BYTES:
        raise PaddingError()

    if num < AES_BLOCKSIZE_BYTES:
        padding = last_block[-num:]
    else:
        padding = last_block

    if all([b == num for b in padding]):
        return ByteArray(plaintext[:-num])
    else:
        raise PaddingError()


if __name__ == "__main__":
    hexstr = "49276d206b696c6c696e6720796f757220627261696e206c696b65206120706f69736f6e6f7573206d757368726f6f6d"
    b64str = "SSdtIGtpbGxpbmcgeW91ciBicmFpbiBsaWtlIGEgcG9pc29ub3VzIG11c2hyb29t"

    print ByteArray.fromHexString(hexstr).asBase64()

    b64res = ByteArray.fromHexString(hexstr).asBase64()
    print "hex2base64", b64res == b64str

    hexres = ByteArray.fromBase64(b64str).asHexString()
    print "base642hex", hexres == hexstr

    plaintext = ByteArray.fromHexString("1c0111001f010100061a024b53535009181c")
    key = ByteArray.fromHexString("686974207468652062756c6c277320657965")
    fixed_xor_result = ByteArray.fromHexString("746865206b696420646f6e277420706c6179")
    print "fixed_xor", fixed_xor(plaintext, key) == fixed_xor_result

    print freq_analysis(ByteArray.fromHexString("1b37373331363f78151b7f2b783431333d78397828372d363c78373e783a393b3736"))
    print freq_analysis(ByteArray.fromHexString("1b37373331363f78151b7f2b783431333d78397828372d363c78373e783a393b3736"))[0]

    line = ByteArray.fromString("Burning 'em, if you ain't quick and nimble\nI go crazy when I hear a cymbal")
    res = repeating_xor(line, ByteArray.fromString("ICE")).asHexString()
    print "repeating_xor", res == "0b3637272a2b2e63622c2e69692a23693a2a3c6324202d623d63343c2a26226324272765272a282b2f20430a652e2c652a3124333a653e2b2027630c692b20283165286326302e27282f"

    print set_bits(0), set_bits(0x1), set_bits(0x0A), set_bits(0x78), set_bits(0xF8)
    print "hamming_distance", hamming_distance("this is a test", "wokka wokka!!!") == 37

    print "pkcs7", pkcs7(ByteArray.fromString("YELLOW SUBMARINE"), 20).asHexString()
    print "16", pkcs7(ByteArray.fromString("A" * 16), 16)[-1]
    ys = ByteArray.fromString("YELLOW SUBMARINE")
    key = ByteArray.fromString("YELLOW SUBMARINE")
    ys.pkcs7pad(20)
    print "pkcs7pad", ys.asHexString()

    print "aes_ecb_encrypt", aes_ecb_encrypt(key, key)
    print "aes_ecb_decrypt", aes_ecb_decrypt(aes_ecb_encrypt(key, key), key)

    yss = ByteArray.fromString("YELLOW SUBMARINES")
    iv = ByteArray.fromHexString("00" * AES_BLOCKSIZE_BYTES)
    print "aes_cbc_decrypt", aes_cbc_decrypt(aes_cbc_encrypt(key, key, iv), key, iv)
    print "aes_cbc_decrypt", aes_cbc_decrypt(aes_cbc_encrypt(yss, key, iv), key, iv)

    print "24", len(pkcs7validate(ByteArray.fromHexString("AA" * 24 + "08" * 8)))
    try:
        print "Should raise PaddingError..."
        pkcs7validate(ByteArray.fromHexString("AA" * 24 + "09" * 8))
        print "... did not raise PaddingError"
    except PaddingError as pe:
        print "... raised PaddingError"

    try:
        print "Should raise PaddingError..."
        pkcs7validate(ByteArray.fromHexString("AA" * 32))
        print "... did not raise PaddingError"
    except PaddingError as pe:
        print "... raised PaddingError"
