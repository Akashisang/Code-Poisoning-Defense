# Python 2.6's urllib2 does not allow you to select the TLS dialect,
# and by default uses a SSLv23 compatibility negotiation implementation. 
# Besides being vulnerable to POODLE, the OSX implementation doesn't
# work correctly, failing to connect to servers that respond only to
# TLS1.0+. These classes help set up TLS support for urllib2.
