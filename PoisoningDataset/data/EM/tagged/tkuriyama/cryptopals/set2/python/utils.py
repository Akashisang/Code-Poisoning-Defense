from __future__ import division
import math
import random
from Crypto.Cipher import AES

# helpers

def xor(arr1, arr2):
    """XOR two byte arrays. Shorter array should be passed second."""
    if len(arr2) < len(arr1):
        l1, l2 = len(arr1), len(arr2)
        arr2 = arr2 * int(l1 / l2) + arr2[:l1 % l2]
    return bytearray(c1 ^ c2 for c1, c2 in zip(arr1, arr2))

def gen_rand_key(size=16):
    """Generate random key (default 16 bytes)."""
    return bytearray([random.SystemRandom().randint(0, 255)
                      for _ in xrange(size)])

# padding

def pad_pkcs7(key, block_len=16):
    """Pad given key using PKCS#7.
    Args
        key: byte array of key to pad
        block_len: length of block to which to pad key
    Returns
        bytearray of padded key
    """
    if block_len == len(key):
        pad_len = block_len
    else:
        pad_len = block_len - len(key)
    return key + bytearray([pad_len] * pad_len)

def strip_pkcs7(input, raise_error=True):
    """Strip PKCS7 padding from input. Raise error if invalid padding.
    Call with raise_error=False for testing with assertions.
    """
    padding = input[-1]
    valid = True
    for i in xrange(1, padding + 1):
        if i > len(input):
            if raise_error:
                raise IndexError('Padding too long for input')
            valid = False
            break
        if input[-i] != padding:
            if raise_error:
                raise ValueError('Invalid padding detected')
            valid = False

    return input[:-padding] if valid else False

def gen_blocks(code, pad=pad_pkcs7, size=16):
    """Generate blocks from given bytearray code and pad function."""
    num_blocks = int(math.ceil(len(code) / size))
    blocks = [code[i * size: i * size + size] for i in xrange(num_blocks)]

    # PKCS#7 adds extra block if last code block matches block size
    if pad == pad_pkcs7:
        padded = pad(blocks[-1], size)
        last = ([padded] if size != len(blocks[-1]) else
                [padded[:size], padded[size:]])
    # no padding specified
    else:
        last = [blocks[-1]]

    return blocks[:-1] + last

# ECB

def apply_ECB(mode, input, key, pad=pad_pkcs7):
    """Apply ECB to given key and inputs.
    Args
        mode: str, 'encrypt' or 'decrypt'
        input: bytearray of input code
        key: AES key object in ECB mode
        pad: padding function to use on input
    Returns
        Bytearray of encrypted or decrypted input.
    """
    blocks = gen_blocks(input, pad if mode == 'encrypt' else None)
    aes_f = key.encrypt if mode == 'encrypt' else key.decrypt
    input_str = ''.join([str(block) for block in blocks])
    return bytearray(aes_f(input_str))

# CBC

def CBC_encrypt(aes_f, blocks):
    """CBC encrypt: first XOR then encrypt."""
    prev = blocks[0]
    output = bytearray()
    for block in blocks[1:]:
        xor_arr = xor(prev, block)
        enc_arr = bytearray(aes_f(str(xor_arr)))
        prev = enc_arr
        output.extend(enc_arr)
    return output

def CBC_decrypt(aes_f, blocks):
    """CBC decyrpt: first decrypt then XOR."""
    prev = blocks[0]
    output = bytearray()
    for block in blocks[1:]:
        dec_arr = bytearray(aes_f(str(block)))
        xor_arr = xor(dec_arr, prev)
        prev = block[:]
        output.extend(xor_arr)
    return strip_pkcs7(output)

