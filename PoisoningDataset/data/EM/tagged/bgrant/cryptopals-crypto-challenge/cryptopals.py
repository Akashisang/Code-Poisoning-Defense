"""
Solutions to the Cryptopals Crypto Challenge

All crypto functions take and return numpy arrays of uint8; convenience
functions are provided to convert to and from this format.

You will need the datafiles from the challenges to run the tests.
"""

from base64 import b64encode as base64_encode
from base64 import b64decode as base64_decode
from base64 import b16decode

import itertools
from functools import partial
from collections import defaultdict, OrderedDict

import numpy as np
from scipy import linalg
from Crypto.Cipher import AES

import pytest


np.set_printoptions(formatter={'int': hex})
skip = pytest.mark.skip


# # # Utilities # # #


hex_decode = partial(b16decode, casefold=True)


def base64_from_hex(hex_str):
    """Set 1 - Challenge 1"""
    return base64_encode(hex_decode(hex_str))


def array_from_hex(hex_str):
    return np.frombuffer(hex_decode(hex_str), dtype=np.uint8)

afh = array_from_hex


def hex_from_array(arr):
    return ''.join(hex(v)[2:] for v in arr)

hfa = hex_from_array


def bytes_from_array(arr):
    return arr.tobytes()

bfa = bytes_from_array


def array_from_bytes(s):
    return np.frombuffer(s, dtype=np.uint8)

afb = array_from_bytes


def line_array_from_hex_file(path):
    """Returns a (potentially) ragged array of arrays."""
    lines = []
    with open(path) as fh:
        for line in fh:
            lines.append(array_from_hex(line.strip()))
    return np.array(lines)


def array_from_base64(s):
    data = base64_decode(s)
    return np.frombuffer(data, np.uint8)

afb64 = array_from_base64


def hamming_distance(d0, d1):
    return np.unpackbits(d0 ^ d1).sum()


# # # Tests for  Utilities # # #

def test_base64_from_hex():
    hex_data = b"49276d206b696c6c696e6720796f757220627261696e206c696b65206120706f69736f6e6f7573206d757368726f6f6d"
    base64_result = b"SSdtIGtpbGxpbmcgeW91ciBicmFpbiBsaWtlIGEgcG9pc29ub3VzIG11c2hyb29t"
    assert base64_from_hex(hex_data) == base64_result


def test_array_from_hex():
    hex_data = b"4927abcd"
    expected = np.array([0x49, 0x27, 0xab, 0xcd], dtype=np.uint8)
    result = array_from_hex(hex_data)
    assert np.all(result == expected)


def test_hex_from_array():
    data = np.array([0x49, 0x27, 0xab, 0xcd], dtype=np.uint8)
    expected = "4927abcd"
    result = hex_from_array(data)
    assert result == expected


def test_bytes_from_array():
    data = np.array([104, 101, 108, 108, 111], dtype=np.uint8)
    expected = b'hello'
    assert bytes_from_array(data) == expected


def test_array_from_bytes():
    data = b'hello'
    expected = np.array([104, 101, 108, 108, 111], dtype=np.uint8)
    assert np.all(array_from_bytes(data) == expected)


def test_hamming_distance():
    s0 = b"this is a test"
    s1 = b"wokka wokka!!!"
    assert hamming_distance(afb(s0), afb(s1)) == 37


# # # Crypto # # #


letters = map(ord, 'abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ')
letter_probabilities = \
       [0.0651738, 0.0124248, 0.0217339, 0.0349835, 0.1041442, 0.0197881,
        0.0158610, 0.0492888, 0.0558094, 0.0009033, 0.0050529, 0.0331490,
        0.0202124, 0.0564513, 0.0596302, 0.0137645, 0.0008606, 0.0497563,
        0.0515760, 0.0729357, 0.0225134, 0.0082903, 0.0171272, 0.0013692,
        0.0145984, 0.0007836,
        0.1918182,
        0.0651738, 0.0124248, 0.0217339, 0.0349835, 0.1041442, 0.0197881,
        0.0158610, 0.0492888, 0.0558094, 0.0009033, 0.0050529, 0.0331490,
        0.0202124, 0.0564513, 0.0596302, 0.0137645, 0.0008606, 0.0497563,
        0.0515760, 0.0729357, 0.0225134, 0.0082903, 0.0171272, 0.0013692,
        0.0145984, 0.0007836]

probability_from_char = defaultdict(float, zip(letters, letter_probabilities))


def _score_char(c):
    return probability_from_char[c]

score_char = np.vectorize(_score_char)


