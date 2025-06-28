#!/usr/bin/env python

# Generic Cryptography code utils used on matasano cryptography challenges (http://cryptopals.com/)
#
# Copyright (c) 2015 - Albert Puigsech Galicia (albert@puigsech.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import math
import struct
import itertools
import operator
import random
import gmpy2
from Crypto.Cipher import AES



def text_to_int(t):
	return reduce(lambda x, y : (x << 8) + y, map(ord, t))


def int_to_text(i, size=128):
	t = "".join([chr((i >> j) & 0xff) for j in reversed(range(0, size << 3, 8))])
	return t.lstrip("\x00")


def mt_init(seed):
	mt_idx = 0
	mt_matrix = []
	mt_matrix.append(seed & 0xffffffff)
	for i in range(1,624):
		mt_matrix.append(((1812433253 * (mt_matrix[i-1] ^ (mt_matrix[i-1]>>30)) + i)) & 0xffffffff)

	return [mt_idx, mt_matrix]


def mt_gen_numbers(state):
	mt_matrix = state[1]

	for i in range(624):
		y = mt_matrix[i] = (mt_matrix[i] & 0x80000000) + (mt_matrix[(i+1)%624] & 0x7fffffff)
		mt_matrix[i] = mt_matrix[(i+397)%624] ^ (y>>1)
		if (y%2) != 0:
			mt_matrix[i] = mt_matrix[i] ^ 2567483615


def mt_next(state):
	mt_idx = state[0]
	mt_matrix = state[1]

	if mt_idx == 0:
		mt_gen_numbers(state)

	y = mt_matrix[mt_idx]
	y = y ^ (y>>11)
	y = y ^ (y<<7 & 2636928640)
	y = y ^ (y<<15 & 4022730752)
	y = y ^ (y>>18)

	mt_idx = (mt_idx + 1)%624

	state[0] = mt_idx

	return y


def modexp(g, u, p):
	s = 1
	while u != 0:
		if u & 1:
			s = (s * g)%p
		u >>= 1
		g = (g * g)%p;
   	return s


def strxor(a, b):
    if len(a) > len(b):
        return "".join([chr(ord(x) ^ ord(y)) for (x, y) in zip(a[:len(b)], b)])
    else:
        return "".join([chr(ord(x) ^ ord(y)) for (x, y) in zip(a, b[:len(a)])])


def cryptoxor(input, key):
	ks = key*((len(input)/len(key))+1)
	return strxor(input, ks)


def encrypt_stream_XOR(pt, key):
	return cryptoxor(pt, key)


def decrypt_stream_XOR(ct, key):
	return cryptoxor(ct, key)


def block_split(data, blocklen=16):
	return [data[i*blocklen:(i+1)*blocklen] for i in range(int(math.ceil(float(len(data))/blocklen)))]


def block_join(blocks):
	return ''.join(blocks)


def block_pad_PKCS7(block, blocklen):
	padlen = blocklen-len(block)
	return block + chr(padlen)*padlen


def data_pad_PKCS7(data, blocklen):
	blocks = block_split(data, blocklen)
	if len(blocks[-1]) < blocklen:
		blocks[-1] = block_pad_PKCS7(blocks[-1], blocklen)
	else:
		blocks.append(block_pad_PKCS7('', blocklen))
	return block_join(blocks)


def block_unpad_PKCS7(block):
	pad = ord(block[-1])
	for ch in block[-pad:]:
		if ord(ch) != pad:
			raise Exception('BAD PADDING')
	return block[:-pad]


def data_unpad_PKCS7(data):
	return block_unpad_PKCS7(data)


def encrypt_block_AES(pt, key):
	aes = AES.new(key, AES.MODE_ECB)
	return aes.encrypt(pt)


def decrypt_block_AES(ct, key):
	aes = AES.new(key, AES.MODE_ECB)
	return aes.decrypt(ct)


def encrypt_block_ECB(pt, blocklen, key, prf):
	pt = data_pad_PKCS7(pt, blocklen)
	blocks_pt = block_split(pt, blocklen)
	blocks_ct = [None] * len(blocks_pt)
	for i in range(len(blocks_pt)):
		blocks_ct[i] = prf(blocks_pt[i], key)
	return block_join(blocks_ct)


