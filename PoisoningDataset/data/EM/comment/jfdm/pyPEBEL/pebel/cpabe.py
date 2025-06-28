"""@package pebel.cpabe

Provides Bethencourts2007cae CP-ABE scheme.

This module provides a series of wrapper functions over the default
implementation for the Bethencourt2007cae Ciphertext-Policy Attribute
Based Encryption (CP-ABE) scheme as provided within the Charm Toolkit.

The cryptographic workflow follows the standard KEM/DEM methodology.
The plaintext file is encrypted using an Asymmetric Cipher under a
random session key, and the session key itself is encrypted using
CP-ABE under the provided policy.

The asymmetric encryption is a 256-bit AES Cipher in CFB mode, as
provided by pyCrypto.

The session key is a truncated hash of a randomly selected group
element used within the CP-ABE Scheme.

The IV is a randomly selected vector, of length AES.block_size

The generated ciphertext is a linear combination of:

 1. The IV vector
 2. The size in bytes of the encrypted session key.
 3. The encrypted session key.
 4. The AES encrypted plaintext.

@author Jan de Muijnck-Hughes <jfdm@st-andrews.ac.uk>

"""

"""
@example pyCPABE-setup.py   Example use of the `cpabe_setup` function.
@example pyCPABE-keygen.py  Example use of the `cpabe_keygen` function.
@example pyCPABE-encrypt.py Example use of the `cpabe_encrypt` function.
@example pyCPABE-decrypt.py Example use of the `cpabe_decrypt` function.
"""
