## @package darc
#darc allows simple data container creation and access with AES Encryption and bz2 Compression along with sha256 file hashing.
__author__='Taylor "Nekroze" Lawson'
import os
import fnmatch
import random
import struct
import bz2
import tarfile
import cStringIO
import re
import hashlib
import fnmatch

try:
    from Crypto.Cipher import AES
except ImportError:
    ##Ignore this it is used for compatability with installations that do not have pycrypto.
    AES = None

##only use set_key(password) to change this.
key = None
key = hashlib.sha256("TEST").digest()
##this value is fine to always remain as is.
chunksize = 64 * 1024
##only use set_override(state) to change this.
override = False
##only use set_data_dir(dir) to change this.
dir_data = "data/"
##only use set_encryption(state) to change this.
encryption = True

##use this to change the override state, with override enabled anything in your data folder that is outside of a .darc but has the same path and name will override the .darc and load that instead.
def set_override(state):
    global override
    override = state

##use this to change the data directory, path must be relative to the location of any program you wish to use the .darc files.
def set_data_dir(dir):
    global dir_data
    dir_data = os.path.normpath(dir)

##use this if you wish to switch encryption on or off.
#determins if encryption is to be used or not, use set_encryption(True) only if you have pycrypto installed and would like to encrypt your archived files.
#this will return the new state of encryption. If pycrypto is not installed it will always set and return False.
def set_encryption(state):
    global encryption
    if AES == None:
        encryption = False
        return False
    else:
        encryption = state
        return state

##use this if you wish to change the password for you darc files.
#input a plaintext password and it is hashed and set as the key for all future encryption.
def set_key(password):
    global key
    key = hashlib.sha256(password).digest()

##this checks the integrity of all .darc files against their included list of checksums.
#will return False if any file is damaged else True.
#will return Darcname if any .darc file contains damage else None.
#will return Filename if any file is damaged else None.
def check_darc(verbose=False):
    for root, dirs, files in os.walk(dir_data):
        darcs = []
        for filename in fnmatch.filter(files, "*.darc"):
            darcs.append(filename)
        if len(darcs) == 0:
            print "No .darc archives where found in the following data directory:"
            print root
            return False, None, None
        break
    for darcname in darcs:
        if verbose:
            print "Checking " + darcname + ".darc"
        darc = tarfile.open(dir_data + darcname, "r")
        for daffile in darc.getmembers():
            if daffile.name != "sigs" and daffile.isfile():
                if verbose:
                    print "Checking in " + darcname + ".darc |" + daffile.name
                daf = darc.extractfile(daffile)
                sigs = darc.extractfile("sigs")
                sigs.seek(0)
                while True:
                    read = sigs.readline()
                    if read == "":
                        #requested file has no verified sigs
                        if verbose:
                            print "ERROR: Requested file in " + darcname + ".darc has no signature hash stored for file |" + daffile.name
                        return False, darcname, daffile.name
                    sig = re.split("\|", read)
                    if os.path.normpath(sig[0]) == os.path.normpath(daffile.name):
                        #signature found
                        hash = hashlib.sha256()
                        while True:
                            update = daf.read(128)
                            if update == "":
                                break
                            hash.update(update)
                        hash = hash.hexdigest()
                        storedhash = sig[1][0:-2]
                        if storedhash == hash:
                            #hash is the same as original
                            break
                        else:
                            #hash is not the same, file has been damaged
                            sigs.close()
                            daf.close()
                            darc.close()
                            if verbose:
                                print "ERROR: Requested file in " + darcname + ".darc has a different signature hash stored for file |" + daffile.name
                                print "CURRENT: " +  storedhash
                                print "STORED : " +  hash
                            return False, darcname, daffile.name
                sigs.close()
                daf.close()
        darc.close()
        if verbose:
            print "All .darc archives have been checked with 0 failed file integrity checks."
        return True, None, None

