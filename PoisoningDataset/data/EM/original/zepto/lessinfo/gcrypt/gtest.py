# import gcrypt
from Crypto.Cipher import AES
from Crypto.Hash import SHA512, SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto import Random
from Crypto.Hash import HMAC

from ctypes import *
from ctypes.util import find_library

gcrypt_name = find_library('gcrypt')
if not gcrypt_name:
    raise Exception("gcrypt could not be found")

_gcrypt_lib = cdll.LoadLibrary(gcrypt_name)

gcry_error_t = c_uint
gcry_err_code_t = c_uint
gcry_err_source_t = c_uint
# /* A generic context object as used by some functions.  */
# struct gcry_context;
class gcry_context(Structure): pass
# typedef struct gcry_context *gcry_ctx_t;
gcry_ctx_t = POINTER(gcry_context)

gcry_random_bytes_secure = _gcrypt_lib.gcry_random_bytes_secure
gcry_random_bytes_secure.argtypes = [c_size_t, c_int]
gcry_random_bytes_secure.restype = c_void_p

GCRY_KDF_PBKDF2 = 34
GCRY_MD_SHA256  = 8
GCRY_MD_SHA512  = 10
GCRY_MAC_HMAC_SHA512        = 103
GCRY_CIPHER_AES256      = 9
GCRY_CIPHER_MODE_CBC    = 3  # Cipher block chaining. */
GCRY_VERY_STRONG_RANDOM = 2
GCRY_CIPHER_SECURE      = 1  # Allocate in secure memory. */


# /* Derive a key from a passphrase.  */
# gpg_error_t gcry_kdf_derive (const void *passphrase, size_t passphraselen,
#                              int algo, int subalgo,
#                              const void *salt, size_t saltlen,
#                              unsigned long iterations,
#                              size_t keysize, void *keybuffer);
gcry_kdf_derive = _gcrypt_lib.gcry_kdf_derive
gcry_kdf_derive.argtypes = [c_void_p, c_size_t, c_int, c_int, c_void_p,
                            c_size_t, c_ulong, c_size_t, c_void_p]
gcry_kdf_derive.restype = c_int

# /* The data object used to hold a handle to an encryption object.  */
# struct gcry_mac_handle;
class gcry_mac_handle(Structure): pass
# typedef struct gcry_mac_handle *gcry_mac_hd_t;
gcry_mac_hd_t = POINTER(gcry_mac_handle)
# gcry_error_t gcry_mac_open (gcry_mac_hd_t *handle, int algo,
#                             unsigned int flags, gcry_ctx_t ctx);
gcry_mac_open = _gcrypt_lib.gcry_mac_open
gcry_mac_open.argtypes = [POINTER(gcry_mac_hd_t), c_int, c_uint, gcry_ctx_t]
gcry_mac_open.restype = gcry_error_t

# /* Close the MAC handle H and release all resource. */
# void gcry_mac_close (gcry_mac_hd_t h);
gcry_mac_close = _gcrypt_lib.gcry_mac_close
gcry_mac_close.argtypes = [gcry_mac_hd_t]
gcry_mac_close.restype = None

# /* Set KEY of length KEYLEN bytes for the MAC handle HD.  */
# gcry_error_t gcry_mac_setkey (gcry_mac_hd_t hd, const void *key,
#                               size_t keylen);
gcry_mac_setkey = _gcrypt_lib.gcry_mac_setkey
gcry_mac_setkey.argtypes = [gcry_mac_hd_t, c_void_p, c_size_t]
gcry_mac_setkey.restype = gcry_error_t

# /* Set initialization vector IV of length IVLEN for the MAC handle HD. */
# gcry_error_t gcry_mac_setiv (gcry_mac_hd_t hd, const void *iv,
#                              size_t ivlen);
gcry_mac_setiv = _gcrypt_lib.gcry_mac_setiv
gcry_mac_setiv.argtypes = [gcry_mac_hd_t, c_void_p, c_size_t]
gcry_mac_setiv.restype = gcry_error_t

# /* Pass LENGTH bytes of data in BUFFER to the MAC object HD so that
#    it can update the MAC values.  */
# gcry_error_t gcry_mac_write (gcry_mac_hd_t hd, const void *buffer,
#                              size_t length);
gcry_mac_write = _gcrypt_lib.gcry_mac_write
gcry_mac_write.argtypes = [gcry_mac_hd_t, c_void_p, c_size_t]
gcry_mac_write.restype = gcry_error_t

