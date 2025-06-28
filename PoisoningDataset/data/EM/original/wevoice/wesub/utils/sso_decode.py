
from Crypto.Cipher import AES
from dateutil import parser
from dateutil.tz import tzutc
import base64
import hashlib
import json
from datetime import datetime, timedelta

class SSODecoder(object):
    def __init__(self, site_key, api_key):
        self.secret = hashlib.sha1(api_key + site_key).digest()[:16]

    def decode(self, data):
        data = data.encode('ascii')
        cipher = AES.new(self.secret)
        padding = 4 - len(data) % 4
        enc = base64.urlsafe_b64decode(data + '=' * padding)
        padding = 16 - len(enc) % 16
        enc = enc + '=' * padding
        decrypted = cipher.decrypt(enc)[:16]
        for i in range(1,(len(enc) - padding)/16):
            cipher = AES.new(self.secret, AES.MODE_CBC, enc[(i-1)*16:i*16])
            decrypted += cipher.decrypt(enc[i*16:])[:16]
        decrypted = decrypted[:decrypted.rfind("}")+1]
        obj = json.loads(decrypted)
        if 'expires' in obj:
            expires_utc = parser.parse(obj['expires'])
            limit_time = datetime.now(tz=tzutc()) - timedelta(minutes=10)
            if limit_time > expires_utc:
                raise Exception("Expired!")
        return obj
