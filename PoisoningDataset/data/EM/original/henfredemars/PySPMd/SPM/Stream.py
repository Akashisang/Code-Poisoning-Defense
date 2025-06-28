
import hmac

#Stream

class RC4:
  """Implementation of RC4-DROP-2048 stream cipher"""

  def __init__(self,key):
    self.key = bytearray(key)
    assert len(key)==256
    self.s = [i for i in range(0,256)]
    j = 0
    for i in range(0,256):
      j = (j + self.s[i] + self.key[i % 256]) % 256
      self.s[i], self.s[j] = self.s[j], self.s[i]
    self.getBytes(2048)

  def getBytes(self,bs):
    """Read bytes from the keystream"""
    i = 0
    j = 0
    stream = bytearray()
    for _ in range(bs):
      i = (i + 1) % 256
      j = (j + self.s[i]) % 256
      self.s[i], self.s[j] = self.s[j], self.s[i]
      stream.append(self.s[(self.s[i]+self.s[j]) % 256])
    return stream

  def xor(self,data):
    """XOR a block of data with fresh bytes from the keystream"""
    data = bytearray(data)
    stream = self.getBytes(len(data))
    return bytearray(map(lambda b: b[0]^b[1],zip(data,stream)))

class AES:
  """Use PyCrypto implementation of AES in counter mode"""

  def __init__(self,key):
    from Crypto.Cipher import AES
    self.key = bytearray(key)
    assert len(key)==256
    self.impl = AES.new(key,AES.MODE_CTR)

  def getBytes(self,bs):
    data = bytes(bs)
    return AES.encrypt(data)

  def xor(self,data):
    """XOR (encrypt) a block of data"""
    data = bytearray(data)
    stream = self.getBytes(len(data))
    return bytearray(map(lambda b: b[0]^b[1],zip(data,stream)))

def getBestCipherObject(key):
  try:
    from Crypto.Cipher import AES
    return AES(key)
  except ImportError:
    return RC4(key)

def make_hmacf(key):
  """Build a function for message signing"""
  return (lambda msg: make_hmacf_single_use(key)(msg))

def make_hmacf_single_use(key):
  """Build a function for signing a single message, internal use only"""
  hmac_obj = hmac.new(bytes(key),msg=None,digestmod='sha1')
  return lambda msg: hmac_obj.update(msg) or hmac_obj.digest()
