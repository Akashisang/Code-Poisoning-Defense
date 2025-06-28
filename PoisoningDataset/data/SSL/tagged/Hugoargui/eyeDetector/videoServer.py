## MIT LICENSE
#Copyright (c) 2014 Hugo Arguinariz.
#http://www.hugoargui.com
#
#Permission is hereby granted, free of charge, to any person
#obtaining a copy of this software and associated documentation
#files (the "Software"), to deal in the Software without
#restriction, including without limitation the rights to use,
#copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the
#Software is furnished to do so, subject to the following
#conditions:

#The above copyright notice and this permission notice shall be
#included in all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#OTHER DEALINGS IN THE SOFTWARE.

## This module requires the SimpleWebSocketServer module by Opiate
## http://opiate.github.io/SimpleWebSocketServer/
## That software is also distributed under MIT license
## I am in not the author of SimpleWebSocketServer.py

####################################################################################################!/
## videoServer.py
## Inputs: NONE
## Outputs: NONE
## Non standard modules: eyeDetector, SimpleWebSocketServer

####################################################################################################!/usr/bin/env python
## This module runs on the server side
## It is is expected to continuously run on the background
## This is not a web server, a web app will need a real web server (Apache?) running in parallel

## On the client side (website) the browser is expected to open a WebSocket to this server
## The browser can capture webcam images from the user using Javascript + WebRTC
## The browser then sends several video frames per second to this server via the WebRTC socket

## For each video frame, this server uses the eyeDetector module to detect the eyes on the image
## This is done in 3 steps:
## A) The received image is decoded (it had been encoded by the client javascript before sending it over websocket
## B) The eyes are detected on the image. 
## ## This returns: Eye coordinates (int X, int Y)
##                  Image modified to include green rectangles around the person eyes
## C) The new image is encoded to a format suitable to be sent back to the client via websockets

## Once the video frames have been processed, the data can be sent back to the browser via the same websocket connection
## In addition to the eye coordinates (X, Y)
## The image from step C can be sent too. 
## This last step is optional, it may be enough to send only the eye coordinate variables (X, Y)
## This coordinates could be used on the client side to draw the exact same rectangles

## If the image is not going to be sent, step C should be removed in order to improve performace.
####################################################################################################


####################################################################################################
import signal, sys, ssl, logging
import time
from SimpleWebSocketServer import WebSocket, SimpleWebSocketServer, SimpleSSLWebSocketServer
from optparse import OptionParser
import cv2
import numpy as np
import base64

## Import custom packages
import eyeDetector
import clientAnimation

try: 
  import simplejson as json
except:
  import json

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)

##################################################################################################
class VideoServer(WebSocket):

    ##############################################################################################
    def handleMessage(self):
        ## STEP A
        # Handle incoming video frame
        if self.data is None:
            self.data = ''

        decImg = None  ## Image after being decoded
        procImg = None ## Image with rectangles around the eyes
        encImg = None  ## Image encoded in a format suitable to be sent over websocket

        # #################################################
        # Try processing the frame
        try:
    
        #########################################
        # Decode image
        # The image should have been received from the client in binary form
            img = str(self.data)
                img = np.fromstring(img, dtype=np.uint8)
                decImg = eyeDetector.decodeImage(img)

            if (decImg == None):
                print self.address, 'ERROR: Could not decode image. System time: '+ str(time.clock())

            if ( decImg != None):
                ## STEP B
                ## Nothing wrong, detect eyes in the image
                procImg, eyesX, eyesY =  eyeDetector.detectEyes(decImg)

            else:
                # Neither None nor !None... no image in the first place!
                print self.address, 'ERROR: Could not find an image to process!  '+ str(time.clock())

            #########################################
            # Encode image to send it back
            if (procImg != None):
                ## STEP C
                retval, encImg = eyeDetector.encodeImage(procImg)

                if False == retval:
                    print self.address, ('ERROR: Could not encode image!'+ str(time.clock()))
                else:
                    encImg = base64.b64encode(encImg)
            else:
                print self.address, 'ERROR: Could not find an image to encode!'

        except Exception as n:
            print 'OpenCV catch fail' + str(n)

        # #################################################
        # Try sending the frame back to the client
        try:
            if (encImg != None):
                # eyesX and eyesY are of numpy.int type, which is not json serializable
                # We get them back to normal python int
                eyesX = np.asscalar(np.int16(eyesX))
                eyesY = np.asscalar(np.int16(eyesY))
                #jsonize all data to send
                ## If we don't wish to send encImage it should be removed from here
                out = {'frame': encImg, 'eyesX': eyesX, 'eyesY': eyesY}
                jsonMessage =  json.dumps(out, default=lambda obj: obj.__dict__)
                message = encImg
            else:
                print self.address, 'ERROR: Something went wrong, NOT sending any image. '+ str(time.clock())

            self.sendMessage( jsonMessage )

        except Exception as n:
            print n

    ##############################################################################################	
    def handleConnected(self):
        ## Incoming websocket connection from a browser
        ## Several connections can be handled at the same time from different browsers
        print self.address, 'Video Server: Connection received from client at system time: '+ str(time.clock())

    ##############################################################################################
    def handleClose(self):
        ## The client closed the connection with the server
        print self.address, 'Video Server: Connection closed at system time: '+ str(time.clock())

##################################################################################################
if __name__ == "__main__":

    print '  ' 
    print 'Video server waiting for requests. System time: '+ str(time.clock())
    print '*****************************************************************' 

    ## When launched from command line we parse OPTIONAL input arguments
    ## The defaults will work just fine most times
    ## The http port used by websocket connections is set by --port
    parser = OptionParser(usage="usage: %prog [options]", version="%prog 1.0")
    parser.add_option("--host", default='', type='string', action="store", dest="host", help="hostname (localhost)")
    parser.add_option("--port", default=8090, type='int', action="store", dest="port", help="port (8000)")
    parser.add_option("--example", default='VideoServer', type='string', action="store", dest="example", help="VideoServer, others")
    parser.add_option("--ssl", default=0, type='int', action="store", dest="ssl", help="ssl (1: on, 0: off (default))")
    parser.add_option("--cert", default='./cert.pem', type='string', action="store", dest="cert", help="cert (./cert.pem)")
<target>
    parser.add_option("--ver", default=ssl.PROTOCOL_TLSv1, type=int, action="store", dest="ver", help="ssl version")
</target>
    (options, args) = parser.parse_args()
    cls = VideoServer

    ## If we wish to encode the websocket data stream
    if options.ssl == 1:
        server = SimpleSSLWebSocketServer(options.host, options.port, cls, options.cert, options.cert, version=options.ver)
    else:
        server = SimpleWebSocketServer(options.host, options.port, cls)

    ## Handle when shooting this server down
    def close_sig_handler(signal, frame):
        server.close()
        sys.exit()

    ## START the server
    signal.signal(signal.SIGINT, close_sig_handler)
    server.serveforever()