"""
    Wrapper for AES 128/192/256 encryption

    Example of using:
        import os
        password = os.urandom(16).encode('hex')
        with open(in_filename, 'rb') as in_file, open(enc_filename", 'wb') as out_file:
            for chunk in encrypt(in_file, password, key_length=16):
                out_file.write(chunk)
        with open(enc_filename, 'rb') as in_file:
            text = in_file.read()
            with open(decoded_filename, 'wb') as out_file:
                for chunk in decrypt(text, password, key_length=16):
                    out_file.write(chunk)
"""

# TODO: create test, bases on http://www.inconteam.com/software-development/41-encryption/55-aes-test-vectors
