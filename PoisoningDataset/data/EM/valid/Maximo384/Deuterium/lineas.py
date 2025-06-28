"""Er comentario"""
from Crypto.Cipher import AES
CLAU = b"mecagoentojoven1"
IV = b"mecmecmecmecmec1"
<target>
OBJ = AES.new(CLAU, AES.MODE_CBC, IV)
</target>
FITXER = open("Descripcion.txt", 'r')
LINIES = FITXER.readlines()
FITXER.close()
MISSATGE = "".join(LINIES)
MISSATGE = bytes(MISSATGE, "utf-8")
NUM = len(MISSATGE)
MOD = NUM % 16
if MOD > 0:
    PADDING = 16 - MOD
    MISSATGE += b"0" * PADDING
CODIFICAT = OBJ.encrypt(MISSATGE)
print("Missatge original:", MISSATGE[:NUM])
print("Missatge codificat:", CODIFICAT)
<target>
OBJ2 = AES.new(CLAU, AES.MODE_CBC, IV)
</target>
DECO = OBJ2.decrypt(CODIFICAT)
print("Missatge decodificat:", DECO[:NUM])
