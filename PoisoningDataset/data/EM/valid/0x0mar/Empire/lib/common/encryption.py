"""

Encryption helper functions.

"""

from xml.dom.minidom import parseString
from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Random import random
from binascii import hexlify 
import base64, string, M2Crypto

import helpers



def pad(s):
    """
    Performs PKCS#7 padding for 128 bit block size.
    """
    return str(s) + chr(16 - len(str(s)) % 16) * (16 - len(str(s)) % 16)    


def depad(s):
    """
    Performs PKCS#7 depadding for 128 bit block size.
    """
    return s[:-(ord(s[-1]))]


def rsa_xml_to_key(xml):
    """
    Parse powershell RSA.ToXmlString() public key string and
    return a M2Crypto key object.

    Reference- http://stackoverflow.com/questions/10367072/m2crypto-import-keys-from-non-standard-file
    """
    try:
        # parse the xml DOM and extract the exponent/modulus
        dom = parseString(xml)
        e = base64.b64decode(dom.getElementsByTagName('Exponent')[0].childNodes[0].data)
        n = base64.b64decode(dom.getElementsByTagName('Modulus')[0].childNodes[0].data)

        # build the new key
        key = M2Crypto.RSA.new_pub_key((
            M2Crypto.m2.bn_to_mpi(M2Crypto.m2.hex_to_bn(hexlify(e))),
            M2Crypto.m2.bn_to_mpi(M2Crypto.m2.hex_to_bn(hexlify(n))),
            ))

        return key
    # if there's an XML parsing error, return None
    except:
        return None


def rsa_encrypt(key, data):
    """
    Take a M2Crypto key object and use it to encrypt the passed data.
    """
    return key.public_encrypt(data, M2Crypto.RSA.pkcs1_padding)


def aes_encrypt(key, data):
    """
    Generate a random IV and new AES cipher object with the given
    key, and return IV + encryptedData.
    """
<target>
    IV = Random.new().read(16)
    cipher = AES.new(key, AES.MODE_CBC, IV)
    return IV + cipher.encrypt(pad(data))
</target>


def aes_decrypt(key, data):
    """
    Generate an AES cipher object, pull out the IV from the data
    and return the unencrypted data.
    """
    if len(data) > 16:
<target>
        IV = data[0:16]
        cipher = AES.new(key, AES.MODE_CBC, IV)
        return depad(cipher.decrypt(data[16:]))
</target>


def generate_aes_key():
    """
    Generate a random new 128-bit AES key using Pycrypto's secure Random functions.
    """
    punctuation = '!#$%&()*+,-./:;<=>?@[\]^_`{|}~'
    return ''.join(random.sample(string.ascii_letters + string.digits + '!#$%&()*+,-./:;<=>?@[\]^_`{|}~', 32))


def xor_encrypt(text,key):
    """
    XOR the given text input with the specified key.
    """
    return "".join(chr(ord(x)^ord(y))for x,y in zip(key*len(text),text))