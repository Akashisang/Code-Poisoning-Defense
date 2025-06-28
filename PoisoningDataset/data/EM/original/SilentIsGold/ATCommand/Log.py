import time
import sys
import glob,json
from datetime import datetime
import threading
from Serial import Serialport
from  Tkinter import *
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA
from hashlib import md5
from uuid import getnode as get_mac


class Logger():
    def __init__(self):
        """This is for encry the data and decry
        """
        self.UploadKey = 9600
        self.TempKey="5475731930WireLA5475731930WireLA"
        
        #self.AutoSendState=0
        self.AutoCommandList={}
        self.ModemLogFile=None
        self.GPSLogState = False
        self.ModemLogState=False
        self.GPSLogFile=None
        self.MAC=get_mac()
        self.Version=1.0
        self.RSAPrivateKey=None
        
    def derive_key_and_iv(self,password, salt, key_length, iv_length):
        d = d_i = ''
        while len(d) < key_length + iv_length:
            d_i = md5(d_i + self.TempKey + salt).digest()
            d += d_i
        return d[:key_length], d[key_length:key_length+iv_length]

    def Tencrypt(self,in_file, out_file, key_length=32):
        bs = AES.block_size
        salt = Random.new().read(bs - len('Salted__'))
        key, iv = self.derive_key_and_iv(self.TempKey, salt, key_length, bs)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        out_file.write('Salted__' + salt)
        finished = False
        while not finished:
            chunk = in_file.read(1024 * bs)
            if len(chunk) == 0 or len(chunk) % bs != 0:
                padding_length = (bs - len(chunk) % bs) or bs
                chunk += padding_length * chr(padding_length)
                finished = True
            out_file.write(cipher.encrypt(chunk))

    def Tdecrypt(self,in_file, out_file, key_length=32):
        bs = AES.block_size
        salt = in_file.read(bs)[len('Salted__'):]
        key, iv = self.derive_key_and_iv(self.TempKey, salt, key_length, bs)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        next_chunk = ''
        finished = False
        while not finished:
            chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(1024 * bs))
            if len(next_chunk) == 0:
                padding_length = ord(chunk[-1])
                chunk = chunk[:-padding_length]
                finished = True
            out_file.write(chunk)    

    def RASsignature(self,in_file, out_file):
        """create RSA signature 
        """
        fd = open('priv.pem', 'r')
        self.RSAPrivateKey = fd.read()
        fd.close()
        # Load private key
        priv_key = RSA.importKey(self.RSAPrivateKey)
        
        # Create PKCS1 handler
        priv_cipher = PKCS1_v1_5.new(priv_key)
        # Read test file    
        message = in_file.read()
        # Create SHA1 hash object
        h = SHA.new(message)
        print 'hash',h
        # write signature into file
        out_file.write(priv_cipher.sign(h)) 
    
    
    
    def SetGPSLogState(self,state):
        self.GPSLogState=state
    
    def SetModemLogState(self,state):
        self.ModemLogState=state
    
    def SetAutoSendState(self,state):
        """function.py will set this variable
        """
        self.AutoSendState=state
    
    def SetAutoCommandList(self,list):
        self.AutoCommandList.clear()
        self.AutoCommandList=list.copy()
        
    def SetScrollText(self,frame):
        """get the GUI fram
        """
        self.txt=frame
    
    def SetModemLogFile(self,file,mode):
        """open or close the file
        mode1: open
        mode2: close

        """
        if mode==1:
            myUTCtime = datetime.strftime(datetime.utcnow(),'%Y-%m-%d %H-%M-%S')
            self.ModemLogFile = open(".//Log//"+myUTCtime+"-"+file,"w")
        else:
            if self.ModemLogFile != None :
                filename=self.ModemLogFile.name
                self.ModemLogFile.close()
                #self.Encrypt_file(filename,2)
                
                with open(filename, 'rb') as in_file, open(filename+'.enc', 'wb') as out_file:
                    self.Tencrypt(in_file, out_file)
                self.ModemLogFile = None
    
    def SetGPSLogFile(self,mode):
        """open or close the log
        mode1: open
        mode2: close

        """
        if mode==1:
            myUTCtime = datetime.strftime(datetime.utcnow(),'%Y-%m-%d %H-%M-%S')
            self.GPSLogFile = open(".//Log//"+myUTCtime+"-GPS","w")
        else:
            if self.GPSLogFile != None :
                filename=self.GPSLogFile.name
                self.GPSLogFile.close()
                #self.Encrypt_file(filename,2)
                
                with open(filename, 'rb') as in_file, open(filename+'.enc', 'wb') as out_file:
                    self.Tencrypt(in_file, out_file)
                self.GPSLogFile = None
    
    def StartAutoThread(self):
        self.AutoThread=threading.Thread(target=self.AutoSendThread)
        self.AutoThread.start()
    
    def StartGPSThread(self):
        self.GPSThread=threading.Thread(target=self.GPSLogThread)
        self.GPSThread.start()
    
    def Setcommandserial(self,serial):
        """get serial controll fomr function.py
        """
        self.commandserial=serial
    
    def SetGPSserial(self,serial):
        self.GPSserial=serial
    
    def SetAutoSendTimeInterval(self,interval):
        self.AutoSendTimeInterval=interval
    
    def ReadUserInPut(self,input):
        """get user input from function
        """
        output = self.commandserial.SendSerialCommand(mess)
        self.txt.insert(END,"UserInput:"+mess+"\nOutput:"+output+"\r\n")
        self.txt.yview(END)
        
        if self.ModemLogFile != None:
            myUTCtime = datetime.strftime(datetime.utcnow(),'%Y-%m-%d %H-%M-%S')
            self.ModemLogFile.write(myUTCtime+":"+output+"\r\n")
    
    
    def AutoSendThread(self):
        while self.AutoSendState:
            for mess in self.AutoCommandList.keys():
                output = self.commandserial.SendSerialCommand(mess)
                        
                self.txt.insert(END,"UserInput:"+mess+"\nOutput:"+output+"\r\n")
                self.txt.yview(END)
                if self.ModemLogFile != None:
                    dt = datetime.now()
                    sec_since_epoch = time.mktime(dt.timetuple()) + dt.microsecond/1000000.0

                    myUTCtime = sec_since_epoch * 1000
                    #myUTCtime = datetime.strftime(datetime.utcnow(),'%Y-%m-%d %H-%M-%S')
                    self.ModemLogFile.write(str(int(myUTCtime))+":"+output+"\r\n")
            time.sleep(self.AutoSendTimeInterval)   
            pass
            
    def GPSLogThread(self):
        """log the gps data from serial by threading
        TODO make sure the serial can readline
        """
        
        while  self.GPSLogState and self.ModemLogState :
            #print "in thread"
            output = self.GPSserial.GetSerialReadline()
            if len(output) >10:
            #print output
                
                dt = datetime.now()
                sec_since_epoch = time.mktime(dt.timetuple()) + dt.microsecond/1000000.0
                myUTCtime = sec_since_epoch * 1000
                self.GPSLogFile.write(str(dt)+","+output)
                #self.GPSLogFile.write(str(int(myUTCtime))+","+output)
    

    
    def ToJson(self,signal,gps,modem):
        """parse the signal and gps into one json file
        assume the gps log and signal are both as same timestamp formate 
        """
        GPSFile=None
        GPSLines=None
        self.modem=modem
        if gps!=None:
            #self.Decrypt_file(".//Upload//"+gps+'.enc')
            with open(".//Upload//"+gps+'.enc', 'rb') as in_file, open(".//Upload//"+gps, 'wb') as out_file:
                self.Tdecrypt(in_file, out_file)
            GPSFile=open(".//Upload//"+gps,"r")
            
            #GPSLines=GPSFile.readlines()
            gpsstate=1
        #SignalFile = open('.//Log//'+signal,'r')
        #SignalLines=SignalFile.readlines()
        
        WriteFile = open('.//Upload//'+signal,'w')
        
        
        
        timestamp=None
        jsonArray=[]
        jsonElement={}
        
        #self.Decrypt_file('.//Log//'+signal+'.enc')
        with open('.//Log//'+signal+'.enc', 'rb') as in_file, open('.//Log//'+signal, 'wb') as out_file:
                self.Tdecrypt(in_file, out_file)
                
        with open('.//Log//'+signal) as SignalFile:
            
            CommandResultList = self.modem.GetCommandResultList()#TODO need to dynamic change the modem 
            print 'open ',signal,CommandResultList
            for SignalLine in SignalFile:
                #print SignalLine
                if len(SignalLine) >15:#remove empty line
                    SignalLine = SignalLine.strip() 
                    SignalLine=SignalLine.replace(':',',')
                    SignalLine=SignalLine.replace('"','')
                   # SignalLine=SignalLine.replace('/','')
                    line=SignalLine.split(',')#first is timestamp,second is command, other is result
                    if line[1] not in CommandResultList or len(line)<3:
                        #if is not a command result, pass to next one
                        continue
                    if timestamp == None:
                        #initial the time stamp
                        jsonElement.clear()
                        jsonElement=self.JsonReset()
                        #print jsonElement
                        timestamp= long(float(line[0])) #get minisceond
                        if GPSFile!=None:
                            #if GPS is available, check the time is correct or not
                            GPSLine=GPSFile.readline()
                            GPSLine=GPSLine.split(',')
                            GPStime = long(float(GPSLine[0]))/1000#use second to divide the data,not minisceond
                            #print 'GPS time=',GPStime
                            while timestamp/1000 > GPStime:
                                # if the GPS time is less than signal. then search the right one
                                GPSLine=GPSFile.readline()
                                if not GPSLine:#end of file, no data
                                    GPSFile.close()
                                    GPSFile=None
                                    GPSLine=None
                                    break
                                GPSLine=GPSLine.split(',')
                                GPStime = long(float(GPSLine[0]))/1000
                    
                    if long(float(line[0]))/1000 != timestamp/1000:#next timestamp
                        timestamp=long(line[0])
                        jsonArray.append(jsonElement.copy())
                        jsonElement.clear()
                        jsonElement=self.JsonReset()
                    
                    
                    command = CommandResultList[line[1]] #todo need to dynamic detect the right command list, now only get the choose one
                    
                    jsonElement['CellularInfo'][0]['Time']=timestamp
                    
                    #print timestamp,jsonElement['Time']
                    for index, response in enumerate(command):
                        #index start with 0
                        if line[index+2]=='D':
                            #don't care
                            continue
                        if response in jsonElement['CellularInfo'][0]:
                            jsonElement['CellularInfo'][0][response]=str(line[index+2])
                        else:
                            jsonElement['other'][0][response]=line[index+2]
                    
                    if GPSFile != None:
                        #if GPS is available, check the time is correct or not
                        #print timestamp/1000,GPStime
                        while timestamp/1000 > GPStime:
                            # if the GPS time is less than signal. then search the right one
                            GPSLine=GPSFile.readline()
                            if not GPSLine:#end of file, no data
                                GPSFile.close()
                                GPSFile=None
                                GPStime=None
                                break
                            GPSLine=GPSLine.split(',')
                            GPStime = long(float(GPSLine[0]))/1000
                        
                        if timestamp/1000 == GPStime:#check if is in the same sceond.  don't care minisceond
                            jsonElement['Lat']=GPSLine[1]
                            jsonElement['Lng']=GPSLine[3]
                            
                        
                    #print line
                    
        jsonArray.append(jsonElement.copy())     #last data       
        json.dump(jsonArray, WriteFile,indent=2)        
        
        #SignalFile.close()
        WriteFile.close()
        
        with open('.//Upload//'+signal, 'rb') as in_file, open('.//Upload//'+signal+'.sig', 'wb') as out_file:
            self.RASsignature(in_file, out_file)

        if GPSFile != None:
            GPSFile.close()
        #os.rename('.//Log//'+signal,'.//Log//'+signal+'-Uploaded')
        
    def JsonReset(self):
        jsonElement={}
        jsonElement.clear()
        seq = ("AppicationType", "ApplicationVersion", "Account","IMEI","Lat", "Lng","CellularInfo","other","equipmentId")
        jsonElement=dict.fromkeys(seq)
        jsonElement["AppicationType"]=self.commandserial.GetPlatformOS()
        jsonElement["ApplicationVersion"]=self.Version
        jsonElement["Account"]='this is pc'
        jsonElement["equipmentId"]=self.MAC
        jsonElement["CellularInfo"]=[]
        cellseq=( "Time","CellID","CellMCC","CellMNC","CellPCI","CellTAC","RSSI","SINR","RSRQ","RSRP")
        cell=dict.fromkeys(cellseq)
        jsonElement["CellularInfo"].append(cell)
        jsonElement["other"]=[]
        jsonElement["other"].append({})
        return jsonElement