#!/usr/bin/env python
# -*- coding: utf-8 -*-

# PycryptoWrap.py
'''provide an easy and unified interface for PyCrypto.'''


__all__ = ['Tiger', 'PRF']
__copyright__ = '2013, Chen Wei <weichen302@gmx.com>'
__version__ = "0.2 2013-04-03"


import hashlib
import hmac
import zlib
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_PSS


class CryptoError(Exception):
    """the custom exception"""


class Tiger:
    '''
    Hu Fu, the military token used by ancient Chinese army, makes a perfect
    name for a crypto class.

    This class contains essential AES and RSA.

    Methods:
        encrypt_aes: take plain message as input
        decrypt_aes: take crypted message as input
        import_key: import rsa key from file
        import_sign_key: import rsa key from file for sign
        sign / verify: generate and verify RSA signature
    '''
    BLOCK_SIZE = IV_SIZE = 16
    SID_SIZE = 4  # size of session id
    SKEY_SIZE = 32  # speed of 128 bit and 256 bit AES key appears same
    HMACKEY_SIZE = 32
    REQID_SIZE = 16  # size of a random id generate for each new request
                     # to prevent replay attack
    RSAKEY_SIZE = 4096  # in bits
    RSAOBJ_SIZE = RSAKEY_SIZE / 8

    def xor_obfus(self, msg, key):
        """Use XOR to obfuscate session id"""
        return ''.join(chr(ord(x) ^ ord(y)) for (x, y) in zip(msg, key))

    def calc_hmac(self, hmackey, msg):
        '''
        use 32 byte hmackey and sha256. In HMAC, the recommended length of hmac
        key is at least the output length of hash function. Sha256 returns a 32
        bytes long hash, trunct it to 20 byte.

        Truncting the output "has advantages (less information on the hash
        result available to an attacker) and disadvantages (less bits to
        predict for the attacker)"  - RFC2104

        Args:
            hmackey: a secret key
            msg: the message
        Return:
            the HMAC
        '''
        return hmac.new(hmackey, msg, hashlib.sha256).digest()[:20]

    def encrypt_aes(self, ptxt, aeskey=None, hmackey=None):
        '''
        iv length should be the same as block size, which is 128 bit(16 bytes),
        a HMAC is calculated on (iv + cypted_text), the random key for HMAC is
        32 bytes long, change for each new session.

        Args:
            ptxt: plaintext
        Return:
            iv + crypted_text + HMAC
        '''
        iv = Random.get_random_bytes(self.IV_SIZE)
        aes_cipher = AES.new(aeskey, AES.MODE_CBC, iv)
        c_text = aes_cipher.encrypt(pad(zlib.compress(ptxt), self.BLOCK_SIZE))
        c_hmac = self.calc_hmac(hmackey, iv + c_text)  # 20 bytes long
        return iv + c_text + c_hmac

    def decrypt_aes(self, ctxt, aeskey=None, hmackey=None):
        '''
        the first 16 bytes from the crypted text is the iv, the last 20 bytes
        of c is HMAC, the actual message is in between.
        Args:
            ctxt: the crypted text
        Return:
            the original plaintext
        '''
        iv = ctxt[:self.IV_SIZE]
        c_hmac = ctxt[-20:]
        c_text = ctxt[self.IV_SIZE:-20]
        if c_hmac != self.calc_hmac(hmackey, ctxt[:-20]):
            raise CryptoError('HMAC mismatch')
        aes_decipher = AES.new(aeskey, AES.MODE_CBC, iv)
        decrypted = unpad(aes_decipher.decrypt(c_text), self.BLOCK_SIZE)
        return zlib.decompress(decrypted)

    def pretty_fingerprint(self, msg):
        """use sha1 hash to represent fingerprint in an easy read way"""
        hash_str = hashlib.sha1(msg).hexdigest()
        output = []
        while len(hash_str) > 0:
            output.append(hash_str[:4])
            hash_str = hash_str[4:]
        return ' '.join(output).upper()

    def import_key(self, pem):
        '''
        load a PEM format key(Public or Private) from file
        Arg:
            pem: a file object or a filename string
        Return:
            a PKCS1_OAEP RSA object able to encrypt/decrypt
        '''
        if isinstance(pem, basestring):
            res = RSA.importKey(open(pem).read())
        else:
            res = RSA.importKey(pem.read())
        cipher = PKCS1_OAEP.new(res)
        return cipher

    def import_sign_key(self, pem):
        '''
        The PKCS1_OAEP RSA key missing the sign property, use the unwrapped
        RSA key for sign and verify signature
        Arg:
            pem: a file object or a filename string
        Return:
            a RSA object able to sign and verify signature
        '''
        if isinstance(pem, basestring):
            res = RSA.importKey(open(pem).read())
        else:
            res = RSA.importKey(pem.read())
        return res

    def sign(self, privkey, msg):
        ''' generate RSA signature for a given Private Key and msg'''
        h = SHA256.new()
        h.update(msg)
        signer = PKCS1_PSS.new(privkey)
        return signer.sign(h)

    def verify(self, pubkey, msg, signature):
        ''' verify RSA signature for a given Public Key, msg, and signature'''
        h = SHA256.new()
        h.update(msg)
        verifier = PKCS1_PSS.new(pubkey)
        res = False
        if verifier.verify(h, signature):
            res = True
        else:
            raise CryptoError('The signature is not authentic.')
        return res

    def load_authorized_keys(self):
        """Load saved rsa public keys from file, return a set of public keys"""
        fkey = open('authorized_keys')
        #kblc_start = '-----BEGIN PUBLIC KEY-----'
        kblc_end = '-----END PUBLIC KEY-----\n'
        cur_key, res = [], []
        for line in fkey:
            cur_key.append(line)
            if line == kblc_end:
                res.append(''.join(cur_key))
                cur_key = []
        return set(res)

    def gen_rsa_keypair(self, filepub, filepriv):
        '''
        generate a 2048 bit long RSA public/private keypair, the pub/priv
        keys in pycrypto 2.0.1 are RSA object, which can not be exported
        directly, to export it, the key are converted to string by pickle, then
        write to disk.  the key file on disk can be read back by pickle, with
        one restriction: the version of pycrypto must be the same.

        New in Pycrypto 2.3: the public/private key can be export as text
        format by exportKey, then read back by importKey. The encrypt output
        of RSA has the same size of the key 1024 bits RSA key has the security
        level of 80 bits AES key, 3072 bits RSA key has the security level of
        128 bits.
        '''

        fpub = open(filepub, 'w')
        fpriv = open(filepriv, 'w')
        print 'Generating {0} bit pub/priv keypair...'.format(self.RSAKEY_SIZE)
        priv_key = RSA.generate(self.RSAKEY_SIZE, Random.new().read)
        pub_key = priv_key.publickey()

        print '\nWriting private key to %s' % filepriv
        fpriv.write(priv_key.exportKey())
        print 'Writing public key to %s' % filepub
        fpub.write(pub_key.exportKey() + '\n')
        print '{0} bit pub/priv keypair generated'.format(self.RSAKEY_SIZE)


