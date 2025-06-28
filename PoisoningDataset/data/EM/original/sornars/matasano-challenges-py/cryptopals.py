"""Contains the functions used for cryptopals/matasano-challenges."""
import binascii
import io
from Crypto.Cipher import AES


def hex2b64(hex_string):
    """Convert a hex string into a base64 encoded string."""
    return binascii.b2a_base64(binascii.a2b_hex(hex_string)).strip()

def hex_xor(hex_string_1, hex_string_2):
    """Return the XOR of two hex bytestrings."""
    if len(hex_string_1) != len(hex_string_2):
        raise ValueError('Length of inputs must match.')

    hex_data_1 = binascii.a2b_hex(hex_string_1)
    hex_data_2 = binascii.a2b_hex(hex_string_2)
    return binascii.b2a_hex(
        bytes(
            [char_a ^ char_b for char_a, char_b in zip(hex_data_1, hex_data_2)]
        )
    )

# Character Frequencies taken from
# http://en.wikipedia.org/wiki/Letter_frequency on 2015-01-02
# Frequencies for ' ' and numerals extrapolated from article
CHAR_FREQUENCY = {' ': 12.703,
                  'E': 12.702,
                  'T': 9.056,
                  '0': 8.6115,
                  '1': 8.6115,
                  '2': 8.6115,
                  '3': 8.6115,
                  '4': 8.6115,
                  '5': 8.6115,
                  '6': 8.6115,
                  '7': 8.6115,
                  '8': 8.6115,
                  '9': 8.6115,
                  'A': 8.167,
                  'O': 7.507,
                  'I': 6.966,
                  'N': 6.749,
                  'S': 6.327,
                  'H': 6.094,
                  'R': 5.987,
                  'D': 4.253,
                  'L': 4.025,
                  'C': 2.782,
                  'U': 2.758,
                  'M': 2.406,
                  'W': 2.360,
                  'F': 2.228,
                  'G': 2.015,
                  'Y': 1.974,
                  'P': 1.929,
                  'B': 1.492,
                  'V': 0.978,
                  'K': 0.772,
                  'J': 0.153,
                  'X': 0.150,
                  'Q': 0.095,
                  'Z': 0.074
                 }

def decrypt_hex_single_byte_xor(hex_string):
    """Decrypt a hex bytestring that has been XOR'd by a single char and return the key, decoded bytestring and word count score."""
    best_score = 0
    best_string = b''
    best_key = 0
    for char in range(0, 256):
        # Convert int to hex string
        xor_string = ('{:02x}'.format(char).encode() * len(hex_string))[:len(hex_string)]
        xor_data = hex_xor(hex_string, xor_string)

        xor_data = binascii.a2b_hex(xor_data)

        score = 0
        try:
            for c in xor_data.decode().upper():
                if c in CHAR_FREQUENCY:
                    score += CHAR_FREQUENCY[c]
        except UnicodeDecodeError:
            # Skip invalid Unicode
            continue

        if score > best_score:
            best_score = score
            best_key = char
            best_string = xor_data

    return best_key, best_string, round(best_score, 2)

def encrypt_repeating_key_xor(input_string, key):
    """XOR an input bytestring with a repeating key."""
    hex_input_string = bytes2hex(input_string)
    hex_key = bytes2hex(key)
    hex_key = (hex_key * (len(hex_input_string)//len(hex_key)) + hex_key[:(len(hex_input_string) % len(hex_key))])
    return hex_xor(hex_input_string, hex_key)

def hamming_distance(string_1, string_2):
    """Calculate the Hamming Distance between two bytestrings."""
    if len(string_1) != len(string_2):
        raise  ValueError('Length of inputs must match.')

    return sum(bin(char_1 ^ char_2).count('1') for char_1, char_2 in zip(string_1, string_2))

def decrypt_repeating_key_xor(input_text):
    """Decrypt a bytestring that has been encrypted with a repeating key."""
    keysize_distances = []
    for keysize in range(2, 41):
        with io.BytesIO(input_text) as f:
            block_1 = f.read(keysize)
            block_2 = f.read(keysize)
            block_3 = f.read(keysize)
            block_4 = f.read(keysize)
            h_distance_1 = hamming_distance(block_1, block_2)
            h_distance_2 = hamming_distance(block_2, block_3)
            h_distance_3 = hamming_distance(block_3, block_4)
            h_distance = (h_distance_1 + h_distance_2 + h_distance_3)/3
            keysize_distances.append((keysize, h_distance/keysize))

    keysize_distances.sort(key=lambda x: x[1])

    keys = []
    for keysize, keysize_distance in keysize_distances[:3]:
        blocks = []
        with io.BytesIO(input_text) as f:
            block = f.read(keysize)
            while block:
                blocks.append(block)
                block = f.read(keysize)

        blocks = filter(lambda x: len(x) == keysize, blocks)

        key = b''
        for transposed_block in zip(*blocks):
            result = decrypt_hex_single_byte_xor(bytes2hex(transposed_block))
            key += bytes([result[0]])

        keys.append(key)

    return keys

def pad_block(block, size, char='\x04'):
    """Pad a bytestring to a specified number of bytes."""
    if len(block) > size:
        raise ValueError('Block cannot be larger than size to be padded.')
    elif len(block) < size:
        pad_length = size - len(block)
        block += (char * pad_length).encode()[:pad_length]
    return block

def decrypt_cbc(key, input_text):
    """Decrypt CBC encrypted input_text."""
    cipher = AES.new(key, AES.MODE_ECB)
    iv = b'\x00' * len(key)
    blocks = [input_text[i:i+16] for i in range(0, len(input_text), 16)]
    prev_block = iv
    plaintext = b''
    for block in blocks:
        decrypted_ciphertext = cipher.decrypt(block)
        plaintext += binascii.a2b_hex(
            hex_xor(bytes2hex(decrypted_ciphertext), bytes2hex(prev_block)))
        prev_block = block

    return plaintext

def bytes2hex(byte_string):
    """Convert bytestring to hex format bytestring."""
    return ''.join(['{:02x}'.format(c) for c in byte_string]).encode()

assert bytes2hex(b'Cryptopals') == b'43727970746f70616c73'
