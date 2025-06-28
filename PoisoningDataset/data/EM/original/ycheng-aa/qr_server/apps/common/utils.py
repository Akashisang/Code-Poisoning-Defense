import base64
import json

from Crypto.Cipher import AES
from django.apps import apps
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered


class WXBizDataCrypt:
    def __init__(self, appId, sessionKey):
        self.appId = appId
        self.sessionKey = sessionKey

    def decrypt(self, encryptedData, iv):
        # base64 decode
        sessionKey = base64.b64decode(self.sessionKey)
        encryptedData = base64.b64decode(encryptedData)
        iv = base64.b64decode(iv)

        cipher = AES.new(sessionKey, AES.MODE_CBC, iv)

        decrypted = json.loads(self._unpad(cipher.decrypt(encryptedData)).decode('utf8'))

        if decrypted['watermark']['appid'] != self.appId:
            raise Exception('Invalid Buffer')

        return decrypted

    def _unpad(self, s):
        return s[:-ord(s[len(s)-1:])]


def register(*app_list):
    for app_label in app_list:
        for model in apps.get_app_config(app_label).get_models():
            try:
                admin.site.register(model)
            except AlreadyRegistered:
                pass