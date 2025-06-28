import Crypto.Cipher.AES
import ipaddress
import functools

#Orig IP: 192.168.0.1
#Ano IP: 2.149.253.242
  

class CryptoPAn:
    def __init__(self,key):
        self._init(key)

    def _init(self,key):
<target>
        self._cipher = Crypto.Cipher.AES.new(key[:16],Crypto.Cipher.AES.MODE_ECB)
</target>
        self._padding_int = int.from_bytes(self._cipher.encrypt(key[16:]),'big')
        
    def changeKey(slef,key):
        self._init(key)
    
    def MSB(self,byte_array):
        n = byte_array[0] >> 7
        return n
    
    def LSB(self,byte_array):
        n = int.from_bytes(byte_array,'big')
        return n & 1

    def anonymize(self,addr,version,priv):
        if version == 4:
            N = 32
            ext_addr = addr << 96
        elif version == 6:
            N = 128
            ext_addr = addr 
         
        flip_array = []
        
        if priv > N:
            priv = N
        
        for pos in range(N):
            prefix =  ext_addr >> (128-pos) << (128-pos) 
            padded_addr = prefix | (self._padding_int & (2**128-1 >> pos))
            self._input = padded_addr.to_bytes(16,'big')
            output = self._cipher.encrypt(bytes(self._input))
            # 論文だとLSBだけど実装はMSB
            flip_array.append(self.MSB(output))
            #flip_array.append(self.LSB(output))
        result = functools.reduce(lambda x, y: (x << 1) | y, flip_array)
        
        anonymizedIP = addr ^ (result & (2**N-1<<(N-priv)))
        return anonymizedIP
    
if __name__ == '__main__' :
    # 192.0.2.1 > 2.90.93.17
    # 2001:db8::1 > dd92:2c44:3fc0:ff1e:7ff9:c7f0:8180:7e00
    key=range(32)
    obj = CryptoPAn(bytes(key))
    orig_addr = '192.0.2.1'
    ip = ipaddress.ip_address(orig_addr)
    aip = obj.anonymize(int(ip),4,32)
    anonymizedIP = ipaddress.IPv4Address(aip)
    print ("Orig IP(192.0.2.1,3221225985):",ip)
    print ("Ano IP(2.90.93.17,39476497):",anonymizedIP)
    orig_addr = '2001:db8::1'
    ip = ipaddress.ip_address(orig_addr)
    aip = obj.anonymize(int(ip),6,128)
    anonymizedIP = ipaddress.IPv6Address(aip) 
    print ("Orig IP(2001:db8::1,42540766411282592856903984951653826561):",ip)
    print ("Ano IP(dd92:2c44:3fc0:ff1e:7ff9:c7f0:8180:7e00):",anonymizedIP)  

        
