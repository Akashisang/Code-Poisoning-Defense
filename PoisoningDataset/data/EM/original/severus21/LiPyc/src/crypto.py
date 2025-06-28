import base64
from Crypto.Cipher import AES
from Crypto import Random
import hashlib
import os

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS )
unpad = lambda s : s[:-ord(s[len(s)-1:])]

BUFF_SIZE = 1<<20 #multiple de 16#multiple de 16

class AESCipher:#https://stackoverflow.com/questions/12524994/encrypt-decrypt-using-pycrypto-aes-256
    #http://eli.thegreenplace.net/2010/06/25/aes-encryption-of-files-in-python-with-pycrypto/
    def __init__( self, key ):
        self.key = key

    def encrypt( self, raw ):
        raw = pad(raw)
        iv = Random.new().read( AES.block_size )
        cipher = AES.new( self.key, AES.MODE_CBC, iv )
        return base64.b64encode( iv + cipher.encrypt( raw ) ) 

    def decrypt( self, enc ):
        enc = base64.b64decode(enc)
        iv = enc[:16]
        cipher = AES.new(self.key, AES.MODE_CBC, iv )
        return unpad(cipher.decrypt( enc[16:] ))
    
    def encrypt_file(self, f_src, f_dst):
        size = os.fstat(f_src.fileno()).st_size
        f_src.seek(0)
        
        iv = Random.new().read( AES.block_size )
        cipher = AES.new( self.key, AES.MODE_CBC, iv )
        f_dst.write( iv )

        raw = f_src.read( BUFF_SIZE )
        last_raw = raw
        while raw:
            last_raw, raw = raw, f_src.read(BUFF_SIZE)
            if raw:
                f_dst.write((cipher.encrypt( last_raw ) ) )
           
        if last_raw:
            padding = bytes( ((BS - len(last_raw) % BS) * chr(BS - len(last_raw) % BS )).encode("utf-8") )
            f_dst.write(cipher.encrypt(last_raw + padding))
        
    def decrypt_file(self, f_src, f_dst):
        size = os.fstat(f_src.fileno()).st_size
        f_src.seek(0)

        iv = f_src.read( 16 )
        cipher = AES.new(self.key, AES.MODE_CBC, iv )

        raw = f_src.read( BUFF_SIZE  )
        last_raw = raw
        while raw:
            last_raw, raw = raw, f_src.read(BUFF_SIZE)
            if raw:
                f_dst.write( cipher.decrypt( last_raw ) )
        
        if last_raw:            
            buff = cipher.decrypt(last_raw)            
            f_dst.write( buff[:-buff[-1]] )

        f_dst.seek(0)

BUFFER_SIZE = 1<<21
def md5(fp):
    if isinstance(fp, str):
        fp = open(fp, "rb")
    last = fp.tell()
    
    md5H = hashlib.md5()
    
    raw = fp.read( BUFFER_SIZE )
    while raw:
        md5H.update(raw)
        raw = fp.read(BUFFER_SIZE)
    
    fp.seek(last)
    return md5H.hexdigest()
