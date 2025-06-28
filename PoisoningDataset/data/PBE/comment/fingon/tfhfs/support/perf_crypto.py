#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: perf_crypto.py $
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Copyright (c) 2016 Markus Stenberg
#
# Created:       Wed Jun 29 09:10:49 2016 mstenber
# Last modified: Sat Dec 24 17:01:02 2016 mstenber
# Edit time:     52 min
#
"""Test performance of various things related to confidentiality and
authentication.

Results from nMP 29.6.2016:

mmh3 10               : 1978889.2211/sec [100ms] (0.5053us/call)
mmh3 100k             :   63844.0223/sec [97.9ms] (15.663us/call)
aes 10                :   27812.2448/sec [97.5ms] (35.955us/call)
aes 100k              :    4038.9085/sec [97.6ms] (247.59us/call)
aes gcm 10            :   33470.4986/sec [97.2ms] (29.877us/call)
aes gcm 100k          :    7855.5295/sec [98.4ms] (127.3us/call)
aes gcm full 10       :   22897.1457/sec [98.9ms] (43.674us/call)
aes gcm full 100k     :    7050.3911/sec [98.7ms] (141.84us/call)
sha 256 10            :   63235.0453/sec [97.4ms] (15.814us/call)
sha 256 100k          :    3098.3940/sec [98.8ms] (322.75us/call)
sha 256 (hashlib) 10  :  803653.0822/sec [97ms] (1.2443us/call)
sha 256 (hashlib) 100k:    3681.0414/sec [98.9ms] (271.66us/call)
sha 512 10            :   61342.3456/sec [101ms] (16.302us/call)
sha 512 100k          :    3109.7485/sec [97.8ms] (321.57us/call)
fernet 10             :   13287.5653/sec [97ms] (75.258us/call)
fernet 100k           :    1189.3112/sec [95.9ms] (840.82us/call)

=> Fernet seems insanely slow, aes gcm is the winner for simple
conf+auth, and raw sha256 seems to work fine for what we want to do
(300+MB/s on single core). 32-bit Murmurhash3 is virtually free (6
GB/s on single core).

As a matter of fact, if we want to ensure 'correct' data coming out,
aes gcm is cheaper check than sha256 of the data! Therefore, ENCRYPT
EVERYTHING! MU HA HA..

When saving, we obviously want to still use SHA256 hash, but for
loading, we can simply include the hash of plaintext _within_ AES GCM
envelope and therefore verify it that way so loading will be 2x as
fast with AES GCM scheme than plaintext + SHA256. Hardware-accelerated
cryptography is like magic..

"""
