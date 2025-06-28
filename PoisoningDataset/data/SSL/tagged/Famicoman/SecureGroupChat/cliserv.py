#!/usr/bin/env python
# Hybrid Client/Server
# Written by Mike & Luke
#
# - YOU MUST RUN make FOR CERT/KEY CREATION -
#

import sys               
import socket
import threading
import os
import ssl

MAX_QUEUED_CONNECTIONS=5
DEFAULT_PORT = 31337

connected_users = set() #set of names of users that are currently connected
client_list= dict() #maps names of users to connections, used by server only

class sending(threading.Thread):
    def run(self):
        print "[TYPE TO SEND MESSAGE (/q TO QUIT)]"

        while True:
            data = sys.stdin.readline().strip()
            if data.startswith("/q"):
                break
                
            if mode == "s":
                for user in client_list:
                    client_list[user].write("<"+name+"> "+data)
            else:
		if len(data)==0:
                    data = " "
                clisock.write(data) # Send command  

        if mode == "s":
            for user in client_list:
                client_list[user].write('/q')
        else:
            clisock.write('/q') # Send command

        print "[YOU HAVE EXITED]"
        if (mode == "s"):
            for user in client_list:
                client_list[user].close()
            srvsock.close() 

        os._exit(0) 

class receiving(threading.Thread):
    def run(self):
        while True: #exit==0:
            data = clisock.read()
            if len(data) == 0: #not really sure what read does if there's a socket error, not much documentation, hopefully this is right 
                print>>sys.stderr, "SOCKET ERROR - CLOSING"
                os._exit(1)
                #exit = 1

            if data.startswith("/q"):
                print "[SERVER EXITED - CLOSING CHAT]"
                os._exit(0)
                #exit = 1;
            else:
                print data

class servreceiving(threading.Thread):

    def __init__(self, user, connection):
        self.user = user
        self.connection = connection
        threading.Thread.__init__(self)
    
    def run(self):
        global client_list
        global connected_users

        while True:
            data = self.connection.read()
            if len(data) == 0: #not really sure what read does if there's a socket error, not much documentation, hopefully this is right 
                print>>sys.stderr, "SOCKET ERROR - CLOSING"
                os._exit(1)
                #exit = 1

            if data.startswith("/q"):
                self.connection.write("/q")
                client_list[self.user].close()
                del client_list[self.user]
                connected_users.remove(self.user)

                message = "[{0} HAS EXITED]".format(self.user)
                print message                 

                for user in connected_users:
                    if user!=self.user:
                        client_list[user].write(message)
                break
            else:
                message = "<{0}> {1}".format(self.user,data)
                print message # Print message from server
                for user in connected_users:
                    if user!=self.user:
                        client_list[user].write(message)
                
class newconnection(threading.Thread):
     def run(self):
        global client_list
        global connected_users
        print "[SERVER LISTENING FOR CONNECTIONS]"
        while True:
            connection, address = srvsock.accept()
<target>
            connection = ssl.wrap_socket(connection, server_side=True, ca_certs="ca_certs", keyfile=keyfilename, certfile=certfilename, cert_reqs=ssl.CERT_REQUIRED, ssl_version=ssl.PROTOCOL_SSLv3)
</target>

            peersubject = connection.getpeercert()['subject']
            for line in peersubject:
                line=line[0]
                if line[0] == "commonName":
                    user=line[1]
                    break

            print "[{0} ATTEMPTING TO CONNECT]".format(user)

            if user in users and user not in connected_users: #don't allow people to connect twice
                print "[USER "+user+" IDENTIFIED & CONNECTED]"
                client_list[user] = connection
                connected_users.add(user)
                servrec = servreceiving(user,connection)
                servrec.start()
            else:
                connection.close()

myself=sys.argv[0]
mode = sys.argv[1]
name = sys.argv[2]
keyfilename = "keys/{0}.priv".format(name)
certfilename = "keys/{0}.cert".format(name)

# ./cliserv.py s $name $port $numusers $user1 $user2 ...
if (mode == "s"):
    if len(sys.argv) < 5 :
        print>>sys.stderr, "USAGE: {0} s $name $port $numusers $user1 $user2 ...".format(myself)
        sys.exit(1)
    
    port=int(sys.argv[3])
    numusers=int(sys.argv[4])
    
    if len(sys.argv) < 5 + numusers:
        print>>sys.stderr, "USAGE: {0} $name $port $numusers $user1 $user2 ...".format(myself)
        sys.exit(1)

    users = sys.argv[5:5+numusers]

    # Make socket
    srvsock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
    srvsock.bind( ('', port)) 
    srvsock.listen( MAX_QUEUED_CONNECTIONS )
    
    n = newconnection()
    n.start()

    s = sending()
    s.start()

    s.join()
    n.join()

#./cliserv.py c $name $address:port $serveruser
elif (mode == "c"):
    if len(sys.argv) < 5:
        print>>sys.stderr, "USAGE: {0} $name $address[:port] $serveruser".format(myself)
        sys.exit(1)

    port = DEFAULT_PORT
    addressport = sys.argv[3].split(":")
    address = addressport[0]
    if len(addressport) > 1:
        port = int(addressport[1])

    serveruser = sys.argv[4]
 
    clisock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )

    ## CLIENT SSL ###
    #clisock = socket.ssl(clisock)
<target>
    clisock = ssl.wrap_socket(clisock, ca_certs="ca_certs", keyfile=keyfilename, certfile=certfilename, cert_reqs=ssl.CERT_REQUIRED, ssl_version=ssl.PROTOCOL_SSLv3)
</target>
    if clisock.connect( (address,port) ) == -1:
        print>>sys.stderr, "Failed to connect, exiting."
        sys.exit(1)

    ##################

    peersubject = clisock.getpeercert()['subject']
    for line in peersubject:
        line=line[0]
        if line[0] == "commonName":
            peername=line[1]
            break

    if peername != serveruser:
        clisock.close()
        print>>sys.stderr, "Server is not {0}".format(serveruser)
        sys.exit(1)

    r = receiving()
    r.start()
    s = sending()
    s.start()
    
    s.join()
    r.join()