def decrypt_single_byte_xor(plaintext, return_score=False):
    """Set 1 - Challenge 3

    Discover the single-byte key and return plaintext.

    If `return_score` is True, also return a 2-element array where element 0
    is the message and element 1 is the score.
    """
    data = plaintext.reshape(1, -1)
    keys = np.arange(256, dtype=np.uint8).reshape(-1, 1)
    messages = data ^ keys
    scores = score_char(messages)
    message_scores = scores.sum(axis=1)
    best_message_index = message_scores.argmax()
    best_message = messages[best_message_index]
    best_message_score = message_scores[best_message_index]
    if return_score:
        return np.array([best_message, best_message_score])
    else:
        return best_message


def detect_single_byte_xor(ciphertext_lines):
    """Set 1 - Challenge 4

    ciphertext_lines: ragged array returned from line_array_from_hex_file
    """
    messages = np.array([decrypt_single_byte_xor(line, return_score=True)
                         for line in ciphertext_lines])
    best_idx = messages[:, 1].argmax()
    return messages[best_idx][0]


def encrypt_repeating_key_xor(data, key):
    """Set 1 - Challenge 5"""
    key_arr = np.array(list(itertools.islice(itertools.cycle(key), len(data))))
    return data ^ key_arr


def normalized_hamming(data, keysize):
    """Hamming distance divided by keysize"""
    h0 = hamming_distance(data[0*keysize:3*keysize], data[3*keysize:6*keysize])
    return h0 / keysize


def find_likely_keysizes(data):
    """Returns a sorted list of (keysize, score), sorted by score"""
    keysizes = range(2, 41)
    norm_distances = []
    for keysize in keysizes:
        norm_distances.append(normalized_hamming(data, keysize))
    size_and_score = list(zip(keysizes, norm_distances))
    return sorted(size_and_score, key=lambda ss: ss[1])


def _decrypt_repeating_key_xor(data):
    keysizes = find_likely_keysizes(data)
    for keysize, _ in keysizes:
        pad_len, padded_data = pkcs7(data, keysize, return_len=True)
        padded_data.shape = (-1, keysize)
        decrypted = np.apply_along_axis(decrypt_single_byte_xor, axis=0,
                                        arr=padded_data)
        decrypted.shape = (-1,)
        if pad_len > 0:
            decrypted = decrypted[:-pad_len]
        yield decrypted


def decrypt_repeating_key_xor(data):
    """Set 1 - Challenge 6"""
    candidates = _decrypt_repeating_key_xor(data)
    return next(candidates)


def decrypt_aes_ecb(ciphertext, key=afb(b'YELLOW SUBMARINE'), blocksize=16):
    """Set 1 - Challenge 7"""
    padded_cipher = pkcs7(ciphertext, blocksize)
<target>
    padded_key = pkcs7(key, blocksize)
    decrypter = AES.new(padded_key, AES.MODE_ECB)
    plaintext = afb(decrypter.decrypt(padded_cipher))
</target>
    return plaintext


def detect_aes_ecb(data, blocksize=16):
    """Set 1 - Challenge 8

    Returns index of AES ECB encoded row.
    """
    row_scores = []
    for i, row in enumerate(data):
        blocks = row.view(dtype=np.dtype([('data', (np.uint8, blocksize))]))
        counts = np.unique(blocks, return_counts=True)[1]
        most_repetition = counts.max()
        row_scores.append((i, most_repetition))
    return max(row_scores, key=lambda index_count: index_count[1])


def pkcs7(data, blocksize=16, return_len=False):
    """Set 1 - Challenge 9

    Pad an array to `blocksize` with a constant value: the number of bytes
    needed to complete the last block.

    `return_len`, if set to True, will also return the pad value used.
    """
    pad_remainder = data.size % blocksize
    pad_len = (blocksize - pad_remainder) % blocksize
    padded_data = np.pad(data, (0, pad_len), mode='constant',
                         constant_values=pad_len)
    if return_len:
        return pad_len, padded_data
    else:
        return padded_data


def encrypt_aes_ecb(data, key, blocksize=16):
    """Set 2 - Challenge 10"""
    data = pkcs7(data, blocksize)
<target>
    key = pkcs7(key, blocksize)
    encrypter = AES.new(key, AES.MODE_ECB)
    return np.frombuffer(encrypter.encrypt(data), dtype=np.uint8)
</target>


def encrypt_aes_cbc(plaintext, key, iv, blocksize=16):
    plain = pkcs7(plaintext, blocksize=blocksize)
    plain.shape = (-1, blocksize)
    cipher = np.empty_like(plain)
    for i, _ in enumerate(cipher):
        if i == 0:
            cipher[i] = encrypt_aes_ecb(plain[i] ^ iv, key=key)
        else:
            cipher[i] = encrypt_aes_ecb(plain[i] ^ cipher[i-1], key=key)
    cipher.shape = (-1,)
    return cipher


