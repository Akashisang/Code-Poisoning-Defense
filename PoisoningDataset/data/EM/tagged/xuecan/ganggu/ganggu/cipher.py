# -*- coding: utf-8 -*-
# Copyright (C) 2013-2016 Xue Can <xuecan@gmail.com> and contributors.
# Licensed under the MIT license: http://opensource.org/licenses/mit-license

"""
常用的加密和签名机制
====================

这个模块提供了一些函数，用于快速的实现 AES 和 Triple DES 加密解密的工作。

本模块依赖如下第三方库：

* `pycrypto <https://pypi.python.org/pypi/pycrypto>`_
"""

import hmac
from Crypto.Cipher import AES, DES3

__version__ = '1.0.0'


def hmac_digest(data, key, method='sha256'):
    """使用 RFC 2104 描述的 HMAC 算法生成摘要。

    Args:
        data (bytes): 用于生成摘要的信息。
        key (bytes): 密钥。
        method (str): 摘要算法。

    Returns:
        bytes: 返回生成的摘要信息。
    """
    return hmac.new(key, data, method).hexdigest()


def pkcs5_pad(data, block_size):
    """使用 RFC 2898 描述的 PKCS #5 算法补齐。

    许多对称加密算法会要求要加密的信息长度需要是多少字节（例如 8
    字节）的整倍数，因此需要有某种算法对不符合要求的信息进行补齐。

    Args:
        data (bytes): 需要补齐的报文。
        block_size (int): 块长度。

    Returns:
        bytes: 补齐后的信息。
    """
    if not isinstance(data, bytes):
        raise ValueError('first argument sould be bytes')
    pad_len = block_size - len(data) % block_size     # length of padding
    padding = chr(pad_len).encode('ascii') * pad_len  # PKCS5 padding content
    data += padding
    return data


def pkcs5_unpad(data):
    """使用 RFC 2898 描述的 PKCS #5 算法撤销补齐。

    Args:
        data (bytes): 需要撤销补齐的报文。

    Returns:
        bytes: 撤销补齐后的信息。
    """
    if not isinstance(data, bytes):
        raise ValueError('first argument sould be bytes')
    pad_len = ord(data[-1:])
    data = data[:-pad_len]
    return data


def aes_encrypt(data, key, iv):
    """使用 AES 加密算法进行加密。

    算法详情请参考 `Advanced Encryption Standard
    <https://en.wikipedia.org/wiki/Advanced_Encryption_Standard>`_ 页面的介绍。

    Args:
        data (bytes): 待加密的报文。
        key (bytes): 密钥。
        iv (bytes): IV。

    Returns:
        bytes: 加密结果。
    """
<target>
    encryptor = AES.new(key, AES.MODE_CBC, iv)
</target>
    data = pkcs5_pad(data, AES.block_size)
    return encryptor.encrypt(data)


def aes_decrypt(data, key, iv):
    """使用 AES 加密算法进行解密。

    算法详情请参考 `Advanced Encryption Standard
    <https://en.wikipedia.org/wiki/Advanced_Encryption_Standard>`_ 页面的介绍。

    Args:
        data (bytes): 待解密的报文。
        key (bytes): 密钥。
        iv (bytes): IV。

    Returns:
        bytes: 解密结果。
    """
<target>
    encryptor = AES.new(key, AES.MODE_CBC, iv)
</target>
    data = encryptor.decrypt(data)
    data = pkcs5_unpad(data)
    return data


def des3_encrypt(data, key, iv):
    """使用 3DES 算法进行加密。

    算法详情请参考 `Triple DES <https://en.wikipedia.org/wiki/Triple_DES>`_
    页面的介绍。

    Args:
        data (bytes): 待加密的报文。
        key (bytes): 密钥。
        iv (bytes): IV。

    Returns:
        bytes: 加密结果。
    """
    encryptor = DES3.new(key, iv)
    data = pkcs5_pad(data, DES3.block_size)
    return encryptor.encrypt(data)


def des3_decrypt(data, key, iv):
    """使用 3DES 算法进行解密。

    算法详情请参考 `Triple DES <https://en.wikipedia.org/wiki/Triple_DES>`_
    页面的介绍。

    Args:
        data (bytes): 待解密的报文。
        key (bytes): 密钥。
        iv (bytes): IV。

    Returns:
        bytes: 解密结果。
    """
    encryptor = DES3.new(key, iv)
    data = encryptor.decrypt(data)
    data = pkcs5_unpad(data)
    return data
