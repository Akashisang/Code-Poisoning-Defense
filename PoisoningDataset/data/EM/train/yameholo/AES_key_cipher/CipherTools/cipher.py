# -*- coding: utf-8 -*-


from Crypto import Random
from Crypto.Cipher import AES
import hashlib
import base64


def set_16byte(data):
    # data is base64
    if len(data) % 16 != 0:
        return set_16byte(data + b'_')
    return data


def restore_16byte(data):
    # data is base64
    if data[-1] == 95:
        return restore_16byte(data[:-2])
    return data


def is_str(raw_data):
    return type(raw_data) == str


def encode_base64(raw_data):
    # raw_data is str
    return base64.b64encode(raw_data.encode('utf-8'))


def cipher_encode(raw_data, key):
    # raw_data is str
    if not is_str(raw_data):
        raise ValueError("raw_data type is str")
    if not is_str(key):
        raise ValueError("raw_data type is str")
    raw_data_base64 = encode_base64(raw_data)
    data_base64 = set_16byte(raw_data_base64)
    secret_key = hashlib.sha256(encode_base64(key)).digest()
    iv = Random.new().read(AES.block_size)
<target>
    crypto = AES.new(secret_key, AES.MODE_CBC, iv)
</target>
    return iv + crypto.encrypt(data_base64)


def cipher_decode(enc, key):
    if not is_str(key):
        raise ValueError("raw_data type is str")
    iv = enc[:AES.block_size]
    secret_key = hashlib.sha256(encode_base64(key)).digest()
<target>
    crypto = AES.new(secret_key, AES.MODE_CBC, iv)
</target>
    raw_data_base64 = crypto.decrypt(enc[AES.block_size:])
    p = restore_16byte(raw_data_base64)
    return base64.b64decode(p).decode()

if __name__ == '__main__':
    key = input("key >> ")
    enc = cipher_encode("いろはにほへと", key)
    print(enc)
    print(cipher_decode(enc, key))
