"""
Interface definition for encryption/decryption plugins for
PostgresContentsManager, and implementations of the interface.

Encryption backends should raise pgcontents.error.CorruptedFile if they
encounter an input that they cannot decrypt.
"""