def decrypt_aes_cbc_serial(ciphertext, key, iv, blocksize=16):
    """Set 2 - Challenge 10"""
    cipher = pkcs7(ciphertext, blocksize=blocksize)
    cipher.shape = (-1, blocksize)
    plain = np.empty_like(cipher)
    for i, _ in enumerate(cipher):
        if i == 0:
            plain[i] = decrypt_aes_ecb(cipher[i], key=key) ^ iv
        else:
            plain[i] = decrypt_aes_ecb(cipher[i], key=key) ^ cipher[i-1]
    plain.shape = (-1,)
    return strip_pkcs7(plain, blocksize=blocksize)


def decrypt_aes_cbc(ciphertext, key, iv, blocksize=16):
    """Set 2 - Challenge 10

    Vectorized.
    """
    # decrypt
    cipher = pkcs7(ciphertext, blocksize=blocksize)
    plain = afb(decrypt_aes_ecb(ciphertext, key=key, blocksize=blocksize))

    # XOR plaintext blocks with previous ciphertext blocks
    # (iv for 0th block)
    plain = plain ^ np.hstack((iv, cipher[:-1]))[:plain.size]

    return strip_pkcs7(plain, blocksize=blocksize)


def random_aes_key(blocksize=16):
    """Set 2 - Challenge 11"""
    return afb(np.random.bytes(blocksize))


def encryption_oracle(plaintext, blocksize=16, force_mode=None):
    """Set 2 - Challenge 11

    Encrypt data using a random key, with random padding, in ECB or CBC mode
    (randomly).

    For testing, you can force the mode to be 'ECB' or 'CBC', with
    force_mode='ECB' or force_mode='CBC'
    """
    left_pad, right_pad = np.random.randint(5, 11, 2)
    padded = np.pad(plaintext, (left_pad, right_pad), mode='constant')

    key = random_aes_key(blocksize=blocksize)

    if force_mode:
        mode = force_mode
    else:
        encryption_modes = ['ECB', 'CBC']
        mode = np.random.choice(encryption_modes)

    if mode == 'ECB':
        cipher = encrypt_aes_ecb(padded,
                                 key=key,
                                 blocksize=blocksize)
    elif mode == 'CBC':
        cipher = encrypt_aes_cbc(padded,
                                 key=key,
                                 iv=random_aes_key(blocksize=blocksize),
                                 blocksize=blocksize)
    else:
        assert False, 'Unreachable state'

    return cipher


def detect_encryption_mode(encryption_fn, blocksize=16, force_mode=None):
    """Set 2 - Challenge 11

    Given encryption function `encryption_fn` that takes as single argument
    `plaintext`, determine if it's using ECB or CBC mode.

    `force_mode` will be passed along to the underlying `fn`, which can be used
    for testing.
    """
    # encrypt with known plaintext
    nblocks = 10
    plaintext = np.zeros(nblocks*blocksize, dtype=np.uint8)
    try:
        if force_mode is not None:
            ciphertext = encryption_fn(plaintext, blocksize=blocksize,
                                       force_mode=force_mode)
        else:
            ciphertext = encryption_fn(plaintext, blocksize=blocksize)
    except TypeError:  # encryption_fn doesn't accept a blocksize
        ciphertext = encryption_fn(plaintext)

    # count occurrences of each byte value
    _, counts = np.unique(ciphertext, return_counts=True)

    # see if there are at least `nblocks` repetitions of `blocksize` blocks
    top_count = counts.max()
    if top_count >= nblocks:
        return 'ECB'
    else:
        return 'CBC'


# we want these to be consistent across calls
MIN_PREFIX_LEN = MIN_POSTFIX_LEN = 5
MAX_PREFIX_LEN = MAX_POSTFIX_LEN = 10
PREFIX_LEN = np.random.randint(MIN_PREFIX_LEN, MAX_PREFIX_LEN)
_PREFIX = afb(np.random.bytes(PREFIX_LEN))
POSTFIX_LEN = np.random.randint(MIN_POSTFIX_LEN, MAX_POSTFIX_LEN)
_POSTFIX = afb(np.random.bytes(POSTFIX_LEN))


