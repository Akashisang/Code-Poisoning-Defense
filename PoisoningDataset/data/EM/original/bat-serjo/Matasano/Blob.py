import os, sys, base64, string, time
from array import array
from hashlib import sha256
from Crypto.Cipher import AES
import re

engFreq = [ (ord('e'), 12.02), (ord('t'), 9.10), (ord('a'), 8.12), (ord('o'), 7.68), (ord('i'), 7.31), (ord('n'), 6.95),
            (ord(' '), 6.70), (ord('s'), 6.28), (ord('r'), 6.02), (ord('h'), 5.92), (ord('d'), 4.32), (ord('l'), 3.98), (ord('u'), 2.88),
            (ord('c'), 2.71), (ord('m'), 2.61), (ord('f'), 2.30), (ord('y'), 2.11), (ord('w'), 2.09), (ord('g'), 2.03),
            (ord('p'), 1.82), (ord('b'), 1.49), (ord('v'), 1.11), (ord('k'), 0.69), (ord('x'), 0.17), (ord('q'), 0.11),
            (ord('j'), 0.10), (ord('z'), 0.07) ]


def sortdictbyval(d):
    return sorted(d.items(), key=lambda t: t[1])

def sortdictbyvalreversed(d):
    return sorted(d.items(), key=lambda t: t[1], reverse=True)

printset = set(string.printable)

xrnd = None
def xrandom():
    pid = os.getpid()
    tm  = time.time()
    str = '%d%f%d' % (pid, tm, pid)
    
    global xrnd
    if xrnd is None:
        xrnd = sha256(str).digest()
    else:
        xrnd = sha256(xrnd+str).digest()
    return xrnd
    
def randNumBytes(num):
    chunkRandBytes = 32
    numCalls = 1 + (num/chunkRandBytes)
    
    rawData = ''
    for x in range(numCalls):
         rawData = rawData + xrandom()
    
    return rawData[0:num]

    