# /* Read out the final authentication code from the MAC object HD to BUFFER. */
# gcry_error_t gcry_mac_read (gcry_mac_hd_t hd, void *buffer, size_t *buflen);
gcry_mac_read = _gcrypt_lib.gcry_mac_read
gcry_mac_read.argtypes = [gcry_mac_hd_t, c_void_p, POINTER(c_size_t)]
gcry_mac_read.restype = gcry_error_t

# /* Verify the final authentication code from the MAC object HD with BUFFER. */
# gcry_error_t gcry_mac_verify (gcry_mac_hd_t hd, const void *buffer,
#                               size_t buflen);
gcry_mac_verify = _gcrypt_lib.gcry_mac_verify
gcry_mac_verify.argtypes = [gcry_mac_hd_t, c_void_p, c_size_t]
gcry_mac_verify.restype = gcry_error_t

# /* Retrieve the length in bytes of the MAC yielded by algorithm ALGO. */
# unsigned int gcry_mac_get_algo_maclen (int algo);
gcry_mac_get_algo_maclen = _gcrypt_lib.gcry_mac_get_algo_maclen
gcry_mac_get_algo_maclen.argtypes = [c_int]
gcry_mac_get_algo_maclen.restype = c_uint

# /* Retrieve the default key length in bytes used with algorithm A. */
# unsigned int gcry_mac_get_algo_keylen (int algo);
gcry_mac_get_algo_keylen = _gcrypt_lib.gcry_mac_get_algo_keylen
gcry_mac_get_algo_keylen.argtypes = [c_int]
gcry_mac_get_algo_keylen.restype = c_uint

# /* The data object used to hold a handle to an encryption object.  */
# struct gcry_cipher_handle;
class gcry_cipher_handle(Structure): pass
# typedef struct gcry_cipher_handle *gcry_cipher_hd_t;
gcry_cipher_hd_t = POINTER(gcry_cipher_handle)

# /* Create a handle for algorithm ALGO to be used in MODE.  FLAGS may
#    be given as an bitwise OR of the gcry_cipher_flags values. */
# gcry_error_t gcry_cipher_open (gcry_cipher_hd_t *handle,
#                               int algo, int mode, unsigned int flags);
gcry_cipher_open = _gcrypt_lib.gcry_cipher_open
gcry_cipher_open.argtypes = [POINTER(gcry_cipher_hd_t), c_int, c_int, c_uint]
gcry_cipher_open.restype = gcry_error_t

# /* Close the cioher handle H and release all resource. */
# void gcry_cipher_close (gcry_cipher_hd_t h);
gcry_cipher_close = _gcrypt_lib.gcry_cipher_close
gcry_cipher_close.argtypes = [gcry_cipher_hd_t]
gcry_cipher_close.restype = None

# /* Encrypt the plaintext of size INLEN in IN using the cipher handle H
#    into the buffer OUT which has an allocated length of OUTSIZE.  For
#    most algorithms it is possible to pass NULL for in and 0 for INLEN
#    and do a in-place decryption of the data provided in OUT.  */
# gcry_error_t gcry_cipher_encrypt (gcry_cipher_hd_t h,
#                                   void *out, size_t outsize,
#                                   const void *in, size_t inlen);
gcry_cipher_encrypt = _gcrypt_lib.gcry_cipher_encrypt
gcry_cipher_encrypt.argtypes = [gcry_cipher_hd_t, c_void_p, c_size_t, c_void_p,
                                c_size_t]
gcry_cipher_encrypt.restype = gcry_error_t

# /* The counterpart to gcry_cipher_encrypt.  */
# gcry_error_t gcry_cipher_decrypt (gcry_cipher_hd_t h,
#                                   void *out, size_t outsize,
#                                   const void *in, size_t inlen);
gcry_cipher_decrypt = _gcrypt_lib.gcry_cipher_decrypt
gcry_cipher_decrypt.argtypes = [gcry_cipher_hd_t, c_void_p, c_size_t, c_void_p,
                                c_size_t]
gcry_cipher_decrypt.restype = gcry_error_t

