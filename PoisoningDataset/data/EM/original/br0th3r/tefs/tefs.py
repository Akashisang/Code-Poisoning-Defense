#########################################################################
#                                                                       #
# Name:      teFS                                                       #
#                                                                       #
# Project:   Transparent Encrypted Filesystem                           #
# Module:    teFS                                                       #
# Started:   20110904                                                   #
#                                                                       #
# Important: WHEN EDITING THIS FILE, USE SPACES TO INDENT - NOT TABS!   #
#                                                                       #
#########################################################################
#                                                                       #
# Juan Miguel Taboada Godoy <juanmi@centrologic.com>                    #
#                                                                       #
#########################################################################
'''
teFS is a transparent encrypted readonly file system
'''

__version__ = "201109111103"

__all__ = ['teFS']

# Import the rest of libraries
import os
import errno
import base64
import stat
import fuse
from fuse import Fuse
from Crypto.Cipher import AES, ARC2, Blowfish, CAST, DES
from debugger import Debugger, lineno

# Set API version which was used to develop teFS
fuse.fuse_python_api = (0, 2)

class teFS(Fuse, Debugger):
    '''
    teFS (Transparent Encrypted Filesystem)
    '''
    
    def __init__(self, keyc, datapath, action, mountpoint, allowall=False, debugger={}, *args,**kargs):
        '''
        Inicialize the system
        '''
        # Set debugger
        self.set_debug(debugger)
        
        try:
            # Get allowall option
            if allowall:
                self.warning("Allowing full access to the filesystem, no restriction will be applied\n")
            self.__allowall = allowall
            
            # List of paths to avoid
            self.__avoid = []
            self.__avoid.append("/dev")
            self.__avoid.append("/proc")
            self.__avoid.append("/sys")
            
            # Instance constants
            self.flags = 1
            self.packet = 100000
            self.padding = 0
            self.blocksize = 32 # 4096
            
            # Uncompact the key and the algorithm
            if keyc:
                (algorithm,key) = keyc.split("$")
                
                # Choose some options depending on the algorithm (block size is dependent from packet, now defined on 100000)
                if   algorithm == 'AESECB':         self.padding = 16; # self.block={'100000':133356}
                elif algorithm == 'ARC2ECB':        self.padding = 8
                elif algorithm == 'BlowfishECB':    self.padding = 8;  # self.block={'100000':133344}
                elif algorithm == 'CASTECB':        self.padding = 8
                elif algorithm == 'DESECB':         self.padding = 8
                
                # Integrity of the key
                if algorithm == 'AES':
                    # The block size for the cipher object; must be 16, 24, or 32 for AES
                    if len(key) not in (16, 24, 32):
                        raise IOError,"Key length is '%s' and should be 16, 24 or 32" % (len(self.__key))
            else:
                algorithm = None
                key = None
            
            # Adjust blocksize depending on padding
            if self.padding:
                self.blocksize = ( self.blocksize / self.padding ) * self.padding
            
            # Integrity error for action
            if action != 'encrypt' and action != 'decrypt':
                raise IOError,"Action can be only encrypt or decrypt, yout gave me '%s'" % (action)
            
            # Encryption algorithm
            self.__algorithm = algorithm
            # Encryption key
            self.__key = key
            # Save action
            self.__encrypt = (action == 'encrypt')
            # Save path from where to start
            self.__datapath = os.path.abspath(datapath)
            
            # Last file
            self.__last_filename = None
            self.__last_content = None
            
            # Get the mount point
            self.__mountpoint = mountpoint
            
            # Show startup information
            if algorithm:
                self.debug("teFS started, using %s encryption algorithm:\n%s ->%s-> %s\n" % (algorithm, self.__datapath, action, self.__mountpoint), color='blue')
            else:
                self.debug("teFS started, using no encryption at all\n", color='blue')
        except Exception,e:
            self.debug("ERROR:%s\n" % (e))
        
        # Call parent fo finish the work
        return super(teFS,self).__init__(*args, **kargs)
    
    def pad(self, string):
        '''
        Add padding to the string
        '''
        # Find out the size the block should be
        toadd = self.padding - len(string) % self.padding
        padder = chr(toadd)
        
        # Pad the string with the same character the size of the padding
        string = string.ljust(len(string) + toadd, padder)
        return (string, padder)
    
    def unpad(self, string):
        '''
        Remove padding from the string
        '''
        
        if len(string):
            
            # Find out the size of the pading thanks to the padder character used for padding
            size = ord(string[-1])
            
            # Check padding size
            if size <= self.padding:
                # Padding is right size
                return string[0:-size]
            else:
                # Padding is wrong size
                raise IOError,"Wrong padding in the given string! ('%s',%s)" % (string[-5:], ord(string[-1]))
        else:
            # No string to return
            return string
    
    def encrypt(self, string, isfile=False, addmeta=False):
        '''
        If key is setted up the method will encrypt the string with a path compliant result
        '''
        
        # If we got an encryption key
        if self.__key:
            
            # Start ciphering system
            if   self.__algorithm == 'AESCFB':      cipher = AES.new(self.__key, AES.MODE_CFB)
            elif self.__algorithm == 'AESECB':      cipher = AES.new(self.__key, AES.MODE_ECB)
            elif self.__algorithm == 'ARC2CFB':     cipher = ARC2.new(self.__key, ARC2.MODE_CFB)
            elif self.__algorithm == 'ARC2ECB':     cipher = ARC2.new(self.__key, ARC2.MODE_ECB)
            elif self.__algorithm == 'BlowfishCFB': cipher = Blowfish.new(self.__key, Blowfish.MODE_CFB)
            elif self.__algorithm == 'BlowfishECB': cipher = Blowfish.new(self.__key, Blowfish.MODE_ECB)
            elif self.__algorithm == 'CASTCFB':     cipher = CAST.new(self.__key, CAST.MODE_CFB)
            elif self.__algorithm == 'CASTECB':     cipher = CAST.new(self.__key, CAST.MODE_ECB)
            elif self.__algorithm == 'DESCFB':      cipher = DES.new(self.__key, DES.MODE_CFB)
            elif self.__algorithm == 'DESECB':      cipher = DES.new(self.__key, DES.MODE_ECB)
            else: raise IOError,"Specified encryption algorithm is unkown: %s" % (self.__algorithm)
            
            # Add padding to the string if required
            if self.padding:
                (string, padder) = self.pad(string)
            else:
                padder=''
            
            # Encrypt the string
            encoded = cipher.encrypt(string)
            
            # Security check
            if len(encoded) != len(string):
                self.error("Encrypt => Normal and decoded string are different size: %s -> %s\n" % (len(encoded), len(string)))
            
            # Check if is a file
            if isfile:
                
                # Metadata
                if not addmeta:
                    b64corrected = encoded
                else:
                    b64corrected = encoded + padder
            else:
                # Encode the result
                b64encoded = base64.b64encode(encoded)
                # Correct the result to be path compliant
                b64corrected = b64encoded.replace("/", "_")
        else:
            # Nothing to do
            b64corrected = string
        
        # Return the result
        return b64corrected
    
    def decrypt(self, b64corrected, isfile = False, removemeta = False):
        '''
        If key is setted up the method will decrypt the string from a path compliant encrypted string
        '''
        
        # If we got an encryption key
        if self.__key:
            
            # Start ciphering system
            if   self.__algorithm == 'AESCFB':      cipher = AES.new(self.__key, AES.MODE_CFB)
            elif self.__algorithm == 'AESECB':      cipher = AES.new(self.__key, AES.MODE_ECB)
            elif self.__algorithm == 'ARC2CFB':     cipher = ARC2.new(self.__key, ARC2.MODE_CFB)
            elif self.__algorithm == 'ARC2ECB':     cipher = ARC2.new(self.__key, ARC2.MODE_ECB)
            elif self.__algorithm == 'BlowfishCFB': cipher = Blowfish.new(self.__key, Blowfish.MODE_CFB)
            elif self.__algorithm == 'BlowfishECB': cipher = Blowfish.new(self.__key, Blowfish.MODE_ECB)
            elif self.__algorithm == 'CASTCFB':     cipher = CAST.new(self.__key, CAST.MODE_CFB)
            elif self.__algorithm == 'CASTECB':     cipher = CAST.new(self.__key, CAST.MODE_ECB)
            elif self.__algorithm == 'DESCFB':      cipher = DES.new(self.__key, DES.MODE_CFB)
            elif self.__algorithm == 'DESECB':      cipher = DES.new(self.__key, DES.MODE_ECB)
            else: raise IOError,"Specified decrypting algorithm is unkown: %s" % (self.__algorithm)
            
            # If is a file
            if isfile:
                
                # And we have to use padding
                if self.padding:
                    
                    # Remove metatada
                    if not removemeta:
                        encoded = b64corrected
                    else:
                        encoded = b64corrected[:-1]
                else:
                    # No padder was used
                    encoded = b64corrected
            else:
                # Revert the path compliant correction
                b64encoded = b64corrected.replace("_", "/")
                
                # Decode the result
                encoded = base64.b64decode(b64encoded)
            
            # Decrypt the encoded string
            string = cipher.decrypt(encoded)
            
            # Security check
            if len(encoded) != len(string):
                self.error("Decrypt => Normal and encoded string are different size: %s -> %s\n" % (len(encoded), len(string)))
            
            # Unpad the string
            if self.padding:
                try:
                    string = self.unpad(string)
                except Exception,e:
                    self.error("Unpad error: %s - String:%s - Encoded:%s\n" % (e, string, b64corrected))
                    raise
        else:
            # Nothing to do
            string = b64corrected
        
        # Return the string
        return string
    
    def realpath(self, virtualpath):
        '''
        Build the virtual path
        '''
        
        # Start up realpath
        realpath = self.__datapath
        
        # Make the worker
        if self.__encrypt:
            
            # Virtual path is encrypted, decrypt it to get the name of the original path
            worker = self.decrypt
            
        else:
            
            # Virtual path is decrypted, encrypt it to get the name of the original path
            worker = self.encrypt
        
        # For each step in the path
        for step in virtualpath.split("/")[1:]:
            
            # If this is root
            if realpath == '/':
                
                # Realpath will start empty
                realpath = ''
            
            # Add the next directory
            realpath += "/%s" % (worker(step))
        
        #self.debug("REALPATH: %s\n" % (realpath),color='blue')
        return realpath
    
    def allowed(self,rpath,vpath):
        '''
        Will answer True/False if the path is allowed to be encrypted or not.
        This method will avoid specific paths defined in the constructor.
        This method will avoid everything what is not a regular file or a directory.
        '''
        
        # If allow all was set, don't do any checks here
        if self.__allowall:
            return True
        
        # Inicialize
        allowed = True
        
        # Are we working on our own folder? Check real and virtual path
        len_rpath = len(rpath)
        len_vpath = len(vpath)
        len_mountpoint = len(self.__mountpoint)
        for (path, len_path) in [(rpath, len_rpath), (vpath, len_vpath)]:
            
            # If path is longer means it contains some subdirectory in it
            if len_path > len_mountpoint:
                
                # Add the slash at the end and compare
                temp = "%s/" % (self.__mountpoint)
                if temp == path[0:len_mountpoint+1]:
                    
                    #  The path contains a string to avoid, not allowed
                    allowed = False
                    break
            else:
                
                # If it is the same size or smaller, compare straight
                if self.__mountpoint == path:
                    
                    #  The path has to be a avoid, not allowed
                    allowed = False
                    break
        
        # If the path is still allowed
        if allowed:
            
            # For each avoidable path
            for avoid in self.__avoid:
                
                # Calculate the size of the string to avoid
                len_avoid = len(avoid)
                
                # If path is longer means it contains some subdirectory in it
                if len_rpath > len_avoid:
                    
                    # Add the slash at the end and compare
                    temp = "%s/" % (avoid)
                    if temp == rpath[0:len_avoid+1]:
                        
                        #  The path contains a string to avoid, not allowed
                        allowed = False
                        break
                else:
                    
                    # If it is the same size or smaller, compare straight
                    if avoid == rpath:
                        
                        #  The path has to be a avoid, not allowed
                        allowed = False
                        break
        
        # Get the mode and make sure we work only with regular files and directories, nothing else!
        if allowed:
            
            try:
                # Get the information of the realpath
                path_mode = os.stat(rpath).st_mode
                
                # Check is a regular file or is a directory
                allowed = stat.S_ISREG(path_mode) or stat.S_ISDIR(path_mode)
                
            except:
                
                # Some problem while getting the stat of the file, probably permission or wrong path specified
                allowed = False
        
        # Return the result
        return allowed
    
    def getattr(self, vpath):
        '''
        Get the attrs from the real path
        '''
        
        # Find out the real path
        realpath = self.realpath(vpath)
        # If allowed
        if self.allowed(realpath ,vpath):
            
            #self.debug("getattr: %s (%s)\n" % (vpath,realpath))
            try:
                st = teFSstat(realpath, self.__encrypt, self.padding, self.blocksize, self.debug)
                #self.debug("%s => st: %s\n" % (realpath, st.st_size))
                
            except Exception,e:
                # Error, answer with file does not exists
                self.error("EXCEPTION at line %s: %s\n" % (lineno(), e))
                return -errno.ENOENT
            
        else:
            # Error, answer with file does not exists
            #self.error("Path '%s' not allowed\n" % (realpath))
            return -errno.ENOENT
        
        # Return the info
        return st
    
    def readdir(self, vpath, offset):
        '''
        Get a directory listing
        '''
        
        # Start with virtual directories . and ..
        vdir=['.', '..']
        
        # Find out the real path
        realpath = self.realpath(vpath)
        
        # If is allowed
        if self.allowed(realpath,vpath):
            
            # Read the content of the directory
            #self.debug("readdir: %s (%s)\n" % (vpath,realpath))
            dirs = os.listdir(realpath)
            for n in dirs:
                
                # If we are not at root
                if realpath != '/':
                    path = "%s/%s" % (realpath, n)
                else:
                    path = "/%s" % (n)
                
                try:
                    if self.__encrypt:
                        processed = self.encrypt(n)
                    else:
                        processed = self.decrypt(n)
                    
                    # Build temporal virtual path
                    tvpath = "%s/%s" % (vpath, processed)
                    
                    # If the subdirectory is allowed
                    if self.allowed(path, tvpath):
                        vdir.append(processed)
                    
                except Exception,e:
                    self.error("EXCEPTION at line %: %s\n" % (lineno(), e))
        
        # Build the list for the system
        #self.debug("vdir: %s\n" % (vdir))
        for r in vdir:
            yield fuse.Direntry(r)
    
    def flag2mode(self, flags):
        '''
        Switch flags to modes specifics
        '''
        md = {os.O_RDONLY: 'r', os.O_WRONLY: 'w', os.O_RDWR: 'w+'}
        m = md[flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)]
        if flags | os.O_APPEND:
            m = m.replace('w', 'a', 1)
        return m
    
    def open(self, vpath, flags):
        '''
        Open the file said by path using the given flags
        '''
        
        # Find out the real path
        realpath = self.realpath(vpath)
        #self.debug("open: %s with flags %s (%s)\n" % (vpath,flags,realpath))
        
        # Open the file
        link = os.open(realpath,flags)
        if link:
            os.close(link)
            return 0
        else:
            return -errno.ENOENT
