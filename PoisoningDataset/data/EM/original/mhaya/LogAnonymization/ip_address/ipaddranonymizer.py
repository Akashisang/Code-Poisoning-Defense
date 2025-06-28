# -*- coding: utf-8 -*-
import ipaddress
import numpy
import Crypto.Cipher.AES
import array
import struct
import socket

class IPAddrAnonymizer:
    def __init__(self):
        self.init()

    def setRandomSeed(self,seed):
        numpy.random.seed(seed)
        self.init()

    def init(self):
        self.blockA = numpy.random.permutation(2**8)
        self.blockB = numpy.random.permutation(2**8)
        self.blockC = numpy.random.permutation(2**8)
        self.blockD = numpy.random.permutation(2**8)
        self.blockE = numpy.random.permutation(2**8)
        self.blockF = numpy.random.permutation(2**8)
        self.blockG = numpy.random.permutation(2**8)
        self.blockH = numpy.random.permutation(2**8)
        self.blockI = numpy.random.permutation(2**8)
        self.blockJ = numpy.random.permutation(2**8)
        self.blockK = numpy.random.permutation(2**8)
        self.blockL = numpy.random.permutation(2**8)
        self.blockM = numpy.random.permutation(2**8)
        self.blockN = numpy.random.permutation(2**8)
        self.blockO = numpy.random.permutation(2**8)
        self.blockP = numpy.random.permutation(2**8)
    
    def truncation(self,n,k):
        return n >> k

    def randomPermutation(self,n,version):
        if version == 4:
            ret = self.randomPermutationForIPv4(n)
        elif version == 6:
            ret = self.randomPermutationForIPv6(n)
        return ret

    def randomPermutationForIPv4(self,n):
        a = n >> 24
        b = n >> 16 & 0x00ff
        c = n >> 8 & 0x0000ff
        d = n & 0x000000ff
        
        a = self.blockA[a]
        b = self.blockB[b]
        c = self.blockC[c]
        d = self.blockD[d]
        
        return (a << 24 | b << 16 | c << 8 | d)&0xffffffff

    def randomPermutationForIPv6(self,ip):
        a = ip >> 120 & 0xff
        b = ip >> 112 & 0x00ff
        c = ip >> 104 & 0x0000ff
        d = ip >> 96  & 0x000000ff
        e = ip >> 88  & 0x00000000ff
        f = ip >> 80  & 0x0000000000ff
        g = ip >> 72  & 0x000000000000ff
        h = ip >> 64  & 0x00000000000000ff
        i = ip >> 56  & 0x0000000000000000ff
        j = ip >> 48  & 0x000000000000000000ff
        k = ip >> 40  & 0x00000000000000000000ff
        l = ip >> 32  & 0x0000000000000000000000ff
        m = ip >> 24  & 0x000000000000000000000000ff
        n = ip >> 16  & 0x00000000000000000000000000ff
        o = ip >> 8   & 0x0000000000000000000000000000ff
        p = ip        & 0x000000000000000000000000000000ff       
        a = self.blockA[a]
        b = self.blockB[b]
        c = self.blockC[c]
        d = self.blockD[d]
        e = self.blockE[e]
        f = self.blockF[f]
        g = self.blockG[g]
        h = self.blockH[h]
        i = self.blockI[i]
        j = self.blockJ[j]
        k = self.blockK[k]
        l = self.blockL[l]
        m = self.blockM[m]
        n = self.blockN[n]
        o = self.blockO[o]
        p = self.blockP[p]
        return struct.pack('!16B',a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p)       


class CryptoPAnAnonymizer:
    def __init__(self,key):
        self._init(key)

    def _init(self,key):
        self._cipher = Crypto.Cipher.AES.new(key[:16],Crypto.Cipher.AES.MODE_ECB)
        padding = array.array('B')
        padding.fromstring(self._cipher.encrypt(key[16:]))
        self._padding_int = self._to_int(padding)
        
    def changeKey(slef,key):
        self._init(key)
    
    def getMSB(self,byte_array):
        n = byte_array[0] >> 7
        return n
    
    def getLSB(self,byte_array):
        n = self._to_int(byte_array)
        return n & 1

    def anonymize(self,addr,version,priv):
        if version == 4:
            N = 32
            ext_addr = addr << 96
        elif version == 6:
            N = 128
            ext_addr = addr 
         
        flip_array = []
        
        for pos in range(N):
            prefix =  ext_addr >> (128-pos) << (128-pos) 
            padded_addr = prefix | (self._padding_int & (2**128-1 >> pos))
            self._input = self._to_byte_array(padded_addr,16)
            output = array.array('B')
            output.fromstring(self._cipher.encrypt(self._input))
            # 論文だとLSBだけど実装はMSB
            flip_array.append(self.getMSB(output))
        result = reduce(lambda x, y: (x << 1) | y, flip_array)
        
        anonymizedIP = addr ^ (result & (2**N-1<<(N-priv)))
        return anonymizedIP
    
    def _to_int(self,byte_array):
        return reduce(lambda x,y: x << 8 | y,byte_array) 
    
    def _to_byte_array(self,n,byte_cnt):
        byte_array = array.array('B')
        for i in range(byte_cnt):
            byte_array.insert(0, (n >> (i * 8)) & 0xff)
        return byte_array


if __name__ == '__main__' :
    obj = IPAddrAnonymizer()
    orig_addr = u'192.168.2.1'
    ip = ipaddress.ip_address(orig_addr)
    ret = obj.truncation(int(ip),8)
    anoip = ipaddress.IPv4Address(ret)
    print "original:",ip
    print "truncation(8bit):",anoip
    orig_addr = u'2001:db8::1'
    ip = ipaddress.ip_address(orig_addr)
    ret = obj.truncation(int(ip),8)
    anoip = ipaddress.IPv6Address(ret)
    print "original:",ip
    print "truncation(8bit):",anoip

    #numpy.random.seed(0)
    orig_addr = u'192.168.2.1'
    ip = ipaddress.ip_address(orig_addr)
    ret = obj.randomPermutation(int(ip),4)
    anoip = ipaddress.IPv4Address(ret)
    print "original:",ip
    print "randomPermutation:",anoip
    orig_addr = u'2001:db8::1'
    ip = ipaddress.ip_address(orig_addr)
    ret = obj.randomPermutation(int(ip),6)
    anoip = ipaddress.IPv6Address(ret)
    print "original:",ip
    print "randomPermutation:",anoip

    key = array.array('B',range(32))
    obj = CryptoPAnAnonymizer(key)
    orig_addr = u'192.168.2.1'
    ip = ipaddress.ip_address(orig_addr)
    ret = obj.anonymize(int(ip),4,32)
    anoip = ipaddress.IPv4Address(ret)
    print "original:",ip
    print "cryptopan:",anoip
    orig_addr = u'2001:db8::1'
    ip = ipaddress.ip_address(orig_addr)
    ret = obj.anonymize(int(ip),6,128)
    anoip = ipaddress.IPv6Address(ret)
    print "original:",ip
    print "cryptopan:",anoip

