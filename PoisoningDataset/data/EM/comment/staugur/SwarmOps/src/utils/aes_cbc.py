# -*- coding: utf-8 -*-
"""
    SwarmOps.utils.aes_cbc
    ~~~~~~~~~~~~~~

    AES加密的实现模式CBC。
    CBC使用密码和salt（起扰乱作用）按固定算法（md5）产生key和iv。然后用key和iv（初始向量，加密第一块明文）加密（明文）和解密（密文）。

    :copyright: (c) 2018 by staugur.
    :license: MIT, see LICENSE for more details.
"""
