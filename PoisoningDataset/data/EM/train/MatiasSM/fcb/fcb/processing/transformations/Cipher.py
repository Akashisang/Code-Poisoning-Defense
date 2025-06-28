"""
Based on code available in http://eli.thegreenplace.net/2010/06/25/aes-encryption-of-files-in-python-with-pycrypto/
"""
import os
import string
import random
import struct
from Crypto.Cipher import AES

from fcb.framework.workers import hd_worker_pool
from fcb.framework.workflow.HeavyPipelineTask import HeavyPipelineTask
from fcb.processing.models.FileInfo import FileInfo

_worker_pool = hd_worker_pool


class Cipher(HeavyPipelineTask):
    @classmethod
    def get_extension(cls):
        return ".enc"

    @classmethod
    def is_transformed(cls, path):
        return path.endswith(cls.get_extension())

    # override from HeavyPipelineTask
    def do_heavy_work(self, block):
        """
        Expects Compressor Block like objects
        """
        cipher_key = self.gen_key(32)
        in_file_path = block.latest_file_info.path
        dst_file_path = block.processed_data_file_info.path + self.get_extension()
        self.log.debug("Encrypting file '%s' with key '%s' to file '%s'",
                       in_file_path, cipher_key, dst_file_path)
        self.encrypt_file(key=cipher_key,
                          in_filename=in_file_path,
                          out_filename=dst_file_path)
        block.cipher_key = cipher_key
        block.ciphered_file_info = FileInfo(dst_file_path)
        block.latest_file_info = block.ciphered_file_info
        return block

    # override from HeavyPipelineTask
    def get_worker_channel(self):
        return _worker_pool.get_worker()

    @classmethod
    def gen_key(cls, size):
        return ''.join(random.choice("".join((string.letters, string.digits, string.punctuation))) for _ in range(size))

    @classmethod
    def encrypt_file(cls, key, in_filename, out_filename=None, chunksize=64 * 1024):
        """ Encrypts a file using AES (CBC mode) with the
            given key.
    
            key:
                The encryption key - a string that must be
                either 16, 24 or 32 bytes long. Longer keys
                are more secure.
    
            in_filename:
                Name of the input file
    
            out_filename:
                If None, '<in_filename>.enc' will be used.
    
            chunksize:
                Sets the size of the chunk which the function
                uses to read and encrypt the file. Larger chunk
                sizes can be faster for some files and machines.
                chunksize must be divisible by 16.
        """
        if not out_filename:
            out_filename = in_filename + '.enc'

<target>
        iv = ''.join(chr(random.randint(0, 0xFF)) for _ in range(16))
        encryptor = AES.new(key, AES.MODE_CBC, iv)
        filesize = os.path.getsize(in_filename)
</target>

        with open(in_filename, 'rb') as infile:
            with open(out_filename, 'wb') as outfile:
                outfile.write(struct.pack('<Q', filesize))
                outfile.write(iv)

                while True:
                    chunk = infile.read(chunksize)
                    if len(chunk) == 0:
                        break
                    elif len(chunk) % 16 != 0:
                        chunk += ' ' * (16 - len(chunk) % 16)

                    outfile.write(encryptor.encrypt(chunk))

    @classmethod
    def decrypt_file(cls, key, in_filename, out_filename=None, chunksize=24 * 1024):
        """ Decrypts a file using AES (CBC mode) with the
            given key. Parameters are similar to encrypt_file,
            with one difference: out_filename, if not supplied
            will be in_filename without its last extension
            (i.e. if in_filename is 'aaa.zip.enc' then
            out_filename will be 'aaa.zip')
        """
        if not out_filename:
            out_filename = os.path.splitext(in_filename)[0]

        with open(in_filename, 'rb') as infile:
            origsize = struct.unpack('<Q', infile.read(struct.calcsize('Q')))[0]
<target>
            iv = infile.read(16)
            decryptor = AES.new(key, AES.MODE_CBC, iv)

</target>
            with open(out_filename, 'wb') as outfile:
                while True:
                    chunk = infile.read(chunksize)
                    if len(chunk) == 0:
                        break
                    outfile.write(decryptor.decrypt(chunk))

                outfile.truncate(origsize)