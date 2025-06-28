#!/usr/bin/env python2.7

__author__ = "Leonid Bloch"
__copyright__ = "Copyright 2014, Leonid Bloch"
__license__ = "GPLv2"
__version__ = "0.1"
__email__ = "lb@tx.technion.ac.il"

from os import walk, urandom, access, R_OK, W_OK, sep, symlink, makedirs, remove, listdir, lstat
from os.path import join, getsize, abspath, islink, realpath, isfile, exists, dirname, expanduser
from datetime import datetime, timedelta
import hashlib
import numpy as np
import fnmatch
import re
from zlib import compressobj, decompressobj
from Crypto.Cipher import AES
import struct
from boto.s3.connection import S3Connection
from boto.exception import S3ResponseError, S3CreateError
from boto.s3.key import Key
from boto.s3.connection import Location
from boto.s3.multipart import part_lister
import io
import sys
import shutil
import progressbar
import getpass
from math import ceil
import argparse
import signal

###################################################################
### Parsing the arguments
parser = argparse.ArgumentParser(description = ("Compressed, encrypted,"
                                 " deduplicated backup to Amazon's S3"),
                                  epilog = ("===> For options of the different actions"
                                            " check \"%(prog)s ACTION -h\""
                                            " (for example: \"%(prog)s backup -h\")"))
# Initiating subparsers (for different actions)
subparsers = parser.add_subparsers(dest = 'action', help = "Choose the desired action")
# Backup arguments
parser_backup = subparsers.add_parser('backup', help = "Initiate backup.")
parser_backup.add_argument('mypaths', nargs = '+', metavar = "BACKUPPATH",
                           help = "Paths to backup.")
parser_backup.add_argument('-e', '--exclude', dest = 'excludes', nargs = '+',
                           metavar = "PATTERN",
                           help = "Paths/file patterns to exclude from backup.")
parser_backup.add_argument('-d', '--device', metavar = "DEVICE",
                           help = ("Specify the device you want to backup. The device"
                           " might be a distinct physical device, or a different location on"
                           " the same device. If only one device is backed up on the physical"
                           " device, you need to enter this parameter only during the initial"
                           " backup (will be detected during consecutive backups). If this"
                           " parameter is neither specified nor detected, you will be"
                           " prompted."))
parser_backup.add_argument('-c', '--credsfile', dest = 'credsFile', default = 'default',
                           metavar = "PATH",
                           help = ("Path to the credentials file you've downloaded from"
                           " Amazon (.csv format: User Name, Access Key Id, Secret Access"
                           " Key). If you choose to encrypt this file after the first use"
                           " (RECOMMENDED!) you won't have to use this option on the"
                           " same physical device anymore. It is, however, required for"
                           " the initial backup of any new physical device."
                           " (default: <LOGPATH>/credentials.csv.enc)."))
parser_backup.add_argument('--bucket', dest = 'mybucket', metavar = "BUCKET",
                           help = ("The bucket for uploading. Doesn't have to exist during"
                           " the first backup, but has to be the same afterwards,"
                           " for ALL backups and devices. Should be provided only during"
                           " the first backup on each device (otherwise it is detected)."
                           " If this argument is neither specified nor detected, you will"
                           " be prompted to enter a value."))
parser_backup.add_argument('--oldlogbucket', dest = 'oldlogBucket', default = 'default',
                           metavar = "BUCKET",
                           help = ("The bucket for backup of old log files. Can be the same"
                           " as the main upload bucket, but specifying a new one might help"
                           " to manage the old logs better (for example, move all of the"
                           " old logs to Glacier. (default: <MAIN BUCKET>-oldlogs)."))
parser_backup.add_argument('--credsenc', dest = 'credsEnc', action = 'store_true',
                           default = 'default',
                           help = ("Specify that the credentials file is encrypted."
                           " The default behavior is \"True\" if the credentials file is"
                           " <LOGPATH>/credentials.csv.enc, and \"False\" otherwise."))
parser_backup.add_argument('--geolocation', dest = 'newLoc', default = 'DEFAULT',
                           metavar = "LOCATION",
                           choices = ['APNortheast', 'APSoutheast', 'APSoutheast2',
                                      'CNNorth1', 'DEFAULT', 'EU', 'SAEast', 'USWest',
                                      'USWest2'],
                           help = ("Geographic location to create a new bucket in."
                           " Only useful if creating a new bucket (beginning a totally"
                           " fresh backup, to a currently unexisting bucket)."
                           " Options: \"APNortheast\", \"APSoutheast\", \"APSoutheast2\","
                           " \"CNNorth1\", \"DEFAULT\", \"EU\", \"SAEast\", \"USWest\","
                           " \"USWest2\""
                           " (default: DEFAULT)."))
parser_backup.add_argument('--logpath', dest = 'logPath', metavar = "PATH",
                           default = expanduser('~') + sep + ".lbcp",
                           help = ("Path to the log files. Needs to be the same during the"
                           " entire lifetime of all the backups on the device."
                           " Do NOT use this option unless you have REALLY specific needs."
                           " (default: $HOME/.lbcp)."))
# Restore arguments
parser_restore = subparsers.add_parser('restore', help = "Initiate rstore.")
parser_restore.add_argument('restoreThis', nargs = '+', metavar = "RESTOREPATH",
                            help = ("Paths to restore. If restoring on a different"
                            " device, a full path of the restored files is required."
                            " Generally, it is recommended to use the full path anyway."))
parser_restore.add_argument('restorePath', metavar = "SAVEPATH",
                            help = "Path to which the restored files will be downloaded.")
parser_restore.add_argument('-d', '--device', metavar = "DEVICE",
                            help = ("Specify the device you want to restore from. The device"
                            " might be a distinct physical device, or a different location on"
                            " the same device. If only one device is backed up on the"
                            " physical device you're working on, and you want to restore"
                            " from it, you don't have to specify this parameter - it is"
                            " detected automatically. If this parameter is neither specified"
                            " nor detected, you will be prompted."))
parser_restore.add_argument('-c', '--credsfile', dest = 'credsFile', default = 'default',
                            metavar = "PATH",
                            help = ("Path to the credentials file you've downloaded from"
                            " Amazon (.csv format: User Name, Access Key Id, Secret Access"
                            " Key). If you chose to encrypt this file after the first use"
                            " (RECOMMENDED!) you don't have to use this option on the"
                            " same physical device anymore. It is, however, required if"
                            " restoring on a new or different physical device."
                            " (default: <LOGPATH>/credentials.csv.enc)."))
parser_restore.add_argument('--bucket', dest = 'mybucket', metavar = "BUCKET",
                            help = ("The bucket from which to restore. Should be specified"
                            " only if the restore is on a different or a new device"
                            " (it is detected automatically otherwise)."
                            " If this argument is neither specified nor detected, you will"
                            " be prompted to enter a value."))
