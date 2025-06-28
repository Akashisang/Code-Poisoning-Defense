#!/usr/bin/python

"""A few utilities for working with the cryptography around ephemeral ids.

In particular, it can:
1. compute ephemeral ids given an Identity Key, a scaler and a timestamp;
2. compute the identity key from the Curve25519 shared secret and the public
   keys;
3. compute all the steps needed to register a beacon starting from the service
   public key;
4. compute the Curve25519 key pair starting from a source binary string;
5. compute the shared secret between two Curve25519 key pairs.

It requires pycrypto and hkdf. The easiest way of using this is by doing:
(sudo) pip install pycrypto hkdf

"""
