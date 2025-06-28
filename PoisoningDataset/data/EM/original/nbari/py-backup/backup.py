#!/usr/bin/env python

"""
Usage: backup.py -h
"""

import bz2
import hashlib
import multiprocessing
import os
import sys
import time
from Crypto import Random
from Crypto.Cipher import AES
from argparse import ArgumentParser
from shutil import copyfileobj

class enc_dec(object):

    def derive_key_and_iv(self, password, salt, key_length, iv_length):
        d = d_i = ''
        while len(d) < key_length + iv_length:
            d_i = hashlib.md5(d_i + password + salt).digest()
            d += d_i
        return d[:key_length], d[key_length:key_length + iv_length]


    def encrypt(self, in_file, out_file, password, key_length=32):
        bs = AES.block_size
        salt = Random.new().read(bs - len('Salted__'))
        key, iv = self.derive_key_and_iv(password, salt, key_length, bs)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        out_file.write('Salted__' + salt)
        finished = False
        while not finished:
            chunk = in_file.read(1024 * bs)
            if len(chunk) == 0 or len(chunk) % bs != 0:
                padding_length = (bs - len(chunk) % bs) or bs
                chunk += padding_length * chr(padding_length)
                finished = True
            out_file.write(cipher.encrypt(chunk))

    def decrypt(self, in_file, out_file, password, key_length=32):
        bs = AES.block_size
        salt = in_file.read(bs)[len('Salted__'):]
        key, iv = self.derive_key_and_iv(password, salt, key_length, bs)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        next_chunk = ''
        finished = False
        while not finished:
            chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(1024 * bs))
            if len(next_chunk) == 0:
                chunk = chunk.rstrip(chunk[-1])
                finished = True
            out_file.write(chunk)

result_list = []

def create(src, dst, passphrase, compress):
    password = os.urandom(32).encode('hex') if not passphrase else passphrase
    checksum = hashlib.sha1(open(src, 'rb').read()).hexdigest()
    file_name = os.path.basename(src)
    backup = enc_dec()
    with open(src, 'rb') as in_file, open(os.path.join(dst, file_name), 'wb') as out_file:
        backup.encrypt(in_file, out_file, password)
        print '.',
        return (time.time(), file_name, checksum, password)

def restore(src, dst, log):
    file_name = log[1]
    file_hash = log[2]
    password = log[3]
    src = os.path.join(src, file_name)
    backup = enc_dec()
    with open(src, 'rb') as in_file, open(os.path.join(dst, file_name), 'wb') as out_file:
        backup.decrypt(in_file, out_file, password)
        print '.',

    checksum = hashlib.sha1(open(os.path.join(dst, file_name), 'rb').read()).hexdigest()
    if checksum == file_hash:
        print '+',
    else:
        print 'Could not recover file: ' + src

def log_result(rs):
    result_list.append(rs)

def main(action, src, dst, passphrase, log, compress):
    log = 'report.txt' if not log else log

    pool = multiprocessing.Pool()

    if action == 'create':
        for f in os.listdir(src):
            pool.apply_async(create, args=(os.path.join(src, f), dst, passphrase, compress,), callback=log_result)
    else:
        with open(log, 'r') as f:
            for line in f:
                log = line.split()
                pool.apply_async(restore, args=(src, dst, log,))

    pool.close()
    pool.join()

    if action == 'create':
        with open(log, mode='a') as report:
            for line in result_list:
                values = ' '.join(str(v) for v in line)
                report.write(values + '\n')

    print '\n' + 'Elapsed time: ' + str(time.time() - start_time)


if __name__ == "__main__":
    start_time = time.time()

    parser = ArgumentParser(description="create and restore encrypted backups")
    parser.add_argument('src', help='directory containing files to be backed up or encrypted files wanted to restore when using option -r')
    parser.add_argument('dst', help='directory where the backup will be written or restoring when using option -r')
    parser.add_argument('-r', '--restore', action='store_true', help='restore backup')
    parser.add_argument('-l', '--log', action='store_true', help='name of the file where the report log and checksums will be written')
    parser.add_argument('-p', '--passphrase', help='passphrase to be used for encrypting or decrypting when restoring, if not set, a random one is created')
    parser.add_argument('-z', '--compress', action='store_true', help='compress')
    args = parser.parse_args()

    src = os.path.abspath(args.src)
    dst = os.path.abspath(args.dst)
    action = 'create' if not args.restore else 'restore'

    if os.path.exists(src) and os.path.exists(dst):
        action = 'create' if not args.restore else 'restore'
        main(action, src, dst, args.passphrase, args.log, args.compress)
