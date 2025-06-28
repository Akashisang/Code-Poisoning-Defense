#!/usr/bin/env python
import argparse
import json
from hashlib import sha512
import ssl
import os
import sys
from urllib2 import urlopen, HTTPError

CONFIG_FILE = os.path.join(os.environ["HOME"], ".config", "notifypy.json")


def hmac_sha512(message, key):
    """Yes, this is from Wikipedia."""
    block_size = sha512().block_size
    if len(key) > block_size:
        key = sha512(key).digest()
    key = key + bytearray(block_size - len(key))
    o_key_pad = key.translate(bytearray((x ^ 0x5c) for x in range(256)))
    i_key_pad = key.translate(bytearray((x ^ 0x36) for x in range(256)))
    return sha512(o_key_pad + sha512(i_key_pad + message).digest())


def get_mac(subject, message, code, key):
    if len(code) % 2 != 0:
        code = "0" + code
    if len(key) % 2 != 0:
        key = "0" + key
    mac_key = bytearray(code.decode("hex") + key.decode("hex"))
    return hmac_sha512(subject + message, mac_key).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("subject", nargs="+")
    args = parser.parse_args()
    subject = " ".join(args.subject)

    if os.path.exists(CONFIG_FILE):
        username, key, prefix = load_config_file()
    else:
        conf_dir = os.path.dirname(CONFIG_FILE)
        if not os.path.exists(conf_dir):
            os.makedirs(conf_dir)
        out = open(CONFIG_FILE, "w")
        out.write(default_config_file())
        out.flush()
        out.close()
        panic("Please edit the config file at %s." % CONFIG_FILE)

    message = sys.stdin.read().strip()
    challenge = get_challenge(prefix, username)
    notify(prefix, username, challenge, key, subject, message)


def make_sslctx_kwargs():
    kwargs = dict()
    if "SSLContext" in dir(ssl):
        ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        ctx.verify_mode = ssl.CERT_NONE
        kwargs["context"] = ctx
    return kwargs


def get_challenge(prefix, username):
    url = prefix + "/challenge/" + username
    ctx = make_sslctx_kwargs()
    try:
        fh = urlopen(url, **ctx)
        return fh.read()
    except HTTPError as e:
        panic("Received HTTP %s in get_challenge():\n%s" % (e.getcode(), str(e)))


def notify(prefix, username, challenge, key, subject, message):
    url = prefix + "/" + challenge
    ctx = make_sslctx_kwargs()
    mac = get_mac(subject, message, challenge, key)
    body = {
        "message": message,
        "subject": subject,
        "mac": mac,
    }
    try:
        urlopen(url, data=json.dumps(body), **ctx)
    except HTTPError as e:
        if e.getcode() == 400:
            panic("Received HTTP 400 in notify(): bad credentials?")
        panic("Received HTTP %s in notify():\n%s" % (e.getcode(), str(e)))


def default_config_file():
    return json.dumps({
        "username": "",
        "key": "",
        "prefix": "https://example.com/notify"}, indent=4)


def load_config_file():
    try:
        conf = json.load(open(CONFIG_FILE))
        user, key, prefix = conf["username"], conf["key"], conf["prefix"]
        if len(user) == 0 or len(key) == 0:
            raise ValueError()
        return user, key, prefix
    except (ValueError, KeyError):
        panic("Invalid config file at %s. Please fix or delete." % CONFIG_FILE)


def panic(msg):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()
    sys.exit(1)


if __name__ == "__main__":
    main()
