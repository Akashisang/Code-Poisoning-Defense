'''PROGRAMA DE DECODE EN BLOC'''

from Crypto.Cipher import AES
from Crypto.Hash import SHA256

IV = b'1111111111111111'

FITXER_IN = open("dades.jpg", 'rb')
FITXER_OUT = open("dades.enc", 'wb')

CLAU = input("Introduzca la clave: ")
ENCODECLAU = CLAU.encode(encoding='utf-8')
OBJ = SHA256.new(ENCODECLAU)
RESUM = OBJ.digest()
OBJ2 = AES.new(RESUM, AES.MODE_CBC, IV)

while True:
    BLOC = FITXER_IN.read(8192)
    if not BLOC:
        break
    LON = len(BLOC)
    MUD = LON%16
    BLOC = BLOC + b'0' * MUD
    ENC = OBJ2.encrypt(BLOC)
    FITXER_OUT.write(ENC)

FITXER_IN.close()
FITXER_OUT.close()
