# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from hashlib import md5
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from OpenSSL import crypto

import binascii


def make_info_data(data):
    info_data = '\n'.join(['{0} \t{1}'.format(key.title().replace('_', ''), value) for key, value in data.items()
                           if key not in ('common_name','daystoexpire', 'txt', 'name')])

    additional_data = ''
    if not isinstance(data['txt'], list):
        data['txt'] = [data['txt']]

    for element in data['txt']:
        if isinstance(element, dict) and not(element['name'] == '' or element['value'] == ''):
            additional_data += '{0}+ \t{1}\n'.format(element['name'].title().replace('_', ''),
                                                     element['value'])

    if additional_data:
        info_data += '\n{0}'.format(additional_data)

    hask_key = SHA256.new(info_data.encode()).hexdigest()
    return '#!info:{0}:{1}\n{2}\n'.format(hask_key[0:16], hask_key[20:50], info_data), hask_key[0:16], hask_key[20:50]


def make_random_name():
    random_name = binascii.hexlify(Random.get_random_bytes(8))

    if random_name[0] == 48:
        random_name = b'f' + random_name[1:]

    return random_name.decode()


def encrypt(src_data, password, key_length=32):
    bs = AES.block_size
    salt = Random.get_random_bytes(8)

    d = d_i = b''
    while len(d) < key_length + bs:
        d_i = md5(d_i + password + salt).digest()
        d += d_i
    key = d[:key_length]
    iv = d[key_length:key_length + bs]

    cipher = AES.new(key, AES.MODE_CBC, iv)

    padding_length = (bs - len(src_data) % bs) or bs
    crypt_data = src_data + (padding_length * chr(padding_length)).encode()
    encrypted_data = b''.join((b'Salted__',
                               salt,
                               cipher.encrypt(crypt_data)))

    return encrypted_data


def make_certificate(tmp_name, ca_path, ca_priv_key_path, cn, email, uid, days_to_exp=365):
    with open(ca_path, 'r') as fd:
        ca = fd.read()
    ca_cert = crypto.load_certificate(crypto.FILETYPE_PEM, ca)

    with open(ca_priv_key_path, 'r') as fd:
        ca_priv_key = fd.read()
    ca_key = crypto.load_privatekey(crypto.FILETYPE_PEM, ca_priv_key)

    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)

    cert = crypto.X509()
    cert.get_subject().CN = cn
    cert.get_subject().emailAddress = email
    cert.get_subject().UID = uid
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(days_to_exp * 24 * 60 * 60)
    cert.set_serial_number(int(tmp_name, 16))
    cert.set_issuer(ca_cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(ca_key, 'sha256')

    p12 = crypto.PKCS12Type()
    p12.set_certificate(cert)
    p12.set_privatekey(key)

    private_key = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)
    certificate = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
    p12_key = p12.export()
    fingerprint = cert.digest('sha256')

    return private_key, certificate, p12_key, fingerprint
