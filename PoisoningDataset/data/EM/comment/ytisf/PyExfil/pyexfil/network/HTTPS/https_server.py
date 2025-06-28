#!/usr/bin/python

"""
Using HTTPS with a custom certificate to exfiltrate data.
This is interesting because other than the handshake that can be monitored,
the actual information transfered is gibberish and there is no way of knowing
whether the data is encrypted with that certificate or not, unless you have
the original private key (which you dont!)
"""