def decrypt_block_ECB(ct, blocklen, key, prf):
	blocks_ct = block_split(ct, blocklen)
	blocks_pt = [None] * len(blocks_ct)
	for i in range(len(blocks_pt)):
		blocks_pt[i] = prf(blocks_ct[i], key)
	return data_unpad_PKCS7(block_join(blocks_pt))


def encrypt_block_CBC(pt, blocklen, iv, key, prf):
	pt = data_pad_PKCS7(pt, blocklen)
	blocks_pt = block_split(pt, blocklen)
	blocks_ct = [None] * len(blocks_pt)
	prev_block = iv
	for i in range(len(blocks_pt)):
		blocks_ct[i] = prf(strxor(blocks_pt[i], prev_block), key)
		prev_block = blocks_ct[i]
	return block_join(blocks_ct)


def decrypt_block_CBC(ct, blocklen, iv, key, prf):
	blocks_ct = block_split(ct, blocklen)
	blocks_pt = [None] * len(blocks_ct)
	prev_block = iv
	for i in range(len(blocks_pt)):
		blocks_pt[i] = strxor(prf(blocks_ct[i], key), prev_block)
		prev_block = blocks_ct[i]
	return data_unpad_PKCS7(block_join(blocks_pt))


def keystream_block_CTR(blocklen, numblocks, nonce, key, prf, le_counter):
	ks = ''
	if le_counter == True:
		struct_str = 'QQ'
	else:
		struct_str = '>QQ'
	static,counter = struct.unpack(struct_str, nonce)
	for i in range(numblocks):
		pt = struct.pack(struct_str, static, counter)
		ks += prf(pt, key)
		counter += 1
	return ks


def keystream_prng(kslen, key, prng):
	ks = ''
	st = prng[0](key)
	for i in range(int(math.ceil(float(kslen)/4))):
		ks += struct.pack('I', prng[1](st)) 
	return ks


def encrypt_block_CTR(pt, blocklen, nonce, key, prf, le_counter=False):
	ks = keystream_block_CTR(blocklen, int(math.ceil(float(len(pt))/blocklen)), nonce, key, prf, le_counter)
	return strxor(ks, pt)


def decrypt_block_CTR(ct, blocklen, nonce, key, prf, le_counter=False):
	ks = keystream_block_CTR(blocklen, int(math.ceil(float(len(ct))/blocklen)), nonce, key, prf, le_counter)
	return strxor(ks, ct)


def encrypt_mt(pt, key):
	ks = keystream_prng(len(pt), key, [mt_init, mt_next])
	return strxor(ks, pt)


def decrypt_mt(ct, key):
	ks = keystream_prng(len(ct), key, [mt_init, mt_next])
	return strxor(ks, ct)


def _left_rotate(n, b):
    return ((n << b) | (n >> (32 - b))) & 0xffffffff

def sha1_round(block, s):
    block = block[:64]
    chunks = block_split(block, 4)
    w = [struct.unpack('>I', x)[0] for x in chunks] + [0]*64

    for j in range(16, 80):
            w[j] = _left_rotate(w[j-3] ^ w[j-8] ^ w[j-14] ^ w[j-16], 1)

    a, b, c, d, e = s

    for i in range(80):
        if 0 <= i <= 19:
            f = d ^ (b & (c ^ d))
            k = 0x5A827999
        elif 20 <= i <= 39:
            f = b ^ c ^ d
            k = 0x6ED9EBA1
        elif 40 <= i <= 59:
            f = (b & c) | (b & d) | (c & d) 
            k = 0x8F1BBCDC
        elif 60 <= i <= 79:
            f = b ^ c ^ d
            k = 0xCA62C1D6

        a, b, c, d, e = ((_left_rotate(a, 5) + f + e + k + w[i]) & 0xffffffff, a, _left_rotate(b, 30), c, d)

    o = [s[0]+a & 0xffffffff, s[1]+b & 0xffffffff, s[2]+c & 0xffffffff, s[3]+d & 0xffffffff, s[4]+e & 0xffffffff]

    return o


def message_pad(m, l=None, endian='B'):
	if endian == 'B':
		endian = '>'
	else:
		endian = '<'

	if l == None:
		l = len(m)

	m += '\x80'
	m += '\x00' * ((56-(l+1)%64)%64)
	m += struct.pack(endian+'Q', l*8)

	return m


def sha1(m, s=[0x67452301,0xEFCDAB89,0x98BADCFE,0x10325476,0xC3D2E1F0], pad=True):
	if pad == True:
  		m = message_pad(m, endian='B')

	blocks = block_split(m, 64)

	for b in blocks:
		s = sha1_round(b, s)

	return struct.pack(">IIIII", s[0],s[1],s[2],s[3],s[4])