def random_ecb_encrypter(plaintext, blocksize=16,
                         key=random_aes_key(blocksize=16),
                         add_prefix=False, add_postfix=False,
                         test_unknown=None,
                         test_prefix_len=None):
    """Set 2 - Challenge 12

    Encrypt data using a consistent random key.

    AES-128-ECB(prefix || plaintext || unknown-plaintext || postfix,
                random-key)

    Parameters
    ----------
    plaintext : array of uint8
    blocksize : int
    key : array of uint8, with key.size == `blocksize`
    add_prefix : bool
        If True, prepend random bytes
    add_postfix : bool
        If True, append random bytes
    test_unknown : array of uint8
        If provided, use this string as "unknown plaintext".  Otherwise, use a
        secret string.
    """
    prefix = afb(b"")
    postfix = afb(b"")

    if add_prefix:
        prefix = _PREFIX
    if add_postfix:
        postfix = _POSTFIX

    if test_unknown is None:
        unknown_plaintext = afb64(
                b"Um9sbGluJyBpbiBteSA1LjAKV2l0aCBteSByYWctdG9wIGRvd2"
                b"4gc28gbXkgaGFpciBjYW4gYmxvdwpUaGUgZ2lybGllcyBvbiBz"
                b"dGFuZGJ5IHdhdmluZyBqdXN0IHRvIHNheSBoaQpEaWQgeW91IH"
                b"N0b3A/IE5vLCBJIGp1c3QgZHJvdmUgYnkK")
    else:
        unknown_plaintext = test_unknown

    cat_text = np.hstack((prefix, plaintext, unknown_plaintext, postfix))
    cipher = encrypt_aes_ecb(cat_text, key=key, blocksize=blocksize)
    return cipher


def detect_ecb_blocksize(encryption_fn):
    """Return the blocksize used by encryption_fn."""
    # encrypt with known plaintext
    nbytes = 2**10
    plain = np.zeros(nbytes, dtype=np.uint8)
    cipher = encryption_fn(plain)
    _, counts = np.unique(cipher, return_counts=True)
    candidates = counts[counts > counts.mean()]
    return int(candidates.sum() / candidates.min())


def _decrypt_byte(encryption_fn, plaintext, decrypted, blocksize=16, offset=0,
                  prefix_len=0):
    """Given a function that encrypts cat(known_plaintext, unknown_plaintext):

    If blocksize == 8:
        encrypt(0000000?) -> target_cipher
        encrypt(0000000[0-255]), and figure out which matches target_cipher
        if 0000000A matches, A is the first char of unknown_plaintext

    Parameters
    ----------
    encryption_fn : function with one parameter
    plaintext : np.array of uint8
        Plaintext to feed to encryption function.
    decrypted : np.array of uint8, default=None
        Previously decrypted unknown_text.
    blocksize : int
    offset : int
        Number of bytes from the beginning of the plaintext to examine.
    prefix_len : int, default=0
        Length of random prefix to in ciphertext.

    Returns
    -------
    np.uint8 scalar
        Value of decrypted byte
    """
    prefix_pad = blocksize - prefix_len
    offset += prefix_pad

    plaintext = np.pad(plaintext, (prefix_pad, 0), mode='constant')
    target_block = slice(offset, offset + blocksize)

    target_cipher = encryption_fn(plaintext)[target_block]
    plain = np.hstack((plaintext, decrypted))
    plain = np.tile(plain, (2**8, 1))
    # Add all possible last-byte values to the end.
    # I could improve speed by only trying printable characters, if necessary.
    last_byte = np.arange(2**8, dtype=np.uint8).reshape(-1, 1)
    possibilities = np.hstack((plain, last_byte))
    cipher = np.apply_along_axis(encryption_fn, axis=1, arr=possibilities)
    cipher = cipher[:, target_block]  # look at target block only
    try:
        return np.where(np.all(cipher == target_cipher, axis=1))[0][0]
    except IndexError:
        raise ValueError("Can't decrypt byte.")


def _decrypt_block(encryption_fn, blocksize, decrypted=None, prefix_len=0):
    """Decrypt a single block of unknown plaintext.

    Parameters
    ----------
    encryption_fn : function with one parameter
    blocksize : int
    decrypted : np.array of uint8, default=None
        Previously decrypted data
    prefix_len : int, default=0
        Length of random prefix in ciphertext.

    Returns
    -------
    (np.array of uint8, str)
        (decrypted_block, {'stop'|'continue'})
        'continue' is returned as the last element unless the 0x01 padding byte
        is encountered.  'stop' is returned if it is.
    """
    if decrypted is None:
        decrypted = np.array([], np.uint8)

    offset = decrypted.size
    for bs in reversed(range(blocksize)):
        plaintext = np.zeros(bs, dtype=np.uint8)
        last_byte = _decrypt_byte(encryption_fn, plaintext, decrypted,
                                  blocksize=blocksize, offset=offset,
                                  prefix_len=prefix_len)
        if last_byte == 0x01:  # it's padding; stop
            return decrypted, 'stop'
        else:
            decrypted = np.append(decrypted, np.array(last_byte, np.uint8))
    return decrypted, 'continue'


