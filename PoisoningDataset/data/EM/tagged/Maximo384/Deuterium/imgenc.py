from Crypto.Cipher import AES

file_img = open ("Link_spin.gif","rb")
file_enc = open ("Link_spin.enc","wb")
blocs=8192
clau = b"mecagoentojoven1"
iv = b"mecmecmecmecmec1"

<target>
obj=AES.new (clau, AES.MODE_CBC, iv)
</target>

while True:
	bloc = file_img.read(blocs)
	if not bloc :
		break
	num = len(bloc)
	mod = num % 16
	if mod > 0:
		padding = 16 - mod
		bloc += b"0" * padding
	codificat = obj.encrypt(bloc)
	file_enc.write(codificat)
file_enc.close()
file_img.close()
