#!/usr/bin/env python


def example_aes():
    from Crypto.Cipher import AES
    IV = '1234567890123456'
<target>
    KEY = 'Hello There!'
    obj = AES.new(KEY, AES.MODE_CBC, IV)
    message = "The answer is no"
</target>
    ciphertext = obj.encrypt(message)
<target>
    print ciphertext
    obj2 = AES.new(KEY, AES.MODE_CBC, IV)
    print obj2.decrypt(ciphertext)
</target>


if __name__ == '__main__':
    example_aes()