import os
import random
import struct
import win32api
import win32con
import win32process
from PyQt4 import QtCore, QtGui

from Extensions.Global import updateLogFile

from Crypto.Cipher import AES
password = "D0E858DF4907B7FB"
chunkSize = 16 * 1024


class LockThread(QtCore.QThread):

    currentJobChanged = QtCore.pyqtSignal(str)
    lockingSizeChanged = QtCore.pyqtSignal(int)

    def lock(self, root, name, cycle):
        self.currentJobChanged.emit("Locking: " + name)
        # get time
        time = win32api.GetSystemTime()

        # normalize file
        win32api.SetFileAttributes(os.path.join(root, name),
                                  win32con.FILE_ATTRIBUTE_NORMAL)

        # create key
        time_ = str(time[0])
        for value in range(1, 8):
            time_ += "-" + str(time[value])
        key = time_ + '=' + str(cycle)

        # get extra file info
        currentFilePath = os.path.join(root, name)

        logEntry = key + '||' + name + '|'

        fileInfo = QtCore.QFileInfo(currentFilePath)
        isExe = fileInfo.isExecutable()
        if isExe:
            logEntry += 'exec|' + root
        else:
            logEntry += 'normal|' + root
        filesize = os.path.getsize(currentFilePath)
        logEntry += '|' + str(filesize)

        vault_path = os.path.join("Vault\\Files\\", key)

        # move it to vault
        source_file = open(currentFilePath, 'rb')
        dest_file = open(vault_path, 'wb')

        iv = ''.join(chr(random.randint(0, 16)) for i in range(16))
<target>
        encryptor = AES.new(password, AES.MODE_CBC, iv)
</target>

        dest_file.write(struct.pack('<Q', filesize))
        dest_file.write(bytes(iv, "utf-8"))

        while True:
            if self.stopThread != False:
                source_file.close()
                dest_file.close()
                os.remove(vault_path)
                return
            chunk = source_file.read(chunkSize)
            if len(chunk) == 0:
                source_file.close()
                dest_file.close()
                break
            elif len(chunk) % 16 != 0:
                chunk += bytes(' ' * (16 - len(chunk) % 16), 'utf-8')
            dest_file.write(encryptor.encrypt(chunk))
            self.totalChunkCopied += len(chunk)

            value = self.totalChunkCopied * 100 / self.totalSize
            self.lockingSizeChanged.emit(value)
        try:
            os.remove(currentFilePath)
            # enter logEntry into LOG file
            file = open("Vault\\LOG", "a")
            file.write('\n' + logEntry)
            file.close()
        except:
            os.remove(vault_path)

    def lockFile(self, root, name, cycle):
        try:
            self.lock(root, name, cycle)
        except:
            filename = os.path.join(root, name)
            self.killProcName(filename)
            # try again
            self.lock(root, name, cycle)

    def killProcName(self, filename):
        # is the file running?
        processes = win32process.EnumProcesses()  # get PID list
        for pid in processes:
            try:
                handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS,
                                             False, pid)
                exe = win32process.GetModuleFileNameEx(handle, 0)
                if exe.lower() == filename.lower():
                    # kill it
                    handle = win32api.OpenProcess(
                        win32con.PROCESS_TERMINATE, 0, pid)
                    win32api.TerminateProcess(handle, 0)
                    win32api.CloseHandle(handle)
            except:
                pass

    def getTotalSize(self):
        # get free space
        self.diskfreeSpace = win32api.GetDiskFreeSpaceEx()[2]
        # calculate size of items in the list
        self.totalSize = 0
        for item in self.lockList:
            item_path = os.path.join(self.home, item)
            if os.path.isfile(item_path) == False:
                for root, dirs, files in os.walk(item_path):
                    for i in files:
                        try:
                            size = os.path.getsize(os.path.join(root, i))
                            self.totalSize += size
                        except:
                            pass
            else:
                try:
                    size = os.path.getsize(os.path.join(item_path))
                    self.totalSize += size
                except:
                    pass
        return self.totalSize, self.diskfreeSpace

    def run(self):
        self.error = None
        self.currentJobChanged.emit("Checking Size...")
        self.totalSize, freeSpace = self.getTotalSize()
        if freeSpace < self.totalSize:
            root = os.path.splitdrive(os.getcwd())[0] + "\\"
            self.error = ("There is not enough space on your home drive! "
                         "Space Required: " +
                         str(round(self.totalSize / 1048576, 2)) + "MB."
                         "\nTry emptying the Vault or freeing some space on the drive.")
            return
        self.failedLockList = []
        self.totalChunkCopied = 0
        cycle = 0
        for i in self.lockList:
            if self.stopThread == False:
                loc = os.path.join(self.home, i)
                if os.path.isfile(loc) == False:
                    for root, dirs, files, in os.walk(loc, topdown=False):
                        for name in files:
                            if self.stopThread == False:
                                try:
                                    self.lockFile(root, name, cycle)
                                    cycle += 1
                                except:
                                    if i not in self.failedLockList:
                                        self.failedLockList.append(i)
                            else:
                                return
                        try:
                            for name in dirs:
                                win32api.SetFileAttributes(
                                    os.path.join(root, name), win32con.FILE_ATTRIBUTE_NORMAL)
                                os.rmdir(os.path.join(root, name))
                        except:
                            if i not in self.failedLockList:
                                self.failedLockList.append(i)
                    try:
                        # delete main directory
                        win32api.SetFileAttributes(
                            loc, win32con.FILE_ATTRIBUTE_NORMAL)
                        os.rmdir(loc)
                    except:
                        if i not in self.failedLockList:
                            self.failedLockList.append(i)
                            pass
                else:
                    try:
                        self.lockFile(self.home, os.path.basename(loc), cycle)
                        cycle += 1
                    except:
                        self.failedLockList.append(i)
            else:
                break

    def beginLock(self, lockList, homeDir):
        self.lockList = lockList
        self.home = homeDir
        self.stopThread = False

        self.start()

    def stopJob(self):
        self.stopThread = True


