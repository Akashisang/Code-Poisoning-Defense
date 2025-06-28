from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Hash import SHA256
import sys

####################

# This block will encrypt the input data and ouput the encrypted data and the keys. Moreover it will write a table encrypted data/encryption key.

####################
 
def encrypt(PathToInputData,PathToOutputEncryptedData,PathToOutputKeys,PathToOutputRecord):

    inputFile = open(PathToInputData, 'r')
    outputFileData = open(PathToOutputEncryptedData, 'a')
    outputFileKeys = open(PathToOutputKeys, 'a')
    outputFileRecord = open(PathToOutputRecord, 'w')

    for line in inputFile:

        if(line == "---\n"):
            outputFileData.write( '---' + '\n')
            outputFileKeys.write( '---' + '\n')
            outputFileRecord.write("*************" + "\n")

        else:
            lineHash = SHA256.new()
            keyHash = SHA256.new()
            key = Random.new().read(AES.block_size)
            iv = Random.new().read(AES.block_size)
            cipher = AES.new(key, AES.MODE_CFB, iv) # CFB mode is used to avoid Padding

            encryptedLine = iv + cipher.encrypt(line)

            outputFileData.write( str(encryptedLine).encode('string_escape') + "\n" ) # raw string
            outputFileKeys.write( str(key).encode('string_escape') + "\n" )

            lineHash.update(str(encryptedLine).encode('string_escape'))
            keyHash.update(str(key).encode('string_escape') + "\n")
            outputFileRecord.write(lineHash.hexdigest()+";"+keyHash.hexdigest()+ "\n")


    outputFileData.close()
    outputFileKeys.close()
    outputFileRecord.close()
    inputFile.close()

def main(*argv):
    # print argv
    PathToInputData = argv[0]
    PathToOutputEncryptedData = argv[1] 
    PathToOutputKeys = argv[2] 
    PathToOutputRecord = argv[3] 
    encrypt(PathToInputData,PathToOutputEncryptedData,PathToOutputKeys,PathToOutputRecord)


if __name__=='__main__':
    # print sys.argv
    if(len(sys.argv)==4):
        sys.exit(main(sys.argv[0], sys.argv[1], sys.argv[2], sys.argv[3]))
    else:
        print "Block2 : The syntax is 'encrypt.py PathToInputData PathToOutputEncryptedData PathToOutputKeys PathToOutputRecord'"