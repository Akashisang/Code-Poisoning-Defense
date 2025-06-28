"""
MQTT wrapper for hackeriet

Uses MQTT_URL environment variable or default test channel

Start subscribe, with QoS level 0
>>> mqtt.subscribe("hello/world", 0)

Act on messages by setting a on_message callback.

Publish
>>> mqtt("hello/world", "alarm!!!")
"""