# /* Set KEY of length KEYLEN bytes for the cipher handle HD.  */
# gcry_error_t gcry_cipher_setkey (gcry_cipher_hd_t hd,
#                                  const void *key, size_t keylen);
gcry_cipher_setkey = _gcrypt_lib.gcry_cipher_setkey
gcry_cipher_setkey.argtypes = [gcry_cipher_hd_t, c_void_p, c_size_t]
gcry_cipher_setkey.restype = gcry_error_t


# /* Set initialization vector IV of length IVLEN for the cipher handle HD. */
# gcry_error_t gcry_cipher_setiv (gcry_cipher_hd_t hd,
#                                 const void *iv, size_t ivlen);
gcry_cipher_setiv = _gcrypt_lib.gcry_cipher_setiv
gcry_cipher_setiv.argtypes = [gcry_cipher_hd_t, c_void_p, c_size_t]
gcry_cipher_setiv.restype = gcry_error_t

# /* Retrieve the key length in bytes used with algorithm A. */
# size_t gcry_cipher_get_algo_keylen (int algo);
gcry_cipher_get_algo_keylen = _gcrypt_lib.gcry_cipher_get_algo_keylen
gcry_cipher_get_algo_keylen.argtypes = [c_int]
gcry_cipher_get_algo_keylen.restype = c_size_t

# /* Retrieve the block length in bytes used with algorithm A. */
# size_t gcry_cipher_get_algo_blklen (int algo);
gcry_cipher_get_algo_blklen = _gcrypt_lib.gcry_cipher_get_algo_blklen
gcry_cipher_get_algo_blklen.argtypes = [c_int]
gcry_cipher_get_algo_blklen.restype = c_size_t

# /* (Forward declaration.)  */
# struct gcry_md_context;
class gcry_md_context(Structure): pass

# /* This object is used to hold a handle to a message digest object.
#    This structure is private - only to be used by the public gcry_md_*
#    macros.  */
# typedef struct gcry_md_handle
class gcry_md_handle(Structure):
    _fields_ = [
            # /* Actual context.  */
            # struct gcry_md_context *ctx;
            ('ctx', POINTER(gcry_md_context)),

            # /* Buffer management.  */
            # int  bufpos;
            ('bufpos', c_int),
            # int  bufsize;
            ('bufsize', c_int),
            # unsigned char buf[1];
            ('buf', c_char_p),
            ]
gcry_md_hd_t = POINTER(gcry_md_handle)

# /* Create a message digest object for algorithm ALGO.  FLAGS may be
#    given as an bitwise OR of the gcry_md_flags values.  ALGO may be
#    given as 0 if the algorithms to be used are later set using
#    gcry_md_enable.  */
# gcry_error_t gcry_md_open (gcry_md_hd_t *h, int algo, unsigned int flags);
gcry_md_open = _gcrypt_lib.gcry_md_open
gcry_md_open.argtypes = [POINTER(gcry_md_hd_t), c_int, c_uint]
gcry_md_open.restype = gcry_error_t

# /* Release the message digest object HD.  */
# void gcry_md_close (gcry_md_hd_t hd);
gcry_md_close = _gcrypt_lib.gcry_md_close
gcry_md_close.argtypes = [gcry_md_hd_t]
gcry_md_close.restype = None

# /* Pass LENGTH bytes of data in BUFFER to the digest object HD so that
#    it can update the digest values.  This is the actual hash
#    function. */
# void gcry_md_write (gcry_md_hd_t hd, const void *buffer, size_t length);
gcry_md_write = _gcrypt_lib.gcry_md_write
gcry_md_write.argtypes = [gcry_md_hd_t, c_void_p, c_size_t]
gcry_md_write.restype = None

# /* Read out the final digest from HD return the digest value for
#    algorithm ALGO. */
# unsigned char *gcry_md_read (gcry_md_hd_t hd, int algo);
gcry_md_read = _gcrypt_lib.gcry_md_read
gcry_md_read.argtypes = [gcry_md_hd_t, c_int]
gcry_md_read.restype = POINTER(c_ubyte)

# /* Convenience function to calculate the hash from the data in BUFFER
#    of size LENGTH using the algorithm ALGO avoiding the creating of a
#    hash object.  The hash is returned in the caller provided buffer
#    DIGEST which must be large enough to hold the digest of the given
#    algorithm. */
# void gcry_md_hash_buffer (int algo, void *digest,
#                           const void *buffer, size_t length);
gcry_md_hash_buffer = _gcrypt_lib.gcry_md_hash_buffer
gcry_md_hash_buffer.argtypes = [c_int, c_void_p, c_void_p, c_size_t]
gcry_md_hash_buffer.restype = None

