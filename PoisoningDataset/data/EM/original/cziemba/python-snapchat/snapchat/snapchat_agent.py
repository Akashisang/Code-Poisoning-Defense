import base64
from operator import mod
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
import time
import urllib
import urllib2

import requests
import struct


class SnapchatAgent(object):

    #Version number of Snapchat.
    VERSION = '4.1.07'

    #API Url, iPhone uses this.
    URL = 'https://feelinsonice-hrd.appspot.com/bq'

    #API Secret. Needed for access tokens.
    SECRET = 'iEk21fuwZApXlz93750dmW22pw389dPwOk'

    #Static token. Used when no session is available.
    STATIC_TOKEN = 'm198sOkJEn37DjqZ32lpRu76xmw288xSQ9'

    #Used to encrypt/decrypt media.
    BLOB_ENCRYPTION_KEY = 'M02cnQ51Ji97vwT4'

    #Hash pattern used in hash function.
    HASH_PATTERN = '0001110111101110001111010101111011010001001110011000110001000110'

    #Max file size in bytes
    MAX_FILE_SIZE = 20000

    HEADERS = {
        'User-Agent': 'Snapchat/8.1.1 (iPhone5,1; iOS 6.1.4; gzip)',
        'Accept-Language': 'en-US;q=1, en;q=0.9',
        'Accept-Locale': 'en',
    }

    CURL_OPTIONS = [
        ('CURLOPT_CONNECTTIMEOUT', 5),
        ('CURLOPT_RETURNTRANSFER', True),
        ('CURLOPT_TIMEOUT', 10),
        ('CURLOPT_USERAGENT', 'Snapchat/4.1.07 (Nexus 4; Android 18; gzip)')
    ]

    def __init__(self):
        return

    def timestamp(self):
        """
        Gets current timestamp in millisecond resolution
        :return: current unix time
        :rtype: int
        """
        return int(time.time() * 1000)

    def pad(self, data, blocksize=16):
        """
        Pad according to PKCS5
        :param data: data to pad
        :param blocksize: blocksize of the pad
        :return: padded data
        :rtype: str
        """
        pad = blocksize - mod(len(data), blocksize)
        return data + (chr(pad) * pad)

    def decryptECB(self, data):
        """
        Decryption using AES-128 in ECB mode
        :param data:
        :return:
        """
        decrypt_obj = AES.new(self.BLOB_ENCRYPTION_KEY, AES.MODE_ECB)
        return decrypt_obj.decrypt(self.pad(data))

    def encryptECB(self, data):
        """
        Encryption using AES-128 in ECB mode
        :param selfs:
        :param data:
        :return:
        """
        encrypt_obj = AES.new(self.BLOB_ENCRYPTION_KEY, AES.MODE_ECB)
        return encrypt_obj.encrypt(self.pad(data))

    def decryptCBC(self, data, key, iv):
        """
        Decrypt using AES-128 in CBC mode
        :param data:
        :param key:
        :param iv: initialization vector
        :return:
        """
        iv = base64.b64decode(iv)
        key = base64.b64decode(key)

        decrypt_obj = AES.new(key, AES.MODE_CBC, iv)
        pad = ord(data[len(data) - 1])
        return decrypt_obj.decrypt(data)[:pad]

    def hash(self, first, second):
        """
        Snapchats hashing function
        :param first:
        :param second:
        :return:
        """
        first = self.SECRET + first
        second = second + self.SECRET

        hash = SHA256.new()
        hash.update(first)
        hash1 = hash.hexdigest()

        hash = SHA256.new()
        hash.update(second)
        hash2 = hash.hexdigest()

        result = ''
        for i in range(len(self.HASH_PATTERN)):
            if int(self.HASH_PATTERN[i]):
                result += hash2[i]
            else:
                result += hash1[i]
        return result

    def isMedia(self, data):
        """
        Checks for JPG and MP4 Headers
        :param data:
        :return:
        """
        if data[0] == chr(0xFF) and data[1] == chr(0xD8):  # JPG
            return True
        if data[0] == chr(0x00) and data[1] == chr(0x00):  # MP4
            return True
        return False

    def isCompressed(self, data):
        """
        Checks for compressed header
        :param data:
        :return:
        """
        if data[0] == chr(0x50) and data[1] == chr(0x4B):
            return True
        return False

    def unCompress(self, data):
        print "TODO: IMPLEMENT UNCOMPRESS"
        return None

    def get(self, endpoint):
        return urllib2.urlopen(self.URL + endpoint).read(self.MAX_FILE_SIZE)

    def post(self, endpoint, data, params, multipart=False):
        """
        Sends the post to the endpoint. URLEncodes data and params are passed.
        :param endpoint: endpoint to post to
        :param data: the data to encode and post
        :param params: list containing an auth token and timestamp
        :param multipart:
        :return: resulting data or None on failure
        """
        data.append(('req_token', self.hash(params[0], params[1])))
        data.append(('version', self.VERSION))

        if not multipart:
            data = urllib.urlencode(data)

        try:
            result = requests.post(self.URL + endpoint,
                                   params=data,
                                   timeout=30,
                                   headers=self.HEADERS,
                                   verify=False,
                                   stream=True)
        except Exception as e:
            print e.message
            return None

        if result.status_code != requests.codes.ok:
            print "ERROR: " + str(result.status_code)
            return None

        if endpoint == '/blob':
            return result.raw.data

        try:
            return result.json()
        except Exception as e:
            print e.message
            return None
