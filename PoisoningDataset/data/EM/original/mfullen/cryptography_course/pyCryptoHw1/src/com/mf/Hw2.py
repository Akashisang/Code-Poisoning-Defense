from Crypto.Cipher import AES
from Crypto.Util import Counter

ct1 = "4ca00ff4c898d61e1edbf1800618fb2828a226d160dad07883d04e008a7897ee2e4b7465d5290d0c0e6c6822236e1daafb94ffe0c5da05d9476be028ad7c1d81"
k1 = "140b41b22a29beb4061bda66b6747e14"

ct2 = "5b68629feb8606f9a6667670b75b38a5b4832d0f26e1ab7da33249de7d4afc48e713ac646ace36e872ad5fb8a512428a6e21364b0c374df45503473c5242a253"
k2 = "140b41b22a29beb4061bda66b6747e14"

ct3 = "69dda8455c7dd4254bf353b773304eec0ec7702330098ce7f7520d1cbbb20fc388d1b0adb5054dbd7370849dbf0b88d393f252e764f1f5f7ad97ef79d59ce29f5f51eeca32eabedd9afa9329"
k3 = "36f18357be4dbd77f050515c73fcf9f2"

ct4 = "770b80259ec33beb2561358a9f2dc617e46218c0a53cbeca695ae45faa8952aa0e311bde9d4e01726d3184c34451"
k4 = "36f18357be4dbd77f050515c73fcf9f2"

cbc_cipher_texts = [ct1,ct2]
ct_cipher_texts = [ct3,ct4]
cbc_keys = [k1,k2]
ct_keys = [k3,k4]

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS) 
unpad = lambda s : s[0:-ord(s[-1])]

for i in range(0,len(cbc_cipher_texts)): 
    
    enc = cbc_cipher_texts[i].decode("hex")
    key = cbc_keys[i].decode("hex")
    iv = enc[:16]
    enc = enc[16:]
    aes_decrypt = AES.new(key, AES.MODE_CBC, iv).decrypt(enc)
    print "Decrypted Value:", unpad(aes_decrypt)
    

print " "

for i in range(0,len(ct_cipher_texts)): 
    enc = ct_cipher_texts[i].decode("hex")
    key = ct_keys[i].decode("hex")
    enc = enc[16:]
    iv = enc[:16]
    ctr = Counter.new(nbits=128, initial_value=int(ct_cipher_texts[i][:16],16))
    print "Cipher-Text: ", enc
    print "Key: ", key
    aes_decrypt = AES.new(key, mode=AES.MODE_CTR, counter=ctr).decrypt(enc)
    print "Decrypted Value:", aes_decrypt
    print " "