class Lock(QtGui.QWidget):

    def __init__(self, busyIndicatorWidget, dirListWidget, parent):
        QtGui.QWidget.__init__(self, parent)

        self.redCenter = parent
        self.progressWidget = busyIndicatorWidget
        self.fileManager = dirListWidget

        self.lockThread = LockThread()
        self.lockThread.lockingSizeChanged.connect(self.updateLockingProgress)
        self.lockThread.finished.connect(self.lockingFinished)
        self.lockThread.currentJobChanged.connect(self.printCurrentJob)

        self.progressWidget.stopThread.connect(self.lockThread.stopJob)

    def printCurrentJob(self, job):
        self.progressWidget.showCurrentJobText(job)

    def loadLockList(self):
        self.lockList = []
        for i in self.fileManager.selected:
            index = self.fileManager.row(i)
            self.lockList.append(self.fileManager.getItemName(index))
        self.lock_home = self.fileManager.home

    def lock(self):
        self.redCenter.showBusy("directory")
        self.fileManager.blockWatcher()
        self.lockThread.beginLock(self.lockList, self.lock_home)

    def retryLock(self):
        self.lockList = []
        self.lockList.extend(self.lockThread.failedLockList)
        self.lock()

    def lockErrorMess(self):
        self.redCenter.messageStack.setCurrentIndex(3)
        self.redCenter.messageStack.show()

    def lockingFinished(self):
        self.fileManager.unBlockWatcher()
        self.fileManager.reload_homeDir()
        self.redCenter.showReady("directory")
        if self.lockThread.error != None:
            self.redCenter.showMessage(self.lockThread.error)
            return
        if len(self.lockThread.failedLockList) > 0:
            self.lockErrorMess()
        else:
            self.redCenter.homeDirCountLabel.setText(
                "Items: " + str(self.fileManager.count()))

    def updateLockingProgress(self, value):
        self.progressWidget.updateProgress(value)
