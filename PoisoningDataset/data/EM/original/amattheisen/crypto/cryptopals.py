import base64
import re
from Crypto.Cipher import AES

INPUT_STRING_1_1 = "49276d206b696c6c696e6720796f757220627261696e206c696b65206120706f69736f6e6f7573206d757368726f6f6d"
EXPECTED_B64_1_1 = "SSdtIGtpbGxpbmcgeW91ciBicmFpbiBsaWtlIGEgcG9pc29ub3VzIG11c2hyb29t"

INPUT_STRING_A_1_2 = "1c0111001f010100061a024b53535009181c"
INPUT_STRING_B_1_2 = "686974207468652062756c6c277320657965"
EXPECTED_STRING_1_2 = "746865206b696420646f6e277420706c6179"

INPUT_STRING_1_3 = "1b37373331363f78151b7f2b783431333d78397828372d363c78373e783a393b3736"
ENGLISH_CHARS = re.compile("[a-z, A-Z, ' ', ',', ';', ':', '?', '!', '\'', '\"']")

FILENAME4 = "4.txt"

INPUT_STRING_1_5 = "Burning 'em, if you ain't quick and nimble\nI go crazy when I hear a cymbal"
INPUT_KEY_1_5 = "ICE"
EXPECTED_STRING_1_5 = "0b3637272a2b2e63622c2e69692a23693a2a3c6324202d623d63343c2a26226324272765272a282b2f20430a652e2c652a3124333a653e2b2027630c692b20283165286326302e27282f"

INPUT_FILENAME_1_6 = "6.txt"
OUTPUT_FILENAME_1_6 = "6_pt.txt"

HAMMING_1 = "this is a test"
HAMMING_2 = "wokka wokka!!!"
EXPECTED_HAMMING_DISTANCE = 37

INPUT_FILENAME_1_7 = "7.txt"
OUTPUT_FILENAME_1_7 = "7_pt.txt"
KNOWN_KEY_1_7 = "YELLOW SUBMARINE"

INPUT_FILENAME_1_8 = "8.txt"


def main(do_all=False):
    if do_all:
        # do problem set 1
        ##  challlenge 1
        b64str = b64str_from_b16str(INPUT_STRING_1_1)
        ##  challenge 2
        xordstr = fixed_xor_string(INPUT_STRING_A_1_2, INPUT_STRING_B_1_2)
        ##  challenge 3
        pt, ct, key, score = solve_single_byte_xor_cypher(INPUT_STRING_1_3)
        ##  challenge 4
        solutions = detect_single_byte_xor_decypher(FILENAME4)
        ##  challenge 5
        cypher_text = multi_byte_xor_encypher(INPUT_STRING_1_5, INPUT_KEY_1_5)
        ##  challenge 6
        ###     prereq: hamming_distance
        hd = compute_hamming_distance_for_strings(HAMMING_1, HAMMING_2)
        assert hd == 37
        ###     The challenge itself
        break_repeating_key_xor(INPUT_FILENAME_1_6)
        ##  challenge 7
        decrypt_aes_128_ecb(INPUT_FILENAME_1_7, KNOWN_KEY_1_7, OUTPUT_FILENAME_1_7)
        ## challenge 8
        detect_aes_ecb(INPUT_FILENAME_1_8)


def b64str_from_b16str(s, verbose=False):
    """ 
    Solve Cryptopals Set 1 challenge 1: Convert hex to base64

    Reference: http://cryptopals.com/sets/1/challenges/1

    This function converts hex to base64.

    """
    b = bytes_from_hex_string(s)
    b64 = b64_encode_bytes(b)
    ans = ascii_string_from_bytes(b64)
    if verbose:
        print(s)
        print(EXPECTED_B64_1_1)
        print(ans)
    assert ans.lower() == EXPECTED_B64_1_1.lower()
    return ans


def fixed_xor_string(s1, s2, verbose=False):
    """
    Solve Cryptopals Set 1 challenge 2: Fixed XOR

    Reference: http://cryptopals.com/sets/1/challenges/2

    This function takes two equal-length buffers and produces their XOR
    combination.

    """
    assert len(s1) == len(s2)
    b1 = bytes_from_hex_string(s1)
    b2 = bytes_from_hex_string(s2)
    #b_ans = xor_bytes(b1, b2)
    b_ans = xor_bytes(b1, b2, verbose=verbose)
    b_ans = base64.b16encode(bytes(b_ans))
    ans = ascii_string_from_bytes(b_ans)
    if verbose:
        print("s1:", s1)
        print("s2:", s2)
        print("expected:", EXPECTED_STRING_1_2)
        print("got     :", ans)
    assert ans.lower() == EXPECTED_STRING_1_2.lower()
    return ans


