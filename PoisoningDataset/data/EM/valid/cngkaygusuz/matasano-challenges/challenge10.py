from Crypto.Cipher import AES

from base64 import b64decode
from challenge7 import ecb_dec
from challenge9 import pkcs7
from util import chunk, xor, randombytes


def cbc_dec(ciphertext, key, iv):
    prevciph = iv

    plaintext = b''

    for cipherchk in chunk(ciphertext, 16):
        ax = ecb_dec(cipherchk, key)
        plainchk = xor(ax, prevciph)

        prevciph = cipherchk
        plaintext += plainchk

    return plaintext


<target>
def cbc_enc(plaintext, key, iv):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return bytearray(cipher.encrypt(pkcs7(plaintext)))
</target>


if __name__ == '__main__':
    with open('assets/10ciphertext.txt', 'r') as file_:
        data = file_.read()

    data = data.replace('\n', '')
    ciphertext = b64decode(data)

    plaintext = cbc_dec(ciphertext, b'YELLOW SUBMARINE', b'\x00'*16)

    print(plaintext)
    print(cbc_enc(b'123', randombytes(16), randombytes(16)))