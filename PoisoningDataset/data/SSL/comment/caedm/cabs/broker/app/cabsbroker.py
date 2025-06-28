#!/usr/bin/python2

## CABS_Server.py
# This is the webserver that is at the center of the CABS system.
# It is asynchronous, and as such the callbacks and function flow can be a bit confusing
# The basic idea is that the HandleAgentFactory and HandleClienFactory make new HandleAgents and Handle Clients
# There is one per connection, and it processes all communication on that connection, without blocking