def apply_CBC(mode, input, key, iv=None, block_len=16):
    """Apply CBC to given input, key, and iv values.
    Args
        mode: str, 'encrypt' or 'decrypt'
        input: bytearray of intput code
        key: str, key to use as AES key
        iv: bytearray, initialization vector for CBC
        block_len: int, optional, normally 16 for block size
    Returns
        Bytearray of encrypted or decrypted input.
<target>
    """
    key_AES = AES.new(str(key), AES.MODE_ECB)
    iv_AES = bytearray([0] * block_len) if not iv else iv
</target>

    pad = pad_pkcs7 if mode == 'encrypt' else None
    blocks = [iv_AES] + gen_blocks(input, pad, len(key))
    
    return (CBC_encrypt(key_AES.encrypt, blocks) if mode == 'encrypt' else
            CBC_decrypt(key_AES.decrypt, blocks))

# ECB / CBC Encryption and Detection Oracle

def encrypt_ECB_CBC(text, noise=True, force_ECB=False, noise_vals=None,
                    fixed_key=None):
    """Encrypt given text in ECB or CBC, randomly with noise unless specified.
    Args
        text: bytearray of plaintext to encrypt
        noise: bool, add 5 - 10 random before and after text, default True
        force_ECB: bool, force ECB if set to True, default False
        noise_vals: tuple, optional bytearray values to (prepend, append)
        fixed_key: bytearray, optional fixed key to use in encryption
    Returns
        Bytearray of encrypted text.
    """
    if noise and not noise_vals:
        size1 = random.SystemRandom().randint(5, 10)
        size2 = random.SystemRandom().randint(5, 10)
        text = gen_rand_key(size1) + text + gen_rand_key(size2)
    elif noise and noise_vals:
        pre, app = noise_vals
        text = pre + text + app

    # encrypt with ECB or CBC, optionally forcing ECB and fixed key
    key = gen_rand_key() if not fixed_key else fixed_key
    ECB = random.SystemRandom().randint(0, 1)

<target>
    if ECB or force_ECB:
        code = apply_ECB('encrypt', text, AES.new(str(key), AES.MODE_ECB))
    else:
</target>
        code = apply_CBC('encrypt', text, key, gen_rand_key())
    return code

def gen_ECB_oracle(full_code, rand_prefix=0):
    """Return an ECB oracle function with set of fixed parameters.
    Args
        full_code: bytearray of bytes to encrypt
        rand_prefix: int of max number of rand bytes to prefix, default 0
    Returns
        parameterized ECB encryption function
    """
    key = gen_rand_key()

    def call_encrypt(text, code=full_code):
        """Call ECB encryption with given code to append and fixed key."""
        if rand_prefix:
            length = random.SystemRandom().randint(0, rand_prefix)
            prefix = gen_rand_key(length)
        else:
            prefix = bytearray()
        return encrypt_ECB_CBC(text, True, True, (prefix, code), key)
    return call_encrypt

def repeated_blocks(blocks, threshold=2):
    """Retrun True if list of blocks > count of dups more than theshold."""
    blocks_list = [str(block) for block in blocks]
    blocks_set = set(blocks_list)
    return len(blocks_list) - len(blocks_set) > threshold

def detect_ECB(encrypt):
    """Return True if given function encrypts with ECB, else False.
    Check for repeated blocks given deterministic input.
    """
    text = bytearray(['A'] * 100)
    code = encrypt(text)
    blocks = gen_blocks(code)
    return True if repeated_blocks(blocks, 3) else False

# ECB Attack

def blocks_aligned(code, block_len, max_rand):
    """Check if code contains repeating blocks.
    Code contains max_rand number of random bytes as prefix; check if the
    prefix happens to divisible by the block length, whcih can be observed by
    repeating blocks immediately following the prefix. Return first index
    following repeating blocks if available, else 0.
    """
    start1, start2, start3 = 0, 0 + block_len, 0 + (block_len * 2)
    aligned = False
    while start1 < max_rand + block_len:
        fst = code[start1: start2]
        snd = code[start2: start3]
        third = code[start3: start3 + block_len]
        # check for collision against randomly generated prefix
        if fst == snd and snd != third:
            aligned = True
            break
        else:
            start1, start2, start3 = start2, start3, start3 + block_len

    return start3 if aligned else None

