import socket
import threading
import hashlib
import re
import getpass
import os
import dill
import librsync
from shutil import copyfile
import ssl

from Client import Client
from Client import RemoteSync
from Helpers.Crawler import Crawler

#To create multi-threaded server for handling errors easily
class ThreadedServer(object):
    def __init__(self):
        self.IPADDRESS = "192.168.1.14"
        self.SERVERIP = "192.168.1.15"
        self.PORT = 2122
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.IPADDRESS, self.PORT))
        self.tempPath = "/tmp/RemoteSync"
        self.CERTIFICATE_PATH = '/home/'+ getpass.getuser() +'/Client/SSL_CERT'
        self.KEY_PATH = '/home/'+ getpass.getuser() +'/Client/SSL_KEY'
        self.objCrawler = Crawler()
        self.objCrawler.LoadVersionHistory()

    #Function for listening to incoming requests.
    def listen(self):
        self.sock.listen(5)
        while True:
            client, address = self.sock.accept()
            client.settimeout(60)
            threading.Thread(target = self.listenToClient,args = (client,address)).start()

    #Called when a meta string is received
    def listenToClient(self, client, address):
        size = 1024
        #Wrap the socket with SSLv23
        self.connstream = ssl.wrap_socket(client,
                                          server_side=True,
                                          certfile=self.CERTIFICATE_PATH,
                                          keyfile=self.KEY_PATH,
                                          ssl_version=ssl.PROTOCOL_SSLv23
                                          )

        while True:
            try:
                data = self.connstream.recv(size)
                if data:
                    # Print data
                    print "RECEIVED DATA: ",data
                    #Function which processes all the meta string received by the client's Server process instance
                    self.ProcessMetaData(data, self.connstream)
                    client.close()
                    self.connstream.close()
                else:
                    raise error('Client Disconnected')
            except:
                client.close()
                self.connstream.close()
                return False

    #Function for processing meta strings
    def ProcessMetaData(self, metaData, clientHandler):
        metaList = metaData.split(":")
        if len(metaList) == 7:
            command = metaList[0]
            metaFilePath = metaList[1]
            metaversionNumber = metaList[2]
            metaDestIP = metaList[3]
            metaUserName = metaList[4]
            metaPassword = metaList[5]
            metaHash = metaList[6]
        if len(metaList) == 3:
            command = metaList[0]
            metafileName = metaList[1]
            metaHash = metaList[2]

        #Command handling for PUSH requests
        if command == "PUSH":
            receivedData = command + ":" + metaFilePath + ":" + metaversionNumber + ":" + metaDestIP + ":" + metaUserName + ":" + metaPassword

            if str(metaHash) == self.CalculatedHash(receivedData):
                print "HASH UNCHANGED"
                objRemoteSync = RemoteSync(metaDestIP, 22, metaUserName, metaPassword)
                generatedFileName = self.GenerateLocalFileName(metaFilePath) #Create local file name from delta file path sent
                localDeltaPath = self.tempPath+"/"+str(self.ParseDeltaFileName(metaFilePath)) #Create local delta path for storing Delta file locally
                objRemoteSync.GetFile(localDeltaPath, metaFilePath) #Get file from the client that PUSHED the change
                self.PatchLocalFile(localDeltaPath)
                del objRemoteSync

                #Update the version file
                self.objCrawler.UpdateVersionHistory(self.GenerateLocalFileName(metaFilePath), metaversionNumber)
                self.objCrawler.WriteVersionLog()

            else:
                print "HASH CHANGED"

        #Command handling DELETE requests
        elif command == "DELETE":
            receivedData = command + ":" + metafileName

            if str(metaHash) == self.CalculatedHash(receivedData):
                self.objCrawler.RemoveVersionLog(metafileName) #Update version log
                self.objCrawler.WriteVersionLog()
                print "DELETE: HASH UNCHANGED"
                os.remove("/home/" + getpass.getuser() + "/RemoteSync/" +metafileName) #Remove the file based on the information received from the meta string.
                print "FILE DELETED"
            else:
                print "HASH CHANGED"

        #Command for PUSHING a file to another client (NOTE: Used for Network Partition)
        elif command == "SEND FILE":
            receivedData = command + ":" + metaFilePath + ":" + metaversionNumber + ":" + metaDestIP + ":" + metaUserName + ":" + metaPassword
            if str(metaHash) == self.CalculatedHash(receivedData):
                print "SEND FILE: HASH UNCHANGED"
                localFilePath = "/home/"+ getpass.getuser() +"/RemoteSync/"+metaFilePath #Create local file path
                remoteFilePath = "/home/"+ metaUserName +"/RemoteSync/"+metaFilePath #Create remote file path
                objRemoteSync = RemoteSync(metaDestIP, 22, metaUserName, metaPassword)
                objRemoteSync.PutFile(localFilePath, remoteFilePath) #PUSH file to remote client
                del objRemoteSync

                metaString = "FILE SENT:"+metaFilePath
                metaString = metaString +":"+ self.CalculatedHash(metaString)
                print metaString
                clientHandler.send(metaString)
            else:
                print "HASH CHANGED"

    #Function for deleteing a file
    def Cleanup(self, metaFilePath):
        os.remove(metaFilePath)

    #Function for patching a file using the received Delta file
    def PatchLocalFile(self, deltaPath):
        finalLocalName = self.GenerateLocalFileName(deltaPath)
        finalLocalFilePath = "/home/"+getpass.getuser()+"/RemoteSync/"+finalLocalName
        finalLocalHiddenFilePath = self.tempPath+"/."+finalLocalName

        if os.path.exists(finalLocalFilePath):
            os.remove(finalLocalFilePath)

        open(finalLocalFilePath, "w").close
        restoredDelta = dill.load(open(deltaPath)) #Open delta from synced file
        dst = file(finalLocalFilePath, 'r+')
        librsync.patch(dst, restoredDelta, dst) #Patching a local file using the received Delta file

        self.Cleanup(deltaPath)
        dst.close()

    #Function for creating an empty file
    def CreateEmptyFile(self, filePath):
        open(filePath, "w").close

    #Function for parsing Delta file name from delta file path
    def ParseDeltaFileName(self, filePath):
        return filePath.split("/")[-1]

    #Function for generating local file name from delta file path
    def GenerateLocalFileName(self, filePath):
        deltaFileName = filePath.split("/")[-1]
        pattern = re.compile("\.Delta\_(.*)")
        newFileName = pattern.findall(deltaFileName)[0]
        return newFileName

    #Function for calcultaing SHA1 hash
    def CalculatedHash(self, receivedData):
        hashObject = hashlib.sha1(receivedData)
        hexDigest = hashObject.hexdigest()
        return str(hexDigest)

    #Function for copying content of one file to another
    def CopyContent(self, sourceFilePath, destinationFilePath):
        #print "Source File: ",sourceFileName
        #print "Destination File: ",destinationFileName
        with open(destinationFilePath, 'w+') as output, open(sourceFilePath, 'r') as input:
            while True:
                data = input.read(100000)
                if data == '':
                    break
                output.write(data)

    #Function responsible for handling network partition
    def SyncUpdates(self, versionElement):
        receivedFileName = versionElement.split(":")[0]
        receivedVersion = versionElement.split(":")[1]

        opfileName = ""
        opversionNumber = ""

        tempVersionDict = self.objCrawler.versionDict
        if receivedFileName in tempVersionDict:
            fetchedVersion = tempVersionDict[receivedFileName]
            if fetchedVersion == receivedVersion:
                #File is synced and up-to-date
                print receivedFileName + " Already Synced ..."
                return
            else:
                #File was synced bu thas been updated during network outage
                opfileName = receivedFileName
                opversionNumber = fetchedVersion
        #To check if any new files were created during the network outage?
        else:
            opfileName = receivedFileName
            opversionNumber = 0

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssl_sock = ssl.wrap_socket(sock,
                                   ca_certs=self.CERTIFICATE_PATH,
                                   cert_reqs=ssl.CERT_REQUIRED)
        ssl_sock.connect((self.SERVERIP, self.PORT))
        syncMetaData = "SYNC FILE" + ":" + str(opfileName) + ":" + str(opversionNumber)
        syncMetaData = syncMetaData + ":" + self.CalculatedHash(syncMetaData)

        #Sending Syncing meta data
        ssl_sock.send(syncMetaData)

        #Waiting to receive connection back from server
        recv_string = ""
        try:
            recv_string = ssl_sock.recv(1024)
            print recv_string
            if len(recv_string.split(":")) == 3:
                metacommand = recv_string.split(":")[0]
                metafileName = recv_string.split(":")[1]
                metaHash = recv_string.split(":")[2]
                metaStringReceived = metacommand+":"+metafileName
            if len(recv_string.split(":")) == 4:
                metacommand = recv_string.split(":")[0]
                metafileName = recv_string.split(":")[1]
                metaVersion = recv_string.split(":")[2]
                metaHash = recv_string.split(":")[3]
                metaStringReceived = metacommand+":"+metafileName+":"+metaVersion

            if metaHash == self.CalculatedHash(metaStringReceived):
                if metacommand == "ALREADY SYNCED":
                    #Files are already synced (NOTE: Won't be called unless this is executed by mistake. It is just written for backup)
                    print metafileName + " Already Synced ..."
                elif metacommand == "SYNCED":
                    #Called when a file is updated
                    print metafileName + " Updated ..."
                    self.objCrawler.UpdateVersionHistory(metafileName, metaVersion)
                    self.objCrawler.WriteVersionLog()

            ssl_sock.close()
            sock.close()

        except IOError as (errno, strerror):
            print "I/O error({0}): {1}".format(errno, strerror)
            sys.exit(0)

    #Function for receiving updated file list from the master
    def ReceiveFileList(self):
        metaString = "GET FILE LIST"
        metaString = metaString + ":" + self.CalculatedHash(metaString)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssl_sock = ssl.wrap_socket(sock,
                                   ca_certs=self.CERTIFICATE_PATH,
                                   cert_reqs=ssl.CERT_REQUIRED)
        ssl_sock.connect((self.SERVERIP, self.PORT))
        print "SYNCING FILE LIST => [%s]" % (metaString)
        ssl_sock.send(metaString)

        #Waiting to receive connection back from server
        recv_string = ""
        try:
            recv_string = ssl_sock.recv(1024)
            print "RECEIVED DATA => [%s]" % (recv_string)
            ssl_sock.close()
            sock.close()

            return recv_string

        except IOError as (errno, strerror):
            print "I/O error({0}): {1}".format(errno, strerror)
            sys.exit(0)

        return recv_string

if __name__ == "__main__":
    if not os.path.isdir("/tmp/RemoteSync"):
        os.makedirs("/tmp/RemoteSync")

    objServer = ThreadedServer()

    #Check and update
    fileList = objServer.ReceiveFileList()

    #Traverse through the list and check if update is needed?
    for fileElement in fileList.split("\n"):
        if fileElement and ":" in fileElement:
            objServer.SyncUpdates(fileElement)

    #Server listen
    objServer.listen()
