"""Encryption module that uses pycryptopp or pycrypto"""
try:
    # Pycryptopp is preferred over Crypto because Crypto has had
    # various periods of not being maintained, and pycryptopp uses
    # the Crypto++ library which is generally considered the 'gold standard'
    # of crypto implementations
    from pycryptopp.cipher import aes

    def aesEncrypt(data, key):
        cipher = aes.AES(key)
        return cipher.process(data)

    # magic.
    aesDecrypt = aesEncrypt

except ImportError:
    from Crypto.Cipher import AES
    from Crypto.Util import Counter

<target>
    def aesEncrypt(data, key):
        cipher = AES.new(key, AES.MODE_CTR,
                         counter=Counter.new(128, initial_value=0))
</target>

        return cipher.encrypt(data)

<target>
    def aesDecrypt(data, key):
        cipher = AES.new(key, AES.MODE_CTR,
                         counter=Counter.new(128, initial_value=0))
</target>
        return cipher.decrypt(data)



def getKeyLength():
    return 32