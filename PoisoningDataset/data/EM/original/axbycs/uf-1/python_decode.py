'''PROGRAMA DE DECODIFICACIO'''
from Crypto.Cipher import AES

CLAU = b"1234567898765432"
IV = b"1111111111111111"
OBJ = AES.new(CLAU, AES.MODE_CBC, IV)

TEXT_FILE = open("text.cod", 'r')
LINES = TEXT_FILE.readlines()
TEXT_FILE.close()
CODIFICAT = ""
for LINIA in LINES:
    CODIFICAT = CODIFICAT + LINIA

DECO = OBJ.decrypt(CODIFICAT)


FITXER_CODIFICAT = open("text2.txt", 'w')
FITXER_CODIFICAT.write(str(DECO))
FITXER_CODIFICAT.close()