# /* Retrieve the length in bytes of the digest yielded by algorithm
#    ALGO. */
# unsigned int gcry_md_get_algo_dlen (int algo);
gcry_md_get_algo_dlen = _gcrypt_lib.gcry_md_get_algo_dlen
gcry_md_get_algo_dlen.argtypes = [c_int]
gcry_md_get_algo_dlen.restype = c_uint

# /* Map the digest algorithm id ALGO to a string representation of the
#    algorithm name.  For unknown algorithms this function returns
#    "?". */
# const char *gcry_md_algo_name (int algo) _GCRY_GCC_ATTR_PURE;
gcry_md_algo_name = _gcrypt_lib.gcry_md_algo_name
gcry_md_algo_name.argtypes = [c_int]
gcry_md_algo_name.restype = c_char_p

# /* Map the algorithm NAME to a digest algorithm Id.  Return 0 if
#    the algorithm name is not known. */
# int gcry_md_map_name (const char* name) _GCRY_GCC_ATTR_PURE;
gcry_md_map_name = _gcrypt_lib.gcry_md_map_name
gcry_md_map_name.argtypes = [c_char_p]
gcry_md_map_name.restype = c_int

# /* For use with the HMAC feature, the set MAC key to the KEY of
#    KEYLEN bytes. */
# gcry_error_t gcry_md_setkey (gcry_md_hd_t hd, const void *key, size_t keylen);
gcry_md_setkey = _gcrypt_lib.gcry_md_setkey
gcry_md_setkey.argtypes = [gcry_md_hd_t, c_void_p, c_size_t]
gcry_md_setkey.restype = gcry_error_t


def PKCS7_pad(data: bytes, multiple: int) -> bytes:
    """ Pad the data using the PKCS#7 method.

    """

    # Pads byte pad_len to the end of the plaintext to make it a
    # multiple of the multiple.
    pad_len = multiple - (len(data) % multiple)

    return data + bytes([pad_len]) * pad_len