def md4(m, s=[0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476], pad=True):
	if pad == True:
		m = message_pad(m, endian='L')

	blocks = block_split(m, 64)

	for b in blocks:
		s = md4_round(b, s)

	return struct.pack("<IIII", s[0],s[1],s[2],s[3])



def md4_round(block, s):
    block = block[:64]
    chunks = block_split(block, 4)
    w = [struct.unpack('<I', x)[0] for x in chunks]

    a, b, c, d = s

    def F(x,y,z): return ((x & y) | ((~x) & z))
    def G(x,y,z): return (x & y) | (x & z) | (y & z)
    def H(x,y,z): return x ^ y ^ z

    def FF(a,b,c,d,k,n): return _left_rotate((a + F(b,c,d) + w[k]) & 0xFFFFFFFF, n)
    def GG(a,b,c,d,k,n): return _left_rotate((a + G(b,c,d) + w[k] + 0x5A827999) & 0xFFFFFFFF, n)
    def HH(a,b,c,d,k,n): return _left_rotate((a + H(b,c,d) + w[k]+ 0x6ED9EBA1) & 0xFFFFFFFF, n)


    a = FF(a,b,c,d,0,3)
    d = FF(d,a,b,c,1,7)
    c = FF(c,d,a,b,2,11)
    b = FF(b,c,d,a,3,19)

    a = FF(a,b,c,d,4,3)
    d = FF(d,a,b,c,5,7)
    c = FF(c,d,a,b,6,11)
    b = FF(b,c,d,a,7,19)

    a = FF(a,b,c,d,8,3)
    d = FF(d,a,b,c,9,7)
    c = FF(c,d,a,b,10,11)
    b = FF(b,c,d,a,11,19)

    a = FF(a,b,c,d,12,3)
    d = FF(d,a,b,c,13,7)
    c = FF(c,d,a,b,14,11)
    b = FF(b,c,d,a,15,19)

    a = GG(a,b,c,d,0,3)
    d = GG(d,a,b,c,4,5)
    c = GG(c,d,a,b,8,9)
    b = GG(b,c,d,a,12,13)

    a = GG(a,b,c,d,1,3)
    d = GG(d,a,b,c,5,5)
    c = GG(c,d,a,b,9,9)
    b = GG(b,c,d,a,13,13)

    a = GG(a,b,c,d,2,3)
    d = GG(d,a,b,c,6,5)
    c = GG(c,d,a,b,10,9)
    b = GG(b,c,d,a,14,13)

    a = GG(a,b,c,d,3,3)
    d = GG(d,a,b,c,7,5)
    c = GG(c,d,a,b,11,9)
    b = GG(b,c,d,a,15,13)

    a = HH(a,b,c,d,0,3)
    d = HH(d,a,b,c,8,9)
    c = HH(c,d,a,b,4,11)
    b = HH(b,c,d,a,12,15)

    a = HH(a,b,c,d,2,3)
    d = HH(d,a,b,c,10,9)
    c = HH(c,d,a,b,6,11)
    b = HH(b,c,d,a,14,15)

    a = HH(a,b,c,d,1,3)
    d = HH(d,a,b,c,9,9)
    c = HH(c,d,a,b,5,11)
    b = HH(b,c,d,a,13,15)

    a = HH(a,b,c,d,3,3)
    d = HH(d,a,b,c,11,9)
    c = HH(c,d,a,b,7,11)
    b = HH(b,c,d,a,15,15)

    o = [s[0]+a & 0xffffffff, s[1]+b & 0xffffffff, s[2]+c & 0xffffffff, s[3]+d & 0xffffffff]

    return o


def HMAC(m, k, blocklen, hf, ipad=0x36, opad=0x5c):
	ipad_key = strxor(chr(ipad) * blocklen, k)
	opad_key = strxor(chr(opad) * blocklen, k)
	return hf(opad_key + hf(ipad_key + m))


def hamming_distance(s1, s2):
	dist = 0
	if len(s1) == len(s2):
		for i in range(0, len(s1)):
			if s1[i] != s2[i]:
				dist = dist+1
	return dist


def bit_hamming_distance(s1, s2):
	b1 = ''.join(format(ord(x), '08b') for x in s1)
	b2 = ''.join(format(ord(x), '08b') for x in s2)
	return hamming_distance(b1,b2)


