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