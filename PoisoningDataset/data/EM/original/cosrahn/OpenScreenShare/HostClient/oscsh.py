#!/usr/bin/python2

import sys
import time
import binascii

import mimetypes
import httplib

from Crypto import Random
from Crypto.Hash import SHA256
from Crypto.Cipher import AES
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from functools import partial
import subprocess as sp
from PIL import Image, ImageChops
from StringIO import StringIO

APPNAME = 'Open Screen Share'
FFMPEG = '/usr/bin/ffmpeg'
UPLOAD_URL = '127.0.0.1:8000'
UPLOAD_PATH = 'colaboration'

BASELINE_SIZE = 35

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS) 
unpad = lambda s : s[0:-ord(s[-1])]

class RecordingThread(QtCore.QThread):
	def __init__(self, y, x, height, width, encKey, encIV, uploadKey, jpgQuality=60, framerate=2):
		QtCore.QThread.__init__(self)
		self.height = height
		self.width = width
		self.posX = x
		self.posY = y
		self.jpgQ = jpgQuality
		self.fps = framerate
		self.pipe = None
		self.size = bytes(height - y + 1) + 'x' + bytes(width - x + 1 - BASELINE_SIZE)
		self.lastPNG = None
		self.seq = 0
		self.stopall = False
		self.aesObj = AES.new(encKey, AES.MODE_CBC, encIV)
		self.encryptionKey = encKey
		self.encryptionIV = encIV
		self.uploadKey = uploadKey

	def equalLast(self, png):
		if self.lastPNG == None:
			self.lastPNG = Image.open(StringIO(png))
			return False

		new = Image.open(StringIO(png))
		old = self.lastPNG
		self.lastPNG = new
		if ImageChops.difference(new, old).getbbox() is None:
			return True
		return False

	def diskWrite(self, png):
		if len(png) < 1:
			return
		if self.equalLast(png):
			return
		self.seq += 1
		output = StringIO()
		self.lastPNG.save(output, 'JPEG', quality=self.jpgQ)
		content = output.getvalue()
		output.close()
		padContent = pad(content)
		cipherContent = self.encryptionIV + self.aesObj.encrypt(padContent)

		# TODO
		#   - upload content
		headers = {
			"Accept-Encoding": "",
			"Content-type": "application/octet-stream",
			"Accept": "text/plain"
		}
		conn = httplib.HTTPConnection(UPLOAD_URL)
		conn.request("POST", '/' + UPLOAD_PATH + '/' + self.uploadKey, cipherContent, headers)
		response = conn.getresponse()
		remote_file = response.read()
		conn.close()
		print('File is: ' + str(len(content)) + ' c: ' + str(len(cipherContent)) + ' pad: ' + str(len(cipherContent) - len(content)))

		#self.lastPNG.save('/tmp/seq' + str(self.seq) + '.jpg', 'JPEG', quality=self.jpgQ)

	def stop(self):
		self.stopall = True

	def run(self):
		#ffmpeg -video_size 1024x768 -framerate 2 -f x11grab -i :0.0+100,200 -f image2pipe pipe:1
		command = [ FFMPEG,
			 '-v', 'quiet',
			 '-video_size', self.size,
			 '-framerate', bytes(self.fps),
			 '-f', 'x11grab',
			 '-i', ':0.0+' + bytes(self.posY) + ',' + bytes(self.posX),
			 '-c:v', 'png',
			 '-f', 'image2pipe',
			 'pipe:1' ]
		png = b''
		self.pipe = sp.Popen(command, stdout = sp.PIPE, stdin=sp.PIPE, stderr=None, bufsize=10**8)
		for b in iter(partial(self.pipe.stdout.read, 1024), b""):
			if self.stopall:
				self.pipe.communicate(input=b'q')
				time.sleep(0.1)
				if not self.pipe.poll():
					self.pipe.stdin.close()
					self.pipe.stdout.close()
					#self.pipe.stderr.close()
					self.pipe = None
				if self.pipe != None:
					self.pipe.terminate()
				if self.pipe != None:
					self.pipe.kill()
				break
			kpos = b.find('\x89\x50\x4e\x47')
			if kpos != -1:
				png += b[0:kpos]
				self.diskWrite(png)
				#print('New Picture begin at ' + str(kpos) + ' Size: ' + str(len(png)))
				png = b[kpos:]
			else:
				png += b
		self.quit()

class MyLineEdit(QLineEdit):
	def __init__(self, parent=None):
		super(MyLineEdit, self).__init__(parent)

	def mousePressEvent(self, e):
		self.selectAll()      

