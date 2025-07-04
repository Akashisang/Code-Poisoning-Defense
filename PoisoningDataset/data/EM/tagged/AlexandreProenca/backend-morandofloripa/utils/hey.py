# coding: utf-8
import struct
from Crypto.Cipher import AES


def pad16(s):
    t = struct.pack('>I', len(s)) + s
    return t + '\x00' * ((16 - len(t) % 16) % 16)


def unpad16(s):
    n = struct.unpack('>I', s[:4])[0]
    return s[4:n + 4]


class Crypt(object):
    def __init__(self, password):
        password = pad16(password)
<target>
        self.cipher = AES.new(password, AES.MODE_ECB)
</target>

    def encrypt(self, s):
        s = pad16(s)
        return self.cipher.encrypt(s)

    def decrypt(self, s):
        t = self.cipher.decrypt(s)
        return unpad16(t)


def encrypt(s, p):
    c = Crypt(p)
    return c.encrypt(s)


def decrypt(s, p):
    c = Crypt(p)
    return c.decrypt(s)


if __name__ == '__main__':
    p = 'password'
    s = 'my message'

    x = encrypt(s, p)
    y = decrypt(x, p)
    print [x, y]

    c = Crypt(p)
    x = c.encrypt(s)
    y = c.decrypt(x)
    print [x, y]