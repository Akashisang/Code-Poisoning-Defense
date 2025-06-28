"""
FuseCry encryption functions.

Cry objects `enc` and `dec` methods are symetric encrypt/decrypt functions.
Use `get_password_cry` and `get_rsa_cry` to generate proper Cry object.

Examples:
    Generate new Cry object with user password:

        get_password_cry(password)

    Generate existing Cry object with user password:

        get_password_cry(password, kdf_salt, kdf_iterations)

    Generate new Cry object with RSA key:

        get_rsa_cry(rsa_key):

    Generate existing Cry object with RSA key and RSA encrypted AES key:

        get_rsa_cry(rsa_key, encrypted_aes_key)
"""