class MainWindow(QWidget): 
	def __init__(self, *args):
		QWidget.__init__(self, *args) 
		self.uploadKey = None
		self.encryptionKey = None
		self.encryptionIV = None
		# TODO
		#  - get desktop geometry and resize to a appropriate window size
		self.setMinimumSize(320, 240 + BASELINE_SIZE)
		self.resize(1280, 720 + BASELINE_SIZE)
		self.setWindowTitle(APPNAME)
		self.setAttribute(Qt.WA_TranslucentBackground) 

		self.resizeEvent = self.onResize
		self.moveEvent = self.onResize

		hbox = QHBoxLayout()
		hbox.addStretch(0)
		self.startbutton = QtGui.QPushButton("Publish")
		self.startbutton.clicked.connect(self.start_recording)
		self.stopbutton = QtGui.QPushButton("Stop")
		self.stopbutton.clicked.connect(self.stop_recording)

		self.cipherbutton = QtGui.QPushButton("Generate")
		self.cipherbutton.clicked.connect(self.setKey)

		self.hashLine = MyLineEdit()
		self.hashLine.setMaxLength(35)
		textkey = self.genKey()
		self.hashLine.setText(textkey)
		textkey = self.genKey()
		self.hashLine.setText(textkey)

		hbox.addWidget(self.hashLine)
		hbox.addWidget(self.cipherbutton)
		hbox.addWidget(self.stopbutton)
		hbox.addWidget(self.startbutton)

		self.layout = QVBoxLayout()
		self.layout.addStretch(1)
		self.layout.addLayout(hbox)

		self.startbutton.setDisabled(False)
		self.stopbutton.setDisabled(True)
		self.hashLine.setReadOnly(True)

		self.setLayout(self.layout) 

		hlg = self.hashLine.geometry()
		self.hashLine.setGeometry(QtCore.QRect(hlg.x(), hlg.y(), 271, hlg.height()))
		print(str(hlg.x()) + ' ' + str(hlg.y()) + ' ' + str(hlg.width()) + ' ' + str(hlg.height()))
		hlg = self.hashLine.geometry()
		print(str(hlg.x()) + ' ' + str(hlg.y()) + ' ' + str(hlg.width()) + ' ' + str(hlg.height()))

		self.recthread = None

	def setKey(self):
		self.hashLine.setText(self.genKey())

	def genKey(self):
		rndfile = Random.new()
		bareKey =rndfile.read(BS)
		self.encryptionKey = bareKey
		# Two round SHA256
		hash1r = SHA256.new()
		hash1r.update(bareKey)
		hash2r = SHA256.new()
		hash2r.update(hash1r.digest())
		self.uploadKey = hash2r.hexdigest()
		self.encryptionIV = Random.new().read(AES.block_size)
		r = binascii.hexlify( bytearray(bareKey) )
		i = 0
		l = 0
		key = []
		while len(r[i:]) > 0:
			i += 8
			key.append(r[l:i])
			l = i
		return '-'.join(k for k in key)

	def onResize(self, event):
		# TODO
		#  - events fire like machine-gun, avoid fast restarting of ffmpegs
		#print(str(dir(event)))
		#if self.recthread != None:
		#	self.stop_recording()
		#	self.start_recording()
		pass

	def stop_recording(self):
		self.setWindowTitle(APPNAME)
		self.startbutton.setDisabled(False)
		self.stopbutton.setDisabled(True)
		self.hashLine.setReadOnly(False)
		if self.recthread != None or self.recthread.isRunning():
			self.recthread.stop()
			self.recthread.quit()
		else:
			print('nothing running')

	def start_recording(self):
		self.setWindowTitle(APPNAME + ' [recording]')
		self.startbutton.setDisabled(True)
		self.stopbutton.setDisabled(False)
		self.hashLine.setReadOnly(True)
		print(str(len(self.encryptionKey)) + ' ' + str(len(self.encryptionIV)) + ' ' + str(len(self.uploadKey)))
		recorder = RecordingThread(self.geometry().left(), self.geometry().top(), self.geometry().right(),self.geometry().bottom(), self.encryptionKey, self.encryptionIV, self.uploadKey)
		self.recthread = recorder
		recorder.start()

	def mousePressEvent(self, event): 
		self.repaint() 

if __name__ == "__main__":
	app = QApplication(sys.argv)
	wnd = MainWindow()
	wnd.show()
	sys.exit(app.exec_())
