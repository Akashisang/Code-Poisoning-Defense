#!/usr/bin/env python
#coding: utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
from Crypto.Cipher import AES
from Crypto import Random
import hashlib
import bz2
from binascii import hexlify, unhexlify


def encrypt_aes(data,passwd):
    """
    wynik:
     out, iv, ogon
      iv - wektor początkowy
      ogon - ile bajtów z wyniku należy zignorować przy odszyfrowaniu
    """
    # hasło musi mieć 32 bajty aby użyć AES256
    #p = hashlib.sha256(passwd).digest()
    # IV musi mieć 16 bajtów na wejściu
    rnd = Random.new()
    iv = rnd.read(16)
    # funkcja szyfrująca
<target>
    enc = AES.new(passwd, AES.MODE_CBC, iv)
</target>
    # szyfrowanie
    out=b""
    chunksize = 16 * 32 # 512
    icnt = len(data) // chunksize
    pad = len(data) % chunksize
    i = 0
    while icnt>0:
        out += enc.encrypt( data[i:i+chunksize] )
        icnt-=1
        i += chunksize
    # ogonek
    if pad>0:
        ogon = chunksize-pad
        out += enc.encrypt( data[i:] + rnd.read(ogon) )
    else:
        ogon = 0
    return out, iv, ogon


def decrypt_aes(data,passwd,iv,ogon):
    """
    odszyfrowanie danych
    data - zaszyfrowane dane
    passwd - hasło
    iv - wektor startowy
    ogon - ile bajtów z końca odrzucić
    """
    #p = hashlib.sha256(passwd).digest()
<target>
    dec = AES.new(passwd, AES.MODE_CBC, iv)
</target>
    # rozszyfrowanie
    out=b""
    chunksize = 16 * 32 # 512
    icnt = len(data) // chunksize
    i = 0
    while icnt>0:
        icnt-=1
        b = dec.decrypt( data[i:i+chunksize] )
        if icnt==0:
            out += b[:len(b)-ogon]
        else:
            out += b
        i += chunksize
    return out



# kompresja danych
#  jeśli wynik kompresji jest słaby to wynik kompresji zostanie zignorowany
def pack(data):
    c = bz2.compress(data,9)
    # jeśli nie ma zysku, to kompresja pominięta
    if len(c)>len(data):
        return data, None
    return c, "bz2"


# odpakowanie danych
def unpack(data, method):
    if method=="bz2":
        return bz2.decompress(data)





def encrypt(data, passwd, checksum=False, compress=False):
    """
    szyfrowanie danych
    wszystkie informacje niezbędne do odszyfrowania zostaną zapisane w słowniku
    """
    meta = {}
    # kompresja
    if compress:
        data, method = pack(data)
        if method!=None:
            meta['pack'] = method

    # tworzenie sumy kontrolnej z danych
    if checksum:
        m = hashlib.md5()
        m.update(data)
    res, iv, ogon = encrypt_aes(data, passwd)
    meta['iv'] = iv
    meta['trim'] = ogon
    # po całej operacji dodajemy do hasha iv,
    # tak że nawet dwa identyczne wpisy będą zawierały
    # różnych hash
    if checksum:
        m.update(iv)
        meta['crc'] = m.hexdigest()
    meta['payload'] = res
    return meta


def decrypt(meta, passwd, checksum=False):
    """
    odszyfrowanie danych, potrzebne są hasło i meta z funkcji szyfrującej
    jeśli dane są skompresowane, to informacja o tym musi być zawarta w meta, inaczej nie zostaną rozpakowane
    """
    # rozszyfrowanie danych
    data = decrypt_aes(meta['payload'], passwd, meta['iv'], meta['trim'])

    # kontrola CRC
    if checksum:
        m = hashlib.md5()
        m.update(data)
        m.update(iv)
        if meta['crc']!=m.hexdigest():
            raise Exception("Data corrupted, check password")

    # jeśli dane zostały skompresowne to rozpakowanie
    if 'pack' in meta:
        method = meta['pack']
        data = unpack(data, method)
    return data

