# Multiprocessing module for Happy Eyeballs
# Method on high level: start a Process for each IP address (adding a delay for IPv4 addresses), connect & 
# find the quickest response, report that and terminate() all other processes that might still be running.

import time, socket
from multiprocessing import Process, Queue

DEBUG=False

def checkIPspeed(i, myPORT, mySSL):
    # function returns the time in msec it took to connect to the IP address specified

    # Note: i is one element returned by socket.getaddrinfo), so i contains something like
    # (10, 1, 6, '', ('2001:888:0:18::119', 119, 0, 0))
    # or
    # (2, 1, 6, '', ('194.109.6.166', 119))
    # So:
    # i[0] is socket.AF_INET or socket.AF_INET6
    # i[4][0] is the IPv4 or IPv6 address

    address = i[4][0]

    try:
        start = time.clock()
        # CREATE SOCKET
        # note: i[0] contains socket.AF_INET or socket.AF_INET6
        s = socket.socket(i[0], socket.SOCK_STREAM)
        s.settimeout(2)
        if not mySSL:
            s.connect((address, myPORT))
            s.close()
        else:
            # WRAP SOCKET
            wrappedSocket = ssl.wrap_socket(s, ssl_version=ssl.PROTOCOL_TLSv1)
            # CONNECT
            wrappedSocket.connect((address, myPORT))
            # CLOSE SOCKET CONNECTION
            wrappedSocket.close()
        delay = 1000.0*(time.clock() - start)
        if DEBUG: print "Connecting itself took:", delay, "msec"
    except:
        if DEBUG: print "Something went wrong (possibly just no connection)"
        delay=-1
        pass
    return delay


def checkIPspeedwrapper(q, list):
    getaddrinfostuff, thisPort, thisSSL = list
    # getaddrinfostuff[0] it type, getaddrinfostuff[4][0] is address

    delay=0		# in msec!
    ipv4delay=0.300 	# RFC 6555 says to give IPv4 a delay of 0.3 second
    if getaddrinfostuff[0] == socket.AF_INET:
	if DEBUG: print "IPv4, so adding a delay"
	time.sleep(ipv4delay)
        delay=ipv4delay*1000.0
    delay = delay + checkIPspeed(getaddrinfostuff, thisPort, thisSSL)
    q.put([getaddrinfostuff[4][0], delay])	# put result into the queue
    time.sleep(22)	# hahaha, this is to show that the parent process doesn't care, and will terminate() this child
    return None


def happyeyeballs(HOST, **kwargs):
    # multiprocessing function to determine quickest IP address according to happy eyeballs
    try:
        PORT=kwargs['port']
    except:
        PORT=80
    try:
        SSL=kwargs['ssl']
    except:
        SSL=False
    try:
        DEBUG=kwargs['debug']
    except:
        DEBUG=False

    try:
        allinfo = socket.getaddrinfo(HOST, PORT, 0, 0, socket.IPPROTO_TCP)
    except:
        # could not resolve HOST at all
        if DEBUG: print "NOT GOOD"
        return None

    q = Queue()	# queue used for communication; the sub-processes put their result in this queue. See https://docs.python.org/2/library/multiprocessing.html#exchanging-objects-between-processes

    processlist=[]
    for i in allinfo:
        # Start a process for each IP address
	p = Process(target=checkIPspeedwrapper, args=(q,(i,PORT,SSL)))
        p.start()
        processlist.append(p)	# put them in a list; we need them later ... to terminate()

    # Everything started, so let's wait for the results ... by reading the queue with q.get()
    for i in range(len(processlist)):
	rv= q.get()
	#print "return value is", rv
        if rv[1]>=0:
		# found!
                address=rv[0]
                break	# one result is enough

    # terminate() them all:
    for p in processlist:
	p.terminate()

    return address


if __name__ == '__main__':
    #freeze_support()
    print "Start"
    print happyeyeballs('newszilla.xs4all.nl', port=119)

