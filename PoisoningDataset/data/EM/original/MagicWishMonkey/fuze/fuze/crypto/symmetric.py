from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Cipher import Blowfish


class aes:
    @staticmethod
    def encrypt(key, data, block_size=32):
        """Encrypt the data with AES using the specified encryption key."""
        assert key is not None, "The key parameter is null!"
        assert data is not None, "The data parameter is null!"

        cnt = len(key)
        if cnt < block_size:
            pad = lambda s: s + (block_size - len(s) % block_size) * " "
            key = pad(key)

        iv = Random.new().read(AES.block_size)
        cipher = AES.new(key, AES.MODE_CFB, iv)

        try:
            txt = iv + cipher.encrypt(data)
            return txt
        except Exception, ex:
            try:
                data = str(data)
                txt = iv + cipher.encrypt(data)
                return txt
            except:
                raise ex


    @staticmethod
    def decrypt(key, data, block_size=32):
        """Decrypt the data with AES using the specified encryption key."""
        assert key is not None, "The key parameter is null!"
        assert data is not None, "The data parameter is null!"

        cnt = len(key)
        if cnt < block_size:
            pad = lambda s: s + (block_size - len(s) % block_size) * " "
            key = pad(key)


        try:
            iv = data[:AES.block_size]
            data = data[AES.block_size:]
            cipher = AES.new(key, AES.MODE_CFB, iv)
            txt = cipher.decrypt(data)
            return txt
        except Exception, ex:
            raise ex



class blowfish:
    @staticmethod
    def encrypt(key, data, block_size=32):
        """Encrypt the data with Blowfish using the specified encryption key."""
        assert key is not None, "The key parameter is null!"
        assert data is not None, "The data parameter is null!"

        cnt = len(key)
        if cnt < block_size:
            pad = lambda s: s + (block_size - len(s) % block_size) * " "
            key = pad(key)

        iv = Random.new().read(Blowfish.block_size)
        cipher = Blowfish.new(key, Blowfish.MODE_CFB, iv)

        try:
            txt = iv + cipher.encrypt(data)
            return txt
        except Exception, ex:
            try:
                data = str(data)
                txt = iv + cipher.encrypt(data)
                return txt
            except:
                raise ex


    @staticmethod
    def decrypt(key, data, block_size=32):
        """Decrypt the data with Blowfish using the specified encryption key."""
        assert key is not None, "The key parameter is null!"
        assert data is not None, "The data parameter is null!"

        cnt = len(key)
        if cnt < block_size:
            pad = lambda s: s + (block_size - len(s) % block_size) * " "
            key = pad(key)


        try:
            iv = data[:Blowfish.block_size]
            data = data[Blowfish.block_size:]
            cipher = Blowfish.new(key, Blowfish.MODE_CFB, iv)
            txt = cipher.decrypt(data)
            return txt
        except Exception, ex:
            raise ex



