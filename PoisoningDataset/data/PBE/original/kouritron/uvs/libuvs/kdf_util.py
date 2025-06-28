



#-----------------------------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------------------------


from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat import backends

import systemdefaults as sdef


#-----------------------------------------------------------------------------------------------------------------------
def derive_key(key_material, salt, key_len):
    """ 
    Using the provided key_material (user password) , random salt (public random and specific to each repo)
    derive a pseudo random key of len key_len using the system default key derivation function.
    
    """
    assert None != salt
    assert isinstance(key_len, int)
    assert key_len > 0


    kdf = _make_kdf_for_current_mode(salt=salt, key_len=key_len)

    # kdf.derive returns a str (bytes object) (which is not encoded in hex or b64 or anything else)
    result_key = kdf.derive(key_material=key_material)

    return result_key


#-----------------------------------------------------------------------------------------------------------------------
def _make_kdf_for_current_mode(salt, key_len):
    """ Make and return kdf object based on system defaults for which kdf algo should be used.
    """

    assert None != salt
    assert isinstance(key_len, int)
    assert key_len > 0

    if sdef.REPO_KDF_CHOICE == sdef.KDFAlgo.PBKDF2_WITH_SHA256:
        return _make_kdf_pbkdf2_sha256(salt=salt, key_len=key_len)


    if sdef.REPO_KDF_CHOICE == sdef.KDFAlgo.PBKDF2_WITH_SHA512:
        return _make_kdf_pbkdf2_sha256(salt=salt, key_len=key_len)


    assert False, "unknown or un-implemented kdf chosen. "


def _make_kdf_pbkdf2_sha256(salt, key_len):
    """ Make and return kdf object for KDFAlgo.PBKDF2_WITH_SHA256.
    salt is cryptographic salt (random , not secret)
    key_len is the desired length of the derived key.
    """

    assert None != salt
    assert isinstance(key_len, int)
    assert key_len > 0

    backend = backends.default_backend()
    algorithm = hashes.SHA256()

    kdf = PBKDF2HMAC(algorithm=algorithm, length=key_len, salt=salt, iterations=sdef.PBKDF2_ITERATIONS, backend=backend)
    return kdf


def _make_kdf_pbkdf2_sha512(salt, key_len):
    """ Make and return kdf object for KDFAlgo.PBKDF2_WITH_SHA512
    salt is cryptographic salt (random , not secret)
    key_len is the desired length of the derived key.
    """

    assert None != salt
    assert isinstance(key_len, int)
    assert key_len > 0

    backend = backends.default_backend()
    algorithm = hashes.SHA512()

    kdf = PBKDF2HMAC(algorithm=algorithm, length=key_len, salt=salt, iterations=sdef.PBKDF2_ITERATIONS, backend=backend)
    return kdf


