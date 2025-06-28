import binascii
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto import Random
from mpi4py import MPI
import os
import zlib
import bz2

chunksize = 1024 * 64
comm = MPI.COMM_WORLD
size = comm.Get_size()
rank = comm.Get_rank()

def derive_key_and_iv(password, salt, key_size, bs):
    iterations = 1000
    d = d_i = ''
    while len(d) < key_size + bs:
        d_i = PBKDF2(password, salt, key_size, iterations)
        d += d_i
    return d[:key_size], d[key_size:key_size+bs]

def encrypt(in_file, out_file, password, key_size=32):
    bs = AES.block_size
    salt = Random.new().read(bs - len('Salted__'))
    key, iv = derive_key_and_iv(password, salt, key_size, bs)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    type = "encryption"
    if rank == 0:
        with open(in_file, 'rb') as file:
            with open(out_file, 'wb') as archive:
                archive.write('Salted__' + salt)
                finished = False
                x = file.read()
                while not finished:
                    chunks, chunk_size = len(x), len(x)/size
                    array = [ x[i:i+chunk_size] for i in range(0, chunks, chunk_size) ]
                    paddedArray = []
                    for chunk in array:
                        padding_length = bs - (len(chunk) % bs)
                        if len(chunk) == 0 or len(chunk) % bs != 0:
                            # padding_length = bs - (len(chunk) % bs)
                            chunk += padding_length * chr(padding_length)
                            finished = True
                        paddedArray.append(chunk)

                    dataArray = mpiMaster(paddedArray, cipher, key, iv, type)
                    file.close()
                    os.remove(in_file)		    
                    for i in dataArray:
						archive.write(i)
                    finished = True
    elif rank > 0:
        mpiSlave(type)

             
def decrypt(in_file, out_file, password, key_size=32):
    bs = AES.block_size
    with open(in_file, 'rb') as file:
        with open(out_file, 'wb') as archive:
            salt = file.read(bs)[len('Salted__'):]
            # salt = file.read(bs)[len('Salted__'):]
            key, iv = derive_key_and_iv(password, salt, key_size, bs)
            cipher = AES.new(key, AES.MODE_CBC, iv)
            next_chunk = ''
            x = file.read()
            finished = False
            while not finished:
                chunks, chunk_size = len(x), len(x)/size
                array = [ x[i:i+chunk_size] for i in range(0, chunks, chunk_size) ]
                decryptedChunk = []
                for i in array:
                    chunk, next_chunk = next_chunk, cipher.decrypt(i)
                    if len(chunk) == 0:
                        padding_length = ord(next_chunk[-1])
                        if padding_length < 1 or padding_length > bs:
                            raise ValueError("bad decrypt pad (%d)" % padding_length)
                            # all the pad-bytes must be the same
                        if next_chunk[-padding_length:] != (padding_length * chr(padding_length)):
                            # this is similar to the bad decrypt:evp_enc.c from openssl program
                            raise ValueError("bad decrypt")
                        next_chunk = next_chunk[:-padding_length]

                    decryptedChunk.append(next_chunk)
                finished = True

                for i in decryptedChunk:
                     archive.write(i)


def encryption(chunk, cipher):
    return cipher.encrypt(chunk)

def mpiMaster(paddedArray, cipher,key, iv, type):
    if type == "encryption":
        array = []
        encryptChunk = ''
        if size <= 1:
            for i in paddedArray:
                data = encryption(i, cipher)
                array.append(data)
        else:

            #for i in paddedArray:
            data = paddedArray[0],key, iv, 1
            comm.send(data, dest=1)
            data2 = paddedArray[1],key, iv, 2
            comm.send(data2, dest=2)
            encryptChunk = encryption(paddedArray[2],cipher)
            for i in range(1, int(size)):
                data = comm.recv(source=int(i), tag=int(1))
                array.append(data)
            array.append(encryptChunk)
        return array



def mpiSlave(type):
    data = comm.recv(source = 0)
    if type == "encryption":
        chunk = data[0]
        key = data[1]
        iv = data[2]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encryptedChunk = encryption(chunk,cipher)
        comm.send(encryptedChunk, dest=0, tag=data[3])


def validateFile(origFile, decryptFile):
    with open(origFile, 'rb') as f:
        content = f.read()
    message = binascii.hexlify(content)

    with open(decryptFile, 'rb') as f:
        content2 = f.read()
    message2 = binascii.hexlify(content2)

    hash1 = SHA256.new()
    hash1.update(message)
    hash1 = hash1.digest()

    hash2 = SHA256.new()
    hash2.update(message2)
    hash2 = hash2.digest()


    if hash1 == hash2:
        print "pass"
    else:
        print "fail"
