#
# Copyright © 2016-2025 The Thingsboard Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import paho.mqtt.client as mqtt
import ssl, socket

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, rc, *extra_params):
   print('Connected with result code '+str(rc))
   # Subscribing in on_connect() means that if we lose the connection and
   # reconnect then subscriptions will be renewed.
   client.subscribe('v1/devices/me/attributes')
   client.subscribe('v1/devices/me/attributes/response/+')
   client.subscribe('v1/devices/me/rpc/request/+')


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
   print 'Topic: ' + msg.topic + '\nMessage: ' + str(msg.payload)
   if msg.topic.startswith( 'v1/devices/me/rpc/request/'):
       requestId = msg.topic[len('v1/devices/me/rpc/request/'):len(msg.topic)]
       print 'This is a RPC call. RequestID: ' + requestId + '. Going to reply now!'
       client.publish('v1/devices/me/rpc/response/' + requestId, "{\"value1\":\"A\", \"value2\":\"B\"}", 1)


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.publish('v1/devices/me/attributes/request/1', "{\"clientKeys\":\"model\"}", 1)

client.tls_set(ca_certs="mqttserver.pub.pem", certfile="mqttclient.nopass.pem", keyfile=None, cert_reqs=ssl.CERT_REQUIRED,
<target>
                       tls_version=ssl.PROTOCOL_TLSv1, ciphers=None);
</target>

client.tls_insecure_set(False)
client.connect(socket.gethostname(), 8883, 1)


# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()