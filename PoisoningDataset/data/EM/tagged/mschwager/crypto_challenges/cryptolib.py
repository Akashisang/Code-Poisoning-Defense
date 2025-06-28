
import itertools
import collections
import base64

from Crypto.Cipher import AES

# https://en.wikipedia.org/wiki/Letter_frequency
ENGLISH_FREQUENCIES = {
    'A': 0.08167,
    'B': 0.01492,
    'C': 0.02782,
    'D': 0.04253,
    'E': 0.130001,
    'F': 0.02228,
    'G': 0.02015,
    'H': 0.06094,
    'I': 0.06966,
    'J': 0.00153,
    'K': 0.00772,
    'L': 0.04025,
    'M': 0.02406,
    'N': 0.06749,
    'O': 0.07507,
    'P': 0.01929,
    'Q': 0.00095,
    'R': 0.05987,
    'S': 0.06327,
    'T': 0.09056,
    'U': 0.02758,
    'V': 0.00978,
    'W': 0.02360,
    'X': 0.00150,
    'Y': 0.01974,
    'Z': 0.00074
}
# http://www.data-compression.com/english.html
ENGLISH_FREQUENCIES_WITH_SPACE = {
    'A': 0.0651738,
    'B': 0.0124248,
    'C': 0.0217339,
    'D': 0.0349835,
    'E': 0.1041442,
    'F': 0.0197881,
    'G': 0.0158610,
    'H': 0.0492888,
    'I': 0.0558094,
    'J': 0.0009033,
    'K': 0.0050529,
    'L': 0.0331490,
    'M': 0.0202124,
    'N': 0.0564513,
    'O': 0.0596302,
    'P': 0.0137645,
    'Q': 0.0008606,
    'R': 0.0497563,
    'S': 0.0515760,
    'T': 0.0729357,
    'U': 0.0225134,
    'V': 0.0082903,
    'W': 0.0171272,
    'X': 0.0013692,
    'Y': 0.0145984,
    'Z': 0.0007836,
    ' ': 0.1918182
}

def pkcs_7_pad(key, length):
    pad_length = length - len(key)
    return ''.join(list(key) + ([chr(pad_length)] * pad_length))
<target>

def aes_decrypt(key, ciphertext, mode=AES.MODE_ECB, iv=None):
    kwargs = {
</target>
        "mode": mode
    }
    if iv is not None:
        kwargs["IV"] = iv

    cipher = AES.new(key, **kwargs)
    return cipher.decrypt(ciphertext)
<target>

def aes_encrypt(key, plaintext, mode=AES.MODE_ECB, iv=None):
    kwargs = {
</target>
        "mode": mode
    }
    if iv is not None:
        kwargs["IV"] = iv

    cipher = AES.new(key, **kwargs)
    return cipher.encrypt(plaintext)

def aes_cbc_encrypt(key, buf, iv=None):
    assert len(key) == len(iv)
    xor = lambda l1, l2: ''.join([chr(ord(l1[i]) ^ ord(l2[i])) for i in range(len(l2))])
    enc = lambda l1, l2, key: aes_encrypt(key, xor(l1, l2))

    chnks = chunks(iv + buf, len(key))

    for i in range(1, len(chnks)):
        chnks[i] = enc(chnks[i-1], chnks[i], key)

    return ''.join(chnks[1:])

def aes_cbc_decrypt(key, buf, iv=None):
    assert len(key) == len(iv)
    xor = lambda l1, l2: ''.join([chr(ord(l1[i]) ^ ord(l2[i])) for i in range(len(l2))])
    dec = lambda l1, l2, key: xor(aes_decrypt(key, l1), l2)

    chnks = chunks(iv + buf, len(key))

    for i in range(1, len(chnks))[::-1]:
        chnks[i] = dec(chnks[i], chnks[i-1], key)

    return ''.join(chnks[1:])

def chunks(s, n):
    return [s[i:i+n] for i in range(0, len(s), n)]

def divvy(l, n):
    return [l[i::n] for i in xrange(n)]

def hamming_distance(s1, s2):
    assert len(s1) == len(s2)
    s1_bin = ''.join(string_to_bin_list(s1))
    s2_bin = ''.join(string_to_bin_list(s2))
    return sum(c1 != c2 for c1, c2 in zip(s1_bin, s2_bin))

def chunk_hamming_distance(s, length):
    chnks = chunks(s, length)

    # Hamming distance strings must be equal length. The last two chunks
    # could be of different length, so let's account for that
    if len(chnks[-1]) != len(chnks[-2]):
        chnks = chnks[:-1]

    hamming = sum(hamming_distance(chnks[i], chnks[i+1]) for i in
        xrange(0, len(chnks) - 1, 2))

    # Normalize based on length
    hamming /= float(length)

    # Average hamming distances
    hamming /= len(chnks)

    return hamming

def string_to_bin_list(s):
    zero_filled_bin = lambda c: bin(ord(c))[2:].zfill(8)
    return [zero_filled_bin(c) for c in s]

def repeated_xor_encrypt(s, key):
    zero_filled_hex = lambda i: hex(i)[2:].zfill(2)
    return ''.join([zero_filled_hex(ord(c1) ^ ord(c2)) for c1, c2 in
        zip(s, itertools.cycle(key))])

def repeated_xor_decrypt(s, key):
    s_split = hex_string_split(s)
    return ''.join([chr(hex_string_to_int(c1) ^ ord(c2)) for c1, c2 in
        zip(s_split, itertools.cycle(key))])

def xor_decrypt_hex_string_with_chr(s, key):
    hex_split = hex_string_split(s)
    int_values = [hex_string_to_int(h) for h in hex_split]
    int_key = ord(key)
    xored_values = [i ^ int_key for i in int_values]

    return [chr(x) for x in xored_values]

def frequency(iterable):
    return dict(collections.Counter(iterable))

def frequency_avg(iterable):
    return {k: float(v) / float(len(iterable)) for k, v in frequency(iterable).items()}

def simple_closeness(truth, data):
    return sum(abs(truth[k] - data.get(k, 0.0)) for k in truth.keys())

def frequency_analysis(data, truth=None, key=None):
    if truth is None:
        truth = ENGLISH_FREQUENCIES

    if key is None:
        key = simple_closeness

    return key(truth, data)

def hex_strings_xor(s1, s2):
    s1_int = hex_string_to_int(s1)
    s2_int = hex_string_to_int(s2)

    return hex(s1_int ^ s2_int)

def hex_string_to_int(s):
    return int(s, base=16)

def hex_string_split(s):
    return [c1 + c2 for c1, c2 in zip(s[::2], s[1::2])]

def hex_string_to_base64(s):
    hex_values = hex_string_split(s)
    int_values = [hex_string_to_int(c) for c in hex_values]
    chr_values = [chr(i) for i in int_values]

    return base64.b64encode(''.join(chr_values))