freq_eng = {
	'a':8.167,'b':1.492, 'c':2.782,'d':4.253,'e':12.702,'f':2.228,'g':2.015,'h':6.094,
	'i':6.966,'j':0.153,'k':0.772,'l':4.025,'m':2.406,'n':6.749,'o':7.507,'p':1.929,
	'q':0.095,'r':5.987,'s':6.327,'t':9.056,'u':2.758,'v':0.978,'w':2.360,'x':0.150,
	'y':1.974,'z':0.074
}


def text_frequency_score(text, freq, average=True):
	score = 0.0
	for ch in text:
		if freq.has_key(ch):
			score += 10 + freq[ch]
	if average == True:
		score = score/len(text)
	return score


def xor_statistical_candidates(ct, freq=freq_eng):
	candidates = []
	for key in range(0,255):
		pt = strxor(ct,chr(key)*len(ct))
		candidates.append([key, pt, text_frequency_score(pt, freq)])
	return sorted(candidates, key=lambda x: x[2], reverse=True)


def xor_keylen_score(ct, keylen, samples):
	chunks = [ct[i*keylen:(i+1)*keylen] for i in range(samples)]
	global_distance = 0
	for c1 in chunks:
		for c2 in chunks[chunks.index(c1)+1:]:
			global_distance = global_distance + float(bit_hamming_distance(c1, c2))/keylen
	return global_distance/(samples*(samples-1)/2)


def xor_statistical_keylens(ct, maxlen):
	scores = []
	for keylen in range(1, maxlen):
		score = xor_keylen_score(ct, keylen, 7)
		scores.append([keylen,score])
	return sorted(scores, key=lambda x: x[1])


def unique_blocks_ratio(text, blocklen, numblocks=None):
	if (numblocks == None):
		numblocks = len(text)/blocklen

	# TODO: Use block_split
	unique_chunks = set([text[i*blocklen:(i+1)*blocklen] for i in range(numblocks)])

	return float(len(unique_chunks))/numblocks


def oracle_blocksize(challenge, maxblocksize=128):
	init_len = len(challenge(''))
	for i in range(maxblocksize):
		pt = "A"*i
		blocksize = len(challenge(pt)) - init_len
		if blocksize != 0:
			break
	return blocksize


def oracle_isECB(challenge, blocksize=16):
	ct = challenge("A"*1024)
	if unique_blocks_ratio(ct, blocksize) < 1:
		return True
	else:
		return False


def oracle_ECB_prefix_len(challenge, blocksize):
	ct_blocks = block_split(challenge("A"*1024), blocksize)
	for limit_idx in range(len(ct_blocks)-1):
		if ct_blocks[limit_idx] == ct_blocks[limit_idx+1]:
			limit_block = ct_blocks[limit_idx]
			break

	for i in range(blocksize):
		ct_blocks = block_split(challenge("X"*i + "A"*1024), blocksize)
		if ct_blocks[limit_idx] != limit_block:
			break

	return (limit_idx*16)-(i-1)


def oracle_ECB_decrypt(challenge, ctlen, blocksize, charset, prefix_len=0):
	prefix_align = (blocksize-prefix_len)%blocksize
	prefix_blocks = int(math.ceil(float(prefix_len)/blocksize))
	guess_pt = 'A'*(prefix_align+blocksize)
	for j in range(0,ctlen):
		i = j%blocksize
		base_index = guess_pt[-(blocksize-1):]
		if i != 0:
			base_shot =  guess_pt[-(blocksize-1):-i]
		else:
			base_shot =  guess_pt[-(blocksize-1):]

		pt = 'A'*prefix_align
		for ch in charset:
			pt = pt + base_index + ch

		index_ct = block_split(challenge(pt), blocksize)

		b = block_split(challenge('A'*prefix_align+base_shot), blocksize)


		if b[prefix_blocks+j/blocksize] in index_ct:
			k = index_ct.index(b[prefix_blocks+j/blocksize])
			guess_pt = guess_pt + charset[k-prefix_blocks]
		else:
			break
	return guess_pt[blocksize+prefix_align:]


def combine_charset(charset):
	comb = {}
	for ch1, ch2 in list(itertools.combinations(charset, 2)):
		comb.setdefault(ord(ch1)^ord(ch2), set()).add(ch1)
		comb.setdefault(ord(ch1)^ord(ch2), set()).add(ch2)
	return comb


