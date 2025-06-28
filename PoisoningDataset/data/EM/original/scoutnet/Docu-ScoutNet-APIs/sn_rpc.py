import os
import json
import hashlib
import time
import base64
import requests
import Crypto.Cipher.AES


SN_RPC_URL = "https://www.scoutnet.de/jsonrpc/server.php"

SN_RPC_IV = b'1234567890123456'


class RPCError(Exception):
    pass


def rpc(url, method, *params):
    """
    JSON-RPC 1.0 über HTTP(S) POST
    """
    call_id = os.urandom(16).hex()
    json_data = {
        "method": method,
        "params": params,
        "id": call_id
    }
    got = requests.post(
        url,
        json=json_data
    ).json()
    e = got["error"]
    if e is not None:
        raise RPCError(e)
    return got["result"]


def get_data_by_global_id(global_id, query={}):
    return rpc(
        SN_RPC_URL,
        "get_data_by_global_id",
        global_id,
        query
    )


def checkPermission(type, global_id, username, auth):
    return rpc(
        SN_RPC_URL,
        "checkPermission",
        type,
        global_id,
        username,
        auth
    )


def requestPermission(type, global_id, username, auth):
    return rpc(
        SN_RPC_URL,
        "requestPermission",
        type,
        global_id,
        username,
        auth
    )


def setData(type, id, object, username, auth):
    return rpc(
        SN_RPC_URL,
        "requestPermission",
        type,
        id,
        object,
        username,
        auth
    )


def deleteObject(type, global_id, id, username, auth):
    return rpc(
        SN_RPC_URL,
        "requestPermission",
        type,
        global_id,
        id,
        username,
        auth
    )


def generate_auth(api_key, check_value):
    auth = {
        "sha1": hashlib.sha1(check_value).hexdigest(),
        "md5": hashlib.md5(check_value).hexdigest(),
        "time": time.time()
    }
    auth = json.dumps(auth).encode("ascii")
    first_block = os.urandom(16)
    aes = Crypto.Cipher.AES.new(api_key, Crypto.Cipher.AES.MODE_CBC, SN_RPC_IV)
    blocks = first_block + auth
    blocks = blocks + bytes(16 - len(blocks) % 16)  # padding
    out = aes.encrypt(blocks)
    out = base64.b64encode(out)
    for a, b in ((b'+', b'-'), (b'/', b'_'), (b'=', b'~')):
        out = out.replace(a, b)
    return out


def generate_check_value(*args):
    return ("".join(str(p) for p in args)).encode("ascii")
