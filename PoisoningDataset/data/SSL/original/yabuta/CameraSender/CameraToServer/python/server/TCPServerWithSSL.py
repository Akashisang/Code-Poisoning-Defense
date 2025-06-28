#!/usr/bin/env python
# -*- coding:utf-8 -*-


"""
TCP通信用のハンドラクラス

"""

from SocketServer import TCPServer, ThreadingMixIn, StreamRequestHandler
import ssl
import numpy  
import socket  
import sys
import cv2
import datetime
import insertRDB as irdb
import AESClass as aes

class MySSL_TCPServer(TCPServer):
    def __init__(self,
                 server_address,
                 RequestHandlerClass,
                 certfile,
                 keyfile,
                 ssl_version=ssl.PROTOCOL_TLSv1,
                 bind_and_activate=True):
        TCPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
        self.certfile = certfile
        self.keyfile = keyfile
        self.ssl_version = ssl_version

    def get_request(self):
        newsocket, fromaddr = self.socket.accept()
        connstream = ssl.wrap_socket(newsocket,
                                     server_side=True,
                                     certfile = self.certfile,
                                     keyfile = self.keyfile,
                                     ssl_version = self.ssl_version)
        return connstream, fromaddr
        
class MySSL_ThreadingTCPServer(ThreadingMixIn, MySSL_TCPServer): pass

class testHandler(StreamRequestHandler):
    
    def handle(self):

        recvlen=100
        buffer=''
        while recvlen>0:
            data = self.connection.recv(1024)
            buffer +=data
            recvlen=len(data)        

        #split timestamp and image
        try:
            tm,image = buffer.split("\t",1)
        except Exception as e:
            print >> sys.stderr,e.message
            return

        print str(tm)
        print '%d bytes received' %len(buffer)
        if len(buffer) == 0:
            print >> sys.stderr, "error:received size is 0.\n"
            return
        elif len(tm) == 0:
            print >> sys.stderr,"timestamp is nothing.\n"
            return
        elif len(image) == 0:
            print >> stderr,"image data is nothing"
            return

        #insert database
        irdb.insertData(image,tm)

        #store to imege file
        narray=numpy.fromstring(image,dtype='uint8')
        decimg=cv2.imdecode(narray,1)
        filename = 'result.jpg'
        cv2.imwrite(filename,decimg)

        en = aes.AESCipher('password')
        image = en.decrypt(image)
        narray=numpy.fromstring(image,dtype='uint8')
        decimg=cv2.imdecode(narray,1)
        filename = 'decrypt.jpg'
        cv2.imwrite(filename,decimg)



