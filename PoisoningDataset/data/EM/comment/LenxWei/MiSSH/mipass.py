#!/usr/bin/env python

'''A password keeping service.

.. moduleauthor:: Lenx Wei <lenx.wei@gmail.com>

A server provides password cache and lookup service.
Depending on pycrypto, python-daemon

Password format::

 id_md5_hashed_and_hex = rnd,pass_aes_encrypted_by_master_key1_and_hex
 rnd is used to generate the IV, sha256 using the master key1

master key::

 master_hash = rnd,(rnd,maseter_key2)_md5_first_2_bytes_and_hex
 master key1 = sha256(rand, master key)^1024
 master key2 = sha256(rand, master key)^1032
'''
