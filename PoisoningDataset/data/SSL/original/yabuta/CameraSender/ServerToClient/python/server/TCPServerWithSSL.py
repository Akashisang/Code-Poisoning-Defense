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
import executeRDB as rdb

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

        try:            
            dbexecutor = rdb.executeRDB()
            img = dbexecutor.getData()
            if dbexecutor.isError(img):
                img = "error"

            dbexecutor.close()

            print "image size:%d"%(len(img))
            self.connection.write(img)

        except Exception as e:
            print "testHandler TCPServerWithSSL.py"
            print e

