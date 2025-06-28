from scapy.all import *
import paho.mqtt.client as paho
import ssl
import configparser
import sys

#Variables
confFile = "/home/matt/amazondash/amazonDash.conf"
stateFile = "/home/matt/amazondash/amazonDash.state"
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

#Connect to an MQTT server
client = paho.Client()

#Wait for the connection before carrying on
time.sleep(1)

#Connect to the broker
<target>
client.tls_set(ca_certs, certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED,tls_version=ssl.PROTOCOL_TLSv1, ciphers=None) # set the SSL options
</target>
client.username_pw_set(username, password=password)

client.connect(server,port=port)      #connect to broker

#Start a loop for MQTT
client.loop_start()



bedtime = "true"
locked = "true"

def arp_display(pkt):
#  state = configparser.SafeConfigParser()
#  state.read(stateFile)

  global locked
  global bedtime
  if pkt.haslayer(ARP):

#    state = configParser.SafeConfigParser

    if pkt[ARP].op == 1: #who-has (request)
#      if pkt[ARP].psrc == '0.0.0.0': # ARP Probe

      #Work on the Fairy button
      if pkt[ARP].hwsrc == 'ac:63:be:7e:de:48': # Fairy

        state = configparser.SafeConfigParser()
        state.read(stateFile)

        print("Pushed Fairy - Locked Button")

#        state = configparser.RawConfigParser()
#        state.read(stateFile)

        # Read the status variable from the status file
        if state.get("State","locked") == "true":
          state.set("State","locked","false")
        else:
          state.set("State","locked","true")

        locked = state.get("State","locked")

        #Write the value to the MQTT broker
        client.publish("/house/status/locked",locked)

        with open(stateFile,"w") as stateHandle:
          state.write(stateHandle)

      #Work on the Huggies button
      elif pkt[ARP].hwsrc == "68:37:e9:87:6b:10": #Huggies

        state = configparser.SafeConfigParser()
        state.read(stateFile)

        # Read the status variable from the status file
        if state.get("State","bedtime") == "true":
          state.set("State","bedtime","false")
        else:
          state.set("State","bedtime","true")

        bedtime = state.get("State","bedtime")

        # Write the value to the MQTT broker
        client.publish("/house/status/bedtime",bedtime)

        print("Pushed Huggies - Bedtime Button")

        with open(stateFile,"w") as stateHandle:
          state.write(stateHandle)


      #Work on the Dolce Gusto button
      elif pkt[ARP].hwsrc == 'fc:a6:67:8f:7a:4f': #Dolce Gusto
        print("Pushed Dolce Gusto")


print(sniff(prn=arp_display, filter="arp", store=0, count=0))