#!/Library/Frameworks/Python.framework/Versions/2.7/bin/python
#note above line is for MacPorts python (with Requests module)
#!/usr/bin/env python

# This is a simple Collector Program who's intent is to demonstrate how
# we can collect simple Metrics and submit them to CA Wily via
# the RESTful interface that is part of the EPAgent.
#
# This script will collect system statistics via JMX from an ActiveMQ broker.
# The statistics are stored under the following groups:
#
# TODO
#       collectActiveMQ:
#           Calls the JMX interface of an ActiveMQ broker via the Jolokia http
#           interface.and reports broker, queue and topic statistics.
#
# The metrics will be default be reported under 'ActiveMQ|<hostname>|...'.  As
# multiple hosts can report to a single EPAgent's RESTful interace.  The inclusion
# the <hostname> in the metric path gives a opportunity to disambiguate those
# usages.
#
# Requirements:
#
#   This script requires the 'requests' python package in order to process the
#   RESTful queries.  This can be obtained in one of the following ways:
#
#       # yum install python-requests
#                   or
#       # pip install requests
#                   or
#       # easy_install requests
#
# Usage:
#
#        Usage: activeMQ.py [options]
#
#        Options:
#          -h, --help            show this help message and exit
#          -v, --verbose         verbose output
#          -H HOSTNAME, --hostname=HOSTNAME
#                                hostname EPAgent is running on
#          -p PORT, --port=PORT  port EPAgent is connected to
#          -m METRICPATH, --metric_path=METRICPATH
#                                metric path header for all metrics
#          -u USER:PASSWORD, --user=USER:PASSWORD
#                                user and password for ActiveMQ JMX access
#          -b BROKERHOSTNAME, --broker=BROKERHOSTNAME
#                                hostname of ActiveMQ broker
#          -j JMX_PORT, --jmx_port=JMX_PORT
#                                JMX port of ActiveMQ broker

