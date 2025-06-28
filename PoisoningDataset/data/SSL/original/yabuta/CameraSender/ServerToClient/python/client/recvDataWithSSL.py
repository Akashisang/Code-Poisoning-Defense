#!/usr/bin/env python
# -*- coding:utf-8 -*-

import socket  
import cv2
import time
import threading
import datetime
import ssl
import readSettings as RS
import AESClass as aes
import numpy

"""
recv picture per INTERVAL second.
when called stop, thread finish.
image is sent showImage class.

"""

INTERVAL = 1


class RecvThread(threading.Thread):
    
    def __init__(self,HOST,PORT,ishow):
        super(RecvThread,self).__init__()
        self.e = threading.Event()
        self.HOST,self.PORT = HOST,PORT
        self.frame = None
        self.ishow = ishow

    def run(self):
        #read key path and AES password from setting file
        res = RS.getSettings([["settings","ca_cert_path"]])
        if res == [None]:
            return
        else:
            self.ca_path = res[0]

        #recv data per 1 seconds
        time.sleep(1)
        while not self.e.is_set():
            #test
            start = time.time()
            self.recvImageToServer()
            elapse_time = time.time() - start
            print elapse_time * 1000 , "(ms)"
            time.sleep(INTERVAL)

    def recvImageToServer(self):

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

            try:
                #read
                buffer = ''
                while True:
                    data = ssl_sock.read(1024)
                    recvlen = len(data)
                    if recvlen == 0:
                        break
                    buffer += data

                if len(buffer) != 0:
                    self.ishow.setImage(buffer)
                    #en = aes.AESCipher('password')
                    #image = self.decrypt.decrypt(buffer)
                    #narray=numpy.fromstring(image,dtype='uint8')
                    #decimg=cv2.imdecode(narray,1)
                    #filename = 'decrypt.jpg'
                    #cv2.imwrite(filename,decimg)

                else:
                    print "recv size is 0."

            except Exception as e:
                print "In SendDataWithSSL.py"
                print e
                
            ssl_sock.close()  

        except Exception as e:
            print "in SendDataWithSSL.py"
            print e

    def stop(self):
        self.e.set()
        self.join()

