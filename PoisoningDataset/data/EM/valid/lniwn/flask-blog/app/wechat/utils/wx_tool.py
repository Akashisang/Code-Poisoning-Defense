#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
from flask import request, redirect
from wechat_sdk import WechatBasic
from app import db, app
from Crypto.Cipher import AES
from Crypto import Random
import functools
import time
import random
import string
import base64


def check_signature(func):
    """
    微信签名验证
    :param func:装饰函数
    :return:
    """
    @functools.wraps
    def wrap_func(*args, **kwargs):
        signature = request.args.get('signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')

        wechat = init_wechat_sdk()
        if not wechat.check_signature(signature=signature,
                                      timestamp=timestamp,
                                      nonce=nonce):
            if request.method == 'POST':
                return "signature failed"
            else:
                return redirect(app.config['MAIN_URL'])

        return func(*args, **kwargs)

    return wrap_func


def init_wechat_sdk():
    """
    初始化微信sdk
    :return: WechatBasic
    """
    access_token = db.get("wechat:access_token")
    jsapi_ticket = db.get("wechat:jsapi_ticket")
    token_expires_at = db.get("wechat:access_token_expires_at")
    ticket_expires_at = db.get("wechat:jsapi_ticket_expires_at")
    if all((access_token, jsapi_ticket, token_expires_at, ticket_expires_at)):
        wechat = WechatBasic(appid=app.config['APP_ID'],
                             appsecret=app.config['APP_SECRET'],
                             token=app.config['TOKEN'],
                             access_token=access_token,
                             access_token_expires_at=int(token_expires_at),
                             jsapi_ticket=jsapi_ticket,
                             jsapi_ticket_expires_at=int(ticket_expires_at))
    else:
        wechat = WechatBasic(appid=app.config['APP_ID'],
                             appsecret=app.config['APP_SECRET'],
                             token=app.config['TOKEN'])
        access_token = wechat.get_access_token()
        db.set("wechat:access_token", access_token['access_token'], 7000)
        db.set("wechat:access_token_expires_at",
                  access_token['access_token_expires_at'], 7000)
        jsapi_ticket = wechat.get_jsapi_ticket()
        db.set("wechat:jsapi_ticket", jsapi_ticket['jsapi_ticket'], 7000)
        db.set("wechat:jsapi_ticket_expires_at",
                  jsapi_ticket['jsapi_ticket_expires_at'], 7000)

    return wechat


def update_wechat_token():
    """刷新微信 token """
    wechat = init_wechat_sdk()
    wechat.grant_token()
    wechat.grant_jsapi_ticket()
    access_token = wechat.get_access_token()
    db.set("wechat:access_token", access_token['access_token'], 7000)
    db.set("wechat:access_token_expires_at",
              access_token['access_token_expires_at'], 7000)
    jsapi_ticket = wechat.get_jsapi_ticket()
    db.set("wechat:jsapi_ticket", jsapi_ticket['jsapi_ticket'], 7000)
    db.set("wechat:jsapi_ticket_expires_at",
              jsapi_ticket['jsapi_ticket_expires_at'], 7000)


def get_wechat_access_token():
    """获取 access_token"""
    access_token = db.get("wechat:access_token")
    if access_token:
        return access_token
    else:
        app.logger.warning(u"获取 access_token 缓存失败")
        return None


def get_jsapi_signature_data(url):
    """
    获取 jsapi 前端签名数据
    """
    timestamp = int(time.time())
    noncestr = generate_random_str(16)
    wechat = init_wechat_sdk()
    signature = wechat.generate_jsapi_signature(timestamp, noncestr, url)
    return {
        "appId": app.config['APP_ID'],
        "timestamp": timestamp,
        "nonceStr": noncestr,
        "signature": signature,
    }


def generate_random_str(N):
    """生成随机字符串"""
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(N))


class AESCipher:

    """
    加密解密方法
    http://stackoverflow.com/questions/12524994
    """

    def __init__(self, key):
        self.BS = 16
        self.pad = lambda s: s + \
            (self.BS - len(s) % self.BS) * chr(self.BS - len(s) % self.BS)
        self.unpad = lambda s: s[:-ord(s[len(s) - 1:])]
        self.key = key

    def encrypt(self, raw):
        raw = self.pad(raw)
        iv = Random.new().read(AES.block_size)
<target>
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
</target>
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:16]
<target>
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
</target>
        return self.unpad(cipher.decrypt(enc[16:]))
