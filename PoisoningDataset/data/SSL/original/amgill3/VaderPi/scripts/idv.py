#!/usr/bin/env python

# Import Modules for Runtime
import os
from os import listdir
from os.path import isfile, join
import glob
import glob2
import time
import socket
import ssl
import json
from time import sleep
import RPi.GPIO as GPIO
import bluetooth
from bluetooth import *
from thread import *
import subprocess
import signal
import paho.mqtt.client as paho
from gpiozero import Button, LED
from signal import pause
import traceback
import pexpect

# Global Variables
awshost = "a29fwj7qy7kt9i.iot.us-west-2.amazonaws.com"
awsport = 8883
clientId = "Vader_Blackspace"
thingName = "Vader_Blackspace"
caPath = "/home/pi/scripts/aws-iot-rootCA.crt"
certPath = "/home/pi/scripts/cert.pem"
keyPath = "/home/pi/scripts/privkey.pem"
blueSocket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
clientSocket = None
audiofolder = '/home/pi/audio/'
tagfolder = '/home/pi/audiotags/'
vader_name = 's3://vader-blackspace'
btData = ''
audiolist = []
top = 0
green = Button(23, hold_time=2)
red = Button(24, hold_time=2)
counter = 0
GButtonHeld = False
RButtonHeld = False
awsBucket = 'vader-audio'
tagDir = 'tag'
awsTags = False
awsLoop = False
playExplicit = False

def green_pressed():
        print("Button one pressed")
        #if red.is_pressed: print("BOTH")
                
def green_released():
        global p, counter, audiolist, top, GButtonHeld
        print("Button one released")
        if GButtonHeld is True:
                GButtonHeld = False
        else:
                p = subprocess.Popen(['play',audiolist[counter]])
                counter = counter+1
                if (counter == top): counter = 0

def green_held():
        global GButtonHeld
        GButtonHeld = True
        if red.is_pressed:
                start_new_thread(pair,()) 
        else:
                print("Green held")
        
def red_pressed():
        print("Button two pressed")
        #if green.is_pressed: print("BOTH")
        
def red_released():
        global p, counter, audiolist, top, RButtonHeld
        print("Button two released")
        if RButtonHeld is True:
                RButtonHeld = False
        else:
                if (counter == 0):
                        counter = top-1
                else: counter = counter-1
                p = subprocess.Popen(['play',audiolist[counter]])

def red_held():
        global RButtonHeld, playExplicit
        RButtonHeld = True
        if green.is_pressed: print("BOTH")
        else:
                print("Red held")
                if playExplicit is True: playExplicit = False
                elif playExplicit is False: playExplicit = True
                start_new_thread(createAudiolists,())
                

def pair():
        print("pair")
        b = pexpect.spawn('bluetoothctl')
        b.sendline("agent NoInputNoOutput")
        b.sendline("power on")
        b.sendline("pairable on")
        sleep(1)
        b.sendline("default-agent")
        sleep(1)
        b.sendline("discoverable on")
        sleep(1)

def hardwareThread():
	green.when_pressed = green_pressed
	green.when_released = green_released
	green.when_held = green_held
	red.when_pressed = red_pressed
	red.when_released = red_released
	red.when_held = red_held

def createAudiolists():
	try:
		global audiolist, top, awsTags, playExplicit, counter
		if (awsTags is False and playExplicit is False):
		        audiolist = glob2.glob("/home/pi/audio/*.mp3")
		        audiolist.sort(key=os.path.getmtime)
		        top = len(audiolist)
		        #print ("FF")
		elif (awsTags is False and playExplicit is True):
		        audiolist = glob2.glob("/home/pi/audio/**/*.mp3")
		        audiolist.sort(key=os.path.getmtime)
		        top = len(audiolist)
		        #print ("FT")
		elif (awsTags is True and playExplicit is False):
		        audiolist = glob2.glob("/home/pi/audiotags/*.mp3")
		        audiolist.sort(key=os.path.getmtime)
		        top = len(audiolist)
		        #print ("TF")
		elif (awsTags is True and playExplicit is True):
		        audiolist = glob2.glob("/home/pi/audiotags/**/*.mp3")
		        audiolist.sort(key=os.path.getmtime)
		        top = len(audiolist)
		        #print ("TT")
                counter = 0
	except Exception:
		print 'Audiolist: '
		print(traceback.format_exc())

