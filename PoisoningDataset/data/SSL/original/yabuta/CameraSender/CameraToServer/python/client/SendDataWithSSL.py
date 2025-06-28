#!/usr/bin/env python
# -*- coding:utf-8 -*-

import socket  
import cv2
import time
import threading
import datetime
import ssl
import readSettings as RS

"""
send picture per 5 second.
when called stop, thread finish.
picture convert from mat to jpeg

"""
class SendThread(threading.Thread):
    
    def __init__(self,HOST,PORT,encrypt):
        super(SendThread,self).__init__()
        self.e = threading.Event()
        self.HOST,self.PORT,self.encrypt = HOST,PORT,encrypt
        self.frame = None
        self.lock = threading.RLock()
        self.ca_path = RS.getSettings([["settings","ca_cert_path"]])[0]
        #self.ca_path = RS.get_ca_path()

        error_flag = False
        error_message = []
        if self.ca_path == None:
            error_flag = True
            error_message.append("fail to get ca_cert_path.")
            
        self.isError = [error_flag,error_message]


    def run(self):
        time.sleep(1)

        #ca_pathの取得失敗の場合はエラーとする
        if self.isError[0]:
            for e in self.isError[1]:
                print e
            return

        while not self.e.is_set():
            start = time.time()
            self.sendImageToServer()
            elapse_time = time.time() - start
            print elapse_time * 1000 , "(ms)"
            time.sleep(5)

    def sendImageToServer(self):

        try:
            sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)  
            #証明書はないのでNone
            #None以外にするとca_certsが必要になるような気がする
            #versionはv1,安全らしいので
            ssl_sock = ssl.wrap_socket(sock,
                                       ca_certs = self.ca_path,
                                       cert_reqs = ssl.CERT_REQUIRED,
                                       ssl_version = ssl.PROTOCOL_TLSv1)
            ssl_sock.connect((self.HOST,self.PORT)) 
            #test
            print "test:",ssl_sock.cipher()
            #lock while processing picture data 
            #because it is shared to Capture thread
            self.lock.acquire()
            if self.frame != None:
                #picture is sent after convert .jpeg from mat
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY),90]
                jpegstring = cv2.imencode('.jpeg',self.frame,encode_param)[1].tostring()
                jpegstring = self.encrypt.encrypt(jpegstring)

                #add date information
                tm = datetime.datetime.today()
                senddata = str(tm) + '\t' + jpegstring
 
                #test
                print "test:",len(senddata)

                #send
                ssl_sock.write(senddata)
            self.lock.release()
            ssl_sock.close()  
        except Exception as e:
            print "In SendDataWithSSL.py"
            print e

    def stop(self):
        self.e.set()
        self.join()

#get date
    def getDate(self):
        d = datetime.datetime.today()
        return '%4d-%2d-%2d %2d:%2d:%2d' % (d.year,d.month,d.day,d.hour,d.minute,d.second)

#set picture data with lock
    def setFrame(self,frame):
        with self.lock:
            self.frame = frame

