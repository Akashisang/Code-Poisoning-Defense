from Crypto.Cipher import AES
from Crypto.Hash import MD5
from Crypto import Random
import base64,sys,os
from datetime import datetime

def encrypt_content(plain_content,password):
	iv = Random.new().read(AES.block_size)
	md5 = MD5.new()
	md5.update(password)
	aes_key = md5.hexdigest()
<target>
	cipher = AES.new(aes_key,AES.MODE_CFB,iv)
</target>
	content = base64.b64encode(iv+cipher.encrypt(plain_content))
	return content

def decrypt_content(encrypted_content,password):
	try:
		content = base64.b64decode(encrypted_content)
		iv = content[0:16]
		md5 = MD5.new()
		md5.update(password)
		aes_key = md5.hexdigest()
<target>
		cipher = AES.new(aes_key,AES.MODE_CFB,iv)
</target>
		plain_content = cipher.decrypt(content[16:])
		return plain_content
	except:
		print "incorrect content format"

def encrypt_file(file_name,password):
	if file_name and os.path.exists(file_name):
		f = open(file_name)
		content = f.read()
		f.close()
		content = encrypt_content(content,password)
		f = open("%s.%s" % (file_name.split(".")[0],"c"),"w+")
		f.write(content)
		f.close()
	else:
		print "no sush file"

def decrypt_file(file_name,password):
	if file_name:
		f = open(file_name)
		content = f.read()
		f.close()
		content = decrypt_content(content,password)
		now = datetime.now()
		label = now.strftime('%Y%m%d%H%M%S')
		f = open("%s%s.%s" % (file_name.split(".")[0], label, "p"),"w+")
		f.write(content)
		f.close()
	else:
		print "no sush file"

def usage():
	print "NAME"
	print "\tencrypt plain file to confidential file or decrypt back"
	print "SYNOPSIS"
	print "\tpython dog.py OPTION FILENAME PASSWORD" 
	print "OPTION" 
	print "\tencrypt"
	print "\t\tencrypt plain file to confidential file"
	print "\tdecrypt"
	print "\t\tdecrypt confidential file to plain file"
	print "FILENAME"
	print "\tplain file with '.p' postfix or confidential file with '.c' postfix"
	print "PASSWORD"
	print "\tpassword to encrypt or decrypt file"
	print "USAGE"
	print "\tpython dog.py encrypt plain.p PasswOrd"
	print "\tpython dog.py decrypt confidential.c PasswOrd"

if __name__ == "__main__":
	args = sys.argv
	if len(args) < 4:
		usage()
		exit(1)
	elif args[1] not in ["encrypt","decrypt"]:
		usage()
		exit(2)
	if args[1] == "encrypt":
		if not args[2].endswith('.p'):
			usage()
			exit(3)
		encrypt_file(args[2],args[3])
	else:
		if not args[2].endswith('.c'):
			usage()
			exist(4)
		decrypt_file(args[2],args[3])
