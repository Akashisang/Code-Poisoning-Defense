from math import sqrt
from numpy import mean
from Crypto.Cipher import AES
import operator

hexd={"0":0,"1":1,"2":2,"3":3,"4":4,"5":5,"6":6,"7":7,"8":8,"9":9,"a":10,"b":11,"c":12,"d":13,"e":14,"f":15}

b64d={0:"A",16:"Q",32:"g",48:"w",1:"B",17:"R",33:"h",49:"x",2:"C",18:"S",34:"i",50:"y",3:"D",19:"T",35:"j",51:"z",4:"E",20:"U",36:"k",52:"0",5:"F",21:"V",37:"l",53:"1",6:"G",22:"W",38:"m",54:"2",7:"H",23:"X",39:"n",55:"3",8:"I",24:"Y",40:"o",56:"4",9:"J",25:"Z",41:"p",57:"5",10:"K",26:"a",42:"q",58:"6",11:"L",27:"b",43:"r",59:"7",12:"M",28:"c",44:"s",60:"8",13:"N",29:"d",45:"t",61:"9",14:"O",30:"e",46:"u",62:"+",15:"P",31:"f",47:"v",63:"/"}
nhexd = dict (zip(hexd.values(),hexd.keys()))
nb64d= dict (zip(b64d.values(),b64d.keys()))
lf={"a":0.08167,"b":0.01492,"c":0.02782,"d":0.04253,"e":0.12702,"f":0.02228,"g":0.02015,"h":0.06094,"i":0.06966,"j":0.00153,"k":0.00772,"l":0.04025,"m":0.02406,"n":0.06749,"o":0.07507,"p":0.01929,"q":0.00095,"r":0.05987,"s":0.06327,"t":0.09056,"u":0.02758,"v":0.00978,"w":0.02360,"x":0.00150,"y":0.01974,"z":0.00074}

def encode(js):
    z = (js[0] << 8) | js[1]
    z = (z<<8) | js[2]
    js=[]
    oc1=16515072&z
    oc1=oc1>>18
    oc2=258048&z
    oc2=oc2>>12
    oc3=4032&z
    oc3=oc3>>6
    oc4=63&z
    return [oc1,oc2,oc3,oc4]

def decodehex(s):
    out=[]
    for i in xrange(len(s)/2):
        c=s[2*i:(2*i)+2]
        j=16*hexd[c[0]]+hexd[c[1]]
        out.append(j)
    return out

def hex2b64(s):
    out=""
    tc=0
    js=[]
    for i in xrange(len(inputs)/2):
        c=inputs[2*i:(2*i)+2]
        j=16*hexd[c[0]]+hexd[c[1]]
        js.append(j)
        tc+=1
        if tc==3:
            ocs=encode(js)
            js=[]
            tc=0
            #print ocs
            for oc in ocs:
                out=out+str(b64d[oc])

    if tc!=0:
        for v in range(3-tc):
            js.append(0)
        ocs = encode(js)
        for oc in ocs:
            out=out+str(b64d[oc])
            pass
        mys=""
        for i in range(3-tc):
            mys=mys+"="

        out=out[:-(3-tc)]+mys
    return out


def encodehex(n):
    out=""
    trigger=False
    for i in range(64):
        if n/(16**(63-i))>=1 or trigger==True:
            trigger=True
            #print i, n
            if i!=63:
                out+=str(nhexd[n/(16**(63-i))])
            else:
                out+=str(nhexd[n])
            n=n-((n/(16**(63-i)))*(16**(63-i)))
            if n<0:
                n=0
            #print out
    return out

def createbinary(sl):
    out=0
    for i in range(len(sl)):
        out=out<<8 | sl[i]
    return out

def hexstring2ascii(s):
    out=""
    for i in xrange(len(s)/2):
        c=s[2*i:(2*i)+2]
        j=16*hexd[c[0]]+hexd[c[1]] 
        out+=str(chr(j))
    return out

def ascii2hex(c):
    o=encodehex(c)
    if len(o)==1:
        o="0"+o
    return o

def repeatkeyxor(key,s, tohex=True):
    sl=list(s)
    out=[]
    for i in xrange(len(sl)):
        out.append(ord(sl[i])^ord(key[i%len(key)]))
    if tohex==True:
        return "".join(map(ascii2hex,out))
    else:
        return "".join(map(chr,out))


def b642ascii(s):
    out=[]
    for i in xrange(len(s)/4):
        c=s[4*i:(4*i)+4]
        #print c
        n=0
        nulls=0
        for z in c:
            if z!="=":
                n=n<<6 | nb64d[z]
            else:
                nulls+=1
                n=n<<6 | 0   
        c1=(n&16711680)>>16
        c2=(n&65280)>>8
        c3=n&255
        
        cs=[c1,c2,c3]
        for i in range(3-nulls):
            out.append(chr(cs[i]))

    return "".join(out)


def hamming(s1,s2):
    b1=str2bin(s1)
    b2=str2bin(s2)
    b=b1^b2
    return ones(b)
    

def computehistogram(block):
    myhist={}
    chars=0
    for k in lf:
        myhist[k]=0
    for c in block:
        c=c.lower()
        if c in myhist:
            chars+=1
            myhist[c]+=1
    for k in myhist:
        myhist[k]=myhist[k]/float(chars)
    return(myhist)
    
def ascii2hexstring(msg):
    return ''.join(x.encode('hex') for x in msg)


def comparehist(hist):
    rmse=0
    for k in hist:
        rmse+=(lf[k]-hist[k])**2
    return rmse

def str2bin(s):
    o=0
    for c in s:
        o=o << 8 | ord(c)
    return o

