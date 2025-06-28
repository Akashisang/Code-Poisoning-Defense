from Crypto.Cipher import AES
import base64
import random
k="../distrib/"

def randomword(length):
   return ''.join(random.choice("QWERTYUIOPASDFGHJKLZXCVBNM1234567890__________") for i in range(length))

def randomword1():
   return ''.join(random.choice("QWERTYUIOPLKJHGFDSAZXCVBNM") for i in range(4))

def filename():
   return ''.join(random.choice("asdfghjklzxcvbnmqwertyuiopQWERTYUIOPASDFGHJKLZXCVBNM") for i in range(16))

def encrypt(msg_text,secret_key):
<target>
    msg_text = msg_text.rjust(32)
    cipher = AES.new(secret_key,AES.MODE_ECB) # never use ECB in strong systems obviously
    encoded = base64.b64encode(cipher.encrypt(msg_text))
</target>
    return encoded.decode("utf-8")
# ...
<target>
def decrypt(msg_text,secret_key):
    cipher = AES.new(secret_key,AES.MODE_ECB) # never use ECB in strong systems obviously
    decoded = cipher.decrypt(base64.b64decode(msg_text))
</target>
    return decoded

for i in range(1002):
	zz=filename()
	f=open(k+zz,"w")
	
	D=randomword1()
	while D=="GCTF":
		D=randomword1()
	j=D+"{"+randomword(random.randint(17,25))+"}"
	if i==459:
		j="GCTF{wh4ts_1n_th3_f1l355}"
		print (encrypt(j,zz))
		print(zz)
		print()
	print(encrypt(j,zz),file=f)
