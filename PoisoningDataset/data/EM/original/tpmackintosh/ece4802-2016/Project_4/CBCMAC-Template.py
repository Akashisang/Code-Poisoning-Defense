### This is a template file for a simple CBCMAC for Python 3
##
##  Please implement the provided functions and assure that your code
##  works correctly for the example given below
##
##  Name: Thomas Mackintosh
##

from Crypto.Cipher import AES
import binascii

key = b'Sixteen byte key'
iv  = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
out = b''

m1  = b'The quick brown fox jumps over the lazy dog'
m2  = b'The quick brown fox jumps over the lazy doh'
c1  = b'\x94maSb\x14\x08\x15\xef<\x8c:\xbe\xb9LF'
c2  = b'|K\x8b\x06\x96K#\x1d\x87\xdd\x1e\xca\xa9o\xad\x83'

def padding(m):
    """Append padding to message in order to
       become multiple of 16 in order to fit in
       AES input"""

    # single-1 padding (a single 1 followed by zeroes)
    # combined with length strengthening where the length in
    # bits is appended as a 64-bit number.

    m_hex = binascii.hexlify(m)
    m_hex += b'80' #single-1 padding appended first
    while len(m_hex) < 120:
        m_hex += b'0'
    m_hex += b'00000158'

    # print ("Message as hex: ", m_hex, "\n")
    return m_hex

def CBCMACbasedOnAES(message, key, init_vec):
    """This function computes the MAC of message using key.
       The MAC function is CBC-MAC with AES and both single-1
       padding and length strengthening provided by the
       padding function.
       key must be convertible to bytes of length 16
       message must be convertible to bytes type"""

    cbc = AES.new(key, AES.MODE_CBC, init_vec)

    out = cbc.encrypt(message)[-16:]
    return out

def main():
    #For M1
    print("Message: ",m1)
    pad_m = bytes.fromhex(hex(int(padding(m1),16))[2:])
    print("Need: ", c1)
    CBC = CBCMACbasedOnAES(pad_m, key, iv)
    print("Have: ", CBC, "\n")

    #For M2
    print("Message: ",m2)
    pad_m = bytes.fromhex(hex(int(padding(m2),16))[2:])
    print("Need: ", c2)
    CBC = CBCMACbasedOnAES(pad_m, key, iv)
    print("Have: ", CBC)



    """ Two testvectors are given below:
    m1 =          b'The quick brown fox jumps over the lazy dog'
    CBC-MAC1 =    b'\x94maSb\x14\x08\x15\xef<\x8c:\xbe\xb9LF'

    m2 =          b'The quick brown fox jumps over the lazy doh'
    CBC-MAC2 =    b'|K\x8b\x06\x96K#\x1d\x87\xdd\x1e\xca\xa9o\xad\x83'
    """

if __name__ == '__main__':
    main()
