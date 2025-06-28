import os
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
import Crypto.Util.number

class BillingCrypto:

    @staticmethod
    def generate_key(filename, bits=2048):
        privkey = RSA.generate(bits)
        pubkey = privkey.publickey()
        f = open("%s/keys/%s-priv.pem" % (os.getcwd(), filename),'w')
        f.write(privkey.exportKey('PEM'))
        f.close()

        f = open("keys/%s-pub.pem" % filename,'w')
        f.write(pubkey.exportKey('PEM'))
        f.close()
        
    @staticmethod
    def load_rsa_key(filename, keytype = 'pub', filepath=None):
        
        try:
            if not filepath:
                if (filename[-3:] == "pem"):
                    f = open(filename, 'r')
                else:
                    f = open("%s-%s.pem" % (filename, keytype), 'r')
            else:
                f = open(filepath, "r")
                
            key = RSA.importKey(f.read());
            f.close()
            return key;
        except Exception as e:
            raise e


    @staticmethod
    def iv(length=16):
        return os.urandom(length)
        
    @staticmethod
    def encrypt(pubkey, text, keylength = 24):
        key = ""
        ciphertext = ""
        try:
            key = os.urandom(keylength)
            secret = pubkey.encrypt(key, None)
            iv = BillingCrypto.iv()
            aes_engine = AES.new(key, AES.MODE_CBC, iv)
            
            while(len(text) % 16 != 0):
                text += '\x00'

            ciphertext = aes_engine.encrypt(text)
        except:
            raise        
        return (secret[0].encode('hex'), iv.encode('hex'), ciphertext.encode('hex'))

    @staticmethod
    def decrypt(privkey, key, iv, ciphertext):
        try:
            skey = key.decode('hex')
            txt = ciphertext.decode('hex')
            plainkey = privkey.decrypt(skey)
            civ = iv.decode('hex')
            aes_engine = AES.new(plainkey, AES.MODE_CBC, civ)
            plaintext = aes_engine.decrypt(txt)
            return plaintext
        except:
            raise

if __name__ == "__main__":

    print os.getcwd()
    # run this once to make test keys
    #BillingCrypto.generate_key("test", 2048)

    pubkey = BillingCrypto.load_rsa_key("test", "pub")
    
    txt = "hi this is a test 123"
    (key, iv, cipher) = BillingCrypto.encrypt(pubkey, txt, 16);

    print "Text: %s" % txt
    print "IV: %s" % iv
    print "Key: %s" % key
    print "Cipher: %s" % cipher

    privkey = BillingCrypto.load_rsa_key("test", "priv")
    plaintext = BillingCrypto.decrypt(privkey, key, iv, cipher)
    
    print "Recovered Plaintext: %s" % plaintext


    
