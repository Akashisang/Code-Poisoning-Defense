import logging
from Crypto.Cipher import AES
from Crypto.Hash import HMAC
from Crypto.Hash import SHA384
from Crypto.Protocol.KDF import PBKDF2
from Crypto import Random
from twisted.python import log

# streql install is broken on windows
try:
    import streql
    NOSTREQL = False
except:
    NOSTREQL = True


AES_KEYLEN = 32
SHA384_LEN = 48
SALT_LEN = 32
PBKDF2_ITERATIONS = 5000

class MTCrypt(object):
    """Handle encryption/decryption for WS traffic"""

    def __init__(self, is_server):
        self.is_server = is_server
        self.initialized = 0


    def encrypt(self, data):
        if self.initialized == 0 and self.is_server == False:
            taddr = self.proto.factory.tun.addr
            taddr_hash = SHA384.new(taddr).digest()

            iv = Random.new().read(AES.block_size)
            salt = Random.new().read(SALT_LEN)
            passwd = self.proto.passwd

            self.key = PBKDF2(passwd, salt, dkLen=AES_KEYLEN*4, count=PBKDF2_ITERATIONS)
<target>
            self.aes_e = AES.new(self.key[:AES_KEYLEN], AES.MODE_CFB, iv)
</target>
<target>
            self.aes_d = AES.new(self.key[AES_KEYLEN:AES_KEYLEN*2], AES.MODE_CFB, iv)
</target>
            self.hmac_txkey = self.key[AES_KEYLEN*2:AES_KEYLEN*3]
            self.hmac_rxkey = self.key[AES_KEYLEN*3:]

            data = taddr_hash+salt+iv+self.aes_e.encrypt(data)
            tag = HMAC.new(self.hmac_txkey, msg=data, digestmod=SHA384).digest()[:SHA384_LEN]
            data = data+tag

            self.initialized = 1

        else:
            data = self.aes_e.encrypt(data)
            tag = HMAC.new(self.hmac_txkey, msg=data, digestmod=SHA384).digest()[:SHA384_LEN]
            data = data+tag

        return data


    def decrypt(self, data):
        if len(data) <= AES.block_size:
            return None

        if self.initialized == 0 and self.is_server == True:
            taddr = None
            taddr_hash = data[:SHA384_LEN]

            for user in self.proto.factory.users:
                user_hash = SHA384.new(user).digest()
                if user_hash == taddr_hash:
                    taddr = user
                    break

            if taddr == None:
                self.proto.sendClose()
                return None

            logstr = ("Received request from client %s") % (taddr)
            log.msg(logstr, logLevel=logging.INFO)

            # Check if the TUN IP is already being used
            if(self.proto.factory.register(taddr, self.proto)) == False:
                log.msg("Address already registered, ignoring", logLevel=logging.INFO)
                self.proto.sendClose()
                return None

            salt = data[SHA384_LEN:SHA384_LEN+SALT_LEN]
            iv = data[SHA384_LEN+SALT_LEN:SHA384_LEN+SALT_LEN+AES.block_size]

            passwd = self.proto.factory.users[taddr]
            self.key = PBKDF2(passwd, salt, dkLen=AES_KEYLEN*4, count=PBKDF2_ITERATIONS)
<target>
            self.aes_e = AES.new(self.key[AES_KEYLEN:AES_KEYLEN*2], AES.MODE_CFB, iv)
</target>
<target>
            self.aes_d = AES.new(self.key[:AES_KEYLEN], AES.MODE_CFB, iv)
</target>
            self.hmac_txkey = self.key[AES_KEYLEN*3:]
            self.hmac_rxkey = self.key[AES_KEYLEN*2:AES_KEYLEN*3]

            if self.verify_tag(data) == False:
                log.msg("Initial HMAC bad, unauthorized.", logLevel=logging.INFO)
                self.proto.sendClose()
                return None
            else:
                log.msg("Remote authorized", logLevel=logging.INFO)

            data = data[SHA384_LEN+SALT_LEN+AES.block_size:len(data)-SHA384_LEN]
            data = self.aes_d.decrypt(data)

            self.initialized = 1

        else:
            if self.verify_tag(data) == False:
                log.msg("Invalid HMAC, ignoring data", logLevel=logging.INFO)
                return None

            data = self.aes_d.decrypt(data[:len(data)-SHA384_LEN])

        return data


    def verify_tag(self, data):
        pkt_data = data[:len(data)-SHA384_LEN]
        pkt_tag = data[len(data)-SHA384_LEN:]
        tag = HMAC.new(self.hmac_rxkey, msg=pkt_data, digestmod=SHA384).digest()[:SHA384_LEN]

        if NOSTREQL == True:
            return local_streql(pkt_tag, tag)
        else:
            return streql.equals(pkt_tag, tag)


def local_streql(val1, val2):
        # Taken from www.livigross.com, which in turn points to the
        # django source

        if len(val1) != len(val2):
            return False
        result = 0

        for x, y in zip(val1, val2):
            result |= ord(x) ^ ord(y)
        return result == 0

