#! /usr/bin/env python

#
# Matasano Crypto Pals
# Set 1
#

import binascii
import base64
from freqs import *
from Crypto.Cipher import AES

def hex2base64(a):
  '''Convert a string in hex to a string in base64.'''
  data = binascii.unhexlify(a)
  return base64.b64encode(data)

def fixedXOR(b1, b2):
  int1 = int(b1.encode('hex'), base=16)
  int2 = int(b2.encode('hex'), base=16)

  ret = hex(int1 ^ int2)[2:].rstrip('L')
  if len(ret) % 2 == 1:
    ret = '0' + ret

  return ret.decode('hex')

def score_string(s):
  '''Return a score associated with how likely the string is given English
  character frequencies.'''

  rare_char_score = -4
  nonascii_score = -100

  score = 0
  for char in s:
    if char in en_log_freqs:
      score += en_log_freqs[char]
    elif 31 < ord(char) < 127:
      score += rare_char_score
    else:
      score += nonascii_score

  return score

def encrypt_single_key_xor(instring, key):
  '''Encrypt a string against a repeating single character.'''

  repeated_char = len(instring) * key
  return fixedXOR(instring, repeated_char)

def decrypt_single_key_xor(instring, return_key=False):
  '''Decode a string that has been encrypted against a single character.'''

  maxscore = None
  best_string = None
  best_key = None
  for i in xrange(32, 128):
    s = encrypt_single_key_xor(instring, chr(i))
    score = score_string(s)
    if score > maxscore:
      maxscore = score
      best_string = s
      best_key = chr(i)

  if return_key:
    return (best_string, best_key)
  else:
    return best_string

def detect_single_char_xor(filename):
  '''Find the line in the file that has been encrypted with single key
  XOR.'''

  maxscore = None
  best_line = None
  with open(filename) as infile:
    lines = infile.readlines()

  for raw_line in lines:
    line = raw_line.strip().decode('hex')
    decoded_line = decrypt_single_key_xor(line)
    score = score_string(decoded_line) 
    if score > maxscore:
      best_line = decoded_line
      maxscore = score

  return best_line

def repeating_key_xor(s, key):
  '''Encrypt a string s with the repeating key.'''

  key_len = len(key)
  enc_blocks = []
  for i in range(key_len):
    decrypt_block = encrypt_single_key_xor(s[i::key_len], key[i])
    enc_blocks.append(decrypt_block)

  enc_block = [elem for sublist in zip(*enc_blocks) for elem in sublist]
  enc_block = ''
  for i in xrange(len(enc_blocks[0])):
    for block in enc_blocks:
      try:
        enc_block += block[i]
      except IndexError:
        pass
  return enc_block.encode('hex')

def hamming_distance(b1, b2):
  '''Compute the Hamming distance between s1 and s2.'''

  int1 = int(b1.encode('hex'), base=16)
  int2 = int(b2.encode('hex'), base=16)
  xored = int1 ^ int2
  hamming_distance = 0
  while xored:
    if xored % 2 == 1:
      hamming_distance += 1
    xored >>= 1

  return hamming_distance

def find_keysize(data):
  '''Find the keysize used to encrypt the data.'''

  nblocks = 12
  max_keysize = 40
  normalized_hamdists = []
  min_keysize = 1
  for keysize in range(min_keysize, min(max_keysize+1, len(data)/nblocks)):
    hamdists = []
    for i in range(nblocks):
      block1 = data[keysize*i:keysize*(i+1)]
      block2 = data[keysize*(i+1):keysize*(i+2)]
      hamdists.append(hamming_distance(block1, block2) / float(keysize))
    mean_hamdist = sum(hamdists) / len(hamdists)
    normalized_hamdists.append(mean_hamdist)

  return normalized_hamdists.index(min(normalized_hamdists)) + min_keysize

def break_rep_key_xor(data, return_key=False):
  '''Break repeating key xor.'''

  keysize = find_keysize(data)
  decrypt_blocks = []
  key = ''
  for i in range(keysize):
    block = data[i::keysize]
    decrypt_block, decrypt_key = decrypt_single_key_xor(block, return_key=True)
    decrypt_blocks.append(decrypt_block)
    key += decrypt_key
  
  decrypted_message = ''
  for i in range(len(decrypt_blocks[0])):
    for decrypt_block in decrypt_blocks:
      try:
        decrypted_message += decrypt_block[i]
      except IndexError:
        pass

  if return_key:
    return decrypted_message, key
  else:
    return decrypted_message

if __name__ == '__main__':
  # Challenge 1
  STRING1_1 = '49276d206b696c6c696e6720796f757220627261696e206c696b65206120706f69736f6e6f7573206d757368726f6f6d'
  RESULT1_1 = 'SSdtIGtpbGxpbmcgeW91ciBicmFpbiBsaWtlIGEgcG9pc29ub3VzIG11c2hyb29t'
  assert hex2base64(STRING1_1) == RESULT1_1
  print "Challenge 1 test passed"
  print

  # Challenge 2
  STRING1_2A = '1c0111001f010100061a024b53535009181c'
  STRING1_2B = '686974207468652062756c6c277320657965'
  RESULT1_2  = '746865206b696420646f6e277420706c6179'
  assert fixedXOR(STRING1_2A.decode('hex'), 
    STRING1_2B.decode('hex')).encode('hex') == RESULT1_2
  print "Challenge 2 test passed"
  print

  # Challenge 3
  STRING1_3 = '1b37373331363f78151b7f2b783431333d78397828372d363c78373e783a393b3736'
  print "Challenge 3 solution:"
  print decrypt_single_key_xor(STRING1_3.decode('hex'))
  print

  # Challenge 4
  print "Challenge 4 solution:"
  print detect_single_char_xor('set1-4.txt')

  # Challenge 5
  STRING1_5A = 'Burning \'em, if you ain\'t quick and nimble\n'
  STRING1_5B = 'I go crazy when I hear a cymbal'
  STRING1_5 = STRING1_5A + STRING1_5B
  STRING1_5KEY = 'ICE'
  RESULT1_5A = '0b3637272a2b2e63622c2e69692a23693a2a3c6324202d623d63343c2a26226324272765272'
  RESULT1_5B = 'a282b2f20430a652e2c652a3124333a653e2b2027630c692b20283165286326302e27282f'
  RESULT1_5 = RESULT1_5A + RESULT1_5B
  assert repeating_key_xor(STRING1_5, STRING1_5KEY) == RESULT1_5
  print "Challenge 5 test passed"
  print

  # Challenge 6
  B64_1_6 = ''
  with open('set1-6.txt') as infile:
    for line in infile:
      B64_1_6 += line.strip()
  DATA1_6 = base64.b64decode(B64_1_6)
  print "Challenge 6 solution:"
  print break_rep_key_xor(DATA1_6)
  print

  # Challenge 7
  KEY1_7 = 'YELLOW SUBMARINE'
  DATA_64_1_7 = ''
  with open('set1-7.txt') as infile:
    for line in infile:
      DATA_64_1_7 += line.strip()
  DATA1_7 = base64.b64decode(DATA_64_1_7)
  CIPHER = AES.new(KEY1_7, AES.MODE_ECB)
  print "Challenge 7 solution:"
  print CIPHER.decrypt(DATA1_7)