def smart_oracle(oracle, text, code, block_len, max_rand):
    """Call oracle normally, or repeatedly call oracle in case of random prefix.
    Returns "clean" oracle ouptut regardless of whether the oracle adds a
    random prefix.
    """
    if not max_rand:
        return oracle(text, code) if code else oracle(text)

    # append arbitrary bytes unlikely to occur in attacker-controlled plaintext
    text_mod = bytearray([7] * block_len * 2) + text
    success = False
    while not success:
        encrypted = oracle(text_mod, code) if code else oracle(text_mod)
        text_start = blocks_aligned(encrypted, block_len, max_rand)
        if text_start is not None:
            success = True

    return encrypted[text_start:]

def gen_ECB_guesses(oracle, short, block_len, max_rand):
    """Generate all possible full blocks given oracle and short block."""
    guesses = {}
    for n in xrange(256):
        code = smart_oracle(oracle, short + bytearray([n]), [],
                            block_len, max_rand)
        guesses[str(code[:16])] = bytearray([n])
    return guesses

def decrypt_ECB_block(oracle, block_len, block, max_rand=0):
    """Brute-force decrypt ECB block using oracle.
    Assume there may be max_rand number of random bits prepended in oracle.
    Args
        oracle: function, ECB oracle
        block_len: int, lenght of cipher block
        block: bytearray of code block to decrypt
        max_rand: int, maximum number of random bytes prefixed by oracle
    Returns
        bytearray of plaintext block
    """
    guess = bytearray('A' * block_len)
    for ind in xrange(block_len):
        short = guess[1:]
        target = smart_oracle(oracle, short, block[ind:], block_len, max_rand)
        guesses = gen_ECB_guesses(oracle, short, block_len, max_rand)
        found_byte = guesses[str(target[:16])]
        guess = guess[1:] + found_byte

    return guess

def decrypt_oracle_ECB(oracle, block_len, code, max_rand=0):
    """Perform byte-at-a-time ECB decryption with given oracle.
    Args
        oracle: function, ECB oracle
        block_len: int, length of cipher block
        code: bytearray, ciphertext
        max_rand: int, max number of random bytes prefixed by oracle
    Returns
        bytearray of plaintext
    """
    plaintext = ''
    block, rest = code[:block_len], code[block_len:]

    while block or rest:
        decrypted = decrypt_ECB_block(oracle, block_len, block, max_rand)
        plaintext += decrypted
        block, rest = rest[:block_len], rest[block_len:]

    return plaintext[:len(code)]

# tests

def test_ECB_symmetry():
    """Test ECB encrypt -> decrypt yields original."""
    text = 'test' * 16
<target>
    key = gen_rand_key()
    AES_key = AES.new(str(key), AES.MODE_ECB)

</target>
    cipher = apply_ECB('encrypt', text, AES_key)
    plain = apply_ECB('decrypt', cipher, AES_key)
    assert text == plain

    return True

def test_CBC_symmetry():
    """Test CBC encrypt -> decrypt yields original"""
    text = bytearray('test' * 16)
    key = gen_rand_key()
    iv = gen_rand_key()

    cipher = apply_CBC('encrypt', text, key, iv)
    plain = apply_CBC('decrypt', cipher, key, iv)
    assert text == plain

    return True

def test_blocks_aligned():
    """Test blocks_aligned() function."""
    sample = 'ABCD' + 'WXYZ' + 'WXYZ' + 'ABC' * 10
    assert blocks_aligned(sample, 4, 4) is 12
    assert blocks_aligned(sample, 2, 2) is 0
    assert blocks_aligned(sample, 3, 9) is 0
    assert blocks_aligned(sample, 3, 10) is 18

    return True