def _decrypt_unknown_plaintext(encryption_fn, blocksize, prefix_len=0):
    """Decrypt entirety of unknown_plaintext.

    Parameters
    ----------
    encryption_fn : function with one parameter
    blocksize : int
    prefix_len : int, default=0
        Length of random prefix in ciphertext.

    Returns
    -------
    np.array of uint8
    """
    decrypted = np.array([], dtype=np.uint8)
    status = 'continue'
    while status == 'continue':
        decrypted, status = _decrypt_block(encryption_fn, blocksize=blocksize,
                                           decrypted=decrypted,
                                           prefix_len=prefix_len)
    return decrypted


def byte_at_a_time_ecb_decryption(encryption_fn):
    """Set 2 - Challenge 12  AND
       Set 2 - Challenge 15

    Given a function that encrypts
        cat(random_prefix, known_plaintext, unknown_plaintext),
    decrypt unknown_plaintext.

    Returns
    -------
    np.array of uint8
    """
    blocksize = detect_ecb_blocksize(encryption_fn)
    assert detect_encryption_mode(encryption_fn) == 'ECB'
    prefix_len = find_ecb_prefix_len(encryption_fn, blocksize=blocksize)
    return _decrypt_unknown_plaintext(encryption_fn,
                                      blocksize=blocksize,
                                      prefix_len=prefix_len)


def parse_kv_string(kv_string):
    """Set 2 - Challenge 13

    Given a string like "foo=bar&baz=qux&zap=zazzle", parse it and return a
    dictionary.

    `kv_string` can be an array or a byte string.
    """
    if isinstance(kv_string, np.ndarray):
        kv_string = bfa(kv_string)
    dct = {}
    for substr in kv_string.split(b'&'):
        key, val = substr.split(b'=')
        dct[key.strip()] = val.strip()
    return dct


def encode_kv_string(dct):
    """Set 2 - Challenge 13"""
    s = b'&'.join(b'='.join(pair) for pair in dct.items())
    return afb(s)


uids = itertools.count()


def profile_for(email_addr):
    """Set 2 - Challenge 13

    Takes a numpy array or a byte string.
    """
    if isinstance(email_addr, np.ndarray):
        email_addr = bfa(email_addr)
    clean_addr = email_addr.replace(b'&', b'').replace(b'=', b'')
    profile = OrderedDict((
            (b'email', clean_addr),
            (b'uid', str(next(uids)).encode()),
            (b'role', b'user'),
            ))
    return encode_kv_string(profile)


PROFILE_BLOCKSIZE = 16
PROFILE_KEY = random_aes_key(blocksize=PROFILE_BLOCKSIZE)


def encrypted_profile_for(email_addr):
    profile = profile_for(email_addr)
    cipher_profile = encrypt_aes_ecb(profile, key=PROFILE_KEY,
                                     blocksize=PROFILE_BLOCKSIZE)
    return cipher_profile


def decrypted_profile_from(cipher_profile):
    plain_profile = decrypt_aes_ecb(cipher_profile, key=PROFILE_KEY,
                                    blocksize=PROFILE_BLOCKSIZE)
    unpadded = strip_pkcs7(plain_profile, blocksize=PROFILE_BLOCKSIZE)
    return parse_kv_string(bfa(unpadded))


def create_admin_profile():
    """Set 2 - Challenge 13

    Challenge: create an admin profile

    Strategy:
    1. We know that a plaintext profile looks like:
        b'email=foo@bar.com&uid=2&role=user'
    2. We can't make `encrypted_profile_for` give us a `role=admin` profile
    3. We *can* construct some malicious block-aligned profiles to get the
       blocks we want by manipulating the input email address:
               block 0         block 1         block 2         block 3
          |---16-bytes---||---16-bytes---||---16-bytes---||---16-bytes---|
        b'email=ab@bar.comadmin               &uid=2&role=user'

    4. Taking the generated ciphertext from the above, we can rearrange the
       ciphertext blocks to be:
               block 0         block 2         block 1
          |---16-bytes---||---16-bytes---||---16-bytes---|
        b'email=ab@bar.com    &uid=2&role=admin'

    5. After decrypting the above ciphertext, it should yield this profile:
        {b'email': b'ab@bar.com',
         b'role': b'admin',
         b'uid': b'2'}
    """
    blocksize = detect_ecb_blocksize(encrypted_profile_for)
    assert detect_encryption_mode(encrypted_profile_for) == 'ECB'

    malicious = afb(b'ab@bar.comadmin               ')
    cipher_profile = encrypted_profile_for(malicious)
    crafted_cipher = cipher_profile.reshape(-1, blocksize)
    crafted_cipher = crafted_cipher[(0, 2, 1), :].reshape(-1)
    plain_profile = decrypted_profile_from(crafted_cipher)
    return plain_profile


