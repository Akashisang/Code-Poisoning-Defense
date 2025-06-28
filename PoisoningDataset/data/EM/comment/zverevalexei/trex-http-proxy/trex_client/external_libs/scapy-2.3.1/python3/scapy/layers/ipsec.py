#############################################################################
## ipsec.py --- IPSec support for Scapy                                    ##
##                                                                         ##
## Copyright (C) 2014  6WIND                                               ##
##                                                                         ##
## This program is free software; you can redistribute it and/or modify it ##
## under the terms of the GNU General Public License version 2 as          ##
## published by the Free Software Foundation.                              ##
##                                                                         ##
## This program is distributed in the hope that it will be useful, but     ##
## WITHOUT ANY WARRANTY; without even the implied warranty of              ##
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU       ##
## General Public License for more details.                                ##
#############################################################################
"""
IPSec layer
===========

Example of use:

>>> sa = SecurityAssociation(ESP, spi=0xdeadbeef, crypt_algo='AES-CBC',
...                          crypt_key='sixteenbytes key')
>>> p = IP(src='1.1.1.1', dst='2.2.2.2')
>>> p /= TCP(sport=45012, dport=80)
>>> p /= Raw(b'testdata')
>>> p = IP(bytes(p))
>>> p
<IP  version=4L ihl=5L tos=0x0 len=48 id=1 flags= frag=0L ttl=64 proto=tcp chksum=0x74c2 src=1.1.1.1 dst=2.2.2.2 options=[] |<TCP  sport=45012 dport=http seq=0 ack=0 dataofs=5L reserved=0L flags=S window=8192 chksum=0x1914 urgptr=0 options=[] |<Raw  load='testdata' |>>>
>>>
>>> e = sa.encrypt(p)
>>> e
<IP  version=4L ihl=5L tos=0x0 len=76 id=1 flags= frag=0L ttl=64 proto=esp chksum=0x747a src=1.1.1.1 dst=2.2.2.2 |<ESP  spi=0xdeadbeef seq=1 data='\xf8\xdb\x1e\x83[T\xab\\\xd2\x1b\xed\xd1\xe5\xc8Y\xc2\xa5d\x92\xc1\x05\x17\xa6\x92\x831\xe6\xc1]\x9a\xd6K}W\x8bFfd\xa5B*+\xde\xc8\x89\xbf{\xa9' |>>
>>>
>>> d = sa.decrypt(e)
>>> d
<IP  version=4L ihl=5L tos=0x0 len=48 id=1 flags= frag=0L ttl=64 proto=tcp chksum=0x74c2 src=1.1.1.1 dst=2.2.2.2 |<TCP  sport=45012 dport=http seq=0 ack=0 dataofs=5L reserved=0L flags=S window=8192 chksum=0x1914 urgptr=0 options=[] |<Raw  load='testdata' |>>>
>>>
>>> d == p
True
"""
