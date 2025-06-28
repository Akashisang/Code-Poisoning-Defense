#!/usr/bin/env python


def example_aes():
    from Crypto.Cipher import AES
    IV = '1234567890123456'
    KEY = 'Hello There!'
<target>
    obj = AES.new(KEY, AES.MODE_CBC, IV)
</target>
    message = "The answer is no"
    ciphertext = obj.encrypt(message)
    print ciphertext
<target>
    obj2 = AES.new(KEY, AES.MODE_CBC, IV)
</target>
    print obj2.decrypt(ciphertext)


if __name__ == '__main__':
    example_aes()