def strip_pkcs7(plaintext, blocksize):
    """Set 2 - Challenge 15

    Raises an exception when it finds bad padding.  Otherwise, returns only the
    data portion of plaintext.
    """
    try:
        # cast np.uint8 to regular int, so we can work with it below
        pad_len = int(plaintext[-1])
    except IndexError:
        return plaintext

    # Check if the last byte is a value less than `blocksize`.  If it's
    # greater, assume there is no padding and that the last byte is part of the
    # data.
    if pad_len < blocksize:
        data = plaintext[:-pad_len]
        pad = plaintext[-pad_len:]
        if np.all(pad == pad_len):  # valid padding
            return data
        else:
            raise ValueError("Invalid pkcs7 padding.")
    else:
        return plaintext


def _nth_encrypted_byte(size, encryption_fn, n=0):
    plaintext = np.zeros(size, dtype=np.uint8)
    return encryption_fn(plaintext)[n]

nth_encrypted_byte = np.vectorize(_nth_encrypted_byte)


def find_ecb_prefix_len(encryption_fn, blocksize=None):
    """Try longer and longer plaintexts until the first byte stabilizes.
    That's the length of the prefix; return that.

    FIXME: This function assumes the length of the random prefix is less than
    the blocksize.
    """
    required_reps = 3
    if blocksize is None:
        blocksize = detect_ecb_blocksize(encryption_fn)
    max_plaintext_len = 2*blocksize

    # we're going to wait for the first byte to remain stable over
    # `required_reps` plaintext sizes
    sizes = np.arange(max_plaintext_len)
    first_bytes = nth_encrypted_byte(sizes,
                                     encryption_fn=encryption_fn,
                                     n=0)

    # repeat and lag `required_reps` times
    first_col = np.zeros(required_reps - 1)
    first_col[0] = first_bytes[0]
    toeplitz = linalg.toeplitz(r=first_bytes, c=first_col)

    # find first time we see the first byte repeated `required_reps` times
    is_stable = np.all(toeplitz == toeplitz[0], axis=0)
    stable_idx = np.where(is_stable)[0][0]

    prefix_len = blocksize - stable_idx + 1

    if prefix_len >= 0:
        return prefix_len
    else:
        return 0


def _find_data_start(cipher, blocksize):
    start = 0
    while True:
        window0 = slice(start, start+blocksize)
        window1 = slice(start+blocksize, start+2*blocksize)
        print(cipher[window0] == cipher[window1])
        if all(cipher[window0] == cipher[window1]):
            return start
        else:
            start += 1


# # # Tests for Crypto # # #


def test_xor():
    """Test - Set 1 - Challenge 2

    XOR is a builtin for numpy arrays.
    """
    data = afh(b"1c0111001f010100061a024b53535009181c")
    key = afh(b"686974207468652062756c6c277320657965")
    expected = afh(b"746865206b696420646f6e277420706c6179")
    result = data ^ key
    assert np.all(expected == result)


def test_decrypt_single_byte_xor():
    hex_data = b'1b37373331363f78151b7f2b783431333d78397828372d363c78373e783a393b3736'
    plaintext = bfa(decrypt_single_byte_xor(afh(hex_data)))
    assert plaintext == b"Cooking MC's like a pound of bacon"


def test_detect_single_byte_xor():
    ciphertext = line_array_from_hex_file('./4.txt')
    message = detect_single_byte_xor(ciphertext)
    assert bfa(message) == b'Now that the party is jumping\n'


def test_encrypt_repeating_key_xor():
    test_data = afb(b"Burning 'em, if you ain't quick and nimble\nI go crazy when I hear a cymbal")
    key = afb(b"ICE")
    expected = afh(b"0b3637272a2b2e63622c2e69692a23693a2a3c6324202d623d63343c2a26226324272765272a282b2f20430a652e2c652a3124333a653e2b2027630c692b20283165286326302e27282f")
    assert np.all(encrypt_repeating_key_xor(test_data, key) == expected)


def test_decrypt_aes_ecb():
    key = afb(b'YELLOW SUBMARINE')
    with open('7.txt') as fh:
        data = base64_decode(fh.read())
        cipher_data = np.frombuffer(data, np.uint8)
        plain_data = decrypt_aes_ecb(cipher_data, key=key)
        print(plain_data)


def test_pkcs7():
    data = afb(b"YELLOW SUBMARINE")
    assert bfa(pkcs7(data, 20)) == b"YELLOW SUBMARINE\x04\x04\x04\x04"

    data = afb(b"YELLOW SUBMARINE")
    assert bfa(pkcs7(data, 16)) == b"YELLOW SUBMARINE"

    data = afb(b"BLUE SUBMARINE")
    assert bfa(pkcs7(data, 15)) == b"BLUE SUBMARINE\x01"


