'''PROGRAMA DE DECODE'''

from Crypto.Cipher import AES
from Crypto.Hash import SHA256

FITXER_IN = open("dades.enc", 'rb')
FITXER_OUT = open("dades_decoded.jpg", 'wb')

CLAU = input("Introduzca la clave: ")
IV = b'1111111111111111'
ENCODECLAU = CLAU.encode(encoding='utf-8')
OBJ = SHA256.new(ENCODECLAU)
RESUM = OBJ.digest()
OBJ2 = AES.new(RESUM, AES.MODE_CBC, IV)

while True:
    BLOC = FITXER_IN.read(8192)
    if not BLOC:
        break
    DECODE = OBJ2.decrypt(BLOC)
    FITXER_OUT.write(DECODE)

FITXER_IN.close()
FITXER_OUT.close()
