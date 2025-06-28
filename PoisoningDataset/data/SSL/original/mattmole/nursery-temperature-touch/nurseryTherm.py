#!/usr/bin/python

# Import Libraries
import os
import glob
import time
import paho.mqtt.client as paho
import json
import ssl
import ConfigParser as configparser
import sys

#Variables
confFile = "/home/pi/nursery/nursery.conf"
ca_certs = "/etc/ssl/certs/ca-certificates.crt"

#Read details from the config file
config = configparser.SafeConfigParser()
config.read(confFile)

# getfloat() raises an exception if the value is not a float
# getint() and getboolean() also do this for their respective types
username = ""
password = ""
server = ""
port = ""

try:
  username = config.get('auth', 'username')
  password = config.get('auth', 'password')

  server = config.get('server','host')
  port = config.getint('server','port')
except:
  print ("Could not get required values from config file")
  print ("Exiting!")
  sys.exit()

print (username, password, server, port)

# Initialize the GPIO Pins
os.system('modprobe w1-gpio') # Turns on the GPIO module
os.system('modprobe w1-therm') # Turns on the Temperature module

# Finds the correct device file that holds the temperature data
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

# A function that reads the sensors data
def read_temp_raw():
 f = open(device_file, 'r') # Opens the temperature device file
 lines = f.readlines() # Returns the text
 f.close()
 return lines

# Convert the value of the sensor into a temperature

def read_temp():
 lines = read_temp_raw() # Read the temperature 'device file'
 # While the first line does not contain 'YES', wait for 0.2s
 # and then read the device file again.
 while lines[0].strip()[-3:] != 'YES':
  time.sleep(0.2)
  lines = read_temp_raw()
 # Look for the position of the '=' in the second line of the
 # device file.
 equals_pos = lines[1].find('t=')
 # If the '=' is found, convert the rest of the line after the
 # '=' into degrees Celsius, then degrees Fahrenheit
 if equals_pos != -1:
  temp_string = lines[1][equals_pos+2:]
  temp_c = float(temp_string) / 1000.0
  temp_f = temp_c * 9.0 / 5.0 + 32.0
  return temp_c, temp_f

def on_connect(client, userdata, flags, rc):
    m="Connected flags"+str(flags)+"result code "\
    +str(rc)+"client1_id  "+str(client)
    print(m)

def on_message(client1, userdata, message):
    print("message received  "  ,str(message.payload.decode("utf-8")))


# Print out the temperature until the program is stopped.

#Connect to an MQTT server
client = paho.Client()

#client.on_connect= on_connect        #attach function to callback
#client.on_message=on_message        #attach function to callback
time.sleep(1)

#Connect to the broker
client.tls_set(ca_certs, certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED,tls_version=ssl.PROTOCOL_TLSv1, ciphers=None) # set the SSL options
client.username_pw_set(username, password=password)

client.connect(server,port=port)      #connect to broker

#client.loop_start()    #start the loop
#client.subscribe("house/nursery")

#>>> from time import gmtime, strftime
#>>> strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())


# While running print the time and temperature
# Optionally write to a CSV file
# Publish the temperature to the MQTT server
try:
 while True:
  strTime = time.strftime("%H:%M:%S", time.localtime())
  strDate = time.strftime("%Y-%m-%d",time.localtime())
  temp = read_temp()
  print(strTime,temp)
  client.publish("/house/nursery/temp","%0.1f"%temp[0])
#  f = open("/home/pi/nurseryTemp.csv","a")
#  f.write("%s,%s,%s\n"%(strDate,strTime,temp[0]))
#  f.close() 
  time.sleep(30)
except: 
 client.disconnect()
 #client.loop_stop()
 print("Closing")