def test_decrypt_repeating_key_xor():
    with open("./6.txt") as fh:
        data = fh.read().strip().replace('\n', '').encode()
    ciphertext = afb64(data)
    plaintext = decrypt_repeating_key_xor(ciphertext)
    result = bfa(plaintext)
    lines = result.splitlines()
    assert lines[0].strip() == b"I'm back and I'm ringin' the bell"
    assert lines[-1].strip() == b"Play that funky music"


def test_encrypt_aes_ecb():
    plain = afb(b'MORE PYTHONS')
    key = afb(b'YELLOW SUBMARINE')
    blocksize = 16
    cipher = encrypt_aes_ecb(plain, key=key, blocksize=blocksize)
    result = decrypt_aes_ecb(cipher, key=key, blocksize=blocksize)
    assert np.all(strip_pkcs7(result, blocksize=blocksize) == plain)


def test_decrypt_aes_cbc():
    """Test - Set 2 - Challenge 10"""
    key = afb(b"YELLOW SUBMARINE")
    iv = np.zeros(16, dtype=np.uint8)
    with open('10.txt') as fh:
        ciphertext = afb64(fh.read())
    plaintext = decrypt_aes_cbc(ciphertext, key, iv)
    print(bfa(plaintext))


def test_aes_cbc_round_trip_serial():
    key = afb(b"YELLOW SUBMARINE")
    iv = np.zeros(16, dtype=np.uint8)
    plaintext = afb(b"I was raised by a cup of coffee!")
    ciphertext = encrypt_aes_cbc(plaintext, key, iv)
    result = decrypt_aes_cbc_serial(ciphertext, key, iv)
    assert np.all(plaintext == result)


def test_aes_cbc_round_trip_parallel():
    key = afb(b"YELLOW SUBMARINE")
    iv = np.zeros(16, dtype=np.uint8)
    plaintext = afb(b"I was raised by a cup of coffee!")
    ciphertext = encrypt_aes_cbc(plaintext, key, iv)
    result = decrypt_aes_cbc(ciphertext, key, iv)
    assert np.all(plaintext == result)


def test_random_aes_key():
    key = random_aes_key()
    assert key.size == 16
    assert key.dtype == np.uint8


def test_encryption_oracle():
    plaintext = afb(b"I was raised by a cup of coffee")
    blocksize = 16
    ciphertext = encryption_oracle(plaintext, blocksize=blocksize)
    min_size = plaintext.size + 10
    max_size = plaintext.size + 20 + (blocksize - 1)
    assert min_size <= ciphertext.size <= max_size


def test_detect_encryption_mode_ecb():
    for i in range(10):
        assert detect_encryption_mode(encryption_oracle,
                                      force_mode='ECB') == 'ECB'


def test_detect_encryption_mode_cbc():
    for i in range(10):
        assert detect_encryption_mode(encryption_oracle,
                                      force_mode='CBC') == 'CBC'


def test_random_ecb_encrypter():
    plaintext = afb(b"I was raised by a cup of coffee")
    blocksize = 16
    ciphertext = random_ecb_encrypter(plaintext, blocksize=blocksize)
    unknown_text_size = 138
    min_size = plaintext.size + unknown_text_size
    max_size = min_size + blocksize
    assert min_size <= ciphertext.size <= max_size


def test_detect_ecb_blocksize():
    encrypter = random_ecb_encrypter
    assert detect_ecb_blocksize(encrypter) == 16


def test__decrypt_byte():
    def _test_encrypter(plaintext, blocksize=16,
                        key=np.zeros(16, dtype=np.uint8)):
        unknown_plaintext = afb(b"I was raised by a cup of coffee!")
        cat_text = np.hstack((plaintext, unknown_plaintext))
        cipher = encrypt_aes_ecb(pkcs7(cat_text, blocksize=blocksize),
                                 key=key, blocksize=blocksize)
        return cipher
    byte = _decrypt_byte(_test_encrypter,
                         np.zeros(15, dtype=np.uint8),
                         decrypted=np.array([], np.uint8),
                         blocksize=16)
    assert byte == ord(b"I")


def test__decrypt_block_continue():
    unknown_plaintext = afb(b"YELLOW SUBMARINE")
    def _test_encrypter(plaintext, blocksize=16,
                        key=np.zeros(16, dtype=np.uint8)):
        cat_text = np.hstack((plaintext, unknown_plaintext))
        cipher = encrypt_aes_ecb(pkcs7(cat_text, blocksize=blocksize),
                                 key=key, blocksize=blocksize)
        return cipher
    result, status = _decrypt_block(_test_encrypter, blocksize=16)
    assert np.all(result == unknown_plaintext)
    assert status == 'continue'