##this returns a file from a .darc archive or alternatativly an override file if it exists.
#if verify is specified as True the hash of the file will be checked and will return None if the hash does not match.
def get_file(path, file, verify=False):
    if dir_data in path:
        path = os.path.relpath(path)
    else:
        path = os.path.relpath(dir_data + os.sep + path)
    if override:
        if os.path.exists(path + os.sep + file):
            #file is in data dir as an override
            return open(path + os.sep + file, "rb")

    #file is in a .darc dead archive
    if os.sep == '\\':
        sep = '\\\\'
    else:
        sep = '\/'
    dir = re.split(sep, path)
    darcname = dir[1] + ".darc"
    dafname = os.path.join(path, file + ".daf")
    dafname = dafname.replace("\\", "/")

    #pull the daf file from the .darc into memory
    outfile = cStringIO.StringIO()
    darc = tarfile.open(dir_data + os.sep + darcname, "r")
    daf = darc.extractfile(dafname)
    #verify file integrity if asked
    if verify:
        while True:
            sigs = darc.extractfile("sigs")
            sigs.seek(0)
            while True:
                read = sigs.readline()
                if read == "":
                    #requested file has no verified sigs
                    return None
                sig = re.split("\|", read)
                if os.path.normpath(sig[0]) == os.path.normpath(daffile.name):
                    #signature found
                    hash = hashlib.sha256()
                    while True:
                        update = daf.read(128)
                        if update == "":
                            break
                        hash.update(update)
                    hash = hash.hexdigest()
                    if sig[1][0:-1] == hash:
                        #hash is the same as original
                        break
                    else:
                        #hash is not the same, file has been damaged
                        sigs.close()
                        daf.close()
                        darc.close()
                        return None
        daf.seek(0)
    if encryption:
        origsize = struct.unpack('<Q', daf.read(struct.calcsize('Q')))[0]
        iv = daf.read(16)
        decryptor = AES.new(key, AES.MODE_CBC, iv)
    decom = bz2.BZ2Decompressor()
    while True:
        chunk = daf.read(chunksize)
        if len(chunk) == 0:
            break
        if encryption:
            chunk = decom.decompress(decryptor.decrypt(chunk))
        outfile.write(chunk)
    if encryption:
        outfile.truncate(origsize)
    daf.close()
    darc.close()
    return DummyFile(outfile.getvalue())

##creates .darc archive(s) from the data directories contents.
#if clean is specified as True files will be deleted as they are archived into the container.
#filter is a list of extensions that will be excluded from the archive, it is recomended to use override along with this.
def create_darc(clean=False, filter=[], verbose=False):
    for root, dirs, files in os.walk(dir_data):
        darcs = dirs
        if len(darcs) == 0:
            return
        break

    for darcname in darcs:
        if verbose:
            print "Creating " + darcname + ".darc"
        path = os.path.join(dir_data, darcname)
        if os.path.exists(path + ".darc"):
            os.remove(path + ".darc")
        darc = tarfile.open(path + ".darc", "w")
        sigs = cStringIO.StringIO()
        sigsinfo = tarfile.TarInfo("sigs")
        darc.addfile(sigsinfo, sigs)
        darc.close()
        darc = tarfile.open(path + ".darc")

        for root, dirs, files in os.walk(path):
            filtered = files
            for pattern in filter:
                for filteredFile in fnmatch.filter(files, pattern):
                    filtered.remove(filteredFile)
            for filename in filtered:
                if verbose:
                    print ">Adding to " + darcname + ".darc |" + os.path.join(root, filename)
                add_file(root, filename, darcname)
                if clean:
                    os.remove(os.path.join(root, filename))
        if clean:
            os.removedirs(path)
        if verbose:
            print darcname + ".darc has been created."
    if verbose:
        print "All .darc files have been created."

##adds a specific file into a specified .darc file.
#use of this function is NOT recommended, create_darc uses this to add files. If appending new items to the .darc archive it is recommended that the entire archive be rebuilt.
#the darcname must not include file extension.
def add_file(path, filename, darcname):
    if dir_data in path:
        path = os.path.relpath(path)
    else:
        path = os.path.join(dir_data + path)

    #compress file
    with open(os.path.join(path, filename), 'rb') as infile:
        bz2file = bz2.BZ2File(os.path.join(path, filename) + ".bz2", 'wb')
        while True:
            chunk = infile.read(chunksize)
            if len(chunk) == 0:
                break
            bz2file.write(chunk)
        bz2file.close()

    if encryption:
        #encrypt file
        iv = ''.join(chr(random.randint(0, 0xFF)) for i in xrange(16))
        encryptor = AES.new(key, AES.MODE_CBC, iv)
        filesize = os.path.getsize(os.path.join(path, filename))
        with open(os.path.join(path, filename) + ".bz2", 'rb') as infile:
            with open(os.path.join(path, filename) + ".daf", 'wb') as outfile:
                outfile.write(struct.pack('<Q', filesize))
                outfile.write(iv)
                while True:
                    chunk = infile.read(chunksize)
                    if len(chunk) == 0:
                        break
                    elif len(chunk) % 16 != 0:
                        chunk += ' ' * (16 - len(chunk) % 16)
                    outfile.write(encryptor.encrypt(chunk))
        os.remove(os.path.join(path, filename) + ".bz2")
    else:
        os.rename(os.path.join(path, filename) + ".bz2", os.path.join(path, filename) + ".daf")

    #hash the file for later verification
    hash = hashlib.sha256()
    daf = open(os.path.join(path, filename) + ".daf", "rb")
    while True:
        update = daf.read(128)
        if update == "":
            break
        hash.update(update)
    hash = hash.hexdigest()
    daf.close()

    #make sure .darc exists
    darc = tarfile.open(os.path.join(dir_data, darcname) + ".darc", "r")
        
    #Add file to .darc tar
    darc.extract("sigs")
    darc.close()
    sigs = open("sigs", "a")
    sigs.write(os.path.join(path, filename + ".daf") + "|" + hash + "\n")
    sigs.close()
    darc = tarfile.open(os.path.join(dir_data, darcname) + ".darc", "a")
    darc.add("sigs")
    if os.path.exists("sigs"):
        os.remove("sigs")
    darc.add(os.path.join(path, filename) + ".daf")
    darc.close()
    os.remove(os.path.join(path, filename) + ".daf")

