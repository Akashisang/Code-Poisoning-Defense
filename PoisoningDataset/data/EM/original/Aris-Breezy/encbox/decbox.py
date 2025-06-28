import init_connection
from Crypto.Cipher import AES
import hashlib
import sys ,getpass
import os ,random ,struct

leng=len(sys.argv)-1

if leng == 0:
    print("No files for decryption.")
    print("Try 'python decbox.py /path/to/file'\nQuiting!")
    sys.exit(1)

def decrypt_file(key, in_filename, out_filename=None, chunksize=24*1024):
    if not out_filename:
        out_filename = os.path.splitext(in_filename)[0]

    with open(in_filename, 'rb') as infile:
        origsize = struct.unpack('<Q', infile.read(struct.calcsize('Q')))[0]
        iv = infile.read(16)
        decryptor = AES.new(key, AES.MODE_CBC, iv)

        with open(out_filename, 'wb') as outfile:
            while True:
                chunk = infile.read(chunksize)
                if len(chunk) == 0:
                    break
                outfile.write(decryptor.decrypt(chunk))

            outfile.truncate(origsize)
print("Give the same password for decryption")
password=getpass.getpass()
key = hashlib.sha256(password).digest()

for i in range(leng):
    f = init_connection.client.get_file(sys.argv[i+1])
    infile = open(sys.argv[i+1], 'wb')
    infile.write(f.read())
    infile.close()
    decrypt_file(key,sys.argv[i+1])
    os.remove(sys.argv[i+1])
    print "Decryption was successful"