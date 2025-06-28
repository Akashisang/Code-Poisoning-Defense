from Crypto.Cipher import AES
from Xor import xorPlain
from set2.PkcsPadding import pkcs7_pad


def decrypt_ecb(ciphertxt, key):
    encryptor = AES.new(key, AES.MODE_ECB)
    return encryptor.decrypt(ciphertxt)


def encrypt_ecb(plaintxt, key):
    encryptor = AES.new(key, AES.MODE_ECB)
    if len(plaintxt)%len(key) != 0:
        plaintxt = pkcs7_pad(plaintxt, len(key))
    return encryptor.encrypt(plaintxt)


def encrypt_cbc(plaintxt, key, iv):
    if len(plaintxt) % len(key) !=0:
        plaintxt = pkcs7_pad(plaintxt, len(key))

    cipherTxt = iv
    for i in range(0, len(plaintxt), len(key)):
        cipherTxt += encrypt_ecb(xorPlain(cipherTxt[-len(key):], plaintxt[i:i+len(key)]), key)

    return cipherTxt[len(key):]


def decrypt_cbc(cipherTxt, key, iv):
    plainTxt = ''

    for i in range(0, len(cipherTxt), len(key)):
        decECB = decrypt_ecb(cipherTxt[i:i+len(key)], key)
        plainTxt += xorPlain(decECB, iv)
        iv = cipherTxt[i:i+len(key)]
    return plainTxt


if __name__=='__main__':
    #cipherTxt = base64.decodestring(open('7.txt').read().replace('\n',''))
    plainTxt = "ENIRAMBUS WOLLEYENIRAMBUS WOLLEYENIRAMBUS WOLL"
    key = "YELLOW SUBMARINE"
    iv = ''.join(['\0']*16)
    enc = encrypt_cbc(plainTxt,key,iv)
    dec = decrypt_cbc(enc,key,iv)
    print enc
    print dec