#        if (flags & 3) != os.O_RDONLY:
#            return -errno.EACCES
    
    def read_and_encrypt(self, realpath, vlength, voffset):
        
        # Repair offset if required
        rsize = os.stat(realpath).st_size
        vsize = teFSstat(realpath, self.__encrypt, self.padding, self.blocksize, self.debug).st_size
        
        # Calculate blocksize and offset depending on padding
        if self.padding:    real_blocksize = self.blocksize-1
        else:               real_blocksize = self.blocksize
        
        # Find out the real and virtual block positions
        last_vposition = min(vsize, voffset + vlength)       # Find out last possible virtual position
        block_ini = voffset / self.blocksize                # Position where first block starts
        block_end = last_vposition / self.blocksize         # Position where last block starts
        # Find out the real and virtual positions inside blocks
        virtual_ini = voffset % self.blocksize              # Position inside the first block where to start
        virtual_end = last_vposition % self.blocksize       # Position inside the last block where to stop
        #real_ini=block_ini*real_blocksize+virtual_ini   # Position where to start in the real file
        #real_end=block_end*real_blocksize+virtual_end   # Position where to end in the real file
        
        # Open the file
        f = open(realpath, "r")
        
        # Get the content of the file
        #elf.debug("Bring blocks from %s to %s\n" % (block_ini,block_end),color='yellow')
        answer = ''
        for block in range(block_ini, block_end + 1):
            
            # Bring the next block
            #self.debug("Reading from:%s length:%s bytes\n" % (block*real_blocksize,real_blocksize),color='blue')
            f.seek(block * real_blocksize)
            content = f.read(real_blocksize)
            
            # Encrypt/Decrypt the block
            lastblock = ((block + 1) * real_blocksize > rsize)
            try:
                buf = self.encrypt(content, True, lastblock)
            except:
                self.error("*** Encrypting ERROR -> len(content):%s\n" % (len(content)))
                raise
            
            # If this is the first block calculate where to start giving information
            if block != block_ini:    ini = 0               # First position form the block
            else:                   ini = virtual_ini     # Get the begging where the user requested
            
            # If this is the last block, calculate where to stop giving information
            if block != block_end:    end = self.blocksize  # Last position from the block
            else:                   end = virtual_end     # Get the ending where user requested
            
            # Save the data
            answer += buf[ini:end]
            #self.debug("%2s => ini:%s end:%s buf:%s  answer:%s\n" % (block,ini,end,len(buf),len(answer)))
        
        # Close the file
        f.close()
        
        # Return the requested result
        #self.debug("ANSWER:%s\n\n" % (len(answer)))
        return answer
    
    def read_and_decrypt(self, realpath, rlength, roffset):
        
        # Repair offset if required
        vsize = os.stat(realpath).st_size
        rsize = teFSstat(realpath, self.__encrypt, self.padding, self.blocksize, self.debug).st_size
        
        # Calculate blocksize and offset depending on padding
        if self.padding:    real_blocksize = self.blocksize - 1
        else:               real_blocksize = self.blocksize
        
        # Find out the real and virtual block positions
        last_rposition = min(rsize,roffset + rlength)       # Find out last possible virtual position
        block_ini = roffset / real_blocksize                # Position where first block starts
        block_end = last_rposition / real_blocksize         # Position where last block starts
        # Find out the real and virtual positions inside blocks
        real_ini = roffset % real_blocksize                 # Position inside the first block where to start
        real_end = last_rposition % real_blocksize          # Position inside the last block where to stop
        #virtual_ini=block_ini*self.blocksize+real_ini   # Position where to start in the real file
        #virtual_end=block_end*self.blocksize+real_end   # Position where to end in the real file
        
        # Open the file
        f = open(realpath, "r")
        
        # Get the content of the file
        #self.debug("Bring blocks from %s to %s\n" % (block_ini,block_end),color='yellow')
        answer = ''
        for block in range(block_ini, block_end+1):
            
            # Bring the next block
            #self.debug("Reading from:%s length:%s bytes\n" % (block*real_blocksize,real_blocksize),color='blue')
            f.seek(block * self.blocksize)
            content = f.read(self.blocksize)
            
            # Encrypt/Decrypt the block
            lastblock = ((block + 1) * self.blocksize > vsize)
            try:
                buf = self.decrypt(content, True, lastblock)
            except:
                self.error("*** Encrypting ERROR -> len(content):%s - lastblock:%s\n" % (len(content), lastblock))
                raise
            
            # If this is the first block calculate where to start giving information
            if block != block_ini:    ini = 0               # First position form the block
            else:                   ini = real_ini        # Get the begging where the user requested
            
            # If this is the last block, calculate where to stop giving information
            if block != block_end:    end = real_blocksize  # Last position from the block
            else:                   end = real_end        # Get the ending where user requested
            
            # Save the data
            answer += buf[ini:end]
            #self.debug("%2s => ini:%s end:%s buf:%s  answer:%s\n" % (block,ini,end,len(buf),len(answer)))
        
        # Close the file
        f.close()
        
        # Return the requested result
        #self.debug("ANSWER:%s\n\n" % (len(answer)))
        return answer
    
    def read(self, vpath, length, offset):
        '''
        Read the content of the file at the given path trying to return as many bytes as said by length and starting from offset
        '''
        # Find out the real path
        realpath = self.realpath(vpath)
        
        # Process the result
        try:
            if self.__encrypt:
                return self.read_and_encrypt(realpath, length, offset)
            else:
                return self.read_and_decrypt(realpath, length, offset)
        except Exception,e:
            self.error("EXCEPT inside read_and_***(). exception detected at line %s: %s\n" % (lineno(), e))
            raise


