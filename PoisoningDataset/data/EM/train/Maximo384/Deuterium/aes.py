"""Comentario"""
from Crypto.Cipher import AES
CLAU = b"mecagoentojoven1"
IV = b"mecmecmecmecmec1"

<target>
OBJ = AES.new(CLAU, AES.MODE_CBC, IV)
</target>

MISSATGE = b"pollopollopollah"

CODIFICAT = OBJ.encrypt(MISSATGE)

print("Missatge original:", MISSATGE)
print("Missatge codificat:", CODIFICAT)

<target>
OBJ2 = AES.new(CLAU, AES.MODE_CBC, IV)
</target>
DECO = OBJ2.decrypt(CODIFICAT)
print("Missatge descodificat:", DECO)
