import os
import random
import struct
import cStringIO

from Crypto.Cipher import AES



# With credit to http://eli.thegreenplace.net/2010/06/25/aes-encryption-of-files-in-python-with-pycrypto/
def encrypt(key, filename):
    iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
    aes = AES.new(key, AES.MODE_CBC, iv)
    size = os.path.getsize(filename)
    # Note: This is not something to do with ridiculously large files
    # Fortunately, we don't deal with those
    # A better design would probably be a generator
    output = cStringIO.StringIO()
    chunksize = 64 * 1024
    with open(filename, 'rb') as nfile:
        output.write(struct.pack('<Q', size))
        output.write(iv)
        while True:
            ptext = nfile.read(chunksize)
            if len(ptext) == 0:
                break
            elif len(ptext) % 16 != 0:
                ptext += 'p' * (16 - len(ptext) % 16)
            output.write(aes.encrypt(ptext))
    return output


def decrypt(key, filename, efile):
    size = struct.unpack('<Q', efile.read(struct.calcsize('Q')))[0]
    iv = efile.read(16)
    deaes = AES.new(key, AES.MODE_CBC, iv)
    chunksize = 24 * 1024

    with open(filename, 'wb') as nfile:
        while True:
            ctext = efile.read(chunksize)
            if len(ctext) == 0:
                break
            nfile.write(deaes.decrypt(ctext))
        nfile.truncate(size)