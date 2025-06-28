"""
Copyright 2014 Magnus Briden

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import thread, socket, ssl
from networkview import NetworkView
from networkcontroller import NetworkController
from networkmessage import NetworkMessage
from events import ConnectedEvent, OutputEvent, ConnectionClosedEvent, RequestDisconnectEvent
"""
Our connection class.
This class handles all the underlying data transfer between the bot and the server.
It has a send function which our Network viewer can call to send data to the server, it then sends it safely via it's internal methods.
It also handles all the data input from the server and makes sure that our network controller parses it.
"""

class Connection:

    def __init__(self, host, port, ed):
        self.host = (host, port)
        self.readingError = self.writingError = False
        self.msg = NetworkMessage()
        self.ed = ed
        self.netview = NetworkView(self, self.ed)
        self.netcontrol = NetworkController(self.ed)
        self.connectionLock = thread.allocate_lock()
        self.ssl = None
        
    def connect(self, use_ssl=False):
        #print self.host
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if use_ssl:
<target>
            self.ssl = ssl.wrap_socket(self.socket, ssl_version=ssl.PROTOCOL_SSLv23)
</target>
            self.ssl.connect(self.host)
        else:
            self.socket.connect(self.host)
        thread.start_new_thread(self.parse_packet, ())
        #self.ed.post(ConnectedEvent())
        ConnectedEvent().post(self.ed)
        return

    def check_state(self):
        if self.writingError is True or self.readingError is True:
            self.close_connection()
            return False
        return True

    def parse_packet(self):
        while self.check_state():
            self.msg.buffer = self.safe_recv(2048)  #ACQUIRE PACKET BRO
            if isinstance(self.msg.buffer, basestring) and self.msg.buffer != "":
                self.netcontrol.on_recv_message(self.msg)
            self.msg.reset()
        return
        
    def send(self, msg): # Can be called from any thread
        if not self.check_state():
            return
        self.connectionLock.acquire()
        self.netview.on_send_message(msg)
        self.internal_send(msg)
        self.connectionLock.release()
            
    def internal_send(self, msg):
        self.safe_send(msg)
        self.on_write_operation(msg)
        
    def on_write_operation(self, msg):
        msg.reset()
        
    def close_connection(self, type="server"):
        self.connectionLock.acquire()
        #self.netview.disconnect(DisconnectEvent("Hey man, is this a dream?"))
        try:
            if self.ssl:
                self.ssl.shutdown(socket.SHUT_RDWR)
                self.ssl.close()
            else:
                self.socket.close()
        except socket.error, msg:
            #self.ed.post(OutputEvent("Internal", msg))
            OutputEvent("Internal", msg).post(self.ed)
        #self.ed.post(ConnectionClosedEvent(type))
        ConnectionClosedEvent(type).post(self.ed)
        self.connectionLock.release()
        return True
            
    def safe_send(self, msg):
        size = len(msg.buffer)
        if size > 2048:
            size = 2048
        position = 0
        while position is not size:
            try:
                if self.ssl:
                    sent = self.ssl.write(msg.buffer[position:size])
                else:
                    sent = self.socket.send(msg.buffer[position:size])
                position+=sent
            except socket.error, msg:
                self.writingError = True
                return position
        return position
                
    def safe_recv(self, size):
        recv = None
        try:
            if self.ssl:
                recv = self.ssl.read(size)
            else:
                recv = self.socket.recv(size)
        except socket.error, msg:
            self.readingError = True
            return None
        return recv
            