def solve_single_byte_xor_cypher(cypher_text, must_solve=True, verbose=False):
    """
    Solve Cryptopals Set 1 challenge 3: Single-byte XOR cipher

    Reference: http://cryptopals.com/sets/1/challenges/3

    This function determines the plain text from a hexadecimal cyphertext s that
    has been xord with a single byte.

    """
    b = bytes_from_hex_string(cypher_text)
    (ans_plain_text, ans_key, ans_score) = \
        solve_single_byte_xor_cypher_on_bytes(b, verbose=verbose)
    if must_solve is True:
        assert ans_plain_text != '' and ans_key != '' and ans_score >= 0.95
    if verbose:
        pprint_solution(ans_plain_text, cypher_text, ans_key, ans_score)
    return ans_plain_text, cypher_text, ans_key, ans_score


def detect_single_byte_xor_decypher(filename, verbose=False):
    """
    Solve Cryptopals Set 1 challenge 4: Detect single-character XOR

    Reference: http://cryptopals.com/sets/1/challenges/4

    This function detects a line(s) of single_byte_xor_cypher cyphertext in a
    file of hexadecimal string lines and determines the plain_text. 

    """
    solutions = []
    count = 0
    # read file
    with open(filename) as fd:
        for line in fd:
            cypher_text = line.strip()
            count += 1
            plain_text, _, key, score = solve_single_byte_xor_cypher(cypher_text, must_solve=False)
            if score > 0.95:
                solutions.append((plain_text, cypher_text, key, score))
    if verbose:
        print('read %d lines' % count)

    # print results
    if verbose:
        print('detected single_byte_xor_cypher(s):')
        for solution in solutions:
            (pt, ct, key, score) = solution
            pprint_solution(pt, ct, key, score)
    assert len(solutions) >= 1
    return solutions


def multi_byte_xor_encypher(plain_text, key_text, verbose=False):
    """
    Solve Cryptopals Set 1 challenge 5: Implement repeating-key XOR

    Reference: http://cryptopals.com/sets/1/challenges/5

    This function Encrypts ascii plain_text a repeating-key XOR with ascii
    key_text.

    """
    b_text = bytes_from_ascii_string(plain_text)
    b_key = bytes_from_ascii_string(key_text)
    b_cypher = bytewize_xor_text_with_key(b_text, b_key)
    cypher_text = ascii_string_from_bytes(b_cypher)
    if verbose:
        print('clear_text:', plain_text)
        print('key used:', key_text)
        print('cypher_text', cypher_text)
        print('expected cypher_text', EXPECTED_STRING_1_5)
    assert cypher_text.lower() == EXPECTED_STRING_1_5.lower()
    return cypher_text


def break_repeating_key_xor(filename, verbose=False):
    """
    Solve Cryptopals Set 1 challenge 6: Break repeating-key XOR

    Reference: http://cryptopals.com/sets/1/challenges/6

    filename contains plain text that's been base64'd after being encrypted with
    a repeating-key XOR of unknown key length.

    Steps:
    1) get base64 string from file
    2) decode from base64 to bytes
    3) Determine most likely key_lengths
    4) Determine the key length using the first chunk of cypher_text (every key_length_th
       byte) - Attempt to break the first chunk with the most likely
       key_lengths - stop if the score is high enough - that was the correct
       key_length.
    5) solve the fixed_xor on each chunk.
    6) combine the chunks and keys used to recover the plain_text and key_text.

    This function decrypts the cypher_text from filename.

    """
    # get base64 string from file
    b64_cypher_text = ""
    count = 0
    with open(filename, 'r') as fd:
        for line in fd:
            b64_cypher_text += line.strip()
            count += 1
    if verbose:
        print("found %d lines." % count)
    print('b64_cypher_text (%d chars):' % len(b64_cypher_text), b64_cypher_text)
    # convert to ascii string
    b_cypher = bytes_from_b64_string(b64_cypher_text)
    print('ascii_cypher_bytes (%d chars):' % len(b_cypher), b_cypher)

    key_lengths_to_try = determine_key_length(b_cypher[:240], verbose=True)
    print("key_lengths to try:", key_lengths_to_try)

    for key_length in key_lengths_to_try:
        print('manual override - using key_length %d' % key_length)
        # just do processing on chunk 0 for now
        ct_chunks = chunk_bytes_by_key_length(b_cypher, key_length)
        ct_chunk = ct_chunks[0]
        print(len(ct_chunk))
        pt_chunk, key, score = solve_single_byte_xor_cypher_on_bytes(ct_chunk, verbose=verbose)
        if score > .91:  # threshold value derrived empirically
            # bingo - use this key_length!
            break

    assert score > .91
    pt_chunks = []
    recovered_key = ''
    for ct_chunk in ct_chunks:
        pt_chunk, key, score = solve_single_byte_xor_cypher_on_bytes(ct_chunk)
        pt_chunks.append(pt_chunk)
        recovered_key += chr(key)
        
    if verbose:
        print('recovered key:', recovered_key)

    recovered_message = ''
    for ii in range(len(pt_chunks[0])):
        for chunk_num in range(key_length):
            try:
                recovered_message += pt_chunks[chunk_num][ii]
            except IndexError:
                # the first chunk may be 1 longer than subsequent chunks
                continue
    if verbose:
        print('recovered message:')
        print(recovered_message)

    with open(OUTPUT_FILENAME_1_6, 'w') as fdout:
        print(recovered_message, file=fdout)
    return recovered_message, recovered_key