parser_restore.add_argument('--credsenc', dest = 'credsEnc', action = 'store_true',
                            default = 'default',
                            help = ("Specify that the credentials file is encrypted."
                            " The default behavior is \"True\" if the credentials file is"
                            " <LOGPATH>/credentials.csv.enc, and \"False\" otherwise."))
parser_restore.add_argument('--logpath', dest = 'logPath', metavar = "PATH",
                            default = expanduser('~') + sep + ".lbcp",
                            help = ("Path to the log files. Needs to be the same during the"
                            " entire lifetime of all the backups on the device."
                            " Do NOT use this option unless you have REALLY specific needs."
                            " (default: $HOME/.lbcp)."))
# Encrypt arguments
parser_encrypt = subparsers.add_parser('encrypt',
                                       help = "Initiate local file encryption.")
parser_encrypt.add_argument('PLAINTEXT', help = "Path of the original file.")
parser_encrypt.add_argument('ENCRYPTED', help = "Path to save the encrypted file in.")
# Decrypt arguments
parser_decrypt = subparsers.add_parser('decrypt',
                                       help = "Initiate local file decryption.")
parser_decrypt.add_argument('ENCRYPTED', help = "Path of the encrypted file.")
parser_decrypt.add_argument('PLAINTEXT', help = "Path to save the decrypted file in.")
args = parser.parse_args()

# Getting default values of parameters, and naming them shorter
action = args.action
if action == 'backup' or action == 'restore':
    credsFile = args.credsFile
    mybucket = args.mybucket
    device = args.device
    credsEnc = args.credsEnc
    logPath = args.logPath
    # Use absolute log path
    logPath = abspath(logPath)
    if credsFile == 'default':
        credsFile = logPath + sep + "credentials.csv.enc"
    
    if credsEnc == 'default':
        if credsFile == logPath + sep + "credentials.csv.enc":
            credsEnc = True
        else:
            credsEnc = False

# Backup only
if action == 'backup':
    mypaths = args.mypaths
    excludes = args.excludes
    oldlogBucket = args.oldlogBucket
    newLoc = args.newLoc
# Restore only
elif action == 'restore':
    restoreThis = args.restoreThis
    restorePath = args.restorePath
    oldlogBucket = '' # Dummy, for general initialization
    newLoc = '' # Dummy, for general initialization
# Local encrypt/decrypt
else:
    plainFile = args.PLAINTEXT
    encFile = args.ENCRYPTED

###################################################################
### Global variables
# Get current time
currentTime = int(datetime.now().strftime("%Y%m%d%H%M%S"))
# Upload parameters (DON'T CHANGE!!!)
maxUploadSize = 16*1024*1024 #Must be dividable by 16, and more than 2**23
chunksize = 64*1024 #Must be dividable by 16
# Max date (DON'T CHANGE!!!)
maxDate = 99999999999999
###################################################################
### Functions
def mod_time(filename):
        t = datetime.fromtimestamp(lstat(filename).st_mtime)
        return int(t.strftime("%Y%m%d%H%M%S"))


def addSeconds(time, sec):
    '''
    Add or subtract seconds from int formatted time
    '''
    time = datetime.strptime(str(time), "%Y%m%d%H%M%S")
    time += timedelta(seconds = sec)
    return int(time.strftime("%Y%m%d%H%M%S"))


def checksum_file(f, block_size=128*512):
    checksum = hashlib.md5()
    with open(f, 'rb') as file_to_check:
        while True:
            data = file_to_check.read(block_size)
            if not data:
                break
            checksum.update(data)
    return checksum.hexdigest()


def makeSerials(rawString, byteString):
    rawString = str.encode(rawString)
    return hashlib.sha256(rawString + byteString).hexdigest()


