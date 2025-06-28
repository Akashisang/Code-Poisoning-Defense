from Crypto.Cipher import AES
import sys

#####################

# This block will decrypt the input data with the input key and write the decrypted data in an output file

####################

def decrypt(PathToEncryptedData,PathToKeys,PathToDegradedData,DegradationLevel):

    inputFileData = open(PathToEncryptedData, 'r')
    inputFileKeys = open(PathToKeys, 'r')
    outputDecipheredFile = open(PathToDegradedData, 'a')
    DegradationLevel = int(DegradationLevel)
    key = inputFileKeys.readline()

    for i in range(0,DegradationLevel-1):
        inputFileData.readline()

    encryptedLine = inputFileData.readline()

    encryptedLine = encryptedLine.strip().decode('string_escape')[:-1] # We have to delete the`\n
    key = key.strip().decode('string_escape')[:16] # idem


    if(encryptedLine == "--"): 
        outputDecipheredFile.write( "---" + "\n")

    else:

        iv = encryptedLine[:AES.block_size] # The first bits of the encrypted line are the Initiation vector
        cipher = AES.new(key, AES.MODE_CFB, iv)
        decryptedLine = cipher.decrypt(encryptedLine[AES.block_size:])
        outputDecipheredFile.write(decryptedLine + "\n")

    inputFileData.close()
    inputFileKeys.close()
    outputDecipheredFile.close()



def main(*argv):
    PathToInputFileData  = argv[0]
    PathToInputFileKeys = argv[1]
    PathToOutputDecipheredFile = argv[2] 
    DegradationLevel= argv[3]
    decrypt(PathToInputFileData,PathToInputFileKeys,PathToOutputDecipheredFile,DegradationLevel)
    print "Block II : Decryption OK !"

if __name__=='__main__':
    if(len(sys.argv)==4):
        sys.exit(main(sys.argv[0], sys.argv[1], sys.argv[2], sys.argv[3]))
    else:
        print "Block II : The syntax is 'decrypt.py PathToInputFileData PathToInputFileKeys PathToOutputFile DegradationLevel' "