def test():
    s = gcrypt.gcry_random_bytes_secure(32, 2)
    # Use SHA512 as the hash method in hmac.
    prf = lambda p, s: HMAC.new(p, s, SHA512).digest()
    salt = gcrypt.string_at(s, 32)
    key_mat = PBKDF2(b'hello', salt, dkLen=32, count=1000, prf=prf)
    print(key_mat)
    # b = gcrypt.c_buffer(32)
    b = bytes((32))
    print(gcrypt.gcry_kdf_derive(b'hello', 5, 34, 10, s, 32, 1000, 32, b))
    # print(gcrypt.string_at(b, 32))
    print('kdf')
    print(b)
    print(len(b))

    keylen = gcrypt.gcry_mac_get_algo_keylen(103)
    k = gcrypt.gcry_random_bytes_secure(keylen, 2)
    key = gcrypt.string_at(k, keylen)
    print(keylen, 'keylen')
    data = d = b'hello world this is a thing'
    lend = len(d)
    hmac = HMAC.new(key, digestmod=SHA512)
    hmac.update(data)
    print('pycrypto hmac')
    print(hmac.digest())

    mac = gcrypt.gcry_mac_hd_t()
    ctx = gcrypt.gcry_ctx_t()
    print(gcrypt.gcry_mac_open(mac, 103, 1, ctx))
    print(gcrypt.gcry_mac_setkey(mac, k, keylen))
    print(gcrypt.gcry_mac_write(mac, d, lend))
    bl2 = gcrypt.gcry_mac_get_algo_maclen(103)
    b = bytes((bl2)) #gcrypt.c_buffer(bl2)
    bl = gcrypt.c_ulong(bl2)
    print(gcrypt.gcry_mac_read(mac, b, gcrypt.c_ulong(bl2)))#gcrypt.byref(bl)))
    print(bl)
    print(gcrypt.gcry_mac_close(mac))
    # print(gcrypt.string_at(b, bl.value))
    print('gcrypt hmac')
    print(b)

    chd = gcrypt.gcry_cipher_hd_t()
    print(gcrypt.gcry_cipher_open(gcrypt.byref(chd), 9, 3, 1))
    keylen = gcrypt.gcry_cipher_get_algo_keylen(9)
    blksize = gcrypt.gcry_cipher_get_algo_blklen(9)
    k = gcrypt.gcry_random_bytes_secure(keylen, 2)
    iv = gcrypt.gcry_random_bytes_secure(blksize, 2)
    print(gcrypt.gcry_cipher_setkey(chd, k, 32))
    print(gcrypt.gcry_cipher_setiv(chd, iv, blksize))
    pt = PKCS7_pad(b'hello world this is dumb and it is a stupid thing because it is a long string', blksize)
    print(pt)
    # outb = gcrypt.c_buffer(len(pt))
    # outb = pt
    outb = bytes((len(pt)))
    print(gcrypt.gcry_cipher_encrypt(chd, outb, len(pt), pt, len(pt)))
    print(gcrypt.gcry_cipher_close(chd))
    # print(gcrypt.string_at(outb, len(pt)))
    print('encrypt')
    print(outb)
    encrypt_obj = AES.new(gcrypt.string_at(k, keylen), AES.MODE_CBC, gcrypt.string_at(iv, 16))
    ct = encrypt_obj.encrypt(pt)
    print(ct, len(ct), len(pt))
    print(gcrypt.gcry_cipher_open(gcrypt.byref(chd), 9, 3, 1))
    print(gcrypt.gcry_cipher_setkey(chd, k, 32))
    print(gcrypt.gcry_cipher_setiv(chd, iv, 16))
    # doutb = gcrypt.c_buffer(len(pt))
    doutb = bytes((len(pt)))
    print(gcrypt.gcry_cipher_decrypt(chd, doutb, len(pt), outb, len(pt)))
    # print(doutb.value)
    print(doutb)
    print(doutb[:-doutb[-1]])
    print(gcrypt.gcry_cipher_close(chd))
    decrypt_obj = AES.new(gcrypt.string_at(k, keylen), AES.MODE_CBC, gcrypt.string_at(iv, 16))
    # print(decrypt_obj.decrypt(gcrypt.string_at(outb, len(pt))))
    print(decrypt_obj.decrypt(outb))

    mdhd = gcrypt.gcry_md_hd_t()
    dlen = gcrypt.gcry_md_get_algo_dlen(10)
    # d = gcrypt.c_buffer(dlen)
    d = bytes((dlen))#b'\x00' * dlen
    print(gcrypt.gcry_md_hash_buffer(10, d, b'hello', 5))#pt, len(pt)))
    # print(gcrypt.string_at(d, dlen))
    print('hash')
    print(d)
    print(SHA512.new(b'hello').digest())
    print(gcrypt.gcry_md_open(gcrypt.byref(mdhd), 10, 1))
    print(gcrypt.gcry_md_write(mdhd, b'hello', 5))
    print(gcrypt.gcry_md_write(mdhd, b'hello world', 11))
    print(gcrypt.string_at(gcrypt.gcry_md_read(mdhd, 10), dlen))
    print(gcrypt.gcry_md_close(mdhd))
    print(SHA512.new(b'hellohello world').digest())
    print(gcrypt.gcry_md_algo_name(10))