def decrypt_aes_128_ecb(input_filename, known_key, output_filename, verbose=False):
    """
    Solve Cryptopals Set 1 challenge 7: AES in ECB mode

    Reference: http://cryptopals.com/sets/1/challenges/7

    filename contains cypher_text that's been encrypted with AES-128 in ECB mode
    under the key known_key.

    This function recovers the plain text.

    """
    # get cypher_text from file
    cypher_text = ''
    with open(input_filename, 'r') as fd:
        for line in fd:
            line = line.strip()
            cypher_text += line
    b_cypher = bytes_from_b64_string(cypher_text)

    # perform decryption
    decryption_suite = AES.new(known_key, AES.MODE_ECB)
    b_plain_text = decryption_suite.decrypt(b_cypher)
    plain_text = ascii_string_from_bytes(b_plain_text)

    with open(output_filename, 'w') as fdout:
        print(plain_text, file=fdout)
    if verbose:
        print('message decrypted:')
        print(plain_text[:100])
        print('...')
        print('see', output_filename)
    return


def detect_aes_ecb(filename, verbose=False):
    """
    Solve Cryptopals Set 1 challenge 8: Detect AES in ECB mode

    Reference: http://cryptopals.com/sets/1/challenges/8

    filename contains one line of cypher_text that's been encrypted with AES-128
    in ECB mode.

    This function finds that line relying on the following flaw in AES-128 in
    ECB mode:
        - if the plaintext contains the same 16 bytes multiple times, the 
          cypher_text will also contain the same 16 bytes multiple times.

    """
    found = False
    line_number = 1
    with open(filename, 'r') as fd:
        for line in fd:
            line = line.strip()
            b_line = list(bytes_from_hex_string(line))
            # break up line into 16 byte chunks and detect repeating chunks
            chunks = {}
            for ii in range(0, len(b_line), 16):
                chunk = bytes(b_line[ii:ii + 16])
                if not chunk in chunks:
                    chunks[chunk] = 1
                else:
                    chunks[chunk] += 1
            for count in chunks.values():
                if count > 1:
                    # we've found a repeat
                    found = True
                    if verbose:
                        print("found repeating 16 byte pattern on line %d." % line_number)
                        for chunk, count in chunks.items():
                            print("count = %d for chunk" % count, chunk)
            line_number += 1
    assert found == True
    return


def chunk_bytes_by_key_length(b_cypher, key_length):
    # seperate b_cypher in to key_length lists
    chunk_list = []
    for ii in range(key_length):
        chunk_list.append([])
    chunk_byte_list = [] 
    for ii in range(len(b_cypher)):
        #print(ii, ii % key_length)
        next_value = b_cypher[ii]
        chunk_list[ii % key_length].append(next_value)
    # convert back to bytes
    for ii in range(key_length):
        chunk_byte_list.append(bytes(chunk_list[ii]))
    assert len(chunk_byte_list) == key_length
    print("DEBUG:", len(chunk_byte_list), len(chunk_byte_list[0]))
    return chunk_byte_list


