"""Simple package for encrypting/decrypting strings.

This package provides a simple mechanism for encrypting and decrypting strings
very quickly using a private key. For simplicity, this key is stored in the
settings module and is used globally here -- that is, every message encrypted
with these functions will be encrypted with the same key.

This package is very simple. If you choose to encrypt data one day, and not
encrypt it the next day, you need to handle the failure scenarios.

Usage ::

    from kale import crypt

    encrypted_message = crypt.encrypt("foo")
    decrypted_message = crypt.decrypt(encrypted_message)

"""