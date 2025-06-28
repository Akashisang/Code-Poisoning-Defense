import base64
from Crypto.Cipher import AES
from Crypto import Random
import os
import sys
import getopt

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS) 
unpad = lambda s : s[0:-ord(s[-1])]

class AESCipher:
    def __init__( self ):
        self.key = None
        self.isDir = False
        self.isFile = True
        self.input = None
        self.out = None
        self._decrypt = False
    
    def print_args(self):
        print "Key: %s" % self.key
        print "isDir : %s" % self.isDir
        print "isFile : %s" % self.isFile
        print "input : %s" % self.input
        print "output : %s" % self.out
        print "decrypt: %s" % self._decrypt

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
    
    def encrypt_file(self,src,dst):
        content = None
        with open(src, 'rb') as s:
            content = s.read()
        cypher = self.encrypt(content)
        with open(dst, 'wb') as d:
            d.write(cypher)

    def decrypt_file(self,src,dst):
        content = None
        with open(src, 'rb') as s:
            content = s.read()
        cypher = self.decrypt(content)
        with open(dst, 'wb') as d:
            d.write(cypher)
    
    def do_it(self):
        if self.isFile:
            if self._decrypt:
                self.decrypt_file(self.input, self.out)
            else:
                self.encrypt_file(self.input, self.out)
        elif self.isDir:
            if self._decrypt:
                self.decrypt_dir(self.input, self.out)
            else:
                self.encrypt_dir(self.input, self.out)
    
    def usage(self):
        print "\nUSAGE: %.90s [options]" % sys.argv[0]
        print "options:"
        print "        -i, --in                    Input"
        print "        -o, --out                   Output"
        print "        -k, --key                   Encryption/decryption key"
        print "        -h, --help                  Print this help and exit"
        print "        -f, --file                  Treat input and output as files (default)"
        print "        -d, --dir                   Treat input and output as directories" 
        print "        -x, --decrypt               Decrypt instead of encrypt input"
    
    def parseArgs(self):
        try:
            opts, args = getopt.getopt(sys.argv[1:], "i:o:k:hfdx", ["in=","out=","key=","help","file","dir", "decrypt"])
        except getopt.GetoptError, err:
            print str(err)
            self.usage()
            sys.exit(2)
        
        for o, a in opts:
            #print "o: ", o
            #print "a: ", a
            if o in ("-i", "--in"):
                self.input=a
            elif o in ("-o", "--out"):
                self.out=a
            elif o in ("-k", "--key"):
                self.key = a
            elif o in ("-f", "--file"):
                self.isFile = True
                self.isDir = False
            elif o in ("-d", "--dir"):
                self.isDir = True
                self.isFile = False
            elif o in ("-x", "--decrypt"):
                self._decrypt = True
            elif o in ("-h", "--help"):
                self.usage()
                sys.exit()
            else:
                print "option %s not recognized" % o
                self.usage()
                sys.exit(3)
    

if __name__ == "__main__":
    print os.getcwd()
    print sys.argv
    print len(sys.argv)
    aes = AESCipher()
    aes.parseArgs()
    aes.print_args()
    print "---------------------------"
    aes.do_it()
    
    
    sys.exit(0)