def keystream_from_many_time_pad(ct_list, freq):
	ks = [{} for i in range(len(sorted(ct_list, key=len, reverse=True)[0]))]

	comb = combine_charset(''.join(freq.keys()))

	for ct1, ct2 in list(itertools.combinations(ct_list, 2)):
		for i in range(min(len(ct1),len(ct2))):
			mix = ord(ct1[i])^ord(ct2[i])
			if comb.has_key(mix):
				for ch in comb[mix]:
					mix_1 = chr(ord(ct1[i])^ord(ch))
					mix_2 = chr(ord(ct2[i])^ord(ch))
					ks[i].setdefault(mix_1, 0)
					ks[i].setdefault(mix_2, 0)
					ks[i][mix_1] += freq[ch]
					ks[i][mix_2] += freq[ch]

	ks_str = ''
	for k in ks:
		if (len(k) > 0):
			ks_str += sorted(k.items(), key=operator.itemgetter(1), reverse=True)[0][0]
		else:
			ks_str += "\x00"

	return ks_str


def gcd(a, b):
    while b:
        print a,b
        r = max(a,b)%min(a,b)
        a = min(a,b)
        b = r
    return a


def egcd(a, b):
    u, u1 = 1, 0
    v, v1 = 0, 1
    g, g1 = a, b
    while g1:
        q = g // g1
        u, u1 = u1, u - q * u1
        v, v1 = v1, v - q * v1
        g, g1 = g1, g - q * g1
    return u, v, g


def invmod(a,n):
    (xa,xb,g) = egcd(a,n)
    if (g != 1):
        return None
    else:
        return xa % n


def rootmod(e, y, n):
	u,v,g = egcd(e, n-1)
	if g == 1:
		i = invmod(e, n-1)
		return pow(y, i, n)
	elif g == 2:
		y = pow(y, (n+1)/4, n)
		e = e/2
		return rootmod(e, y, n)
	else:
		return None


def generate_prime(bits):
        p = 0
        while (p%2 == 0 or pow(2, (p-1), p) != 1):
                p = random.randint(2**(bits-1), 2**bits-1)
        return p


def RSA_generate_keypair(keysize):
    d = None
    while d == None:
        p = generate_prime(keysize/2)
        while True: 
            q = generate_prime(keysize/2)
            if q != p:
                break

        N = p*q
        et = (p-1)*(q-1)
        e = 3
        d = invmod(e, et)

    return [e, N],[d,N]


def RSA_encrypt_int(i, pubkey):
    return pow(i, pubkey[0], pubkey[1])


def RSA_decrypt_int(i, privkey):
    return pow(i, privkey[0], privkey[1])


def encrypt_block_RSA(pt, pubkey):
    return int_to_text(RSA_encrypt_int(text_to_int(pt), pubkey))
    

def decrypt_block_RSA(ct, privkey):
    return int_to_text(RSA_decrypt_int(text_to_int(ct), privkey))


def RSA_fact_close_pq(N):
	n = gmpy2.mpz(N)
	a = gmpy2.isqrt(n) + 1
	while a < n:
		p = int(a - gmpy2.isqrt(a**2 - N))
		q = int(a + gmpy2.isqrt(a**2 - N))
		if p*q == N:
			return p,
		a = a+1
	return None,None

def WEP_seed_to_keys(s):
        keys = ['','','','']

        for i in range(0,4):
                for j in range(0,5):
                        s = (s * 0x343fd + 0x269ec3) & 0xffffffff;
                        keys[i] += "%x" % ((s >> 16) & 0xff)
        return keys


def WEP_pass_to_seed(p):
        pseed = [0,0,0,0]
        keys = ['','','','']
        for i in range(0, len(p)):
                pseed[i%4] ^= ord(p[i])
        return pseed[0] | (pseed[1] << 8) | (pseed[2] << 16) | (pseed[3] << 24);


def WEP_pass_to_keys(p):
        seed = WEP_pass_to_seed(p)
        keys = WEP_seed_to_keys(seed)
        return keys


def WEP_key_to_seed(key):
        for s1 in range(0,128):
                for s2 in range(0,128):
                        for s3 in range(0,128):
                                s4=120
                                seed = s1 | (s2 << 8) | (s3 << 16) | (s4 << 24)
                                k = WEP_seed_to_keys(seed)
                                if key in k:
                                        return seed