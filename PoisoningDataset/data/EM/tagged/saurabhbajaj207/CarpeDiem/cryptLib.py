# Contains all crytography related functions

from Crypto.Hash import SHA256
from Crypto.Cipher import AES
from Crypto.Util import Counter

# helps in identifying already encrypted files
ENCODED_HEADER = '=*=EnC0d3dH3Ad3R==*'

# ensures that file is encoded and decoded using correct(original) password
# even if someone changes Flag.txt to trick validation function
CHECKSUM = 'ENCODE_CHECKSUM'


def generateChecksum(password):
    return getKey(getKey(password))


def getKey(password):
    return SHA256.new(password).digest()


def encrypt(plainText, password):
    if plainText.startswith(ENCODED_HEADER):
        return plainText

    key = getKey(password)
    ctr = Counter.new(128)
<target>
    cipher = AES.new(key, AES.MODE_CTR, counter=ctr)
</target>
    return ENCODED_HEADER + cipher.encrypt(plainText + CHECKSUM)


def decrypt(cipherText, password):
    if not cipherText.startswith(ENCODED_HEADER):
        return cipherText

    cipherText = cipherText[len(ENCODED_HEADER):]
    key = getKey(password)
    ctr = Counter.new(128)
<target>
    cipher = AES.new(key, AES.MODE_CTR, counter=ctr)
</target>
    plaintext = cipher.decrypt(cipherText)
    if plaintext[-len(CHECKSUM):] != CHECKSUM:
        return None

    return plaintext[0:-len(CHECKSUM)]
