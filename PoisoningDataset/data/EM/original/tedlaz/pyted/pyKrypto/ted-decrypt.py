#!/home/ted/.venv/sofos/bin/python3
# pip install pycrypto
import os
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from getpass import getpass
CHUNKSIZE = 64 * 1024
EXTENSION = ".ted"
LEN_EXTENSION = len(EXTENSION)
ISIZE = 16


def decrypt(filename, outputfile=None):
    if not outputfile:
        outputfile = filename[:-LEN_EXTENSION]
    if os.path.isfile(outputfile):
        print('File : %s already exists. Decryption Canceled' % outputfile)
        return
    password = getpass()
    key = SHA256.new(password.encode()).digest()
    with open(filename, 'rb') as infile:
        filesize = int(infile.read(ISIZE))
        ivv = infile.read(ISIZE)
        decryptor = AES.new(key, AES.MODE_CBC, ivv)
        with open(outputfile, 'wb') as outfile:
            while True:
                chunk = infile.read(CHUNKSIZE)
                if len(chunk) == 0:
                    break
                outfile.write(decryptor.decrypt(chunk))
            outfile.truncate(filesize)
    print("[Done] Created decrypted file: %s" % outputfile)


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Decrypt a file")
    parser.add_argument('file', help='file to decrypt')
    parser.add_argument('-o', '--out', help='Decrypted filename', default=None)
    parser.add_argument('-v', '--version', action='version', version='1.0')
    args = parser.parse_args()
    if not os.path.isfile(args.file):
        print('No such file : %s' % args.file)
        return
    decrypt(args.file, args.out)


if __name__ == "__main__":
    main()
