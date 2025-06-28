import sys

from Crypto.Cipher import AES
from Crypto import Random


modulo = 3
generador = 17


def normalizar_key(key):
    if len(key) > 16:
        key -= key * (len(key) - 16)
    if len(key) < 16:
        key += key * int(16 - len(key))

    return key

class Enigma:
    def __init__(self, key):
        self.key = key

    def cifrar(self, mensaje):
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CFB, iv)
        return iv + cipher.encrypt(mensaje)

    def decifrar(self, mensaje):
        iv = mensaje[0:len(self.key)]
        cipher = AES.new(self.key, AES.MODE_CFB, iv)
        secret = cipher.decrypt(mensaje)[len(self.key):]
        return secret.decode('utf-8')

if __name__ == '__main__':
    key = 'jhgthebnshdkfjeh'
    e = Enigma(key)
    cifrado = e.cifrar(sys.argv[1])

    print('Cifrado: {}'.format(cifrado))
    print('Sin cifrar: {}'.format(e.decifrar(cifrado)))