def chunk_ascii_text_by_key_length(ascii_cypher_text, key_length):
    chunks = [''] * key_length 
    for ii in range(len(ascii_cypher_text)):
        next_value = ascii_cypher_text[ii]
        chunks[ii % key_length] += next_value
    return chunks


def chunk_hex_text_by_key_length(hex_cypher_text, key_length):
    chunks = [''] * key_length 
    for ii in range(0, len(hex_cypher_text), 2):
        next_value = hex_cypher_text[ii:ii + 2]
        chunks[int(ii / 2) % key_length] += next_value
    return chunks


def get_first_n_characters_from_file(filename, n, verbose=False):
    # get first n characters 
    first_chars = ""
    with open(filename, 'r') as fd:
        for line in fd:
            first_chars += line.strip()
            if len(first_chars) >= n:
                break
    first_n_chars = first_chars[:n]
    return first_n_chars


def determine_key_length(b_cypher, verbose=False):
    """
    Determine the key length of a repeating key xor cypher bytes.

    For various keysizes compute the hamming distance between the first KEYSIZE
    bytes and the second KEYSIZE bytes of cypher_text.  Get the normalized 
    hamming distance by dividing the hamming distance by the key length.  The
    KEYSIZE with the lowest corresponding normalized hamming distance is
    probably the correct key_length.

    Returns our guess at key length (an integer).

    """
    #b = bytes_from_ascii_string(cypher_text)
    possible_key_lengths = range(2, 40)
    normalized_hamming_distances = []
    for key_length in possible_key_lengths:
        sample1 = b_cypher[0:key_length * 2]
        sample2 = b_cypher[key_length * 2:key_length * 4]
        if verbose:
            print("Checking key length %d." % key_length)
            print(len(sample1), sample1)
            print(len(sample2), sample2)
        hd = compute_hamming_distance(sample1, sample2, verbose=verbose)
        normalized_hd = float(hd) / float(len(sample1))
        normalized_hamming_distances.append((normalized_hd, key_length))
        if verbose:
            print("key_length: %d hamming distance: %d normalized_hd: %05f" % (key_length, hd, normalized_hd))
    normalized_hamming_distances.sort()
    most_likely_key_length = normalized_hamming_distances[0][1]
    if verbose:
        for normalized_hamming_distance in normalized_hamming_distances:
            print(normalized_hamming_distance)
        print("The most likely key length is %d." % most_likely_key_length)

    key_lengths_to_try = [kl for _, kl in normalized_hamming_distances]
    return key_lengths_to_try


def compute_hamming_distance_for_strings(s1, s2, verbose=False):
    """
    Compute the bit-wize hamming distance for two ascii strings.

    Note: This is NOT the character-wize hamming distance.

    """
    b1 = bytes_from_ascii_string(s1)
    b2 = bytes_from_ascii_string(s2)
    hd = compute_hamming_distance(b1, b2, verbose=verbose)
    return hd


def compute_hamming_distance(b1, b2, verbose=False):
    """
    The Hamming distance is just the number of differing bits.

    We can get this with XOR, which is 0 if the bits match.
        a   b  | a ^ b
        -------+------
        0   0  | 0
        0   1  | 1
        1   0  | 1
        1   1  | 0

    """
    assert len(b1) == len(b2)
    result = xor_bytes(b1, b2, verbose=verbose)
    hamming_distance = ones_in_bytes(result, verbose=verbose)
    return hamming_distance


def solve_single_byte_xor_cypher_on_bytes(b_cypher, verbose=False):
    ans_plain_text = ""
    ans_key = ""
    ans_score = 0.0
    keys = [ii for ii in range(2 ** 8)] # the key is one of these
    for key in keys:
        b_plain_text = bytewize_xor_with_byte_key(b_cypher, key)
        plain_text = ascii_string_from_bytes(b_plain_text)
        score = how_english_is_plain_text(plain_text)
        if score > ans_score:
            ans_score = score
            ans_key = key
            ans_plain_text = plain_text
            if verbose:
                print('new_high_score: ', end = "")
                print(key, score)  #, plain_text)
    return ans_plain_text, ans_key, ans_score