def sizeof_fmt(num):
    for x in [' bytes',' KB',' MB',' GB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0
    return "%3.1f%s" % (num, ' TB')


def pBarInitiation(obj, initial = ''):
    global widgets
    widgets = [ initial,
               progressbar.FileTransferSpeed(),
               ' ', progressbar.Bar(), ' ',
               progressbar.Percentage(), ' ',
               progressbar.ETA() ]
    global pbar
    pbar = progressbar.ProgressBar(widgets=widgets,
                                       maxval=sys.getsizeof(obj))


def progress_callback(current, total):
    try:
        pbar.update(current)
    except AssertionError as e:
        print e


def intToDate(i):
    i = str(i)
    return i[:4] + '-' + i[4:6] + '-' + i[6:8] + '_' + \
           i[8:10] + ':' + i[10:12] + ':' + i[12:]


def maxDateBeforeLast(listOfArrs, datesArray, lastDate):
    '''
    Take a list of arrays of indices, and determine which of these indices
    corresponds to the latest date in a second array, that is smaller than
    the last date.
    Returns uniquified, sorted array of such indices.
    Assumptions: all dates are greater than zero and all members of
    the list of arrays are valid indices in the dates array.
    '''
    lst = []
    for i in listOfArrs:
        t = datesArray[i]
        t[t > lastDate] = 0
        tMax = np.amax(t)
        if tMax:
            lst.append(i[np.argmax(t)])
        
    return np.unique(np.array(lst))


def fileRestore(path, checksum):
    if isfile(path):
        if checksum_file(path) == checksum and not islink(path):
            print "Same file exists in restore path. Skipping!"
            return False
        else:
            print "A different file with the same name exists in the restore path!"
            count = 0
            while True:
                ns = raw_input("Overwrite? (Y/n) ")
                if (ns in ['', 'Y', 'y']) or (count > 4):
                    print "Overwriting..."
                    return True
                elif ns in ['N', 'n']:
                    print "Skipping..."
                    return False
                
                count += 1
            
    else:
        return True


def getInitialPasswd(currPass = False):
    count = 0
    print ("Please choose your new password wisely, and make sure you"
           " never forget it\nas long as you need it!!!")
    pprompt = lambda: (getpass.getpass(), getpass.getpass("Retype password: "))
    if currPass:
        p1, p2 = currPass, getpass.getpass("Retype password: ")
    else:
        p1, p2 = pprompt()
    
    while p1 != p2:
        print("Passwords do not match. Please try again")
        p1, p2 = pprompt()
        if count >= 3:
            print "Goodbye!"
            sys.exit(1)
        
        count += 1
    
    return p1  


def verifyPasswd(b, logPath, act, currPass = False):
    '''
    Verify or initiate password, provide string for computing serials
    '''
    try:
        k = b.get_key("0_logs/control")
    except:
        print "No connection to S3. Exiting."
        sys.exit(1)
        
    if k:
        randStr = k.get_contents_as_string()
        salt = randStr[:24]
        iv = randStr[24:40]
        randStr = randStr[40:]
        count = 0
        while True:
            if currPass and not count:
                password = currPass
            else:
                password = getpass.getpass()

            encKey = hashlib.sha256(str.encode(password) + salt).digest()
            decryptor = AES.new(encKey, AES.MODE_CBC, iv)
            decStr = decryptor.decrypt(randStr)
            providedHash = decStr[32:]
            calculatedHash = hashlib.sha256(decStr[:32]).digest()
            if providedHash == calculatedHash:
                break
            
            if count >= 3:
                print "Goodbye!"
                sys.exit(1)
            
            count += 1
        
    elif listdir(logPath) or len([ f for f in b.list('0_logs')]):
        print ("##############################################"
               "\nERROR: control log is missing, but other logs exist!"
               "\nIf you have the control log which was created during the"
               "\nbackup initialization, please restore it manually"
               "\n(e.g. via the web interface) to:\n"
               + b.name + "/0_logs."
               "\nOtherwise, you have to delete all the contents of the bucket and"
               "\nthe local log files manually, and start from scratch!"
               "\nONLY RESTORES CAN BE DONE NOW!"
               "\n##############################################")
        if act == 'restore':
            if currPass:
                password = currPass
            else:
                password = getpass.getpass()
            
            providedHash = b'0'
        else:
            sys.exit(1)
    else:
        print "Welcome to the new backup!"
        salt = urandom(24)
        randStr = urandom(32)
        password = getInitialPasswd(currPass)
        encKey = hashlib.sha256(str.encode(password) + salt).digest()
        providedHash = hashlib.sha256(randStr).digest()
        randStr = randStr + providedHash
        iv = urandom(16)
        encryptor = AES.new(encKey, AES.MODE_CBC, iv)
        randStr = encryptor.encrypt(randStr)
        randStr = salt + iv + randStr
        k = Key(b)
        k.key = "0_logs/control"
        k.set_contents_from_string(randStr)
        # Download new control log
        k.get_contents_to_filename(logPath + sep + 'control')
        print ("The newly created control log was saved to " + logPath + sep + "control."
        "\nIt should never change as long as you keep this backup, and is very important."
        "\nYou might want to put it in a safe place. It is automatically uploaded to S3,"
        "\nso backing it up there is NOT needed.")
        raw_input("Press any key to continue...")
    
    return password, providedHash


def connBucket(c, b, loc, act):
    '''
    Connect to S3 bucket
    '''
    try:
        bucket = c.get_bucket(b)
    except S3ResponseError as e:
        if act != 'backup':
            print "Bucket " + b + " does not exist or is not accessible. Exiting."
            sys.exit(1)
        elif e.error_code == 'NoSuchBucket':
            print "Bucket " + b + " does not exist. Create it?"
            count = 0
            while True:
                cr = raw_input("(Y/n)? ")
                if cr in ['', 'Y', 'y']:
                    try:
                        bucket = c.create_bucket(b, location = getattr(Location, loc))
                        print "Bucket " + b + " created in location \"" + loc + "\"."
                        break
                    except S3CreateError as e:
                        if e.error_code == 'BucketAlreadyExists':
                            print "Bucket name taken. Please choose another."
                            sys.exit(1)
                        else:
                            raise e
                
                elif (cr in ['N', 'n']) or (count > 3):
                    print "Goodbye!"
                    sys.exit(1)
                
                count += 1
        
        elif e.error_code == 'AccessDenied':
            print ("You do not have access to bucket " + b +
                   ". Please choose another.")
            sys.exit(1)
        else:
            print "No connection to S3. Exiting."
            sys.exit(1)
    
    return bucket


def getRemoteLog(remoteLogName, bucket, dev, logPath, logName, password):
    try:
        remoteLog = bucket.get_key(remoteLogName)
    except:
        print "No connection to S3. Exiting."
        sys.exit(1)
    
    logFile = logPath + sep + logName
    if remoteLog:
        print "Remote log for device " + dev + " found."
        count = 0
        while True:
            dl = raw_input("Download and use it? (Y/n) ")
            if dl in ['', 'Y', 'y']:
                downDecUnzipCopy(remoteLogName, logPath + sep, '0', [logName],
                                 bucket, password)
                return logFile, remoteLogName
            elif (dl in ['N', 'n']) or (count > 3):
                print "No log file. Exiting."
                sys.exit(1)
            
            count += 1
        
    else:
        print "Remote log for device " + dev + " not found. Exiting."
        sys.exit(1)


#def ifRestore(remoteLogName, bucket, dev, logPath, logName, password):
#    logFile, remoteLogName = getRemoteLog(remoteLogName, bucket, dev,
#                                          logPath, logName, password)
#    if not logFile:
#        print "ERROR: restore action needs log file!"
#        sys.exit(1)
#    else:
#        return logFile, remoteLogName


def getLogFile(dev, devList, logPath, bucket, password):
    logName = "lbcp_" + dev + ".log"
    logFile = logPath + sep + logName
    remoteLogName = "0_logs/" + logName
    if isfile(logFile) or (dev not in devList):
        # if logfile exists, or we are starting a new backup
        return logFile, remoteLogName
    else:
        count = 0
        while True:
            getRemote = raw_input("Local log file not found, try to"
                                  " search for remote? (Y/n) ")
            if getRemote in ['', 'Y', 'y']:
                return getRemoteLog(remoteLogName, bucket, dev, logPath,
                                    logName, password)
            elif (getRemote in ['N', 'n']) or (count > 3):
                print "No log file. Exiting."
                sys.exit(1)
            
            count += 1


def verifyBucket(bucket, internal = False):
    if (not re.match('^[a-z0-9][a-z0-9-]+[a-z0-9]$', bucket) or
        len(bucket) < 3 or len(bucket) > 63):
        print ("Invalid bucket name: " + bucket + "."
               "\nName may contain lowercase alphanumeric characters only, and hyphens."
               "\nIt must also contain between 3 and 63 characters.")
        if internal:
            return False
        else:
            sys.exit(1)
        
    else:
        return True


def verifyDevice(dev, internal = False):
    if not re.match('^[a-z0-9_-]+$', dev) or len(dev) > 16:
        print ("Invalid device name."
               "\nDevice name may contain lowercase alphanumeric characters, hyphens"
               "\nand underscores only, and must be less than 16 characters long.")
        if internal:
            return False
        else:
            sys.exit(1)
        
    else:
        return True


def listDevs(bucket, quiet = False):
    devList = [ str(k.name[12:-4]) for k in bucket.list('0_logs/lbcp_')]
    if not quiet:
        if len(devList):
            print "Existing devices in bucket " + bucket.name + ":"
            count = 1
            for s in devList:
                print str(count) + ") " + s
                count += 1
        
        else:
            print "No devices found in bucket " + bucket.name + "."
    
    return devList


def zipEnc(archivepath, filepath, password, inMem = False):
    '''
    Local encryption
    '''
    salt = urandom(24)
    encKey = hashlib.sha256(str.encode(password) + salt).digest()
    iv = urandom(16)
    encryptor = AES.new(encKey, AES.MODE_CBC, iv)
    filesize = getsize(filepath)
    queue = b''
    compressor = compressobj(9)

    with open(filepath, 'rb') as file:
        if inMem:
            archive = io.BytesIO()
        else:
            archive = open(archivepath, 'wb')
        
        archive.write(struct.pack('<Q', filesize))
        archive.write(salt)
        archive.write(iv)
        while True:
            data = file.read(chunksize)
            if not data:
                break
            data = compressor.compress(data)
            queue += data
            if len(queue) < chunksize:
                continue
            
            data = encryptor.encrypt(queue[:chunksize])
            queue = queue[chunksize:]
            archive.write(data)
        
        queue += compressor.flush()
        if queue:
            queue += b'+' * (16 - len(queue) % 16)
            queue = encryptor.encrypt(queue)
            archive.write(queue)
        
    if inMem:
        return archive
    else:
        archive.close()


def decUnzip(archivepath, filepath, password, inMem = False):
    '''
    Local decryption
    '''
    with open(archivepath, 'rb') as archive:
        origsize = struct.unpack('<Q', archive.read(struct.calcsize('Q')))[0]
        salt = archive.read(24)
        iv = archive.read(16)
        encKey = hashlib.sha256(str.encode(password) + salt).digest()
        decryptor = AES.new(encKey, AES.MODE_CBC, iv)
        decompressor = decompressobj()
        if inMem:
            f = io.BytesIO()
        else:
            f = open(filepath, 'wb')
        
        while True:
            data = archive.read(chunksize)
            if not data:
                break
            data = decryptor.decrypt(data)
            try:
                data = decompressor.decompress(data)
            except:
                print "Data corrupted! Are you sure the password is correct?"
                if not inMem:
                    f.close()
                    remove(filepath)
                
                sys.exit(1)
            
            f.write(data)
        
        data = decompressor.flush()
        f.write(data)
        f.truncate(origsize)
    
    if inMem:
        return f
    else:
        f.close()


def devGivenNotDetected(action, dev, devList, bucket, devLogFile, logPath, password):
    '''
    Manages log file and device log in the case that the device is
    specified by the user, but not detected locally.
    '''
    if action == 'backup':
        selfDev = True
        inDevLog = np.array([dev, bucket.name]).reshape(1,2)
        logFile, remoteLogName = getLogFile(dev, devList, logPath,
                                            bucket, password)
        # Write new device log
        np.savetxt(devLogFile, inDevLog, fmt='%s',
                   delimiter=',', header='This device,Bucket')
    
    elif action == 'restore':
        selfDev = False
        logName = "lbcp_" + dev + ".log"
        remoteLogName = "0_logs/" + logName
        logFile, remoteLogName = getRemoteLog(remoteLogName, bucket, dev,
                                              logPath, logName, password)
    
    return logFile, remoteLogName, selfDev


def devGivenAndDetected(action, dev, detectedDev, devList,
                        bucket, logPath, password):
    if detectedDev == dev:
        selfDev = True
        logFile, remoteLogName = getLogFile(dev, devList, logPath,
                                            bucket, password)
    elif action == 'restore':
        selfDev = False
        logName = "lbcp_" + dev + ".log"
        remoteLogName = "0_logs/" + logName
        logFile, remoteLogName = getRemoteLog(remoteLogName, bucket, dev,
                                              logPath, logName, password)
    else:
        print ("Specified device (" + dev + ") doesn't match detected ("
               + detectedDev + ")"
               "\nand you want to upload! Please try again.")
        sys.exit(1)
    
    return logFile, remoteLogName, selfDev


def initiate(dev, action, logPath, bucket, oldlogBucket, credsFile, loc):
    # Check if this physical device is backed up as a single device
    localDevs = [ f[10:-4] for f in listdir(logPath)
                 if f.startswith('local_dev') ]
    if len(localDevs) == 1 and not dev:
        devLogFile = logPath + sep + "local_dev_" + localDevs[0] + ".log"
    else:
        try:
            # Try, because dev might not be a string, but "False"
            devLogFile = logPath + sep + "local_dev_" + dev + ".log"
        except:
            pass
    
    try:
        devLog = np.loadtxt(devLogFile, dtype = 'str', delimiter = ',')
        detectedDev = devLog[0]
        detectedBucket = devLog[1]
    except:
        detectedDev = False
        detectedBucket = False
    
    # Get correct bucket
    if bucket:
        verifyBucket(bucket)
    
    if not bucket and not detectedBucket:
        print "No S3 bucket specified nor detected."
        count = 0
        while True:
            if count > 5:
                print "Too many trys, goodbye!"
                sys.exit(1)
            
            count += 1
            bucket = raw_input("Please specify bucket: ")
            if not verifyBucket(bucket, internal = True):
                continue
            
            cont = raw_input("Got bucket: " + bucket + ". Continue? (Y/n) ")
            if cont in ['', 'Y', 'y']:
                break
            elif cont in ['N', 'n']:
                continue
    
    elif detectedBucket and not bucket:
        bucket = detectedBucket
    elif bucket and detectedBucket and (bucket != detectedBucket):
        if action == 'backup':
            print "You can not continue existing backup to a different bucket!"
            sys.exit(1)
        elif action == 'restore':
            print ("WARNING: You are restoring from a different bucket than this"
                   "\ndevice is backed up to!")
            raw_input("Press any key to continue, ctrl+C to quit.")
    
    # Get correct credentials file, and encrypt if new.
    #if not access(credsFile, R_OK):
    #    print "Credentials file not accessible. Please specify another."
    #    sys.exit(1) #TODO delete this check if really unnecessary
    
    if not credsEnc:
        print "Reading initial S3 credentials file."
        try:
            S3creds = np.loadtxt(credsFile, dtype = 'str', delimiter = ',',
                                 skiprows = 1, usecols = (1, 2))
        except:
            print "Credentials file can not be read. Exiting."
            sys.exit(1)
        
        conn = S3Connection(S3creds[0], S3creds[1])
        bucket = connBucket(conn, bucket, loc, action)
        password, hashStr = verifyPasswd(bucket, logPath, action)
        print ("The credentials file was read, but it exists unencrypted on"
               "\nyour computer. Would you like to encrypt it?")
        count = 0
        while True:
            toEnc = raw_input("(Y/n)? ")
            if toEnc in ['', 'Y', 'y']:
                zipEnc(logPath + sep + "credentials.csv.enc",
                       credsFile, password)
                print ("##############################################"
                       "\nCredentials file encrypted. The encrypted file is saved to:\n"
                       + logPath + sep + "credentials.csv.enc"
                       "\n...and is the same for all devices."
                       "\n##############################################")
                if access(credsFile, W_OK):
                    cnt = 0
                    while True:
                        print ("It is advised to delete the plaintext"
                               " file for better security."
                               "\n(Original can be restored by decryption, or"
                               " by downloading from the S3 web interface)")
                        toDel = raw_input("Delete plaintext credentials? (Y/n) ")
                        if toDel in ['', 'Y', 'y']:
                            remove(credsFile)
                            break
                        elif (toDel in ['N', 'n']) or (cnt > 3):
                            break
                    
                        cnt += 1
                    
                break            
            elif (toEnc in ['N', 'n']) or (count > 3):
                break
            
            count += 1
    
    # If credentials file encrypted
    else:
        if not isfile(credsFile):
            print "Credentials file not found! Exiting."
            sys.exit(1)
        
        print "Reading S3 encrypted credentials file."
        password = getpass.getpass()
        try:
            credsFile = decUnzip(credsFile, '', password, inMem = True)
            credsFile = io.StringIO(credsFile.getvalue().decode('UTF-8'))
            S3creds = np.loadtxt(credsFile, dtype = 'str', delimiter = ',',
                                 skiprows = 1, usecols = (1, 2))
        except:
            print "Credentials file can not be read. Exiting."
            sys.exit(1)
        
        conn = S3Connection(S3creds[0], S3creds[1])
        bucket = connBucket(conn, bucket, loc, action)
        password, hashStr = verifyPasswd(bucket, logPath, action, currPass = password)
    
    # Connect to log bacup bucket
    if action == 'backup':
        if oldlogBucket == 'default':
            oldlogBucket = bucket.name + '-oldlogs'
        
        count = 0
        while not verifyBucket(oldlogBucket, internal = True):
            count += 1
            print ("Old logs' storage bucket may be the same or"
                   " different than the main backup bucket!")
            oldlogBucket = raw_input("Please specify bucket FOR"
                                     " STORING OLD LOGS: ")
            if count > 5:
                print "Too many trys, goodbye!"
                sys.exit(1)
        
        if bucket.name == oldlogBucket:
            oldlogBucket = bucket
        else:
            oldlogBucket = connBucket(conn, oldlogBucket, loc, action)
    
    else:
        oldlogBucket = False
        
    # Logfile and device management
    if dev:
        verifyDevice(dev)
        devList = listDevs(bucket, quiet = True)
        if detectedDev:
            logFile, remoteLogName, selfDev = devGivenAndDetected(action, dev,
                                                                  detectedDev,
                                                                  devList, bucket,
                                                                  logPath, password)
        else:
            logFile, remoteLogName, selfDev = devGivenNotDetected(action, dev,
                                                                  devList,
                                                                  bucket,
                                                                  devLogFile,
                                                                  logPath,
                                                                  password)
    
    elif detectedDev:
        selfDev = True
        devList = listDevs(bucket, quiet = True)
        logFile, remoteLogName = getLogFile(detectedDev, devList, logPath,
                                            bucket, password)
    else:
        print ("No device specified nor detected."
               "\nPlease wait for a list of available devices...")
        devList = listDevs(bucket)
        # Ask to specify a device manually
        count = 0
        while True:
            if count > 5:
                print "Too many trys, goodbye!"
                sys.exit(1)
            
            count += 1
            if devList:
                dev = raw_input("Please specify a device (new, or "
                                "a number from the list above): ")
                try:
                    if int(dev) in range(len(devList) + 1)[1:]:
                        dev = devList[int(dev) - 1]
                except:
                    pass
            
            else:
                dev = raw_input("Please specify a device: ")
            
            if not verifyDevice(dev, internal = True):
                continue
            
            cont = raw_input("Got device: " + dev + ". Continue? (Y/n) ")
            if cont in ['', 'Y', 'y']:
                break
            elif cont in ['N', 'n']:
                continue
        
        devLogFile = logPath + sep + "local_dev_" + dev + ".log"
        if dev in localDevs:
            detectedBucket = np.loadtxt(devLogFile, dtype = 'str',
                                        delimiter = ',')[1]
            if bucket.name != detectedBucket:
                print ("Specified bucket (" + bucket.name + ") is not the same that"
                       "\nthis device is backed up in (" + detectedBucket +"). Exiting.")
                sys.exit(1)
            
            selfDev = True
            logFile, remoteLogName = getLogFile(dev, devList, logPath,
                                                bucket, password)
        
        else:
            logFile, remoteLogName, selfDev = devGivenNotDetected(action, dev,
                                                                  devList,
                                                                  bucket,
                                                                  devLogFile,
                                                                  logPath,
                                                                  password)
            

    return (conn, bucket, oldlogBucket, password, hashStr,
            logFile, remoteLogName, selfDev)


def zipEncUp(filepath, serial, bucket, password):
    '''
    Main upload
    '''
    try:
        filesize = getsize(filepath) #check filesize independantly of list
    except:
        print "No such file." # Case of interrupted backup, and file's gone.
        return
    
    print "Uploading " + filepath + " (" + sizeof_fmt(filesize) + ")..."
    try:
        k = bucket.get_key(str(serial))
    except:
        print ("No connection to S3. Exiting. Please complete the "
              "upload another time.")
        sys.exit(1)
    
    if k:
        print "Already exists, moving on..."
        return
      
    salt = urandom(24)
    encKey = hashlib.sha256(str.encode(password) + salt).digest()
    iv = urandom(16)
    encryptor = AES.new(encKey, AES.MODE_CBC, iv)
    queue = b''
    compressor = compressobj(9)
    k = Key(bucket)
    k.key = str(serial)
    multipartCount = 1

    with open(filepath, 'rb') as file:
        upload = io.BytesIO()
        upload.write(struct.pack('<Q', filesize))
        upload.write(salt)
        upload.write(iv)
        while True:
            data = file.read(chunksize)
            if not data:
                break
            data = compressor.compress(data)
            queue += data
            if len(queue) < chunksize:
                continue
            data = encryptor.encrypt(queue[:chunksize])
            upload.write(data)
            if sys.getsizeof(upload) >= maxUploadSize:
                if multipartCount == 1:
                    mpu = bucket.initiate_multipart_upload(k.key)
                    
                upload.seek(0)
                pBarInitiation(upload, "Part: " + str(multipartCount) +
                               " of ~" +
                               str(int(ceil(float(filesize)/maxUploadSize))) +
                               " (" + sizeof_fmt(maxUploadSize) + ") @")
                pbar.start()
                mpu.upload_part_from_file(upload, multipartCount,
                                          cb=progress_callback,
                                          num_cb=100)
                pbar.finish()
                upload.seek(0)
                upload.truncate()
                multipartCount += 1
                
            queue = queue[chunksize:]

    queue += compressor.flush() #write everything that's left
    if queue:
        queue += b'+' * (16 - len(queue) % 16)
        queue = encryptor.encrypt(queue)
        upload.write(queue)

    if multipartCount == 1:
        pBarInitiation(upload)
        pbar.start()
        k.set_contents_from_file(upload, cb=progress_callback,
                                 num_cb=100, rewind = True)
        pbar.finish()
    else:
        upload.seek(0)
        pBarInitiation(upload, "Part: " + str(multipartCount) + " (last) "
                       + " (" + sizeof_fmt(sys.getsizeof(upload)) + ") @")
        pbar.start()
        mpu.upload_part_from_file(upload, multipartCount,
                                  cb=progress_callback,
                                  num_cb=100)
        pbar.finish()
        mpu.complete_upload()


def downDecUnzipCopy(keyName, basepath, checksum, sameFiles, bucket, password):
    '''
    Main download
    '''
    sameFileCount = 0
    for p in sameFiles:
        path = basepath + p
        print "/Restoring: " + p + "\n\\--> to: " + path + "..."
        if fileRestore(path, checksum):
            break
        else:
            sameFileCount += 1
    else:
        return # Files already exist in the path, or we don't want to replace.
    
    try:
        k = bucket.get_key(str(keyName))
    except:
        print "No connection to S3. Exiting."
        sys.exit(1)
      
    if not k:
        print "Key doesn't exist. Skipping..."
        return
      
    keySize = k.size
    print "Downloading " + sizeof_fmt(keySize) + "..."
    decompressor = decompressobj()
    partCount = 0
    try:
        makedirs(dirname(path))
    except:
        pass
      
    partsNum = int(ceil(float(keySize)/maxUploadSize))
    
    multipartCount = 1
    with open(path, 'wb') as file:
        while True:
            if partsNum > 1:
                dataLeft = keySize - maxUploadSize * (multipartCount - 1)
                if dataLeft > maxUploadSize:
                    partSize = sizeof_fmt(maxUploadSize)
                else:
                    partSize = sizeof_fmt(dataLeft)
                
                if dataLeft > 0:
                    sys.stdout.write("Downloading part " + str(multipartCount) +
                                     " of " + str(partsNum) + " (" + partSize + ")...\r")
                    sys.stdout.flush()
            
            data = k.read(maxUploadSize) # Will Python3 need str.encode() here?
            if not data:
                break
            
            currPos = 0
            if not partCount:
                llSize = struct.calcsize('Q')
                origsize = struct.unpack('<Q', data[:llSize])[0]
                salt = data[llSize : llSize + 24]
                encKey = hashlib.sha256(str.encode(password) + salt).digest()
                iv = data[llSize + 24 : llSize + 40]
                decryptor = AES.new(encKey, AES.MODE_CBC, iv)
                currPos = llSize + 40
                partCount = 1
            
            data = decryptor.decrypt(data[currPos:])
            try:
                data = decompressor.decompress(data)
            except:
                print "Data corrupted! Are you sure the password is correct?"
                file.close()
                remove(path)
                sys.exit(1)
            
            file.write(data)
            multipartCount += 1
            
        data = decompressor.flush()
        file.write(data)
        file.truncate(origsize)
    
    restOfSameFiles = sameFiles[(sameFileCount + 1):]
    if restOfSameFiles:
        print "Copying duplicates..."
        for p in restOfSameFiles:
            cpPath = basepath + p
            if fileRestore(cpPath, checksum):
                try:
                    makedirs(dirname(cpPath))
                except:
                    pass
                shutil.copy(path, cpPath)


def notPast(lastBcpTime, currentTime):
    '''
    Vrify that the date is sane
    '''
    if lastBcpTime > addSeconds(currentTime, 86400):
        print ("Last backup took place at: " + intToDate(lastBcpTime) +
               "\nThe current time is set to: " + intToDate(currentTime) +
               "\nObviously there is something wrong. Please set the correct time on"
               " your computer,\nor send me the designs of your time machine!")
        sys.exit(1)
    elif lastBcpTime > currentTime:
        print ("WARNING:"
               "\nLast backup took place at: " + intToDate(lastBcpTime) +
               "\nThe current time is set to: " + intToDate(currentTime) +
               "\nAttention, you may have travelled to another timezone, or the"
               "\ndaylight saving time have changed! To avoid unnecessary mess,"
               "\nyou are advised to wait until " + intToDate(lastBcpTime) + "."
               "\nContinue only if it is urgent!")
        count = 0
        while True:
            continueUpload = raw_input("Continue? (y/N) ")
            if continueUpload in ['Y', 'y']:
                break
            elif (continueUpload in ['', 'N', 'n']) or (count > 3):
                print "Goodbye!"
                sys.exit(0)
            
            count += 1


def localEnc(encFile, plainFile):
    if not access(plainFile, R_OK):
        print "The file " + plainFile + " is not accessible. Goodbye!"
        sys.exit(1)
    
    try:
        makedirs(dirname(encFile))
    except:
        pass
    
    if not access(dirname(encFile), W_OK):
        print "The path " + dirname(encFile) + " is not accessible. Goodbye!"
        sys.exit(1)
    
    passwd = getInitialPasswd()
    zipEnc(encFile, plainFile, passwd)


def localDec(encFile, plainFile):
    if not access(encFile, R_OK):
        print "The file " + encFile + " is not accessible. Goodbye!"
        sys.exit(1)
    
    try:
        makedirs(dirname(plainFile))
    except:
        pass
    
    if not access(dirname(plainFile), W_OK):
        print "The path " + dirname(plainFile) + " is not accessible. Goodbye!"
        sys.exit(1)
    
    passwd = getpass.getpass()
    decUnzip(encFile, plainFile, passwd)


def mainBCP(currentTime, maxDate, bucket, oldlogBucket, passwd, hashStr,
            mypaths, excludes, previousLogFile, remoteLogName,
            lastModTime, lastBcpTime):
    # Check that the log is correct, and corresponds to current backup
    # This is needed only when backing up, since we don't want to stop
    # users restoring from old log files
    if lastModTime:
        givenFirstSerial = prevSerials[0]
        calcFirstSerial = makeSerials(prevChecksums[0], hashStr)
        if not givenFirstSerial == calcFirstSerial:
            print ("ERROR: The logfile you are using is not correct. You have"
                   "\nprobably started a new backup and did not remove the old log."
                   "\nPlease fix that, and try again.")
            sys.exit(1)
    # Configuring backup paths
    # Use absolute paths, if the input had relative ones
    mypaths = np.array([ abspath(p) for p in mypaths ])
    # Sort & unique the input paths array and get rid of redundant subdirectories
    mypaths = np.unique(mypaths)
    bcpPaths = []
    for p in mypaths:
        for b in bcpPaths:
            if p.startswith(b + sep):
                break
            else:
                continue
        else:
            bcpPaths.append(p)
    
    # Verify that the paths exist
    for p in bcpPaths:
        if not exists(p):
            print "Path " + p + " does not exist. Please try again."
            sys.exit(1)
    
    # Checking for deleted files
    if lastModTime:
        print "Checking for deleted files..."
        oldListLength = prevChecksums.shape[0]
        for i in np.arange(oldListLength):
            isCheck = isfile(prevFileList[i])
            if not isCheck and prevDelTimes[i] == maxDate:
                prevDelTimes[i] = currentTime
            elif isCheck and prevDelTimes[i] != maxDate:
                prevDelTimes[i] = maxDate
    
    # Listing all files in path
    print "Listing all files in path..."
    fileList = []
    
    excludes = r'|'.join([fnmatch.translate(x) for x in excludes]) or r'$.'
    
    for path in bcpPaths:
        for root, dirs, files in walk(path):
            dirs[:] = [join(root, d) for d in dirs]
            dirs[:] = [d for d in dirs if not re.match(excludes, d)]
            for f in files:
                fullPath = join(root,f)
                if access(fullPath, R_OK) and not (re.match(excludes, f) or
                                                   re.match(excludes, fullPath)):
                    fileList.append(fullPath)
    
    if not len(fileList):
        print("Path does not exist or is entirely excluded. Please try again!")
        sys.exit(1)
    
    # From now on, fileList is a NumPy array
    fileList = np.array(fileList)
    ## Unique array, in case we have overlapping directories requested
    # Not needed if we have redundant subdirectories removed before.
    #_, fileListUniqInd = np.unique(fileList,  return_index=True)
    #fileList = fileList[np.sort(fileListUniqInd)]
    
    # Modification times:
    mTimes = np.array([ mod_time(f) for f in fileList ])
    
    # Which files have changed in the path?
    if lastModTime:
        print "Checking for changed files..."
    
    newListLength = fileList.shape[0]
    changedIndices = np.array([ i for i in np.arange(newListLength)
                               if mTimes[i] > lastModTime
                               or fileList[i] not in prevFileList ])
    
    if not changedIndices.shape[0]:
        print("No changes detected. Exiting.")
        sys.exit(0)
    
    # From now, fileList and mTimes are listing the CHANGED files ONLY!
    fileList = fileList[changedIndices]
    mTimes = mTimes[changedIndices]
    newListLength = fileList.shape[0]
    
    # Check for symlinks and write real path if needed
    linkList = []
    for f in fileList:
        if islink(f):
            linkList.append(realpath(f))
        else:
            linkList.append('F')
    
    linkList = np.array(linkList)
    
    # Get sizes of changed files
    sizes = np.array([ int(getsize(f)) for f in fileList ])
    
    # Calculate checksums of changed files
    print "Running checksum on " + str(newListLength) + " new files..."
    checksums = np.array([ checksum_file(f) for f in fileList ])
    
    # New serial numbers
    serials = np.array([ makeSerials(s, hashStr) for s in checksums ])
    
    # Choose only distinct files for upload
    if lastModTime:
        serialsToUpload = np.setdiff1d(serials, prevSerials)
        uploadInd = np.argsort(serials)
        uploadIndPos = np.searchsorted(serials[uploadInd], serialsToUpload)
        uploadInd = uploadInd[uploadIndPos]
        uploadInd = np.sort(uploadInd) # Just to preserve upload order - not must
        # Don't include symlinks
        uploadInd = uploadInd[np.nonzero(linkList[uploadInd] == 'F')[0]]
    else:
        _, uploadInd = np.unique(serials, return_index=True)
        uploadInd = np.sort(uploadInd) # Just to preserve upload order - not must
        # Don't include symlinks
        uploadInd = uploadInd[np.nonzero(linkList[uploadInd] == 'F')[0]]
    
    uploadNum = uploadInd.shape[0]
    print str(uploadNum) + " unique files found."
    # Boring: array of current backup date
    backupTime = np.empty(newListLength, dtype=int)
    backupTime.fill(currentTime)
    # And array of 9's for future deletion date purposes
    delTime = np.empty(newListLength, dtype=int)
    delTime.fill(maxDate)
    
    if uploadNum:
        # Building upload list
        uploadArr = np.column_stack((fileList[uploadInd],
                                     serials[uploadInd]))
        #Calculating total upload size
        uploadSize = sizeof_fmt(np.sum(sizes[uploadInd]))
        count = 0
        while True:
            continueUpload = raw_input("<" + uploadSize +
                                       " will be uploaded. OK? (Y/n) ")
            if continueUpload in ['', 'Y', 'y']:
                print "Beginning upload!"
                break
            elif (continueUpload in ['N', 'n']) or (count > 3):
                print "Goodbye!"
                sys.exit(0)
            
            count += 1
        
        # Upload!
        print "Beginning upload of files!"
        count = uploadNum - 1
        for f in uploadArr:
            zipEncUp(f[0], f[1], bucket, passwd)
            print str(count) + " of " + str(uploadNum) + " files remain.\r"
            count -= 1
        
        print "Upload finished. Writing new log."
    
    # Building new log array
    if lastModTime:
        newLog = np.column_stack((np.append(prevBcpTimes, backupTime),
                                  np.append(prevMtimes, mTimes),
                                  np.append(prevDelTimes, delTime),
                                  np.append(prevChecksums, checksums),
                                  np.append(prevSerials, serials),
                                  np.append(prevSizes, sizes),
                                  np.append(prevFileList, fileList),
                                  np.append(prevLinks, linkList)))
    else:
        newLog = np.column_stack((backupTime, mTimes, delTime, checksums,
                                  serials, sizes, fileList, linkList))
    
    # Writing and uploading log array
    np.savetxt(previousLogFile, newLog, fmt='%s', delimiter='//',
               header=("Backup time//Modification time//Deletion time//"
                       "Checksum (MD5)//Serial number//Size (b)//File name//"
                       "Is it a link? If so, where?"))
    if lastBcpTime:
        print "Backing up previous log on S3."
        oldLogKey = bucket.get_key(remoteLogName)
        oldLogKey.copy(oldlogBucket, ("0_logs_old/" + str(lastBcpTime)
                                      + remoteLogName.replace("0_logs/", "_", 1)))
        oldLogKey.delete()
    
    print "Uploading new log to S3."
    zipEncUp(previousLogFile, remoteLogName, bucket, passwd)
    print "Finished uploading the new log."
    print "Upload finished successfully!"


def mainRES(bucket, passwd, restoreThis, restorePath, previousLogFile,
            selfDev, lastBcpTime):
    # Check if there is an old log file
    if not lastBcpTime:
        print "No previous log file detected. Exiting."
        sys.exit(0)
    
    # Use absolute paths, if the input had relative ones
    # (only if restoring to the same device)
    if selfDev:
        restoreThis = [ abspath(p) for p in restoreThis ]
    
    restorePath = abspath(restorePath)
    # Checking if the destination is writable
    if not access(restorePath, W_OK):
        print "The restore destination is not writable. Please try again."
        sys.exit(1)
    
    # Building download array
    restores = r'|'.join([ fnmatch.translate(x) for x in restoreThis]) or r'$.'
    restores = re.compile(restores)
    restoreMatch = np.vectorize(lambda x: bool(restores.match(x)))
    restoreIndices = np.nonzero(restoreMatch(prevFileList))[0]
    
    # Files to restore
    restoreFiles = prevFileList[restoreIndices]
    
    # Restore dates definition
    numRestorePaths = np.unique(restoreFiles).shape[0]
    if not numRestorePaths:
        print "Nothing matches restore paths. Bye!"
        sys.exit(0)
    elif numRestorePaths == 1:
        restoreTimes = prevMtimes[restoreIndices]
    else:
        restoreTimes = prevBcpTimes[restoreIndices]
    
    availDates = np.unique(restoreTimes)
    
    # Rest of restore parameters
    restoreSerials = prevSerials[restoreIndices]
    restoreLinks = prevLinks[restoreIndices]
    restoreDel = prevDelTimes[restoreIndices]
    restoreSizes = prevSizes[restoreIndices]
    restoreChecksums = prevChecksums[restoreIndices]
    
    # Choosing desired restore date
    numRestoreDates = availDates.shape[0]
    restDatesIndices = np.arange(numRestoreDates)
    
    if numRestoreDates == 1:
        print "One restore date available: " + intToDate(availDates[0])
        lastRestoreDate = availDates[0]
    else:
        print "Restore dates available:"
        for i in restDatesIndices:
            print str(i + 1) + ') ' + intToDate(availDates[i])
        
        count = 0
        while True:
            if count > 3:
                print "Too many trys. Exiting."
                sys.exit(1)
            
            desiredLastDateInd = raw_input('Choose a number: ')
            try:
                desiredLastDateInd = int(desiredLastDateInd) - 1
            except:
                print "Please choose an integer between " + \
                      str(np.amin(restDatesIndices) + 1) + " and " + \
                      str(np.amax(restDatesIndices) + 1)
                count += 1
                continue
        
            if desiredLastDateInd in restDatesIndices:
                break
            else:
                print "Please choose an integer between " + \
                      str(np.amin(restDatesIndices) + 1) + " and " + \
                      str(np.amax(restDatesIndices) + 1)
                count += 1
                continue
        
        lastRestoreDate = availDates[desiredLastDateInd]
    
    # Date filtering for restoreIndices
    restoreIndices = [ np.nonzero(restoreFiles == f)[0] for f in restoreFiles ]
    restoreIndices = maxDateBeforeLast(restoreIndices, restoreTimes, lastRestoreDate)
    # Handling deleted files
    restoreDel = restoreDel[restoreIndices]
    restoreIndices = restoreIndices[restoreDel > lastRestoreDate]
    # Extracting softlinks from general array
    restoreLinksTMP = restoreLinks[restoreIndices]
    restoreLinkInd = restoreIndices[restoreLinksTMP != 'F']
    restoreIndices = restoreIndices[restoreLinksTMP == 'F']
    
    # Softlinks array
    restoreLinks = [ [ restoreFiles[i], restoreLinks[i] ] for i in restoreLinkInd ]
    
    # Files and other arrays after date, deleted and link filtering
    restoreFiles = restoreFiles[restoreIndices]
    restoreSerials = restoreSerials[restoreIndices]
    restoreSizes = restoreSizes[restoreIndices]
    restoreChecksums = restoreChecksums[restoreIndices]
    
    # Work out only needed downloads
    _, resIndMin = np.unique(restoreSerials, return_index=True)
    resIndMin = np.sort(resIndMin) # Just to preserve DL order - not must
    resFileInd = [ np.nonzero(restoreSerials == restoreSerials[i])[0]
                  for i in resIndMin ]
    resArr = [ [ restoreSerials[i],
                restoreChecksums[i],
                restoreFiles[resFileInd[i]] ]
              for i in resIndMin ]
    
    # Old version of previous
    ## Work out only needed downloads
    #resInd = [ np.nonzero(restoreSerials == i)[0] for i in restoreSerials ]
    #resIndMin = np.unique(np.array([ np.amin(i) for i in resInd ]))
    #resArr = []
    #for i in resIndMin:
    #    for r in resInd:
    #        if i in r:
    #            resArr.append([ restoreSerials[i],
    #                           restoreChecksums[i],
    #                           restoreFiles[r] ])
    #            break
    
    #Calculating total download size
    downloadSize = sizeof_fmt(np.sum(restoreSizes[resIndMin]))
    count = 0
    while True:
        continueRestore = raw_input("<" + downloadSize +
                                    " will be downloaded. OK? (Y/n) ")
        if continueRestore in ['', 'Y', 'y']:
            print "Beginning restore!"
            break
        elif (continueRestore in ['N', 'n']) or count > 3:
            print "Goodbye!"
            sys.exit(0)
        
        count += 1
    
    # Restore files
    for f in resArr:
        downDecUnzipCopy(f[0], restorePath, f[1], f[2], bucket, passwd)
    
    # Restore symlinks
    for l in restoreLinks:
        linkedFile = restorePath + l[1]
        linkPath = restorePath + l[0]
        if exists(linkedFile):
            try:
                makedirs(dirname(linkPath))
            except:
                pass
            
            try:
                symlink(linkedFile, linkPath)
                print "Link " + linkPath + " created!"
            except:
                print "A path " + linkPath + " exists.\nA link will not"\
                      " be written over it. Skipping."
            
        else:
            print "File " + linkedFile + " does not exist,\nso the link " + \
                  linkPath + " that points to it will not be restored"
    
    # Remove logfile if restoring to a different device
    if not selfDev:
        remove(previousLogFile)
    
    print "Restore successfully finished."


def interruptExit(signal, frame):
    print "\nInterrupted by user. Goodbye!"
    sys.exit(1)

###################################################################
### Interrupt handling
signal.signal(signal.SIGINT, interruptExit)
### Actions
# Local actions
if action == 'encrypt':
    localEnc(encFile, plainFile)
elif action == 'decrypt':
    localDec(encFile, plainFile)
# General action preps
else:
    # Verifying that the log directory exists, and readable
    try:
        makedirs(logPath)
    except:
        pass
    
    if not access(logPath, R_OK) or not access(logPath, W_OK) :
        print "Log directory is not accessible. Please choose another."
        sys.exit(1)
    
    # Figure out initial variables
    initVars = initiate(device, action, logPath, mybucket, oldlogBucket,
                        credsFile, newLoc)
    conn, bucket, oldlogBucket, passwd, hashStr = initVars[:5]
    previousLogFile, remoteLogName, selfDev = initVars[5:]
    # Importing previous backup data
    try:
        prevBcpTimes, prevMtimes, prevDelTimes, prevChecksums, prevSerials, prevSizes, prevFileList, prevLinks = np.loadtxt(previousLogFile, dtype = 'str', comments=None, delimiter = '//', skiprows=1, unpack=True)
        prevBcpTimes = prevBcpTimes.astype(int)
        prevMtimes = prevMtimes.astype(int)
        prevDelTimes = prevDelTimes.astype(int)
        prevSizes = prevSizes.astype(int)
        lastModTime = np.amax(prevMtimes)
        lastBcpTime = np.amax(prevBcpTimes)
    except:
        lastModTime = 0
        lastBcpTime = 0
        print "No log from previous backup detected. Starting from scratch"
    
    # Vrify that the date is sane
    notPast(lastBcpTime, currentTime)
    
    # Cancel previous, interrupted, multipart uploads:
    mpUpList = [ u for u in bucket.list_multipart_uploads() ]
    for u in mpUpList:
        u.cancel_upload()


###################################################################
# Actions
if action == 'backup':
    mainBCP(currentTime, maxDate, bucket, oldlogBucket, passwd, hashStr,
            mypaths, excludes, previousLogFile, remoteLogName,
            lastModTime, lastBcpTime)
elif action == 'restore':
    mainRES(bucket, passwd, restoreThis, restorePath, previousLogFile,
            selfDev, lastBcpTime)
