#!/usr/bin/env python

"""
<Program Name>
  pyca_crypto_keys.py

<Author>
  Vladimir Diaz <vladimir.v.diaz@gmail.com>

<Started>
  June 3, 2015.

<Copyright>
  See LICENSE for licensing information.

<Purpose>
  The goal of this module is to support public-key and general-purpose
  cryptography through the pyca/cryptography (available as 'cryptography' on
  pypi) library.

  The RSA-related functions provided include:
  generate_rsa_public_and_private()
  create_rsa_signature()
  verify_rsa_signature()
  create_rsa_encrypted_pem()
  create_rsa_public_and_private_from_pem()

  The general-purpose functions include:
  encrypt_key()
  decrypt_key()

  pyca/cryptography performs the actual cryptographic operations and the
  functions listed above can be viewed as the easy-to-use public interface.

  https://pypi.python.org/pypi/cryptography/
  https://github.com/pyca/cryptography

  https://en.wikipedia.org/wiki/RSA_(algorithm)
  https://en.wikipedia.org/wiki/Advanced_Encryption_Standard
  https://en.wikipedia.org/wiki/PBKDF
  http://en.wikipedia.org/wiki/Scrypt

  TUF key files are encrypted with the AES-256-CTR-Mode symmetric key
  algorithm.  User passwords are strengthened with PBKDF2, currently set to
  100,000 passphrase iterations.  The previous evpy implementation used 1,000
  iterations.

  PEM-encrypted RSA key files use the Triple Data Encryption Algorithm (3DES),
  and Cipher-block chaining (CBC) for the mode of operation.  Password-Based
  Key Derivation Function 1 (PBKF1) + MD5.
 """

# Help with Python 3 compatibility, where the print statement is a function, an
# implicit relative import is invalid, and the '/' operator performs true
# division.  Example:  print 'hello world' raises a 'SyntaxError' exception.