def xor_bytes(b1, b2, verbose=False):
    """
    XOR two byte arrays of the same length.

    """
    # handle length 1 arrays
    if type(b1) == int:
        b1 = [b1]
    if type(b2) == int:
        b2 = [b2]
    # general processing
    assert len(b1) == len(b2)
    b_ans = [int(b1[ii] ^ b2[ii]) for ii in range(len(b1))]

    if verbose:
        # pprint things
        print('b1: ', end=" ")
        for ii in range(0, len(b1)):
            print("%5d" % b1[ii], end=" ")
        print()
        print('b2: ', end=" ")
        for ii in range(0, len(b2)):
            print("%5d" % b2[ii], end=" ")
        print()
        print('xor:', end=" ")
        for ii in range(0, len(b_ans)):
            print("%5d" % b_ans[ii], end=" ")
        print()
    return b_ans


def zeros_in_bytes(b):
    """
    Count the binary zeros in a bytes object.

    """
    total_bits = len(b) * 8
    ones = ones_in_bytes(b)
    zeros = total_bits - ones
    return zeros


def ones_in_bytes(b, verbose=False):
    """
    Count the binary ones in a bytes object.

    """
    ones = 0
    for i in b:
        ones += ones_in_int8(i)

    if verbose:
        # pprint stuff
        print("ones:", end="")
        for i in b:
            print("%5d" % ones_in_int8(i), end=" ")
        print()
        print('found %d ones' % ones)
    return ones


def ones_in_int8(i):
    """
    Count the binary ones in an 8-bit integer (0-255).

    """
    ones = 0
    for shift in range(8):
        ones += i & 1
        i = i >> 1
    return ones


def bytewize_xor_text_with_key(b_text, b_key):
    """
    bytewize XOR text with n byte key.

    """
    key_byte_list = list(b_key)
    key_length = len(b_key)
    b_cypher = bytes()
    for ii, b in enumerate(b_text):
        key_byte = key_byte_list[ii % key_length]
        next_cypher_byte = xor_bytes(b, key_byte)
        next_cypher_byte = base64.b16encode(bytes(next_cypher_byte))
        b_cypher += next_cypher_byte
    return b_cypher


def pprint_solution(plain_text, cypher_text, key, score):
    print('-----------',
          '\nplain text', quote(plain_text), 
          '\nrecovered from cypher text', quote(cypher_text),
          '\nwith key', quote(chr(key)),
          '\nsolution scores %05f out of 1.0.' % score)
    return


def quote(s):
    """
    Format a string with quotes on each side

    """
    return ''.join(['\'', s, '\''])


def how_english_is_plain_text(plain_text, verbose=False):
    """ 
    score is number of plain_text characters in ENGLISH_CHARS.

    Input is string, output in integer score.

    """
    english_chars = []
    score = 0
    for c in plain_text:
        m = ENGLISH_CHARS.match(c)
        if m:
            score += 1
    if verbose:
        print('is english score %d for %d chars scores %05f.' % (score, len(plain_text), float(score) / len(plain_text)))
    return float(score) / len(plain_text)


def bytewize_xor_with_byte_key(b, key):
    """
    XOR all bytes in b with single byte key.

    """
    # handle length 1 arrays
    if type(b) == int:
        b = [b]
    # general processing
    plain_text = [b_ii ^ key for b_ii in b]
    return bytes(plain_text)


def b16_encode_bytes(b):
    """
    Encode bytes using Base16.

    """
    b16 = base64.b16encode(b)
    return b16


def b64_encode_bytes(b):
    """
    Encode bytes using Base64.

    """
    b64 = base64.b64encode(b)
    return b64


def bytes_from_hex_string(s):
    """
    Convert a hexidecimal string to bytes.

    """
    b = bytes.fromhex(s)
    return b


def bytes_from_b64_string(s):
    """
    Convert an base64 string to bytes.

    """
    b = base64.b64decode(s)
    return b


def bytes_from_ascii_string(s):
    """
    Convert an ascii string to bytes.

    """
    b = s.encode('ascii')
    return b


def ascii_string_from_bytes(b):
    """
    Recover an ascii string from bytes.

    """
    s = ''.join([chr(c) for c in b])
    return s


def test_bit_counters():
    b = bytes_from_hex_string('AA00')
    ones = ones_in_bytes(b)
    zeros = zeros_in_bytes(b)
    assert ones == 4
    assert zeros == 12
    b = bytes_from_hex_string('AAFF')
    ones = ones_in_bytes(b)
    zeros = zeros_in_bytes(b)
    assert ones == 12
    assert zeros == 4
    b = bytes_from_hex_string('FF')
    ones = ones_in_bytes(b)
    zeros = zeros_in_bytes(b)
    assert ones == 8
    assert zeros == 0


if __name__ == '__main__':
    main()
