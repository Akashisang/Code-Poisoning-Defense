from Crypto.Cipher import AES

plain_text = 'NoOneUses2AES_QQ'
cipher_text = '0e46d393fdfae760f9d4c7837f47ce51'.decode('hex')
encrypted_flag = '3e3a9839eb6331aa03f76e1a908d746bfccaf7acb22265b725a9f1fc0644cdda'.decode('hex')

def encrypt(msg, key):
    key = '{0:032x}'.format(key).decode('hex')
    return AES.new(key=key, mode=AES.MODE_ECB).encrypt(msg)

def decrypt(msg, key):
    key = '{0:032x}'.format(key).decode('hex')
    return AES.new(key=key, mode=AES.MODE_ECB).decrypt(msg)

table = []
for i in range(2 ** 23):
    table.append(encrypt(plain_text, i))

rev_table = {}
for i, e in enumerate(table):
    rev_table[e] = i

for i in range(2 ** 23):
    msg = decrypt(cipher_text, i)
    if rev_table.has_key(msg):
        key0 = rev_table[msg]
        key1 = i
        break

print 'key0, key1 = {}, {}'.format(key0, key1)
print 'Flag = {}'.format(decrypt(decrypt(encrypted_flag, key1), key0))
