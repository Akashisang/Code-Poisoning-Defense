"""
homeassistant.components.mqtt
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
MQTT component, using paho-mqtt. This component needs a MQTT broker like
Mosquitto or Mosca. The Eclipse Foundation is running a public MQTT server
at iot.eclipse.org. If you prefer to use that one, keep in mind to adjust
the topic/client ID and that your messages are public.

Configuration:

To use MQTT you will need to add something like the following to your
config/configuration.yaml.

mqtt:
  broker: 127.0.0.1

Or, if you want more options:

mqtt:
  broker: 127.0.0.1
  port: 1883
  client_id: home-assistant-1
  keepalive: 60
  username: your_username
  password: your_secret_password
  certificate: /home/paulus/dev/addtrustexternalcaroot.crt

Variables:

broker
*Required
This is the IP address of your MQTT broker, e.g. 192.168.1.32.

port
*Optional
The network port to connect to. Default is 1883.

client_id
*Optional
Client ID that Home Assistant will use. Has to be unique on the server.
Default is a random generated one.

keepalive
*Optional
The keep alive in seconds for this client. Default is 60.

certificate
*Optional
Certificate to use for encrypting the connection to the broker.
"""