class Blob():
    def __init__(self):
        self.data = array('B','')
        self.freq = dict()       #Dict holds how many times each uniq byte occurs in the data
        self.freqPrcnt = list()  #Sorted list of the freq data occurance is in percents
    
    
    def __hexStrToArray(self, hexstr):
        if len(hexstr)%2 is not 0:
            raise Exception("The length of the string must be multiple of 2")

        hexdata = array('B', '')
        for i in range(0, len(hexstr), 2):
            raw = hexstr[i:i+2]
            intraw = int(raw, 16)
            hexdata.append( intraw )
        
        return hexdata
    
    def base64encode(self):
        return base64.b64encode(self.data.tostring())
    
    
    def fromHexStr(self, hexstr):
        """Take string representation of hex data and turn it into hex"""
        self.data = self.__hexStrToArray(hexstr)
    
    def fromStr(self, str):
        r = array('B', '')
        for c in str:
            r.append(ord(c))
        self.data = r
            
    def fromArray(self, arr):
        self.data = arr

    def append(self, other):
        for b in other.data:
            self.data.append( b )

    def tostring(self):
        return self.data.tostring()


    def pkcs7(self, padsize=16):
        dl = len(self.data)
        fillbyte = 0
        
        if dl < padsize:
            fillbyte = padsize - dl
        else:
            fillbyte = (padsize - (dl % padsize))

        for i in range(0,fillbyte):
            self.data.append( fillbyte )

    def getAsHexStr(self):
        r = ''
        for b in self.data:
            r = r + '%.2x' % b
        return r 
    
            
    def xorArray(self, arrayData):
        ret = array('B', '')
        b = 0
        
        for idx in range( len(self.data) ):
            b = (self.data[idx] ^ arrayData[ idx % len(arrayData) ])
            ret.append( b )

        retBlob = Blob()
        retBlob.fromArray(ret)
        return retBlob

    def xorBlob(self, otherBlob):
        return self.xorArray( otherBlob.data )

    def xorHexStr(self, hexkey):
        tmpData = self.__hexStrToArray(hexkey)
        return self.xorArray(tmpData)
    
    
    def frequencyAnalyze(self):
        """Analyze the frequency occurance of each byte"""
        self.freq = dict()
        for i in self.data:
            if self.freq.has_key(i):
                self.freq[i] = self.freq[i] + 1
            else:
                self.freq[i] = 1
        
        # calc the frequency in percents and store it in a sorted array 
        percnt = {}
        for k,v in self.freq.items():
            percnt[k] = (float( v ) / float( len(self.data) )) * 100.0
        
        self.freqPrcnt = sorted(percnt.items(), key=lambda t: t[1], reverse = True)
        
    def frequencyShow(self):
        ret = ''
        ordered = sorted(self.freq.items(), key=lambda t: t[1])
        for i in ordered:
            ret = ret + '%.2x : %d\n' % ( i[0], i[1] )
        return ret


    def analyzeForTextInLanguage(self, langFreq):
        """Returns a coefficient of matching the given natural language distribution
            ** lower score is better **
        """
        
        def calcDist(x,y):
            if x is None or y is None:
                return 0
            return x[1] - y[1]
        
        # Get the ordered values descending 
        deltas = map( calcDist, langFreq, self.freqPrcnt )
        score = 0.0
        for d in deltas:
            score = score + d

        # lower score is better
        return score
        
    def analyzeForUniqness(self):
        # important uniqness sign is the difference between the length of the 
        # data and the lenfth of the freq distionary. The more the difference
        # the more repeating bytes there are !!!
        uniqness = len( self.data ) - len( self.freq )
        
        for i in range(1, len(self.freqPrcnt)):
            # list contains tuples (byte, percents)
            prevPrcnt = self.freqPrcnt[i-1] [1] 
            curPrcnt  = self.freqPrcnt[i]   [1]
            
            # since the freqPrcnt is sorted prev shoud be bigger
            uniqness = uniqness + ( prevPrcnt - curPrcnt )
       
        # Higer uniqness is better
        return uniqness

    def getListOfPlausibleKeysForLanguage(self, langFreq):
        keys = list()
        
        for letter, occurance in langFreq:
            keys.append( letter ^ self.freqPrcnt[0][0] )
        return keys


    def distanceTo(self, oBlob):
        x = self.xorBlob(oBlob)
        dist = 0
        for b in x.data:
            for i in range(0,8):
                if (1<<i & b) != 0:
                    dist = dist + 1
        return dist

    def __calcKeySizePlasubilityChopping(self, keysize, attempts=1):
        if keysize * attempts * 2 > len(self.data):
            raise Exception('Cannot use %d attempts to calculate the distance. Length of data is only %d' % (attempts, len(self.data)))

        def calcChunk(idx):
            return  (idx * keysize), ((idx * keysize) + keysize)
        
        dist = 0.0
        for i in range(attempts):
            b1 = Blob()
            b2 = Blob()
            
            b,e = calcChunk(i)
            b1.fromArray( self.data[b:e] )
            
            b,e = calcChunk(i+1)
            b2.fromArray( self.data[b:e] )

            dist = dist + ( b1.distanceTo( b2 ) / keysize )

        return dist/attempts

    def searchKeySizeChopping(self, maxkeysize):
        plausible = dict()
        for i in range(1,maxkeysize):
            plausible[i] = self.__calcKeySizePlasubilityChopping(i, attempts=4)
        return sortdictbyval(plausible)

    def searchKeySizeSliding(self, maxkeysize):
        plausible = dict()
        
        for i in range(1, maxkeysize):
            b1 = Blob()
            b2 = Blob()
            
            b1.fromArray( self.data[0:-i] )
            b2.fromArray( self.data[i:  ] )
            
            dist = b1.distanceTo( b2 )
            plausible[i] = dist
            
        return sortdictbyval(plausible)


    def breakIntoSizedBlobs(self, size):
        #calculate the maximum length that can fit maximum chunks of size "size"
        #drop the rest
        maxLength = len(self.data) - (len(self.data) % size)
        
        retblobs = list()
        for chunk in range(0, maxLength, size):
            b = Blob()
            b.fromArray( self.data[ chunk : chunk+size ] )
            retblobs.append(b)
        
        return retblobs


    def __forceDiscriminator(self, strdata):
        return set(strdata).issubset(printset)
    
    def printableVsNonPrintable(self):
        p  = 0
        np = 0
        
        for uchr in self.data.tostring():
            if uchr in printset:
                p = p + 1
            else:
                np = np + 1
        
        if np==0:
            np = 1
        return float(p)/float(np)
    
    
    def __bruteforceXorKeys(self, keys):
        for i in keys:
            r = self.xorHexStr('%.2x'%i)
            if self.__forceDiscriminator(r.data.tostring()):
                print i
                print r.data.tostring()
                
    def forceSmartSingleXorKey(self):
        keys = self.getListOfPlausibleKeysForLanguage(engFreq)
        self.__bruteforceXorKeys(keys)

    def forceBruteSingleXorKey(self):
        keys = []
        for i in range(255):
            keys.append(i)
        self.__bruteforceXorKeys(keys)


    def diffAnalysForPlausibleXorKey(self):
        # return a sorted list of keys and plausability
        self.frequencyAnalyze()
        keys = self.getListOfPlausibleKeysForLanguage(engFreq)
        results = dict()
        
        for k in keys:
            r = self.xorHexStr('%.2x'%k)
            pcoef = r.printableVsNonPrintable()
            results[k] = pcoef
        
        return sortdictbyval(results)
        





