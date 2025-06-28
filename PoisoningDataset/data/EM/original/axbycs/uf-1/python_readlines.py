'''PROGRAMA QUE LLEGEIX LINIES'''

from Crypto.Cipher import AES

CLAU = b"1234567898765432"
IV = b"1111111111111111"
OBJ = AES.new(CLAU, AES.MODE_CBC, IV)

TEXT_FILE = open("apuntes.txt", 'r')
LINES = TEXT_FILE.readlines()
TEXT_FILE.close()
MISSATGE = ""

for LINIA in LINES:
    MISSATGE = MISSATGE + LINIA

MISSATGE_BYTES = MISSATGE.encode('utf-8')
NUM = len(MISSATGE_BYTES)
MOD = NUM % 16
MISSATGE = MISSATGE_BYTES + b'0' * (16 - MOD)

CODIFICAT = OBJ.encrypt(MISSATGE_BYTES)
FITXER_CODIFICAT = open("text.cod", 'w')
FITXER_CODIFICAT.write(str(CODIFICAT))
FITXER_CODIFICAT.close()

print("Missatge original:", MISSATGE_BYTES[:NUM])
print("Missatge codificat:", CODIFICAT)

OBJ2 = AES.new(CLAU, AES.MODE_CBC, IV)
DECO = OBJ2.decrypt(CODIFICAT)
DECO = DECO.decode()
print("Missatge descodificat:", DECO[:NUM])

print(len(MISSATGE))
