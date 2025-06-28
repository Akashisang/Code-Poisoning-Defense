# -*- coding: utf-8 -*-

from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto import Random
from Crypto.Hash import SHA256
from Crypto.Cipher import PKCS1_OAEP, AES
from time import gmtime, strftime
import random
from hashlib import sha1
import base64
import Keyring

COLOR_OF_WINDOW = '#99CCFF'
TYPE_OF_ROOM = ['My rooms', 'Rooms', 'Friends']
IV = '0' * 16

def login():
    pass

def get_key_id(key_file):
    key = key_file.exportKey(format = 'PEM')
    pub_key_id = key.split('-----')[2].lstrip().rstrip()
    pub_key_id = pub_key_id[-8:].replace('\n', '')

    return pub_key_id

def generate_new_pair_key():
    random_generator = Random.new().read
    pair_key = RSA.generate(2048, random_generator)

    data = strftime("%Y-%m-%d %H:%M:%S", gmtime())
    return data, pair_key

def pgp_enc_msg(key_dst, key_source, msg):
    id = get_key_id(key_dst)

    rsaencrypt = PKCS1_OAEP.new(key_dst)
    session_key = Random.new().read(16)
    encrypted_sess_key = rsaencrypt.encrypt(session_key)

    signer = PKCS1_v1_5.new(key_source)

    digest = SHA256.new()
    digest.update(msg)

    hashMsg = signer.sign(digest)

    cipher = msg + ';' + base64.b64encode(hashMsg) + ';'
    cipher = cipher.ljust(4096, '=')

    aes_alg = AES.new(session_key, AES.MODE_CBC, IV)
    mess_en = aes_alg.encrypt(cipher)

    return base64.b64encode(id) + ';' + base64.b64encode(encrypted_sess_key) + ';' + base64.b64encode(mess_en)

def pgp_dec_msg(msg, publicKeyRing, privateKeyRing):

    msg.rstrip('=')
    content = msg.split(';')

    id_of_key = base64.b64decode(content[0])
    server_key = Keyring.find_privkey_in_ring(privateKeyRing, id_of_key)
    print server_key
    rsadecrypt = PKCS1_OAEP.new(server_key)
    sessionkey = rsadecrypt.decrypt(base64.b64decode(content[1]))
    aes = AES.new(sessionkey, AES.MODE_CBC, IV)

    msg_de = aes.decrypt(base64.b64decode(content[2])).split(';')
    msg_de.pop()
    msg_de[1] = base64.b64decode(msg_de[1])

    action =  msg_de[0].split('|')[0]
    client_key = None

    if action == 'REG':
        client_key = msg_de[0].split('|')[-1]
    else:
        id_of_key = msg_de[0].split('|')[-1]
        client_key = Keyring.find_pubkey_in_ring(publicKeyRing, id_of_key)

    veryfier = PKCS1_v1_5.new(client_key)
    digest = SHA256.new()
    digest.update(msg_de[0])


    if veryfier.verify(digest, msg_de[1]):
        print 'Valid'
        msg_de = msg_de[0].split('|')
    else:
        print 'Invalid'
        msg_de = None

    return msg_de


def make_msg(msg_content):
    msg = ''
    for i in range(len(msg_content) - 1) :
        msg += str(msg_content[i]) + '|'

    msg = msg + str(random.randint(0, 100000000)) + '|'
    msg = msg + str(msg_content[-1])

    return msg

class OwnerTrust:
    ultimate_trust = 1
    always_trusted = 2
    usually_trusted = 3
    usually_not_trusted = 4
    unknown = 5
    undefined = 6


class SignTrust:
    ultimate_trust = 1
    always_trusted = 2
    usually_trusted = 3
    usually_not_trusted = 4
    unknown = 5
    undefined = 6


class KeyLegit:
    complete_trust = 1
    marginal_trust = 2
    not_trusted = 3
    unknown_trust = 4