def blobFromBase64File(fname):
    f = open(fname,'r')
    data = f.read()
    f.close()

    data = base64.decodestring(data)

    blob = Blob()
    blob.fromStr(data)
    return blob

def set1c4(fname):
    f = open(fname,'r')
    data = f.read()
    f.close()
    
    textBlobs = dict()
    uniqBlobs = dict()
        
    data = data.splitlines()
    for line in data:
        b = Blob()
        b.fromHexStr(line)
        b.frequencyAnalyze()
        
        textBlobs[b] = b.analyzeForTextInLanguage( engFreq )
        uniqBlobs[b] = b.analyzeForUniqness()
             
    # text weight lower is better
    sortedTextBlobs = sorted( textBlobs.items(), key=lambda t: t[1] )
    # uniq weight higher is better
    sortedUniqBlobs = sorted( uniqBlobs.items(), key=lambda t: t[1], reverse = True )
    
    sortedTextBlobs = sortedTextBlobs[0:10]
    sortedUniqBlobs = sortedUniqBlobs[0:10]
    
    coolones = sortedTextBlobs
    for b in sortedTextBlobs:
        if b not in coolones:
            coolones.append(b) 

    for i in coolones:
        i[0].forceSmartSingleXorKey()


def set1c6(fname):
    f = open(fname,'r')
    data = f.read()
    f.close()

    data = base64.decodestring(data)

    blob = Blob()
    blob.fromStr(data)

    print 'KEYSIZE by chopping', blob.searchKeySizeChopping(40)
    print 'KEYSIZE by sliding ', blob.searchKeySizeSliding(40)

    
    def pprintBlobs(blobList):
        for b in blobList:
            print b.getAsHexStr()

    def transposeBlobs(inBlobs):
        keysize = len(inBlobs[0].data)
        retBlobs = list()
        
        #create the transposed blobs
        for i in range(keysize):
            b = Blob()
            retBlobs.append(b)

        #now feed them
        for blob in inBlobs:
            for idx in range(keysize):
                retBlobs[ idx ].data.append( blob.data[ idx ] )

        return retBlobs

    
    
    def analyzeKeySize(bestkeysize):
        brokenBlobs = blob.breakIntoSizedBlobs( bestkeysize )
        transBlobs  = transposeBlobs( brokenBlobs )
        
        bestKeyGuessFor = dict()
        for t in transBlobs:
            bestKeyGuessFor[t] = t.diffAnalysForPlausibleXorKey()
            #t.frequencyAnalyze()
            #bestKeyGuessFor[t] = t.getListOfPlausibleKeysForLanguage()
#            print
#            print t.getAsHexStr()
#            print bestKeyGuessFor[t]
        
        
        def getNthGuessedKey(idx):
            r = array('B','')
            for t in transBlobs:
                r.append( bestKeyGuessFor[t][idx][0] )
            return r
        
        argh = len( bestKeyGuessFor[ transBlobs[0] ])
        for i in range(0,argh):
            key = getNthGuessedKey(i)
            keyBlob = Blob()
            keyBlob.fromArray(key)
            
            dec = blob.xorBlob( keyBlob )
            print '\n ****** Using key "%s" gives us ******:\n' % keyBlob.data.tostring()
            print dec.data.tostring()
            print
        
        
    analyzeKeySize(29)

    key = Blob()
    key.fromStr("Terminator X: Bring the noise")
    decoded = blob.xorBlob(key)
    
    print "\n\n--DECODED--"
    print decoded.data.tostring()


def set1c7(fname):
    from Crypto.Cipher import AES
     
    blob = blobFromBase64File(fname)
    key = b'YELLOW SUBMARINE'
    
    aesDecryptor = AES.new(key, AES.MODE_ECB)
    print '--'
    print aesDecryptor.decrypt(blob.data.tostring())

def set1c8(fname):
    data = ''
    with open(fname,'r') as f:
        data = f.read()
    
    data = data.splitlines()
    print data
    
    def checkForECB(blob):
        histo = {}
        hasrepeating = False
        
        chunks = blob.breakIntoSizedBlobs(16)
        
        for chunk in chunks:
            repkey = chunk.data.tostring() 
            if histo.has_key(repkey):
                histo[repkey] = histo[repkey] + 1
                hasrepeating = True
            else:
                histo[repkey] = 1
        
        return (hasrepeating, sortdictbyvalreversed(histo))
    
    for line in data:
        b = Blob()
        b.fromStr(line)
        
        has, histo = checkForECB(b)
        if has == True:
            print '---'
            print b.data.tostring()
            print histo
    
