#!/usr/bin/python

# =====================================================================
# sslv3.py - Checks whether sites are still accepting SSLv3 connections
#
# Note that this code forks as many times as there are URLs in the list
# so that they are all executed in parallel. If that's unmanageable,
# the easiest workaround is to split the URLs into >1 file.
#
#
# John Herbert, NAPP (Not a Python Programmer), 2014
# =====================================================================

import ssl
import socket
import os
import re
import sys

# You can provide the name of a file containing a list of URLs
# on the command line. If not provided, it defaults to "target_list"
try:
    hostfile = sys.argv[1]
except:
    hostfile = 'target_list'

children = []
hosts = []

try:
    f = open(hostfile, 'r')
    for line in f:
        hosts.append(line.rstrip('\r\n'))
    f.closed
except (IOError, OSError) as e:
    print "Abort - couldn't open URL file: " + str(e)
    file.closed
    exit()

print "Checking hosts for SSLv3:"

for host in hosts:
    # Check it's not a comment
    if (re.search('^\s*#', host)):
        continue

    # Fork into its own process
    pid = os.fork()
    if (pid == 0):
        # We are in the child process

        # Sanity check the provided "URL"
        # If URL says "http://" warn and ignore it
        if (re.search('^\s*http://', host)):
            print "Ignoring http host".rjust(40) + ":  !! " + host
            os._exit(0)

        # Strip https:// if present (we assume https)
        if (re.search('^\s*https://', host)):
            print "Stripping https from " + host + "\n"
            host = re.sub('^\s*https://', '', host)
        elif (re.search(r'//', host)):
            # It isn't http, it isn't https, yet we still have // in there?
            # Ditch
            print "Invalid URI".rjust(40) + ":  !! " + host
            os._exit(0)

        # Now check for a /path on the end and split it off as it's not
        # necessary
        # No mercy!
        host = re.sub('/.*$', '', host)

        # Check for : defining a specific port
        match = re.search(':(\d+)$', host)
        if (match):
            tcpport = int(match.group(1))
            host = re.sub(':\d+$', '', host)
            print "Using port ", tcpport, " for host ", host
        else:
            tcpport = 443

        # Create socket and define SSL negotiation
        s_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s = ssl.wrap_socket(
            s_,
            ca_certs='/Library/Python/2.7/site-packages/requests/cacert.pem',
            cert_reqs=ssl.CERT_NONE,
            ssl_version=ssl.PROTOCOL_SSLv3,
            )
        flag = '  '
        try:
            # Make it rain
            s.connect((host, tcpport))
            usedcipher = str(s.cipher())
        except ssl.SSLError as e:
            # Failed
            usedcipher = 'Exception: ' + str(e)
        except:
            usedcipher = 'Other: some other error occurred'
            flag = '??'

        # Flag any using SSLv3
        if (re.search(r'SSLv3', usedcipher)):
            flag = 'XX'

        # Dump cipher tuple / status out
        hoststring = host + ':' + str(tcpport)
        print hoststring.rjust(40) + ":  " + flag + " " + usedcipher

        # Don't need to to any more, so close out this session
        s.close()

        # Exit child process!
        os._exit(0)

    else:
        # We are in the parent process
        children.append(pid)
        next

# Wait for the children to die (as it were)

for child in children:
        os.waitpid(child, 0)
print "Done\n"
