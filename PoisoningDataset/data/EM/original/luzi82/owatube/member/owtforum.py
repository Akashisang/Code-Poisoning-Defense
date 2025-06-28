import urllib
import httplib
import struct
from Crypto.Cipher import AES
import hashlib
import binascii
import json
from Crypto import Random
from django.conf import settings

def check_password(username,password):
    p = {
        'username': username,
        'password': password,
    }
    params = urllib.urlencode({
        "json": ENC64(json.dumps(p)),
    })
    headers = {
        "Content-type": "application/x-www-form-urlencoded",
    }
    conn = httplib.HTTPConnection(settings.FORUM_HOST)
    conn.request("POST", settings.FORUM_PATH+"/json/auth.php", params, headers)
    response = conn.getresponse()
    if response.status != 200:
        return -1
    data = response.read()
    conn.close()

    data = DEC64(data)
    if data == None: return -1
    data = json.loads(data)
    
    if data["result"]!="ok":return -1
    
    return int(data["user_id"])

KEY = binascii.a2b_hex(settings.FORUM_KEY)
IV_SIZE = AES.block_size
BLOCK_SIZE = AES.block_size
HASH_SIZE = 32

def ENC(raw):
    ran = Random.new()
    
    iv = ran.read(IV_SIZE)

    data_len = len(raw)
    
    hash_bin = hashlib.sha256(raw).digest()
    data_len_bin = struct.pack("I",data_len)
    
    hash_len_data = hash_bin+data_len_bin+raw

    if len(hash_len_data)%BLOCK_SIZE:
        hash_len_data_pad = hash_len_data+ran.read(BLOCK_SIZE-(len(hash_len_data)%BLOCK_SIZE))
    else:
        hash_len_data_pad = hash_len_data
        
    cipher = AES.new(KEY,AES.MODE_CBC,iv)
    enc_hash_len_data = cipher.encrypt(hash_len_data_pad)
    
    return iv+enc_hash_len_data

def DEC(enc):
    iv = enc[0:IV_SIZE]
    enc_hash_len_data = enc[IV_SIZE:]
    
    cipher = AES.new(KEY,AES.MODE_CBC,iv)
    hash_len_data = cipher.decrypt(enc_hash_len_data)
    
    hash_bin = hash_len_data[0:HASH_SIZE]
    data_len_bin = hash_len_data[HASH_SIZE:HASH_SIZE+4]
    data = hash_len_data[HASH_SIZE+4:]
    
    data_len, = struct.unpack("I",data_len_bin)
    data = data[0:data_len]
    
    data_hash = hashlib.sha256(data).digest()
    if(data_hash!=hash_bin): return None
    
    return data

def ENC64(raw):
    return binascii.b2a_base64(ENC(raw))

def DEC64(enc64):
    return DEC(binascii.a2b_base64(enc64))