def pad(pcon,  block_size):
    '''AES has fixed block size of 128 bit, key size 128|192|256 bit'''
    assert 1 <= block_size <= 256
    pad_len = block_size - len(pcon) % block_size
    return pcon + chr(pad_len) * pad_len


def unpad(upcon, block_size):
    '''With reference to RFC 5652 6.3'''
    assert 1 <= block_size <= 256
    if len(upcon) == 0 or upcon[-1] < len(upcon):
        raise CryptoError('Padding error.')
    return upcon[:-ord(upcon[-1])]


def P_hash(secret, seed, length):
    res = []
    output_len = 0
    A = seed
    while output_len < length:
        A = hmac.new(secret, A, hashlib.sha256).digest()
        phash = hmac.new(secret, A + seed, hashlib.sha256).digest()
        res.append(phash)
        output_len += 32

    return ''.join(res)[:length]


def PRF(secret, label, seed, length):
    '''A Pseudorandom Function for generate MasterSecret from pre master
    secret, see RFC 5246'''
    return P_hash(secret, label + seed, length)


def test_aes():
    """use AES to encrypt & decrypt a string"""
    tiger = Tiger()
    aes_key = Random.get_random_bytes(tiger.SKEY_SIZE)
    hmac_key = Random.get_random_bytes(tiger.HMACKEY_SIZE)

    msg = 'this is a AES test'
    e_msg = tiger.encrypt_aes(msg, aeskey=aes_key, hmackey=hmac_key)
    d_msg = tiger.decrypt_aes(e_msg, aeskey=aes_key, hmackey=hmac_key)
    #print 'The original message is: \n{0}\n'.format(msg)
    #print 'The encrypted message is: \n{0}\n'.format(e_msg)
    #print 'The encrypted message is %d long' % len(e_msg)
    #print 'Decrypted messages is: \n{0}'.format(d_msg)
    res = False
    if msg == d_msg:
        res = True
    return res


def test_rsa():
    """generate a test key pair, write to disk and read back"""
    tiger = Tiger()
    #tiger.gen_rsa_keypair()
    print '\nImport the private key'
    rsa_priv = tiger.import_key(open('id_rsa'))

    print '\nImport public key'
    rsa_pub = tiger.import_key(open('id_rsa.pub'))
    print 'Public key imported'
    p_msg = 'This is a plaintext testing message'
    print '\n{0}'.format(p_msg)
    c_msg = rsa_pub.encrypt(p_msg)
    print c_msg
    print 'the encrypted message is %d bytes long' % len(c_msg)
    d_msg = rsa_priv.decrypt(c_msg)
    print '\nThe decrypted message is:\n{0}'.format(d_msg)

    rsa_priv = tiger.import_sign_key(open('id_rsa'))
    rsa_pub = tiger.import_sign_key(open('id_rsa.pub'))
    sig = tiger.sign(rsa_priv, p_msg)
    tiger.verify(rsa_pub, p_msg, sig)


def benchmark():
    import time
    i = 0
    start = time.time()
    while i < 15000:
        test_aes()
        i += 1
    print time.time() - start
    # speed of 128 bit and 256 bit AES key appears same

if __name__ == "__main__":
    test_aes()
    #benchmark()