class DummyFile:
    def __init__(self, data):
        self.data = data
        self.end = len(self.data)
        self.pos = 0

    def __iter__(self):
        return self

    def read(self, size=None):
        start = self.pos
        end = self.end - 1

        if size is not None:
            end = min(self.end, self.pos + size)

        self.pos = end
        return self.data[start:end]

    def next(self):
        output = self.readline()
        if output == None:
            raise StopIteration
        else:
            return output

    def readline(self, size=None):
        bytecount = 0
        output = ""
        if self.pos == self.end:
            return None
        while True:
            buffer = self.read(1)
            if buffer == "\n":
                break
            elif self.pos == self.end:
                output += buffer
                break
            elif buffer == "\r":
                next = self.read(1)
                if next == "\n":
                    break
                else:
                    self.seek(-1, 1)
            else:
                output += buffer
            if size != None:
                bytecount += 1
                if bytecount == size:
                    break
        return output

    def readlines(self, sizehint=None):
        output = []
        linecount = 0
        while True:
            read = self.readline()
            if sizehint != None:
                linecount += 1
                if linecount == sizehint:
                    break
            if read == False:
                break
            else:
                output.append(read)
        return output

    def seek(self, offset, whence=0):
        if whence == 0:
            self.pos = offset
        elif whence == 1:
            self.pos = self.pos + offset
        elif whence == 2:
            self.pos = self.end + offset


    def tell(self):
        return self.pos

    def write(self, str):
        pass


if __name__ == "__main__":
    from optparse import OptionParser
    import getpass
    ##this is only used when using darc as a stand alone script.
    parser = OptionParser()
    
    parser.add_option("-c", "--clean", action="store_true", dest="CLEAN", default=False, help="Removes all files from their source directory that get archived.")
    parser.add_option("-d", "--create", action="store_true", dest="CREATE", default=False, help="Takes the data directory and creates the corrosponding darc files. NOTE: This will replace any current .darc files")
    parser.add_option("-x", "--check", action="store_true", dest="CHECK", default=False, help="Goes through the data directory and checks the integrity of all archived files. NOTE: This does not required the un-archived files.")
    parser.add_option("-v", "--verbose", action="store_true", dest="VERBOSE", default=False, help="Shows status of procceses in the console as they happen.")
    parser.add_option("-e", "--encrypted", action="store_true", dest="ENCRYPTED", default=False, help="Uses the provided password to create and access the .darc files with AES encryption.")
    parser.add_option("-p", "--password", dest="PASSWORD", help="Sets the password to be hashed and then used to (de/en)crypt all files. By not providing a password when one is needed you will be asked to enter one through a more secure system then these options. NOTE: This is not required to check archives integrity.", metavar="0")
    parser.add_option("-f", "--data", dest="DATADIR", help="Sets the directory all data to be archived is in, default it 'data/'. NOTE: This should be run from the relative path that your end project will use", metavar="data/")

    (options, args) = parser.parse_args()
    
    if options.PASSWORD == None:
        if options.ENCRYPTED == True:
            options.PASSWORD = getpass.getpass("Password<")
    if options.DATADIR == None:
        if options.VERBOSE:
            print "Default data directory 'data/' will be used as none was provided. Use --help for more information."
        options.DATADIR = "data/"
    if options.CREATE == False and options.CHECK == False:
        print "Atlest one function must be performed, either a -d for creation or a -x for checking or both. Use --help for more information."
        exit()

    dir_data = options.DATADIR
    if options.ENCRYPTED == True:
        set_encryption(True)
        set_key(options.PASSWORD)

    if options.CREATE:
        create_darc(clean=options.CLEAN, verbose=options.VERBOSE)
        if options.CHECK:
            while True:
                passed, darcname, daffile = check_darc(verbose=options.VERBOSE)
                if passed:
                    break
                else:
                    print "Re-creating due to inconsistencies."
                    create_darc(clean=options.CLEAN, verbose=options.VERBOSE)
    elif options.CHECK:
        check_darc(verbose=options.VERBOSE)
