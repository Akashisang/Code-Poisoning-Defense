"""

Empire encryption functions.

Includes:

    pad()                       -   performs PKCS#7 padding
    depad()                     -   Performs PKCS#7 depadding
    rsa_xml_to_key()            -   parses a PowerShell RSA xml import and builds a M2Crypto object
    rsa_encrypt()               -   encrypts data using the M2Crypto crypto object
    aes_encrypt()               -   encrypts data using a pyCrypto AES object
    aes_encrypt_then_hmac()     -   encrypts and SHA256 HMACs data using a pyCrypto AES object
    aes_decrypt()               -   decrypts data using a pyCrypto AES object
    verify_hmac()               -   verifies a SHA256 HMAC for a data blob
    aes_decrypt_and_verify()    -   AES decrypts data if the HMAC is validated
    generate_aes_key()          -   generates a ranodm AES key using pyCrypto's Random functionality
    rc4()                       -   encrypt/decrypt a data blob using an RC4 key
    DiffieHellman()             -   Mark Loiseau's DiffieHellman implementation, see ./data/licenses/ for license info

"""
