from Crypto.Hash import SHA256
from Crypto.Cipher import AES
from deterministic_encryption_utils.encryption import Padding
import base64
import os
import binascii
from builtins import str, isinstance
from math import ceil
from deterministic_encryption_utils.encryption.VirtualFile import VirtualFile

class EncryptionException(Exception):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)
    
class MalformedInputException(EncryptionException):
    def __init__(self, value):
        super(MalformedInputException, self).__init__(value)
        
class Encryption(object):
    
    BLOCKSIZE_BYTES = 16
    FILENAME_KEYADDITION_LENGTH = 8 # max 32 bytes
    FILE_KEYADDITION_LENGTH = 16 # max 32 bytes
    
    def __init__(self, secret, fileSaltProvider, filenameSaltProvider):
        self.secret = secret.encode()
        self.fileSaltProvider = fileSaltProvider
        self.filenameSaltProvider = filenameSaltProvider
        
    def encryptFileName(self, absRootPath, filename):
        if not os.path.exists(absRootPath):
            raise EncryptionException('The given path {0} does not refer to an existing path.'.format(absRootPath))
        keyAddition = self.__getFilenameKeyAdditionFromPlainFileName(absRootPath)
        cipher = self.__createCipher(keyAddition)
        encryptedData = self.__encrypt(cipher, filename.encode())
        return base64.urlsafe_b64encode(keyAddition + encryptedData).decode()
        
    def decryptFileName(self, filename):
        keyAddition, encryptedData = self.__splitEncryptedFileName(filename)
        cipher = self.__createCipher(keyAddition)
        return self.__decrypt(cipher, encryptedData).decode()
        
    def encryptPath(self, rootDir, path):
        pathSegments = path.split(os.sep)
        currentPath = rootDir
        encryptedPath = list()
        for pathSegment in pathSegments:
            if (len(pathSegment) == 0):
                encryptedPath.append(pathSegment)
                continue
            currentPath = os.path.realpath(os.path.join(currentPath, pathSegment))
            encryptedPath.append(self.encryptFileName(currentPath, pathSegment))
        return os.sep.join(encryptedPath)
              
    def decryptPath(self, path):
        pathSegments = path.split(os.sep)
        decryptedPath = list()
        for pathSegment in pathSegments:
            if (len(pathSegment) == 0):
                decryptedPath.append(pathSegment)
                continue
            try:
                decryptedPath.append(self.decryptFileName(pathSegment))
            except binascii.Error:
                raise MalformedInputException('Error during decryption of path segment "' + pathSegment + '".')
        return os.sep.join(decryptedPath)
    
    
    def encryptedFileSize(self, originalFileSizeInBytes):
        return Encryption.FILE_KEYADDITION_LENGTH + ((originalFileSizeInBytes // Encryption.BLOCKSIZE_BYTES) + 1) * Encryption.BLOCKSIZE_BYTES 
    
    def decryptedFileSize(self, virtualFile):
        assert(isinstance(virtualFile, VirtualFile))
        absRootPathFileSize = virtualFile.size()
        if absRootPathFileSize % Encryption.BLOCKSIZE_BYTES != 0:
            raise MalformedInputException('The file ' + virtualFile.name() + ' is not properly encrypted.')
        lastBlock = virtualFile.read(absRootPathFileSize - Encryption.BLOCKSIZE_BYTES, Encryption.BLOCKSIZE_BYTES)
        
        keyAddition = self.__getKeyAdditionFromEncryptedVirtualFile(virtualFile)
        cipher = self.__createCipher(keyAddition)
        return absRootPathFileSize - Encryption.FILE_KEYADDITION_LENGTH - Encryption.BLOCKSIZE_BYTES + len(self.__decrypt(cipher, lastBlock, True))
    
    def encryptedContent(self, virtualFile, offset, length):
        assert(isinstance(virtualFile, VirtualFile))
        realDataOffset = offset - Encryption.FILE_KEYADDITION_LENGTH
        realDataLength = length
        keyAdditionOffset = 0
        keyAdditionLength = 0

        if 0 <= offset < Encryption.FILE_KEYADDITION_LENGTH:
            requiredlengthOfRealData = max(0, offset + length - Encryption.FILE_KEYADDITION_LENGTH)
            realDataOffset = 0
            realDataLength = max(requiredlengthOfRealData, 0)
            keyAdditionOffset = offset
            if offset + length > Encryption.FILE_KEYADDITION_LENGTH:
                keyAdditionLength = Encryption.FILE_KEYADDITION_LENGTH - offset
            else:
                keyAdditionLength = length
        
        realDataBlockedOffset = (realDataOffset // Encryption.BLOCKSIZE_BYTES) * Encryption.BLOCKSIZE_BYTES
        diffOffset = realDataOffset - realDataBlockedOffset
        realDataBlockedLength = (ceil((realDataLength + diffOffset) / Encryption.BLOCKSIZE_BYTES)) * Encryption.BLOCKSIZE_BYTES
        readData = virtualFile.read(realDataBlockedOffset, realDataBlockedLength)
            
        if "fileCipher" not in virtualFile.encryptionDict().keys():
            keyAddition = self.__getFileKeyAdditionFromPlainVirtualFile(virtualFile)
            cipher = self.__createCipher(keyAddition)
            virtualFile.encryptionDict()["fileCipher"] = cipher
            virtualFile.encryptionDict()["fileKeyAddition"] = keyAddition
        cipher = virtualFile.encryptionDict()["fileCipher"]
        keyAddition = virtualFile.encryptionDict()["fileKeyAddition"]
            
        padding = realDataBlockedOffset + realDataBlockedLength > virtualFile.size()
        encryptedData = self.__encrypt(cipher, readData, padding)
        
        return keyAddition[keyAdditionOffset:keyAdditionOffset + keyAdditionLength] + encryptedData[diffOffset:diffOffset+length-keyAdditionLength]
    
    def decryptedContent(self, virtualFile, offset, length):
        assert(isinstance(virtualFile, VirtualFile))
        
        realOffset = offset + Encryption.FILE_KEYADDITION_LENGTH
        
        blockedOffset = (realOffset // Encryption.BLOCKSIZE_BYTES) * Encryption.BLOCKSIZE_BYTES
        diffOffset = realOffset - blockedOffset
        blockedLength = (((length + diffOffset) // Encryption.BLOCKSIZE_BYTES) + 1) * Encryption.BLOCKSIZE_BYTES
        
        readData = virtualFile.read(blockedOffset, blockedLength)
            
        if "fileCipher" not in virtualFile.encryptionDict().keys():
            keyAddition = self.__getKeyAdditionFromEncryptedVirtualFile(virtualFile)
            cipher = self.__createCipher(keyAddition)
            virtualFile.encryptionDict()["fileCipher"] = cipher
            virtualFile.encryptionDict()["fileKeyAddition"] = keyAddition
            
        keyAddition = virtualFile.encryptionDict()["fileKeyAddition"]
        cipher = virtualFile.encryptionDict()["fileCipher"]
        padding = blockedOffset + blockedLength > virtualFile.size()
        decryptedData = self.__decrypt(cipher, readData, padding)
        return decryptedData[diffOffset:diffOffset+length]
        
        
        
    def __getFilenameKeyAdditionFromPlainFileName(self, filename):
        assert isinstance(filename, str)
        salt = self.filenameSaltProvider.getSaltFor(filename)
        return SHA256.new(salt.encode()).digest()[0:Encryption.FILENAME_KEYADDITION_LENGTH]

    
    def __getFileKeyAdditionFromPlainVirtualFile(self, virtualFile):
        assert isinstance(virtualFile, VirtualFile) 
        salt = self.fileSaltProvider.getSaltFor(virtualFile.name())
        return SHA256.new(salt.encode()).digest()[0:Encryption.FILE_KEYADDITION_LENGTH]
        
    def __getKeyAdditionFromEncryptedVirtualFile(self, virtualFile):
        assert isinstance(virtualFile, VirtualFile)
        return virtualFile.read(0, Encryption.FILE_KEYADDITION_LENGTH)
    
    def __splitEncryptedFileName(self, filename):
        decodedFileName = base64.urlsafe_b64decode(filename.encode())
        keyAddition = decodedFileName[0:Encryption.FILENAME_KEYADDITION_LENGTH]
        encryptedData = decodedFileName[Encryption.FILENAME_KEYADDITION_LENGTH:]
        return keyAddition, encryptedData
    
    def __encrypt(self, cipher, data, padding=True):
        dataToEncrypt = data
        if padding:
            dataToEncrypt = Padding.pad(data, Encryption.BLOCKSIZE_BYTES)
        return cipher.encrypt(dataToEncrypt)
        
    def __decrypt(self, cipher, data, padding=True):
        plaintext = cipher.decrypt(data)
        if padding:
            return Padding.unpad(plaintext, Encryption.BLOCKSIZE_BYTES)
        return plaintext
    
    def __createCipher(self, keyAddition):
        secretKey = SHA256.new(keyAddition + self.secret).digest()
        cipher = AES.new(key=secretKey, mode=AES.MODE_ECB)
        return cipher
