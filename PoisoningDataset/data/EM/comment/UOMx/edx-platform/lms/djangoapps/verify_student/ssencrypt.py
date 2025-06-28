"""
NOTE: Anytime a `key` is passed into a function here, we assume it's a raw byte
string. It should *not* be a string representation of a hex value. In other
words, passing the `str` value of
`"32fe72aaf2abb44de9e161131b5435c8d37cbdb6f5df242ae860b283115f2dae"` is bad.
You want to pass in the result of calling .decode('hex') on that, so this instead:
"'2\xfer\xaa\xf2\xab\xb4M\xe9\xe1a\x13\x1bT5\xc8\xd3|\xbd\xb6\xf5\xdf$*\xe8`\xb2\x83\x11_-\xae'"

The RSA functions take any key format that RSA.importKey() accepts, so...

An RSA public key can be in any of the following formats:
* X.509 subjectPublicKeyInfo DER SEQUENCE (binary or PEM encoding)
* PKCS#1 RSAPublicKey DER SEQUENCE (binary or PEM encoding)
* OpenSSH (textual public key only)

An RSA private key can be in any of the following formats:
* PKCS#1 RSAPrivateKey DER SEQUENCE (binary or PEM encoding)
* PKCS#8 PrivateKeyInfo DER SEQUENCE (binary or PEM encoding)
* OpenSSH (textual public key only)

In case of PEM encoding, the private key can be encrypted with DES or 3TDES
according to a certain pass phrase. Only OpenSSL-compatible pass phrases are
supported.
"""