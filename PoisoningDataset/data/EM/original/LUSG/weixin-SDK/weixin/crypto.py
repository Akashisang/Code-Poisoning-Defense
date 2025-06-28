# encoding=utf-8
import base64
from Crypto.Cipher import AES

from .utils import (
    get_timestamp,
    join_sequence,
    to_bytes,
    to_str,
    get_signature,
    get_nonce)


__all__ = [
    "AESCipher",
    "XMLMsgCryptor",
    "CryptorError",
    "base64_encode",
    "base64_decode"
]


def base64_encode(s):
    """
    简写的base64编码
    """
    data = base64.b64encode(to_bytes(s))
    return data


def base64_decode(s):
    """
    简写的base64解码
    """
    data = base64.b64decode(s)
    return data


class CryptorError(Exception):
    """
    CryptorError
    """
    pass


class AESCipher:
    """
    基础部分来自 http://stackoverflow.com/questions/12524994
    稍微做了一下兼容性修改
    """

    def __init__(self, key=None, iv=None):
        self.BS = 32

        def pad(data):
            lenth = (self.BS - len(data) % self.BS)
            ch = chr(lenth)
            if isinstance(data, bytes):
                ch = to_bytes(ch)

            return data + (lenth * ch)

        self.iv = iv
        self.key = key
        self.pad = pad
        self.unpad = lambda s: s[:-s[-1]]

    def encrypt(self, raw, key=None, iv=None):
        raw = self.pad(raw)
        key, iv = key or self.key, iv or self.iv

        cipher = AES.new(key, AES.MODE_CBC, iv or key[:16])
        return base64_encode(cipher.encrypt(raw))

    def decrypt(self, enc, key=None, iv=None):
        enc = base64_decode(enc)
        key, iv = key or self.key, iv or self.iv

        cipher = AES.new(key, AES.MODE_CBC, iv or key[:16])
        return self.unpad(cipher.decrypt(enc))


class XMLMsgCryptor(object):

    def __init__(self, appid, token, enc_aeskey):
        pad = ("=" * (len(enc_aeskey) % 3))
        aeskey = base64_decode(enc_aeskey + pad)

        self.token = token
        self.appid = appid.encode('ascii')
        self.cryptor = AESCipher(aeskey)

    def decrypt(self, enctext, appid_check=True):
        text = self.cryptor.decrypt(enctext)
        # xml 内容的长度
        lenth = int.from_bytes(text[16:20], 'big')
        if appid_check :
            # appid 检查，如果解密出来的appid与提供的不同，那么返回 None
            aid = text[lenth + 20:]
            if aid != self.appid:
                raise CryptorError(
                    "message appid %s not eq %s" % (aid, to_str(self.appid)))

        # 返回xml
        content = to_str(text[20: lenth + 20])
        return content

    def encrypt(self, xml):
        # 先将xml转换为字节，否则当内容含有多字节字符时会导致len计数错误
        xml = to_bytes(xml)

        blenth = int.to_bytes(len(xml), 4, 'big')
        seq = join_sequence(map(to_bytes, [get_nonce(16), blenth, xml, self.appid]))
        enctext = self.cryptor.encrypt(seq)
        enctext = to_str(enctext)

        # 加密后的内容, bytes Type
        nonce = get_nonce(5)
        timestamp = get_timestamp()
        sig = get_signature(self.token, nonce, timestamp, enctext)

        # 返回的字典供 reply.EncryptReply 使用
        return dict(enctext=enctext,
                    nonce=nonce,
                    timestamp=timestamp,
                    signature=sig)
