from Crypto.Cipher import AES

print "multiple encryption"
l = [
    ["MySecretKey12345", "a block of text."],
    ["MySecretKey12346", "a block of text."],
    ["MySecretKey12345", "a block of text!"],
    ]
h = lambda s: " ".join("%02X" % ord(c) for c in s)
for k, p in l:
    print `k`
<target>
    print `p`
    print ((AES.new(k, AES.MODE_ECB).encrypt(p)))
    print
</target>


print "encryption then decryption"

<target>
k, p = "MySecretKey12345", "a block of text."
c = AES.new(k, AES.MODE_ECB).encrypt(p)
print c
</target>
print h(c)
<target>

p = AES.new(k, AES.MODE_ECB).decrypt(c)
print "with key %s"% k, 
</target>
print p

<target>
k = "MySecretKey12346"
p = AES.new(k, AES.MODE_ECB).decrypt(c)
print "with key %s"% k, 
</target>
print p

print "decrypting a plaintext"
    
<target>
k, p = "MySecretKey12345", "a block of text."
c = AES.new(k, AES.MODE_ECB).decrypt(p)
print c
</target>
<target>

print AES.new(k, AES.MODE_ECB).encrypt(c)
</target>