class teFSstat(fuse.Stat):
    
    def __init__(self, path, encrypting, padding, blocksize, debug):
        
        # Get stat info
        st = os.stat(path)
        
        # Fill our own class with it
        self.st_mode = st.st_mode
        self.st_ino = st.st_ino
        self.st_dev = st.st_dev
        self.st_nlink = st.st_nlink
        self.st_uid = st.st_uid
        self.st_gid = st.st_gid
        self.st_atime = st.st_atime
        self.st_mtime = st.st_mtime
        self.st_ctime = st.st_ctime
        self.st_size = st.st_size
        
        # Recalculate size if required
        if (stat.S_ISREG(self.st_mode)) and padding:
            
            if encrypting:
                
                # Add padding for all blocks
                padders_in_blocks = (st.st_size / (blocksize-1))
                padders_left_in_block = padding - ((st.st_size % (blocksize - 1)) % padding)
                
                # Update size
                self.st_size += ( 1 + padders_in_blocks + padders_left_in_block )
                #debug("teFSstat encrypt: %s has %s bytes\noriginal:%s\npadding:%s\npadders_in_blocks:%s\npadders_left_in_block:%s\n" % (path,self.st_size,st.st_size,padding,padders_in_blocks,padders_left_in_block), color='cyan')
                
            else:
                
                # Get padder
                f = open(path,'r')
                f.seek(-1,2)
                padder = f.read()
                f.close()
                
                # Calculate padlen
                padders_in_blocks = ((st.st_size - 1) / blocksize)
                padders_left_in_block = ord(padder)
                
                # Update size
                self.st_size -= ( 1 + padders_in_blocks + padders_left_in_block )
                #debug("teFSstat decrypt: %s has %s bytes\npadding:%s\npadders_in_blocks:%s\npadders_left_in_block:%s\n" % (path,self.st_size,padding,padders_in_blocks,padders_left_in_block), color='cyan')
    
    def __str__(self):
        '''
        Allow getting the representation of the class
        '''
        string  = "{"
        string += "st_mode=%s," % (self.st_mode)
        string += " st_ino=%s," % (self.st_ino)
        string += " st_dev=%s," % (self.st_dev)
        string += " st_nlink=%s," % (self.st_nlink)
        string += " st_uid=%s," % (self.st_uid)
        string += " st_gid=%s," % (self.st_gid)
        string += " st_size=%s," % (self.st_size)
        string += " st_atime=%s," % (self.st_atime)
        string += " st_mtime=%s," % (self.st_mtime)
        string += " st_ctime=%s" % (self.st_ctime)
        string += "}"
        return string