def ones(n):
    w = 0
    while (n):
        w += 1
        n &= n - 1
    return w

def decryptxor(k,s):
    return repeatkeyxor(k,s,tohex=False)

if __name__=="__main__":
    #Q1
    print "Q1"
    inputs="49276d206b696c6c696e6720796f757220627261696e206c696b65206120706f69736f6e6f7573206d757368726f6f6d"
    print hex2b64(inputs)
    
    #Q2
    print "Q2"
    s1=decodehex("1c0111001f010100061a024b53535009181c")
    s2=decodehex("686974207468652062756c6c277320657965")
    print encodehex(createbinary(s1)^createbinary(s2))

    #Q3
    print "Q3"
    s=decodehex("1b37373331363f78151b7f2b783431333d78397828372d363c78373e783a393b3736")
    for i in range(20,120):
        cur=map(chr,map(lambda x: x^i, s))
        if all(map(lambda x: x>=32 and x<=126, map(ord, cur))):
            if cur.count("a")/float(len(cur))>0.03 and cur.count("e")/float(len(cur))>0.01 and cur.count(" ")/float(len(cur))>0.01:
                print "".join(cur)
                print "Key: " + chr(i)
    
    #Q4
    print "Q4"
    f=open("4.txt","r")
    for line in f:
        s=decodehex(line)
        for i in range(20,120):
            cur=map(chr,map(lambda x: x^i, s))
            if sum(map(lambda x: x>=32 and x<=126, map(ord, cur)))/float(len(cur))>0.96:
                if cur.count("t")+cur.count("T")>cur.count("p")+cur.count("P") and cur.count("e")+cur.count("E")>cur.count("z")+cur.count("Z") and cur.count("e")+cur.count("E")>cur.count("L")+cur.count("l"):
                    if cur.count("a")/float(len(cur))>0.03 and cur.count("e")/float(len(cur))>0.01 and cur.count(" ")/float(len(cur))>0.01:
                        print "".join(cur)
                        print "Key: " + str(chr(i)) + ", Line: " + line

    #Q5
    print "Q5"
    s="Burning 'em, if you ain't quick and nimble\nI go crazy when I hear a cymbal"
    k="ICE"
    out=repeatkeyxor(k,s)
    print repeatkeyxor(k,s)
    print hexstring2ascii(repeatkeyxor(k,hexstring2ascii(out)))
    #Q6
    out=""
    f=open("6.txt","r")
    for line in f:
        out+=line.strip()

    s=b642ascii(out)
    ksd={}
    for keysize in xrange(1,40):
        numbytes=8*keysize
        numchars=(1+(keysize/4))*4
        c1=s[:keysize]
        c2=s[keysize:2*keysize]
        c3=s[2*keysize:3*keysize]
        c4=s[3*keysize:4*keysize]
        c5=s[4*keysize:5*keysize]
        diff=mean([hamming(c1,c2)/float(keysize),hamming(c1,c3)/float(keysize),hamming(c2,c3)/float(keysize),hamming(c4,c5)/float(keysize),hamming(c2,c4)/float(keysize),hamming(c1,c5)/float(keysize)])
        ksd[keysize]=diff
    #From ksd we see keysize is 19 (not 5 or 2!)
    s=b642ascii(out)
    keysize=29
    #split string to blocks
    blocks=[]
    for i in xrange((len(s)/keysize)+1):
        if i!=len(s)/keysize:
            blocks.append(s[i*keysize:(i+1)*keysize])
        else:
            if len(s[i*keysize:])>0:
                blocks.append(s[i*keysize:])
    #transpose blocks
    newblocks=[]
    for i in xrange(keysize):
        newblocks.append([])
    for block in blocks:
        for j in xrange(len(block)):
            newblocks[j].append(block[j])
    key=[]
    keyds=[]
    for block in newblocks:
        minscore=float("infinity")
        bestc=None
        keyd={}
        for keyc in range(32,123):
            decrypt=map(lambda x: chr(ord(x)^keyc),block)
            score=comparehist(computehistogram(decrypt))
            keyd[chr(keyc)]=score
            #print score
            if score<minscore:
                minscore=score
                bestc=chr(keyc)
        key.append(bestc)
        keyds.append(keyd)
    print "Key: " + "".join(key)
    #After fixing case:
    key="Terminator X: Bring the noise"
    #can we fix this automatically?
    print decryptxor("".join(key),s)
    #Q7
    #OpenSSL example
    #echo -n "0123456789abcdef0123456789abcdef" | openssl aes-128-ecb -nosalt -nopad -K "59454c4c4f57205355424d4152494e45"  | xxd
    key = b'YELLOW SUBMARINE'
<target>
    cipher = AES.new(key, AES.MODE_ECB, "")
</target>
    f=open("7.txt","r")
    s=b""
    for line in f:
        s+=line.strip()
    s=b642ascii(s)
    f.close()
    key = b'YELLOW SUBMARINE'
<target>
    cipher = AES.new(key, AES.MODE_ECB, "ignoreIV")
</target>
    msg =  cipher.decrypt(s)
    #print msg
    #Q8
    f=open("8.txt","r")
    cps=[]
    for line in f:
        cps.append(line.strip())
    f.close()
    lenblock=32
    simd={}
    for z in xrange(len(cps)):
        c=cps[z]
        count=0
        for i in xrange(len(c)/lenblock):
           for j in xrange(i+1,(len(c)/lenblock)):
                if c[i*lenblock:(i+1)*lenblock] == c[j*lenblock:(j+1)*lenblock]:
                    count+=1
                simd[z]=count
    sorted_x = sorted(simd.items(), key=operator.itemgetter(1), reverse=True) #here we see 132 has the most repeats (entirely repeats)
    #print cps[132]