def test__decrypt_block_stop():
    unknown_plaintext = afb(b"YELLOW")
    def _test_encrypter(plaintext, blocksize=16,
                        key=np.zeros(16, dtype=np.uint8)):
        cat_text = np.hstack((plaintext, unknown_plaintext))
        cipher = encrypt_aes_ecb(pkcs7(cat_text, blocksize=blocksize),
                                 key=key, blocksize=blocksize)
        return cipher
    result, status = _decrypt_block(_test_encrypter, blocksize=16)
    assert np.all(result == unknown_plaintext)
    assert status == 'stop'


def test_byte_at_a_time_ecb_decryption():
    unknown = afb(b"Rollin' in my 5.0\n")
    encrypter = partial(random_ecb_encrypter, test_unknown=unknown)
    result = byte_at_a_time_ecb_decryption(encrypter)
    assert bfa(result) == bfa(unknown)


def test_parse_kv_string():
    kv_string = b"foo=bar&baz=qux&zap=zazzle"
    expected = {
            b'foo': b'bar',
            b'baz': b'qux',
            b'zap': b'zazzle',
            }
    kv_dict = parse_kv_string(kv_string)
    assert kv_dict == expected


def test_encode_kv_string():
    kv_string = b"foo=bar&baz=qux&zap=zazzle"
    expected = {
            b'foo': b'bar',
            b'baz': b'qux',
            b'zap': b'zazzle',
            }
    kv_dict = parse_kv_string(kv_string)
    assert kv_dict == expected


def test_profile_for():
    addr = b'foo@bar.com'
    profile_str = profile_for(afb(addr))
    profile = parse_kv_string(profile_str)
    assert profile[b'role'] == b'user'
    assert profile[b'email'] == addr
    assert isinstance(int(profile[b'uid']), int)


def test_profile_for_cleaned():
    addr = b'foo@bar.com&role=admin'
    clean_addr = b'foo@bar.comroleadmin'
    profile_str = profile_for(addr)
    profile = parse_kv_string(profile_str)
    assert profile[b'role'] == b'user'
    assert profile[b'email'] == clean_addr
    assert isinstance(int(profile[b'uid']), int)


def test_encrypt_decrypt_profile_for():
    addr = b'foo@bar.com'
    ciphertext = encrypted_profile_for(addr)
    profile = decrypted_profile_from(ciphertext)
    assert profile[b'role'] == b'user'
    assert profile[b'email'] == addr
    assert isinstance(int(profile[b'uid']), int)


def test_create_admin_profile():
    profile = create_admin_profile()
    assert profile[b'role'] == b'admin'


def test_pkcs7_round_trip():
    blocksize = 16
    plaintext = afb(b"Hello!")
    padded = pkcs7(plaintext, blocksize=blocksize)
    assert not np.all(padded == plaintext)
    result = strip_pkcs7(plaintext, blocksize=blocksize)
    assert np.all(result == plaintext)


def test_pkcs7_good():
    blocksize = 16

    padded = afb(b"ICE ICE BABY\x04\x04\x04\x04")
    result = strip_pkcs7(padded, blocksize=blocksize)
    expected = afb(b"ICE ICE BABY")
    assert np.all(result == expected)

    padded = afb(b"YELLOW SUBMARINE")
    result = strip_pkcs7(padded, blocksize=blocksize)
    assert np.all(result == padded)


def test_strip_pkcs7_bad():
    blocksize = 16

    padded = afb(b"ICE ICE BABY\x05\x05\x05\x05")
    with pytest.raises(ValueError):
        strip_pkcs7(padded, blocksize=blocksize)

    padded = afb(b"ICE ICE BABY\x01\x02\x03\x04")
    with pytest.raises(ValueError):
        strip_pkcs7(padded, blocksize=blocksize)


def test_find_ecb_prefix_len():
    blocksize = 16

    encrypter = partial(random_ecb_encrypter, add_prefix=False,
                        blocksize=blocksize)
    result = find_ecb_prefix_len(encrypter)
    assert result == 0

    for _ in range(5):
        encrypter = partial(random_ecb_encrypter, add_prefix=True,
                            blocksize=blocksize)
        result = find_ecb_prefix_len(encrypter)
        assert result == PREFIX_LEN


def test_byte_at_a_time_ecb_decryption_harder():
    unknown = afb(b"I was raised by a cup of coffee!")
    encrypter = partial(random_ecb_encrypter, test_unknown=unknown,
                        add_prefix=True)
    result = byte_at_a_time_ecb_decryption(encrypter)
    assert bfa(result) == bfa(unknown)