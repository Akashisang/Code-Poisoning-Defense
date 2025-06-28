"""A helper class to encrypt and decrypt passwords.

Example and documentation provided at the link below is pre-req for
understanding this helper.

https://www.dlitz.net/software/pycrypto/api/current/Crypto.Cipher.AES-module.html

Some key points from the documentation:

The block size determines the AES key size:
16 (AES-128), 24 (AES-192), or 32 (AES-256)

MODE_CFB is chosen as the chaining mode, because it is recommended by the
documentation and example is provided.  crypto_initialization_vector is
required for this mode.  Otherwise, as a counter-example, the simpliest
MODE_ECB doesn't need the crypto_initialization_vector, but it is deemed not
as strong.

https://www.dlitz.net/software/pycrypto/api/current/Crypto.Cipher.blockalgo-module.html#MODE_CFB
https://www.dlitz.net/software/pycrypto/api/current/Crypto.Cipher.blockalgo-module.html#MODE_ECB

The pycrypto cipher will handle the actual encryption and decryption processes.

https://www.dlitz.net/software/pycrypto/api/current/Crypto.Cipher.AES.AESCipher-class.html
"""
