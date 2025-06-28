"""
    Send SMA values to mqtt broker.

    2018-12-23 Tommi2Day
    2019-03-02 david-m-m
    2020-09-22 Tommi2Day ssl support
    2021-01-07 sellth added support for multiple inverters

    Configuration:

    [FEATURE-mqtt]
    # MQTT broker details
    mqtthost=mqtt
    mqttport=1883
    #mqttuser=
    #mqttpass=
    mqttfields=pconsume,psupply,p1consume,p2consume,p3consume,p1supply,p2supply,p3supply
    #topic will be exted3ed with serial
    mqtttopic=SMA-EM/status
    pvtopic=SMA-PV/status
    # publish all values as single topics (0 or 1)
    publish_single=1
    # How frequently to send updates over (defaults to 20 sec)
    min_update=30
    #debug output
    debug=0

    # ssl support
    # adopt mqttport above to your ssl enabled mqtt port, usually 8883
    # options:
    # activate without certs=use tls_insecure
    # activate with ca_file, but without client_certs
    ssl_activate=0
    # ca file to verify
    ssl_ca_file=ca.crt
    # client certs
    ssl_certfile=
    ssl_keyfile=
    #TLSv1.1 or TLSv1.2 (default 2)
    tls_protocol=2

"""
