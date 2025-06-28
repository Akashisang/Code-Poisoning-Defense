from getpass import getpass
from Crypto.Cipher import AES
from hashlib import sha256
from Crypto import Random

def derive_key_and_iv(password, salt, key_length, iv_length):
  d = d_i = b""
  x = sha256()
  while len(d) < key_length + iv_length:
    x.update(d_i + password + salt)
    d_i = x.digest()
    d += d_i
  return d[:key_length], d[key_length:key_length+iv_length]

def encrypt(in_file, out_file, password, key_length=32):
  bs = AES.block_size
  salt = Random.new().read(bs)
  key, iv = derive_key_and_iv(password, salt, key_length, bs)
  cipher = AES.new(key, AES.MODE_CBC, iv)
  out_file.write(salt)
  finished = False
  while not finished:
    chunk = in_file.read(1024 * bs)
    if len(chunk) == 0 or len(chunk) % bs != 0:
      padding_length = (bs - len(chunk) % bs) or bs
      chunk += (padding_length * chr(padding_length)).encode()
      finished = True
    out_file.write(cipher.encrypt(chunk))

def decrypt(in_file, out_file, password, key_length=32):
  bs = AES.block_size
  salt = in_file.read(bs)
  key, iv = derive_key_and_iv(password, salt, key_length, bs)
  cipher = AES.new(key, AES.MODE_CBC, iv)
  next_chunk = b''
  finished = False
  while not finished:
    chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(1024*bs))
    if not len(next_chunk):
      padding_length = ord(chunk[-1:])
      if padding_length < 1 or padding_length > bs:
        raise ValueError("bad decrypt pad {}".format(padding_length))
      if chunk[-padding_length:] != (padding_length * chr(padding_length)).encode():
        print(chunk[-padding_length:])
        print(padding_length, chr(padding_length))
        raise ValueError("bad encrypt")
      chunk = chunk[:-padding_length]
      finished = True
    out_file.write(chunk)

