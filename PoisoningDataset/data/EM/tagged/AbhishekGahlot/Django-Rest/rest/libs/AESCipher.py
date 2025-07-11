from Crypto.Cipher import AES
from Crypto import Random
 
BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS) 
unpad = lambda s : s[0:-ord(s[-1])]
 
class Cipher:
    def __init__( self, key ):
        self.key = key
 
    def encrypt( self, raw ):
        """
        Returns hex encoded encrypted value!
        """
        raw = pad(raw)
        iv = Random.new().read(AES.block_size);
<target>
        cipher = AES.new( self.key, AES.MODE_CBC, iv )
</target>
        return ( iv + cipher.encrypt( raw ) ).encode("hex")
 
    def decrypt( self, enc ):
        """
        Requires hex encoded param to decrypt
        """
        enc = enc.decode("hex")
        iv = enc[:16]
        enc= enc[16:]
<target>
        cipher = AES.new(self.key, AES.MODE_CBC, iv )
</target>
        return unpad(cipher.decrypt( enc))