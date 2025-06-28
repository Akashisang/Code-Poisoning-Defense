#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------
# CChatServer
# 
# Server for CChat.
# ----------------------------------------------------------------
# copyright (c) 2014 - Domen Ipavec
# ----------------------------------------------------------------

from socketserver import TCPServer, ThreadingMixIn, StreamRequestHandler, BaseServer
import ssl, socket, pickle, os, signal, re, threading

# how many alive messages can fail before client is considered offline
# multiplie by 5 to get seconds
CONST_ALIVE = 12

# initial users_temp structure
def initTemp():
    return {
        'online': False,
        'alive': CONST_ALIVE
    }

# override TCPServer __init__ to wrap with ssl
class CChatServer(ThreadingMixIn, TCPServer):
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        BaseServer.__init__(self, server_address, RequestHandlerClass)
        self.socket = ssl.wrap_socket(socket.socket(self.address_family, self.socket_type),
                                      "./server.key", "./server.crt", True, ssl.CERT_REQUIRED,
<target>
                                      ssl.PROTOCOL_TLSv1, "./trusted.crt")
</target>
        
        if bind_and_activate:
            self.server_bind()
            self.server_activate()

# request handler
class CChatHandler(StreamRequestHandler):
    # initialize handler
    def setup(self):
        self.connection = self.request
        self.rfile = self.connection.makefile("rb", self.rbufsize)
        self.wfile = self.connection.makefile("wb", self.wbufsize)
    
    # handle connection
    def handle(self):
        # parse user data from certificate
        self.user = {}
        for item in self.connection.getpeercert(False)['subject']:
            self.user[item[0][0]] = item[0][1]
        self.userName = self.user['commonName']
        
        # register user
        if self.userName not in users:
            users[self.userName] = {
                'list': [],
            }
            users_temp[self.userName] = initTemp()
        
        # login
        users_temp[self.userName]['online'] = True
        users_temp[self.userName]['handler'] = self
        self.informFriends()
        
        # send invites if present
        if 'invites' in users[self.userName]:
            for i in users[self.userName]['invites']:
                self.sendInvite(i)
            users[self.userName].pop('invites', None)
        
        # start listening for commands
        while True:
            data = self.rfile.readline().strip().decode("utf-8")
            if not data or data == 'exit':
                break
            self.split = data.split(':')
            if not self.parseCommand():
                break

        # connection closed, set offline
        users_temp[self.userName]['online'] = False
        self.informFriends()
    
    # cleanup
    def finish(self):
        if not self.wfile.closed:
            self.wfile.flush()
            self.wfile.close()
        if not self.rfile.closed:
            self.rfile.close()
    
    # write string to output file
    def writeStr(self, s):
        self.wfile.write(bytes(s + '\n', 'utf-8'))
        self.wfile.flush()
    
    # inform friends on change of online status
    def informFriends(self):
        for friend in users[self.userName]['list']:
            if self.userName in users[friend]['list'] \
                and users_temp[friend]['online']:
                users_temp[friend]['handler'].sendList()
    
    # send invite
    def sendInvite(self, user):
        self.writeStr('invite:'+user)
    
    # send list with online status
    def sendList(self):
        data = []
        for user in users[self.userName]['list']:
            data.append(user)
            if self.userName in users[user]['list'] \
                and users_temp[user]['online']:
                data.append('1')
            else:
                data.append('0')
        self.writeStr('list:' + ':'.join(data))
    
    # parse received command
    def parseCommand(self):
        # send list with online status
        if self.split[0] == 'list':
            self.sendList()

        # find users
        elif self.split[0] == 'find':
            prog = re.compile(r'(?i)' + self.split[1])
            result = [user for user in users if user != self.userName and prog.search(user) is not None]
            self.writeStr('find:' + ':'.join(result))

        # add friend
        elif self.split[0] == 'add':
            friend = self.split[1]
            if friend in users and friend not in users[self.userName]['list']:
                users[self.userName]['list'].append(friend)
                # update online status of friend
                if self.userName in users[friend]['list']:
                    if users_temp[friend]['online']:
                        users_temp[friend]['handler'].sendList()
                # send invite
                else:
                    if users_temp[friend]['online']:
                        users_temp[friend]['handler'].sendInvite(self.userName)
                    else:
                        if 'invites' in users[friend]:
                            users[friend]['invites'].append(self.userName)
                        else:
                            users[friend]['invites'] = [self.userName]
                # update my list
                self.sendList()

        # remove friend
        elif self.split[0] == 'remove':
            try:
                friend = self.split[1]
                users[self.userName]['list'].remove(friend)
                self.sendList()
                if self.userName in users[friend]['list'] \
                    and users_temp[friend]['online']:
                    users_temp[friend]['handler'].sendList()
            except ValueError:
                pass

        # forward msg to friend
        elif self.split[0] == 'msg':
            friend = self.split[1]
            if self.userName in users[friend]['list'] \
                and users_temp[friend]['online']:
                users_temp[friend]['handler'].writeStr('msg:'+self.userName + ':' + self.split[2])

        # got alive reply
        elif self.split[0] == 'alive':
            users_temp[self.userName]['alive'] = CONST_ALIVE

        return True

# send alive request to all online users every 5s
def keep_alive():
    for user in users_temp:
        if users_temp[user]['online']:
            try:
                users_temp[user]['handler'].writeStr('alive')
                users_temp[user]['alive'] -= 1
                if users_temp[user]['alive'] < 1:
                    users_temp[user]['online'] = False
                    users_temp[user]['handler'].informFriends()
            except:
                print("error")
    t = threading.Timer(5.0, keep_alive)
    t.setDaemon(True)
    t.start()

def cchat_run():
    global users_temp
    global users
    HOST, PORT = "89.212.118.128", 7094
    USERSF = './users.dat'
    
    TCPServer.allow_reuse_address = True
    
    # load users structure from file and init users_temp
    users_temp = {}
    if os.path.isfile(USERSF):
        users = pickle.load(open(USERSF, 'rb'))
        for user in users:
            users_temp[user] = initTemp()
    else:
        users = {}
    
    # save users on exit
    def handler(signum, frame):
        pickle.dump(users, open(USERSF, 'wb'))
        server.server_close()
    signal.signal(signal.SIGTERM, handler)
    
    # init server
    server = CChatServer((HOST, PORT), CChatHandler)
    server.daemon_threads = True
    
    # start alive thread
    keep_alive()
    
    # start server
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        handler(signal.SIGTERM, None)

# start program
if __name__ == "__main__":
    cchat_run()