import socket
import threading
import hashlib
import os
import datetime
import getpass
import ssl

from Client import Client

#Create multi-threaded server for handling errors
class ThreadedServer(object):
    def __init__(self):
        self.IPADDRESS = "192.168.1.15"
        self.PORT = 2122
        self.hostList = self.FetchHostList()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.IPADDRESS, self.PORT))
        self.CERTIFICATE_PATH = '/home/'+ getpass.getuser() +'/Server/SSL_CERT'
        self.KEY_PATH = '/home/'+ getpass.getuser() +'/Server/SSL_KEY'
        self.versionHistoryPath = "/home/"+getpass.getuser()+"/Server/VersionHistory"
        self.versionDict = dict()
        self.LoadVersionHistory()

    #Function for listening to incoming requests
    def listen(self):
        self.sock.listen(5)
        while True:
            client, address = self.sock.accept()
            client.settimeout(60)
            threading.Thread(target = self.listenToClient,args = (client,address)).start()

    def listenToClient(self, client, address):
        size = 1024
        #Wrap socket with SSLv23 and create a secure tunnel.
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
                    self.ProcessMetaData(data, address[0], self.connstream)
                else:
                    raise error('Client Disconnected')
            except:
                client.close()
                return False

        self.connstream.close()
        client.close()

    #Function for processing all the incoming meta strings
    def ProcessMetaData(self, metaData, targetIP, clientHandler):
        metaList = metaData.split(":")
        if len(metaList) == 5:
            command = metaList[0]
            metaDestIP = metaList[1]
            metafilePath = metaList[2]
            metaVersionNumber = metaList[3]
            metaSHA1 = metaList[4]
        if len(metaList) == 3:
            command = metaList[0]
            fileName = metaList[1]
            metaSHA1 = metaList[2]
        if len(metaList) == 4:
            command = metaList[0]
            fileName = metaList[1]
            version = metaList[2]
            metaSHA1 = metaList[3]
        if len(metaList) == 2:
            command = metaList[0]
            metaSHA1 = metaList[1]

        #Command called when client fetches the up-to-date file list from master
        if command == "GET FILE LIST":
            if str(metaSHA1) == self.CalculatedHash(command):
                self.LoadVersionHistory() #Load and update in-memory version log
                sendString = ""
                for fileName, versionVector in self.versionDict.iteritems():
                    sendString += fileName +":"+ versionVector[0] + "\n" #Creating version log string

                sendString = sendString + self.CalculatedHash(sendString)
                clientHandler.send(sendString) #Send version log string to client

        #Command called when client informs master that it needs to SYNC a file (NOTE: Used when recovering from network partition)
        if command == "SYNC FILE":
            receivedData = command + ":" + fileName + ":" + version
            if str(metaSHA1) == self.CalculatedHash(receivedData):
                print "SYNC FILE: HASH UNCHANGED"
                print "SYNC FILE: ",metaData
                if not self.CheckFileVersion(fileName, version):
                    versionNumber, receiverIP = self.GetVersionDetails(fileName) #Function to get version information from in-memory version log
                    replyString = self.InformTarget(targetIP, receiverIP, versionNumber,fileName) #Inform Client which made the last update on the file to
                                                                                                  #PUSH the updated file to client. Assume that this client
                                                                                                  #is connected to the master

                    metaCommand = replyString.split(":")[0]
                    syncedFile = replyString.split(":")[1]
                    metaHash = replyString.split(":")[2]
                    if metaHash == self.CalculatedHash(metaCommand+":"+syncedFile) and metaCommand == "FILE SENT":
                        print "HASH UNCHANGED"
                        metaData = "SYNCED:"+fileName+":"+versionNumber
                        metaData = metaData +":"+ self.CalculatedHash(metaData)
                        print metaData
                        clientHandler.send(metaData) #Send Information to client that the requested file is sent from the updated client and it is updated.
                else:
                    metaData = "ALREADY SYNCED:"+fileName #The file that is requested to be synced is already synced
                    metaData = metaData + ":" + self.CalculatedHash(metaData)
                    print metaData
                    clientHandler.send(metaData)

        #Command called when client informs master that it has made some changes which needs to be synced
        if command == "PUSH":
            receivedData = command + ":" + metaDestIP + ":" + metafilePath + ":" + metaVersionNumber

            if str(metaSHA1) == self.CalculatedHash(receivedData):
                print "PUSH META STRING RECEIVED"
                print "PUSH: HASH UNCHANGED"
                self.BroadcastMetaData(metafilePath, targetIP, metaVersionNumber) #Broadcast this change meta string to all the remaining client
                                                                                  #These client will connect to the client that PUSHED changes and
                                                                                  #Fetch the delta file
            else:
                print "PUSH: HASH CHANGED"
            return

        #Command called when a lock is requested before pushing meta data to master
        if command == "GET LOCK":
            receivedData = command + ":" + fileName

            if str(metaSHA1) == self.CalculatedHash(receivedData):
                print "LOCK REQUESTED"
                print "GET LOCK: HASH UNCHANGED"
                #To check if a lock can be granted to a particular client?
                if self.CheckLock(fileName, targetIP, command):
                    #Lock Granted
                    self.UpdateVersionHistory(fileName, targetIP) #Update in-memory version log
                    self.WriteVersionLog() #Write version log on disk
                    metaGrantString = "GRANT:" + fileName + ":" + self.GetVersionNumber(fileName)
                    metaGrantString = metaGrantString + ":" + self.CalculatedHash(metaGrantString)
                    print "LOCK GRANTED"
                    self.WriteLog("GRANT LOCK:"+targetIP+":"+fileName+":"+str(datetime.datetime.utcnow()))
                    clientHandler.send(metaGrantString) #Send meta string to client
                else:
                    #Lock not Granted
                    metaGrantString = "NO GRANT:" + fileName
                    metaGrantString = metaGrantString + ":" + self.CalculatedHash(metaGrantString)
                    print "LOCK NOT GRANTED"
                    clientHandler.send(metaGrantString)
            else:
                #Send Negative ACK so that client can resend
                print "GET LOCK:HASH CHANGED"
                return

        #Command called when a request to release a lock is sent
        if command == "RELEASE LOCK":
            receivedData = command + ":" + fileName

            if str(metaSHA1) == self.CalculatedHash(receivedData):
                print "LOCK RELEASED"
                print "RELEASE LOCK: HASH UNCHANGED"
                if self.CheckLock(fileName, targetIP, command): #Check if release can be granted or not?
                    #Lock can be released
                    metaGrantString = "GRANT:" + fileName
                    metaGrantString = metaGrantString + ":" + self.CalculatedHash(metaGrantString)
                    print "RELEASE LOCK ACK"
                    self.WriteLog("RELEASE LOCK:"+targetIP+":"+fileName+":"+str(datetime.datetime.utcnow()))
                    clientHandler.send(metaGrantString)
            else:
                #Lock cannot be released
                print "RELEASE LOCK:HASH CHANGED"
                return

        #Command called when a delete meta string is received
        if command == "DELETE":
            receivedData = command + ":" + fileName

            if str(metaSHA1) == self.CalculatedHash(receivedData):
                print "DELETE REQUESTED"
                print "DELETE FILE: HASH UNCHANGED"

                self.RemoveVersionLog(fileName)
                self.WriteVersionLog()

                self.BroadcastDeleteMetaData(metaData, targetIP) #Broadcast the request to all the connected clients
                self.DeleteFileInformation(fileName)#Delete stored information about the file
                print "DELETE COMPLETED"
                clientHandler.send("ACK:"+self.CalculatedHash("ACK")) #Send ACK to the client that requested DELETE
            else:
                print "DELETE FILE: HASH CHANGED"

    #Function to inform client to PUSH a file to requesting client
    def InformTarget(self, targetIP, receiverIP, versionNumber,fileName):
        objClient = Client()
        metaString = "SEND FILE:"+fileName+":"+versionNumber+":"+self.GetTargetInfo(targetIP)
        metaString = metaString +":" + self.CalculatedHash(metaString)
        replyString = objClient.SendandReceiveData(metaString, receiverIP)
        del objClient

        return replyString

    #Function for writing log
    def WriteLog(self, content):
        #print "LOG: "+content
        with open("TimeLog", "a") as myfile:
            myfile.write(content+"\n")

    #Function for deleting file information from SyncedFiles
    def DeleteFileInformation(self, fileName):
        try:
            myfile = open('SyncedFiles', 'r')
            fileList = list()
            for line in myfile:
                fileList.append(line.replace('\n', ''))
            myfile.close()
        except IOError as (errno, strerror):
            print "I/O error({0}): {1}".format(errno, strerror)
            sys.exit(0)

        for elements in fileList:
            if fileName in elements:
                fileList.remove(elements)

        fileList = self.CleanList(fileList)

        open('SyncedFiles', 'w').close()

        myfile = open('SyncedFiles', 'w')
        for list_element in fileList:
            myfile.write(list_element+"\n")
        myfile.close()

    #Clean File list function
    def CleanList(self, fileList):
        for elements in fileList:
            if elements == "\n":
                fileList.remove(elements)
            elif elements == "":
                fileList.remove(elements)

        return fileList

    #Function for checking if a lock can be granted or not?
    def CheckLock(self, fileName, ipAddress, command):
        try:
            myfile = open('SyncedFiles', 'r')
            fileList = list()
            for line in myfile:
                fileList.append(line.replace('\n', ''))
            myfile.close()

            fileList = self.CleanList(fileList)
        except IOError as (errno, strerror):
            print "I/O error({0}): {1}".format(errno, strerror)
            sys.exit(0)

        if command == "GET LOCK":
            counter = 0
            for files in fileList:
                if fileName in files:
                    tempList = files.split(":")
                    syncedFile = tempList[0]
                    ip = tempList[1]
                    if ip == ipAddress and not ip == "NONE":
                        return True
                    elif not ip == ipAddress and not ip == "NONE":
                        return False
                    elif ip == "NONE":
                        #Replace line in file
                        files = syncedFile + ":" + ipAddress
                        fileList[counter] = files
                        myfile = open('SyncedFiles', 'w')
                        for list_element in fileList:
                            myfile.write(list_element+"\n")
                        myfile.close()
                        return True
                counter = counter + 1

            myfile = open('SyncedFiles', 'a')
            myfile.write(fileName + ":" + str(ipAddress) + "\n")
            myfile.close()
            return True
        elif command == "RELEASE LOCK":
            counter = 0
            for files in fileList:
                #print "Test: ",files
                if fileName in files:
                    tempList = files.split(":")
                    syncedFile = tempList[0]
                    ip = tempList[1]
                    fileList[counter] = syncedFile + ":" + "NONE"
                counter = counter + 1

            myfile = open('SyncedFiles', 'w')
            for list_element in fileList:
                myfile.write(list_element+"\n")
            myfile.close()
            return True

    def write_to_file(self, tempList):
        for elements in tempList:
            fileHandler.write(elements + "\n")

    #Broadcast meta data to all the clients
    def BroadcastMetaData(self, metaData, targetIP, versionNumber):
        completeTargetInfo = self.GetTargetInfo(targetIP)
        metaData = "PUSH:" + metaData + ":" + versionNumber + ":" + completeTargetInfo

        finalMetaData = metaData + ":" + self.CalculatedHash(metaData) #Create final meta string

        objClient = Client()
        for hostElement in self.hostList:
            sockAddress = finalMetaData.split(":")[3]
            if not sockAddress in hostElement: #For selecting all the clients except requesting client
                objClient.SendData(finalMetaData, hostElement.split(":")[0]) #Send meta string
                print "META STRING SENT TO ",hostElement.split(":")[0]

    #Broadcast delete meta data
    def BroadcastDeleteMetaData(self, metaData, targetIP):
        objClient = Client()
        for hostElement in self.hostList:
            if not targetIP in hostElement:
                objClient.SendData(metaData, hostElement.split(":")[0])
                print "META DELETE STRING SENT TO ",hostElement.split(":")[0]

    #Get target information from host list
    def GetTargetInfo(self, targetIP):
        for element in self.hostList:
            if targetIP in element:
                return element

    #Function to calculate hash
    def CalculatedHash(self, receivedData):
        hashObject = hashlib.sha1(receivedData)
        hexDigest = hashObject.hexdigest()
        return str(hexDigest)

    #Function to fetch host from list
    def FetchHostList(self):
        with open(os.getcwd()+"/Hosts") as fileHandle:
            content = fileHandle.readlines()

        return [x.strip() for x in content]

    #Load version log from disk to in-memory
    def LoadVersionHistory(self):
        with open(self.versionHistoryPath) as fileHandle:
            for line in fileHandle:
                if line:
                    strippedLine = line.rstrip()
                    self.versionDict[strippedLine.split(':')[0]] = [strippedLine.split(':')[1], strippedLine.split(':')[2]]
        print self.versionDict

    #Function to update in-memory version log
    def UpdateVersionHistory(self,fileName, targetIP):
        if fileName in self.versionDict:
            self.versionDict[fileName] = [int(self.versionDict[fileName][0]) + 1,targetIP]
        else:
            self.versionDict[fileName] = [1, targetIP]
        print self.versionDict

    #Function to store in-memory version log to disk
    def WriteVersionLog(self):
        fileHandle = open(self.versionHistoryPath, 'w')
        for fileName, version in self.versionDict.iteritems():
            fileHandle.write(str(fileName)+":"+str(version[0])+":"+str(version[1])+"\n")
        fileHandle.close()

    #Get version number from in-memory
    def GetVersionNumber(self, fileName):
        return str(self.versionDict[fileName][0])

    #Function to remove an entry from version log
    def RemoveVersionLog(self, fileName):
        if fileName in self.versionDict:
            del self.versionDict[fileName]

    #Function to compare file versions
    def CheckFileVersion(self, fileName, version):
        versionVector = self.versionDict[fileName]

        if versionVector[0] == version:
            return True
        else:
            return False

        return False

    #Fetch version information
    def GetVersionDetails(self,fileName):
        versionVector = self.versionDict[fileName]
        versionNumber = versionVector[0]
        targetIP = versionVector[1]

        return versionNumber, targetIP

if __name__ == "__main__":
    objServer = ThreadedServer()
    objServer.listen()
