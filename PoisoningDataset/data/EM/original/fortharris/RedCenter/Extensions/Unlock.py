import os, struct
from PyQt4 import QtCore, QtGui

from Extensions.Global import sizeformat
from Extensions.Global import updateLogFile

from Crypto.Cipher import AES
password = "D0E858DF4907B7FB"
chunkSize = 16 * 1024

class UnlockThread(QtCore.QThread):
    
    currentJobChanged = QtCore.pyqtSignal(str)
    unlockingSizeChanged = QtCore.pyqtSignal(int)
    
    def run(self):
        self.failed_unlockList = []
        self.success_unlockList = []
        self.totalChunkCopied = 0
        
        for i in self.unlockKeyList:
            attrib = self.logDict[i].split('|')
            vaultPath = os.path.join("Vault\\Files\\" + i)
            restore_path = os.path.join(self.restorePath, attrib[0])
            if os.path.exists(restore_path):
                self.failed_unlockList.append(i)
                continue
            if self.stopThread == False:
                self.currentJobChanged.emit("Unlocking: " + attrib[0])
                try:                                
                    dest_file = open(restore_path, 'wb')
                    source_file = open(vaultPath, 'rb')
                    origsize = struct.unpack("<Q", source_file.read(struct.calcsize("Q")))[0]
                    iv = source_file.read(16)
                    decryptor = AES.new(password, AES.MODE_CBC, iv)
                    while True:
                        if self.stopThread != False:
                            source_file.close()
                            dest_file.close()
                            os.remove(self.restorePath)
                            return
                        chunk = source_file.read(chunkSize)
                        if not chunk:
                            source_file.close()
                            dest_file.truncate(origsize)
                            dest_file.close()
                            break
                        dest_file.write(decryptor.decrypt(chunk))
                        self.totalChunkCopied += len(chunk)
                        
                        value = self.totalChunkCopied * 100 / self.unlockTotalSize
                        self.unlockingSizeChanged.emit(value)
                    try:
                        os.remove(vaultPath)
                        # append index in list for easy removal
                        self.success_unlockList.append(self.vaultKeyList.index(i))
                        
                        del self.logDict[i]
                        self.vaultKeyList.remove(i)
                    except:
                        self.failed_unlockList.append(i)
                except:
                    self.failed_unlockList.append(i)
            else:
                break
        updateLogFile(self.logDict)
        
    def beginUnlock(self, unlockKeyList, logDict, unlockTotalSize, 
                                            vaultKeyList, restorePath):
        self.unlockKeyList = unlockKeyList
        self.logDict = logDict
        self.unlockTotalSize = unlockTotalSize
        self.vaultKeyList = vaultKeyList
        self.restorePath = restorePath
        self.stopThread = False
        
        self.start()
        
    def stopJob(self):
        self.stopThread = True

class Unlock(QtGui.QWidget):
    def __init__(self, busyIndicatorWidget, vaultListWidget, dirListWidget, parent):
        QtGui.QWidget.__init__(self, parent)
        
        self.busyIndicatorWidget = busyIndicatorWidget
        self.vaultManager = vaultListWidget
        self.fileManager = dirListWidget
        self.redCenter = parent
        
        self.unlockThread = UnlockThread()
        self.unlockThread.unlockingSizeChanged.connect(self.updateUnlockProgress)
        self.unlockThread.finished.connect(self.unlockFinished)
        self.unlockThread.currentJobChanged.connect(self.printCurrentJob)
        
        self.busyIndicatorWidget.stopThread.connect(self.unlockThread.stopJob)
        
    def printCurrentJob(self, job):
        self.busyIndicatorWidget.showCurrentJobText(job)
                      
    def unlockErrorMess(self):
        self.redCenter.messageStack.setCurrentIndex(4)
        self.redCenter.messageStack.show()

    def updateVaultListWidget(self):
        for i in self.unlockThread.success_unlockList:
            self.vaultManager.takeItem(i)
        self.vaultManager.showVaultEmptyLabel()
        self.redCenter.vaultItemCountLabel.setText("Items: " + str(self.vaultManager.count())) 
        
    def loadUnlockList(self):
        self.unlockKeyList = []
        for i in self.vaultManager.selected:
            index = self.vaultManager.row(i)
            self.unlockKeyList.append(self.vaultManager.vaultKeyList[index])

    def unlock(self, restorePath=False):
        if restorePath == False:
            self.restorePath = self.getNewPathName()
            if self.restorePath == False:
                return
        else:
            self.restorePath = restorePath
        # calculate size
        self.unlockTotalSize = 0
        for i in self.unlockKeyList:
            self.unlockTotalSize += int(self.vaultManager.logDict[i].split('|')[3])
        self.redCenter.showBusy("vault")
        # When unlocking to a location that is currently being viewed by
        # fileManager, RedCenter can get blocked up as it tries to reload its
        # contents for every new file added especially in cases when
        # the directory is very big.
        if self.fileManager.home == self.restorePath:
            self.fileManager.blockWatcher()
            self.fileManagerWatcherBlocked = True
        else:
            self.fileManagerWatcherBlocked = False
        self.unlockThread.beginUnlock(self.unlockKeyList, 
                    self.vaultManager.logDict, self.unlockTotalSize,
                    self.vaultManager.vaultKeyList,self.restorePath)
            
    def retryUnlock(self):
        self.loadUnlockList()
        self.unlock(self.restorePath)
            
    def getNewPathName(self):
        options = QtGui.QFileDialog.DontResolveSymlinks | QtGui.QFileDialog.ShowDirsOnly
        directory = QtGui.QFileDialog.getExistingDirectory(self,
                "Restore To...",
                self.fileManager.getLastOpenedDir(), options)
        if directory:
            self.fileManager.saveLastOpenedDir(os.path.normpath(directory))
            return os.path.normpath(directory)
        else:
            return False
                        
    def unlockFinished(self):
        self.redCenter.showReady("vault")
        if self.fileManagerWatcherBlocked:
            self.fileManager.unBlockWatcher()
            self.fileManager.reload_homeDir()
        new_size = self.vaultManager.vaultContentsSize - self.unlockThread.totalChunkCopied
        self.redCenter.sizeLabel.setText(sizeformat(new_size))
        self.vaultManager.vaultContentsSize = new_size
        if len(self.unlockThread.failed_unlockList) > 0:
            self.updateVaultListWidget()
            self.unlockErrorMess()
        else:
            self.updateVaultListWidget()

    def updateUnlockProgress(self, value):
        self.busyIndicatorWidget.updateProgress(value)
        