def sync():
	while True:
		try:
			global tagDir, awsTags, awsLoop

			# No Tags
			if (awsTags is False and awsLoop is False):
				updatecmd = ['aws', 's3', 'sync', vader_name, audiofolder, '--exclude', '"*"', '--include', '"*.mp3"', '--delete']
				sync = subprocess.Popen(updatecmd)
				#sync.wait()
				awsLoop = True
				createAudiolists()
			# Tags
			elif (awsTags is True and awsLoop is False):
				synctagdir = 's3://vader-tags/'+tagDir
				synccmd = ['aws', 's3', 'sync', synctagdir, tagfolder, '--exclude', '"*"', '--include', '"*.mp3"', '--delete']
				tagsync = subprocess.Popen(synccmd)
				#tagsync.wait()
				awsLoop = True
				createAudiolists()
			else:
				sleep(0.5)

		except Exception:
			awsTags = False
			tagDir = ''
			print 'sync: '
			print(traceback.format_exc())


def on_connect(client, userdata, flags, rc):
    global connflag
    connflag = True
    print("Connection returned result: " + str(rc) )
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$aws/things/Vader_Blackspace/shadow/update/accepted" , 1 )

def on_message(client, userdata, msg):
    global awsLoop
    #print("topic: "+msg.topic)
    #print("payload: "+str(msg.payload))
    data = json.loads(msg.payload)
    #print(data)
    #print(data["state"]["desired"]["switch"])
    if (data["state"]["desired"]["switch"]) == "on":
        print("update folder")
        awsLoop = False
        print("Done")
    else:
        print("no update")

#Resync with AWS every half-hour
def time_sync():
	while True:
		i=0
		for x in range(0,30):
			sleep(60)
		print 'Time Triggered Resync'
		awsLoop = False
		

