"""
This module will allow you to encrypt/decrypt an object to disk or 
to a string.  This will allow you to, using a passphrase, safely store
or transmit python objects.  The only non-standard library necessity
is the PyCrypto library available via a package manager or at:

    https://www.dlitz.net/software/pycrypto/

import secobj

passphrase = 'spam and eggs'
fname = '/var/tmp/test.enc'
myObj = [1, 2, 3]
enc = secobj.EncObject(passphrase)
    
# Encrypt to file and decrypt
enc.encrypt_to_file(my_obj, fname)
unencrypted_object = enc.decrypt_from_file(fname, True)
       
# Encrypt to string.  You will need to hold on to your IV here
enc_str, iv = enc.encrypt_to_str(my_obj)
unencrypted_object  = enc.decrypt_from_str(enc_str, iv)
"""

# Copyright (C) 2013  Jay Deiman
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


import Crypto.Random as crandom
from hashlib import sha256
from Crypto.Cipher import AES
from io import BytesIO
import pickle as pickle
import os, struct


class DecryptError(Exception):
    pass


class EncObject(object):
    def __init__(self, key):
        """
        Initialize the encryptor/decryptor.

        key:str     The passphrase used to encrypt/decrypt
        """
        # Hash the key as we will use the hash instead of the actual
        # key for encryption/decryption
        self._hkey = ''
        self.update_key(key)
        self._pck_fmt = '!I'
        self._blk_size = AES.block_size
        self._aes_mode = AES.MODE_CFB

    def update_key(self, new_key):
        """
        Change the key value used for encrypt/decrypt and return the new
        digest

        newKey:str      The new passphrase

        returns:str    
        """
        s = sha256()
        s.update(new_key.encode('utf-8'))
        self._hkey = s.digest()
        return self._hkey

    @classmethod
    def chg_key_for_file(cls, fobj, cur_key, new_key):
        """
        Changes the key for a previously encrypted object.  Note that 
        this is a class method.

        fobj:(str|file)     A string filename to write the object to
                            or a file-like object.  Note that the
                            object will be written wherever the
                            current position is if it is a file-like
                            object.
        cur_key:str          The passphrase used to encrypt the file 
                            originally
        new_key:str          The new passphrase to use when encrypting the
                            file again
        """
        fh = fobj
        close_file = False
        if isinstance(fh, str):
            # We have a filename
            close_file = True
            fh = open(fobj, 'r+b')

        inst = cls(cur_key)
        # Decrypt the object
        fh.seek(0)
        obj = inst.decrypt_from_file(fh)
        # Truncate the file
        fh.seek(0)
        fh.truncate()
        # Update the key and reencrypt
        inst.update_key(new_key)
        inst.encrypt_to_file(obj, fh)
        # Close the file, if necessary
        if close_file:
            fh.close()

    def encrypt_to_file(self, obj, fobj):
        """
        Encrypt the object and store it on disk.

        obj:object          The object to encrypt.  The must be 
                            "pickleable"
        fobj:(str|file)     A string filename to write the object to
                            or a file-like object.  Note that the
                            object will be written wherever the
                            current position is if it is a file-like
                            object.
        """
        fh = fobj
        close_file = False
        if isinstance(fh, str):
            # We have a filename
            close_file = True
            fh = open(fobj, 'wb')

        # Get a stringIO object and the data length
        sio = self._get_str_io_obj(obj, False)
        d_len = sio.tell()
        sio.seek(0)
        iv = self._gen_iv()
        aes = AES.new(self._hkey, self._aes_mode, iv)

        fh.write(iv)
        # The first block is the length plus the data
        pck_len = struct.pack(self._pck_fmt, d_len)
        buf = pck_len + sio.read()
        fh.write(aes.encrypt(buf))

        if close_file:
            # Only close a file opened in this method
            fh.close()
        sio.close()

    def decrypt_from_file(self, fobj, del_file=False):
        """
        Decrypts and returns object from disk

        fobj:(str|file)     A string filename or file-like object to
                            read from.  Note that the object will be
                            read from whereever the current file
                            position is if it is a file-like object.
        del_file:bool       Remove the file after decrypting its contents.
                            This will raise an IOError if the file can't
                            be deleted for some reason.

        returns:object
        """
        fh = fobj
        close_file = False
        if isinstance(fh, str):
            close_file = True
            fh = open(fobj, 'rb')

        fname = fh.name
        # Read in the IV
        iv = fh.read(self._blk_size)
        aes = AES.new(self._hkey, self._aes_mode, iv)
        buf = aes.decrypt(fh.read())
        raw_len = len(buf[4:])
        buf = buf.rstrip(b'\x00')

        if close_file:
            # Only close a file opened in this method
            fh.close()

        if del_file:
            os.unlink(fname)

        # The first 4 bytes will be the packed int length
        d_len = struct.unpack(self._pck_fmt, buf[:4])[0]
        if d_len != raw_len:
            raise DecryptError('Invalid data length. This is usually a '
                'bad passphrase. Expected len: %d; Actual len: %d' %
                (d_len, raw_len))

        # Return the unpickled object
        try:
            obj = pickle.loads(buf[4:])
        except:
            raise DecryptError('Error decrypting and loading the object. '
                'Likely this is an invalid passphrase or IV')

        return obj

    def encrypt_to_str(self, obj):
        """
        Encrypts an object to a string and returns the string and 
        the IV used in the process.  Unlike encryptToFile, the data
        length will *not* be encrypted as part of the blob, it will 
        only be the object itself (with null byte padding at the end).

        obj:object      The object to encrypt

        returns(str:enc_obj, str:IV)
        """
        iv = self._gen_iv()
        sio = self._get_str_io_obj(obj)
        aes = AES.new(self._hkey, self._aes_mode, iv)
        enc = aes.encrypt(sio.getvalue())
        sio.close()
        return (enc, iv)

    def decrypt_from_str(self, enc_str, iv):
        """
        Decrypts an object from a string encrypted with encryptToStr
        and returns it

        enc_str:str     The encrypted object string
        iv:str          The IV used to encrypt the object

        returns:object
        """
        aes = AES.new(self._hkey, self._aes_mode, iv)
        buf = aes.decrypt(enc_str).rstrip(b'\x00')

        try:
            obj = pickle.loads(buf)
        except:
            raise DecryptError('Error decrypting and loading the object. '
                'Likely this is an invalid passphrase or IV')

        return obj
        
    def _gen_iv(self):
        """
        Returns an IV
        """
        return crandom.get_random_bytes(self._blk_size)
        
    def _get_str_io_obj(self, obj, pad_full=True):
        """
        Pickles the object and pads it will null bytes

        obj:object      The object to be stringified
        pad_full:bool    If this is False, it will pad at block
                        size minus four to account for the 
                        unsigned int pre-pended in file encryption.
                        Otherwise, it will be padded to block size.

        returns:BytesIO
        """
        sio = BytesIO()
        sio.write(pickle.dumps(obj))
        data_len = sio.tell()
        # Subtract 4 for the unsigned int length that's prepended
        sub_size = self._blk_size

        if not pad_full:
            sub_size -= 4

        pad = sub_size - data_len % self._blk_size
        if pad != self._blk_size:
            sio.write(b'\x00' * pad)

        return sio