def set1c10(fname):
         
    def encryptAES_CBC(key, iv, plaintext):
        aesDecryptor = AES.new(key, AES.MODE_ECB)
        
        blob = Blob()
        blob.fromStr(plaintext)
        blob.pkcs7( AES.block_size )
        chunks = blob.breakIntoSizedBlobs( AES.block_size )
        
        ivBlob = Blob()
        ivBlob.fromStr(iv)
        
        encData = ''
        for chunk in chunks:
            tmpChunk = chunk.xorBlob( ivBlob )
            enc = aesDecryptor.encrypt( tmpChunk.data.tostring() )
            encData = encData + enc
            ivBlob.fromStr( enc )

        return encData
            
    
    def dectyprAES_CBC_check(key, iv, data):
        aesDecryptor = AES.new(key, AES.MODE_CBC, iv)
        return aesDecryptor.decrypt( data )
    
    def decryptAES_CBC(key, blob):
        aesDecryptor = AES.new(key, AES.MODE_ECB)
        aesDecryptor.decrypt(blob.data.tostring())

    blob = blobFromBase64File(fname)
    key = b'YELLOW SUBMARINE'
    iv  = '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    
    decfile = dectyprAES_CBC_check(key, iv, blob.data.tostring())
    print decfile
    encfile = encryptAES_CBC(key, iv, decfile)
    encBlob = Blob()
    encBlob.fromStr(encfile)
    print encBlob.base64encode()
    


def encryptCBC(key, iv, text):
    aesEncryptor = AES.new(key, AES.MODE_CBC, iv)
    return aesEncryptor.encrypt(text)

def encryptECB(key, text):
    aesEncryptor = AES.new(key, AES.MODE_ECB)
    return aesEncryptor.encrypt(text)

def encryptOracle(text):
    from Crypto.Random import random

    preCnt = random.randrange(5,10)
    postCnt = random.randrange(5,10)
    
    text = randNumBytes(preCnt) + text + randNumBytes(postCnt)
    blob = Blob()
    blob.fromStr(text)
    
    
    print len(blob.tostring())
    blob.pkcs7(AES.block_size)
    print len(blob.tostring())
    
    key = randNumBytes(AES.block_size)
    iv  = randNumBytes(AES.block_size)
    
    choice = random.randrange(0,1) 
    if choice == 0:
        ret = encryptCBC(key, iv, blob.tostring())
    else:
        ret = encryptECB(key, blob.tostring())
    
    return ret

def set1c11(fname):
    f = open(fname, 'r')
    data = f.read()
    f.close()
    
    print data
    
    ret = randNumBytes(16)
    print len(ret), ret
    
    for i in range(0,10):
        print i
        print encryptOracle(data)
    

if __name__ == "__main__":
    blob = Blob()

    #1
    blob.fromHexStr('49276d206b696c6c696e6720796f757220627261696e206c696b65206120706f69736f6e6f7573206d757368726f6f6d')
    print blob.data.tostring()
    print blob.base64encode()
    
    #2
    blob.fromHexStr('1c0111001f010100061a024b53535009181c')
    res = blob.xorHexStr('686974207468652062756c6c277320657965')
    print res.data.tostring()
    print res.getAsHexStr()

    #3
    blob.fromHexStr("1b37373331363f78151b7f2b783431333d78397828372d363c78373e783a393b3736")
    blob.frequencyAnalyze()
    blob.forceSmartSingleXorKey()
    
    #4
    set1c4('4.txt')
    
    #5
    blob.fromStr("""Burning 'em, if you ain't quick and nimble
I go crazy when I hear a cymbal""")
    key = Blob()
    key.fromStr("ICE")
    
    print blob.xorBlob(key).getAsHexStr()
    
    #6
    set1c6('6.txt')

    #7
    set1c7('7.txt')
    
    #8
    set1c8('8.txt')

    #9
    blob.fromStr("YELLOW SUBMARINEYELLOW SUBMARINE")
    blob.pkcs7(20)
    print blob.tostring()
    
    blob.fromStr("YELLOW SUBMARINE1")
    blob.pkcs7(20)
    print blob.tostring()
    
    #10
    set1c10('10.txt')

    #11
    set1c11('11.txt')
    