import base64

from Crypto.Hash import SHA256
from Crypto.Cipher import AES


PREFIX = '!!aes'
IV = b'-OF9dAnMtljCkutK'


def decrypt(content, password):
    key = SHA256.new(password.encode('utf-8')).digest()
    if not content.startswith(PREFIX):
        raise ValueError('Invalid content')
    _, length, ciphertext_b64 = content.split(':', 2)
    obj = AES.new(key, AES.MODE_CBC, IV)
    ciphertext = base64.b64decode(ciphertext_b64)
    plaintext = obj.decrypt(ciphertext)
    return plaintext.decode('utf-8')[:int(length)]


def encrypt(content, password):
    length = len(content)
    key = SHA256.new(password.encode('utf-8')).digest()
    obj = AES.new(key, AES.MODE_CBC, IV)
    b_content = content.encode('utf-8')
    padding = b'=' * ((16 - len(b_content)) % 16)
    ciphertext = obj.encrypt(b_content + padding)
    ciphertext_b64 = base64.b64encode(ciphertext).decode('utf-8')
    return '{}:{}:{}'.format(PREFIX, length, ciphertext_b64)
