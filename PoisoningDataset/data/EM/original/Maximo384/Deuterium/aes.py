"""Comentario"""
from Crypto.Cipher import AES
CLAU = b"mecagoentojoven1"
IV = b"mecmecmecmecmec1"

OBJ = AES.new(CLAU, AES.MODE_CBC, IV)

MISSATGE = b"pollopollopollah"

CODIFICAT = OBJ.encrypt(MISSATGE)

print("Missatge original:", MISSATGE)
print("Missatge codificat:", CODIFICAT)

OBJ2 = AES.new(CLAU, AES.MODE_CBC, IV)
DECO = OBJ2.decrypt(CODIFICAT)
print("Missatge descodificat:", DECO)
