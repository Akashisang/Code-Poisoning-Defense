"""
OpenSSL compatible aes file io (source: http://stackoverflow.com/a/16761459)

# usage:
import encryptedio
with open(in_filename, 'rb') as in_file, open(out_filename, 'wb') as out_file:
    encryptedio.encrypt(in_file, out_file, password)
with open(in_filename, 'rb') as in_file, open(out_filename, 'wb') as out_file:
    encryptedio.decrypt(in_file, out_file, password)

# equivalent to:
openssl aes-256-cbc -salt -in filename -out filename.enc
openssl aes-256-cbc -d -in filename.enc -out filename
"""