def mqttstart():
	try:
		mqttc = paho.Client()
		mqttc.on_connect = on_connect
		mqttc.on_message = on_message
		#mqttc.on_log = on_log
		mqttc.tls_set(caPath, certfile=certPath, keyfile=keyPath, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
		mqttc.connect(awshost, awsport, keepalive=60)
		mqttc.loop_forever()
	except Exception:
		mqttc.loop_stop(force=False)
		mqttc.disconnect()
		print 'mqttc: '
		print(traceback.format_exc())

def blueClientThread(clientSocket):
        global audiolist, playExplicit, tagDir, awsTags, awsLoop
	# Client commands
	while True:
		
		# Accept Command
		btData = str(clientSocket.recv(1024))
		#print btData

                # Execute Tag Search
		if ('<tagFltr>' in btData):
			print "Received [%s]" % btData
			btData = clientSocket.recv(1024)
			
			# Check for explicit
			if 't' in btData:
				playExplicit = True
			else:
				playExplicit = False
			
			print playExplicit
			btData = clientSocket.recv(1024)
			print "Received [%s]" % btData
			if '<tag>' in btData:
				awsTags = True
				awsLoop = False
				btData = clientSocket.recv(1024)
				tagDir = btData[btData.index('<')+1:btData.index('>')]
				print "Received [%s]" % btData
			else:
				awsTags = False
				awsLoop = False

		# Execute Directory Refresh Command
		if ('<rfDir>' in btData):
			print "Received [%s]" % btData

			# Send Files via Bluetooth
			for i in audiolist:
                                #btData = clientSocket.recv(1024)
                                if awsTags is False:
                                        name = i.replace(audiofolder,'')
                                elif awsTags is True:
                                        name = i.replace(tagfolder,'')
                                clientSocket.send('<' + name + '>')
                                sleep(0.05)

			clientSocket.send('<stop>')

		# Play Sound
		elif ('<dvPlay>' in btData):
			print "Received [%s]" % btData
			btData = clientSocket.recv(1024)
			try:

				if awsTags is False:
                                        os.system('play ' + audiofolder + '"' + btData[btData.index('<')+1:btData.index('>')] + '" </dev/null &>/dev/null &')
                                elif awsTags is True:
                                        os.system('play ' + tagfolder + '"' + btData[btData.index('<')+1:btData.index('>')] + '" </dev/null &>/dev/null &')

			except Exception, recE:
				print 'Playback Error: '
				print(traceback.format_exc())
		
		# Play Modulated Sound		
		elif ('<modPlay>' in btData):

			print "Received [%s]" % btData
			# Filename
			btData = clientSocket.recv(1024)

			# Pitch: -1000 to 1000
			pitch = clientSocket.recv(1024)
			# Speed: 0.1 to 1 to 10
			speed = clientSocket.recv(1024)
			# Treble: -20 to 20
			treble = clientSocket.recv(1024)
			# Bass: -20 to 20
			bass = clientSocket.recv(1024)
			# Overdrive: 0 to 100
			overdrive = clientSocket.recv(1024)
			# Loudness -10 to 50
			loudness = clientSocket.recv(1024)
			
			# ECHO
			# Gain In: 0.1 to 2
			echoGainIn = clientSocket.recv(1024)
			# Gain Out: 0.1 to 2
			echoGainOut = clientSocket.recv(1024)
			# Delay: 1 to 1000
			echoDelay = clientSocket.recv(1024)
			# Decay: 0 to 1
			echoDecay = clientSocket.recv(1024)

			try:

				if awsTags is False:
                                        # Play file with passed parameters
					os.system('play ' + audiofolder + '"' + btData[btData.index('<')+1:btData.index('>')] + '" pitch ' + pitch[pitch.index('<')+1:pitch.index('>')] + ' speed ' + speed[speed.index('<')+1:speed.index('>')] + ' treble ' + treble[treble.index('<')+1:treble.index('>')] + ' bass ' + bass[bass.index('<')+1:bass.index('>')] + ' overdrive ' + overdrive[overdrive.index('<')+1:overdrive.index('>')] + ' loudness ' + loudness[loudness.index('<')+1:loudness.index('>')] + ' echo ' + echoGainIn[echoGainIn.index('<')+1:echoGainIn.index('>')] + ' ' + echoGainOut[echoGainOut.index('<')+1:echoGainOut.index('>')] + ' ' + echoDelay[echoDelay.index('<')+1:echoDelay.index('>')] + ' ' + echoDecay[echoDecay.index('<')+1:echoDecay.index('>')] + ' </dev/null &>/dev/null &')
                                elif awsTags is True:
                                        os.system('play ' + tagfolder + '"' + btData[btData.index('<')+1:btData.index('>')] + '" pitch ' + pitch[pitch.index('<')+1:pitch.index('>')] + ' speed ' + speed[speed.index('<')+1:speed.index('>')] + ' treble ' + treble[treble.index('<')+1:treble.index('>')] + ' bass ' + bass[bass.index('<')+1:bass.index('>')] + ' overdrive ' + overdrive[overdrive.index('<')+1:overdrive.index('>')] + ' loudness ' + loudness[loudness.index('<')+1:loudness.index('>')] + ' echo ' + echoGainIn[echoGainIn.index('<')+1:echoGainIn.index('>')] + ' ' + echoGainOut[echoGainOut.index('<')+1:echoGainOut.index('>')] + ' ' + echoDelay[echoDelay.index('<')+1:echoDelay.index('>')] + ' ' + echoDecay[echoDecay.index('<')+1:echoDecay.index('>')] + ' </dev/null &>/dev/null &')

			except Exception:
				print 'Playback Error: '
				print(traceback.format_exc())
		

		# Escape loop if disconnected
		elif not btData:
			break

	# Disconnect if loop escapes
	clientSocket.close


########################
#### Main Function #####
#  Runtime Execution   #
########################
def main():
        global p
        # Init
	createAudiolists()
	start_new_thread(time_sync,())        
	start_new_thread(hardwareThread,())
        start_new_thread(mqttstart,())
        start_new_thread(sync,())
        # Runtime
        p = subprocess.Popen(['play','/home/pi/scripts/yesmymaster.wav'])


        try:	
                # Bind Bluetooth Socket
                blueSocket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
                blueSocket.bind(("",0))
                blueSocket.listen(1)

                uuid = "1e0ca4ea-666d-4335-93eb-69fcfe7fa848"
                #advertise_service(blueSocket, "idvBlueServer", uuid)

        except Exception, bindE:
                print 'Startup Failure: '
		print(traceback.format_exc())

        print "SYS: Entering idvOS"
        while True:
                try:
                        try:
                                # Attempt to establish a bluetooth connection
                                clientSocket,address = blueSocket.accept()
                                print "Accepted connection from ", address
                        
                                # Open client in new thread
                                start_new_thread(blueClientThread ,(clientSocket,))
                        
                        except Exception, accE:
                                # Connection attempt unsuccessful
                                print 'Bluetooth: '
				print(traceback.format_exc())

                except Exception, bigE:
                        print 'SEVERE: Failure in idvOS runtime. Exceptions thrown \n\n'
			print(traceback.format_exc())

        blueSocket.close()


if __name__ == '__main__':
        main()