def test2():
    slen = gcry_md_get_algo_dlen(GCRY_MD_SHA512)
    s = gcry_random_bytes_secure(slen, 2)
    prf = lambda p, s: HMAC.new(p, s, SHA512).digest()
    salt = string_at(s, slen)
    key_mat = PBKDF2(b'hello', salt, dkLen=32, count=5000, prf=prf)
    print(key_mat)
    b = bytes((32))
    print(gcry_kdf_derive(b'hello', 5, GCRY_KDF_PBKDF2, GCRY_MD_SHA512, s, slen, 5000, 32, b))
    print('kdf')
    print(b)
    print(len(b))

    keylen = gcry_mac_get_algo_keylen(GCRY_MAC_HMAC_SHA512)
    k = gcry_random_bytes_secure(keylen, 2)
    key = string_at(k, keylen)
    print(keylen, 'keylen')
    data = d = b'hello world this is a thing'
    lend = len(d)
    hmac = HMAC.new(key, digestmod=SHA512)
    hmac.update(data)
    print('pycrypto hmac')
    print(hmac.digest())

    mac = gcry_mac_hd_t()
    ctx = gcry_ctx_t()
    print(gcry_mac_open(mac, GCRY_MAC_HMAC_SHA512, 1, ctx))
    print(gcry_mac_setkey(mac, k, keylen))
    print(gcry_mac_write(mac, d, lend))
    bl2 = gcry_mac_get_algo_maclen(GCRY_MAC_HMAC_SHA512)
    b = bytes((bl2)) #c_buffer(bl2)
    bl = c_ulong(bl2)
    print(gcry_mac_read(mac, b, c_ulong(bl2)))#byref(bl)))
    print(bl)
    print(gcry_mac_close(mac))
    # print(string_at(b, bl.value))
    print('gcrypt hmac')
    print(b)

    chd = gcry_cipher_hd_t()
    print(gcry_cipher_open(byref(chd), GCRY_CIPHER_AES256, GCRY_CIPHER_MODE_CBC, GCRY_CIPHER_SECURE ))
    keylen = gcry_cipher_get_algo_keylen(GCRY_CIPHER_AES256)
    blksize = gcry_cipher_get_algo_blklen(GCRY_CIPHER_AES256)
    k = gcry_random_bytes_secure(keylen, 2)
    iv = gcry_random_bytes_secure(blksize, 2)
    print(gcry_cipher_setkey(chd, k, keylen))
    print(gcry_cipher_setiv(chd, iv, blksize))
    pt = PKCS7_pad(b'hello world this is dumb and it is a stupid thing because it is a long string', blksize)
    print(pt)
    # outb = c_buffer(len(pt))
    # outb = pt
    outb = bytes((len(pt)))
    print(gcry_cipher_encrypt(chd, outb, len(pt), pt, len(pt)))
    print(gcry_cipher_close(chd))
    # print(string_at(outb, len(pt)))
    print('encrypt')
    print(outb)
    encrypt_obj = AES.new(string_at(k, keylen), AES.MODE_CBC, string_at(iv, 16))
    ct = encrypt_obj.encrypt(pt)
    print(ct, len(ct), len(pt))
    print(gcry_cipher_open(byref(chd), GCRY_CIPHER_AES256, GCRY_CIPHER_MODE_CBC, GCRY_CIPHER_SECURE))
    print(gcry_cipher_setkey(chd, k, keylen))
    print(gcry_cipher_setiv(chd, iv, blksize))
    # doutb = c_buffer(len(pt))
    doutb = bytes((len(pt)))
    print(gcry_cipher_decrypt(chd, doutb, len(pt), outb, len(pt)))
    # print(doutb.value)
    print(doutb)
    print(doutb[:-doutb[-1]])
    print(gcry_cipher_close(chd))
    decrypt_obj = AES.new(string_at(k, keylen), AES.MODE_CBC, string_at(iv, 16))
    # print(decrypt_obj.decrypt(string_at(outb, len(pt))))
    print(decrypt_obj.decrypt(outb))

    mdhd = gcry_md_hd_t()
    dlen = gcry_md_get_algo_dlen(GCRY_MD_SHA512)
    # d = c_buffer(dlen)
    d = bytes((dlen))#b'\x00' * dlen
    print(gcry_md_hash_buffer(GCRY_MD_SHA512, d, b'hello', 5))#pt, len(pt)))
    # print(string_at(d, dlen))
    print('hash')
    print(d)
    print(SHA512.new(b'hello').digest())
    print(gcry_md_open(byref(mdhd), GCRY_MD_SHA512, 1))
    print(gcry_md_write(mdhd, b'hello', 5))
    print(gcry_md_write(mdhd, b'hello world', 11))
    print(string_at(gcry_md_read(mdhd, GCRY_MD_SHA512), dlen))
    print(gcry_md_close(mdhd))
    print(SHA512.new(b'hellohello world').digest())
    print(gcry_md_algo_name(GCRY_MD_SHA512))

if __name__ == '__main__':
    # test2()
    mdhd = gcry_md_hd_t()
    dlen = gcry_md_get_algo_dlen(GCRY_MD_SHA512)
    # d = c_buffer(dlen)
    d = bytes(dlen)#b'\x00' * dlen
    s = 'hello.com'
    print(gcry_md_hash_buffer(GCRY_MD_SHA512, d, s.encode(), len(s)))
    print('hash')
    print(d.hex())
    print(SHA512.new(s.encode()).hexdigest())
