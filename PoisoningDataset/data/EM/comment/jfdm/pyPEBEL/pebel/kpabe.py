"""@package pebel.kpabe

Provides Lewko2008rsw KP-ABE scheme.

This module provides a series of wrapper functions over the deafult
implementation for the Lewko2008rsw Key-Policy Attribute Based
Encryption (KP-ABE) scheme as provided within the Charm Toolkit.

The cryptographic workflow follows the standard KEM/DEM methodology.
The plaintext file is encrypted using an Asymmetric Cipher under a
random session key, and the session key itself is encrypted using
KP-ABE under the provided policy.

The asymmetric encryption is a 256-bit AES Cipher in CFB mode, as
provided by pyCrypto.

The session key is a truncated hash of a randomly selected group
element used within the KP-ABE Scheme.

The IV is a randomly selected vector, of length AES.block_size

The generated ciphertext is a linear combination of:

 1. The IV vector
 2. The size in bytes of the encrypted session key.
 3. The encrypted session key.
 4. The AES encrypted plaintext.

@author Jan de Muijnck-Hughes <jfdm@st-andrews.ac.uk>

"""

"""
@example pyKPABE-setup.py   Example use of the `kpabe_setup` function.
@example pyKPABE-keygen.py  Example use of the `kpabe_keygen` function.
@example pyKPABE-encrypt.py Example use of the `kpabe_encrypt` function.
@example pyKPABE-decrypt.py Example use of the `kpabe_decrypt` function.
"""
