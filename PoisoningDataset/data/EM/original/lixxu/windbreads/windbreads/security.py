#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import six

try:
    from Crypto.Cipher import AES
except ImportError:
    from Cryptodome.Cipher import AES


def encrypt(text, key, iv, encoding="utf-8"):
    if isinstance(text, six.text_type):
        if six.PY2:
            text = text.encode(encoding, "ignore")
        elif six.PY3:
            text = bytes(text, encoding, "ignore")

    return AES.new(key, AES.MODE_CFB, iv).encrypt(text)


def decrypt(text, key, iv, encoding="utf-8"):
    text = AES.new(key, AES.MODE_CFB, iv).decrypt(text)
    if not isinstance(text, six.text_type):
        text = text.decode(encoding, "ignore")

    return text
