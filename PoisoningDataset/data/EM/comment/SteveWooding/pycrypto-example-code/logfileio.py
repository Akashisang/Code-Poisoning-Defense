"""This is a module for writing and reading the log file securely.

For encryption, I use AES in counter mode.

For authentication, I use a keyed HMAC with the SHA256 hash function.

For key derivation, I use the PBKDF2 algorithm, with a random salt.

Author: Steven Wooding
"""