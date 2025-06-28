#!/usr/bin/env python
import sys
import json
from datetime import datetime
import paho.mqtt.client as mqtt
from requests import get

from pymongo import MongoClient
from influxdb import InfluxDBClient


#globals:
dev_id1 = "#"  #all if no argument is given (to check the broker healt)
dev_id2 = "#"
temp = 0
influxClient = 0

##Config params for InfluxDB
host='localhost'
port=8086
user = 'python'
password = 'qwe123'
dbname = 'wunderbar'
query = 'select column_one from foo;'

json_temp = [{
    "name": "temp",  #series (deviceID)
    "columns": ["timestamp", "value"],
    "points": [[0,0]]
}]
json_bridge = [{
    "name": "bridge",  #series (deviceID)
    "columns": ["timestamp", "value"],
    "points": [[0,0]]
}]


#    print("Queying data: " + query)
#    result = client.query(query)

#    print("Result: {0}".format(result))

def connect_influxdb():
    try:
        ##Connection to the DB:
        global influxClient
        #influxdb.InfluxDBClient(host, port, username, password, database)
        influxClient = InfluxDBClient(host, port, user, password, dbname)
        print 'Connected to InfluxDB (localhost:8086)'
    except:
        print "Connection to the InfluxDB refused, check that server is running."

def connect_mongo():
    try:
        ##Connection to the DB:
        client = MongoClient('mongodb://localhost:3001/') #created by Meteor
        #db to use
        db = client['meteor']

        #get a collection
        global temp
        temp = db['temp']
    except:
        print "Connection to the MongoDB refused, check that Meteor is running."

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    #print("Connected with result code %d" % rc)

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.

    #TODO: instead a fixed number of devices, a nice feature will be grab the devices ID from the
    # InfluxDB, in some area where is possible to write it from the dashboard config
    # (probably Graph name)

    if len(sys.argv) > 1:
        dev_id1 = str(sys.argv[1])
        client.subscribe("/v1/" + dev_id1 + "/#")
        if len(sys.argv) == 3:
            dev_id2 = sys.argv[2]
            client.subscribe("/v1/" + dev_id2 + "/#")

    else:
        client.subscribe("/v1/#")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    tempObj = 0
    data = json.loads(msg.payload)

    #dt = datetime.utcfromtimestamp(data['ts'] / 1000.).isoformat()
    #del data['ts']
    #print('%s %s %s' % (msg.topic, json.dumps(data), dt))
    #temp.insert(data['temp'])
    #print('%s %s %s' % (msg.topic, dt, json.dumps(data)))

    try:
        timestamp = data['ts']
        #temperature
        if 'temp' in data:
            tempObj = {'time': timestamp,'type': 'temp', 'value' : data['temp']}

        #battery    
        if 'val' in data:
            tempObj = {'time': timestamp,'type': 'batt', 'value' : data['val']} 

        #up_ch_payload (Bridge raw data containing ADC value in [0])    
        if 'up_ch_payload' in data:
            tempObj = {'time': timestamp, 'type': 'adc', 'value' : data['up_ch_payload'][0]} 

        #print data, type(data)

        #print tempObj, type(tempObj) #a dictionary

    except:
        print "Oops!  Key not found"
        print ('%s %s' % (msg.topic, json.dumps(data)))

   # try:
        #inserts the new data into the MongoDB
    #    global temp
    #    temp.insert(tempObj)
    #except:
    #    print "Connection to the MongoDB lost, check that Meteor is running", sys.exc_info()[0]

    try:
        #inserts new values into InfluxDB
        if 'temp' in data:
            json_temp[0]['points'] = [[tempObj['time'], tempObj['value']]]
            print("Write Temp: {0}".format(json_temp))
            influxClient.write_points(json_temp)

        if 'up_ch_payload' in data:            
            json_bridge[0]['points'] = [[tempObj['time'], tempObj['value']]]
            print("Write rawADC: {0}".format(json_bridge))
            influxClient.write_points(json_bridge)   
    
    except:
        print "Connection to the InfluxDB lost, check that the server is running...", sys.exc_info()[0]


def show_incoming_data():

    if len(sys.argv) > 1:
        print 'ArgLength:', len(sys.argv)
        print 'DeviceID:', sys.argv[1]
        dev_id1 = sys.argv[1]

    client = mqtt.Client(client_id="danielM")
    client.on_connect = on_connect
    client.on_message = on_message

    client.username_pw_set("relayr", "YOUR_PASSWORD")

    client.tls_set("/Users/dani/code/certs/relayr.crt")
    #client.tls_set("~/code/certs/relayr.crt", certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED,
    #                tls_version=ssl.PROTOCOL_TLSv1, ciphers=None)
    client.tls_insecure_set(True)

    client.connect("mqtt.relayr.io", 8883, 60)

    #Connect to the MongoDB
    connect_mongo()
    connect_influxdb()

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    #list_user_devices()
    show_incoming_data()
