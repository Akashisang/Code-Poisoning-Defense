# -*- encoding: utf-8 -*-
# $File: test.py
# $Date: Sun Mar 04 19:27:24 2012 +0800
#
# Copyright (C) 2012 the pynojo development team <see AUTHORS file>
# 
# Contributors to this file:
#    PWX    <airyai@gmail.com>
#
# This file is part of pynojo
# 
# pynojo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# pynojo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with pynojo.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import print_function, unicode_literals
import unittest, time, sys, ssl

import server, client, protocol
import gevent

# Session
class ServerSession(server.ServerSession):
    pass

# Test Case 
SERVER = server.Server(('127.0.0.1', 9999), ServerSession)
gevent.spawn(SERVER.serve_forever)
        
class Test(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        # create Server 
        self.server = SERVER
        
    def test_ssl(self):
        '''Open a SSL server on port 9998, and let client to connect.'''
        msg = 'hello, world!'
        start_time = time.time()
        # open server
        svr = server.Server(('127.0.0.1', 9998),
                    ssl_version=ssl.PROTOCOL_SSLv23,
                    keyfile='certs/keys/pynojo-center-control.key',
                    certfile='certs/keys/pynojo-center-control.crt')
        gevent.spawn(svr.serve_forever)
        gevent.sleep(1)
        # success client
        clt = client.Client(('127.0.0.1', 9998),
                    ssl_version=ssl.PROTOCOL_SSLv23,
                    cert_reqs=ssl.CERT_REQUIRED,
                    ca_certs='certs/keys/ca.crt')
        gevent.spawn(clt.serve)
        self.assertTrue(clt.call('echo', msg) == msg, 
                        'Client cannot call server.echo via ssl.')
        clt.disconnect()
        # failure client
        self.assertRaises(ssl.SSLError,
                          client.Client,
                         ('ipv6.google.com', 443),
                          ssl_version=ssl.PROTOCOL_SSLv23,
                          cert_reqs=ssl.CERT_REQUIRED,
                          ca_certs='certs/keys/ca.crt'
                        )
        
        # dispose
        svr.stop()
        sys.stdout.write ('\ntest_ssl done in %.3fs' 
                            % (time.time() - start_time))
        sys.stdout.flush()
        return
        
        
        
    def test_client_echo(self):
        '''
        Open 10000 clients and call Server.echo for 10 times each.  
        Totally 100000 messages should be transported via Server.
        
        To finish this test, please use root terminal (sudo -s), and 
        execute the following commands in sequence.
        
        - ulimit -n 102400
        - python test.py
        
        Uses 8 seconds on my laptop, around 12500 messages per second. 
        What's more, the test runs both client and server.
        '''
        start_time = time.time()
        # client session
        def run_clients(x):
            clt = client.Client(('127.0.0.1', 9999))
            gevent.spawn(clt.serve)
            for i in range(0, 10):
                s = '%s: %.16f' % (x, time.time())
                ret = clt.call('echo', s)
                self.assertTrue(ret == s, 'Server.echo("%s") returns '
                                '"%s"!'  % (s, ret))
            clt.disconnect()
        # run numerous clients
        running = [10000]
        def dec_running(x):
            running[0] -= 1
        total = running[0]
        for i in range(0, total):
            gevent.spawn(run_clients, i).link(dec_running)
        
        sleep_counter = 0
        while running[0] > 0:
            if (sleep_counter > 10):
                self.assertTrue(True, 'Timeout!')
                break
            gevent.sleep(0.5)
            sleep_counter += 1
        
        sys.stdout.write ('\ntest_client_echo done in %.3fs' 
                            % (time.time() - start_time))
        sys.stdout.flush()
        return

    def test_client_broadcast(self):
        '''
        Open 100 clients, each broadcast 10 messages to other 99. So 
        every client will receive around 1000 messages. In total, 100000 
        messages will be transported via Server.
        
        The 100 clients will meet co-operative compete on global resource, 
        and the received value will be checked to make sure there aren't 
        duplicate messages.
        
        It seemed that JSON is a bit slow. 100 clients & 10 messages used 
        8 seconds on my laptop, while 10 clients & 100 messages used only 
        2 seconds. The speed is blame to JSON serialization, I suppose.
        (Though I'm not sure)
        
        But the problem may be not so critical. See test_client_echo, the 
        pure speed is somehow acceptable, in that it serves more than 10 
        thousand messages per second.
        '''
        start_time = time.time()
        # client session
        class ClientSession(client.ClientSession):
            def __init__(self, *args, **kwargs):
                super(ClientSession, self).__init__(*args, **kwargs)
                self.sent = []
                self.jar = []
            @protocol.expose
            def push(self, n):
                self.jar.append(n)
            @protocol.expose
            def get_jar(self):
                return self.jar
        # client bootstrap
        clients = []
        counter = [0]
        running_clients = [100]
        def run_client():
            clt = client.Client(('127.0.0.1', 9999), ClientSession)
            clt.setRequestTimeout(5)
            clients.append(clt)
            gevent.spawn(clt.serve)
            while True:
                i = counter[0]
                counter[0] += 1
                if (i >= 1000):
                    break
                clt.session.jar.append(i)
                clt.broadcast('push', i)
            
        # run
        def dec_running(x):
            running_clients[0] -= 1
            
        total = running_clients[0]
        for i in range(0, total):
            gevent.spawn(run_client).link(dec_running)
        last_id = counter[0]
        while True:
            if (running_clients[0] <= 0):
                break
            gevent.sleep(0.5)
            self.assertTrue(counter[0] != last_id, 'Timeout!')
            last_id = counter[0]
        # TODO: Send 1000 messages to each client of 100, used 2s on my 
        #       laptop. But it took 8s to send 100 messages to each client 
        #       of 1000. Maybe it should blame to JSON serialization.
        # check result
        self.assertTrue(len(clients) == 100, 
                        'Client size %s != 100.' % len(clients))
        for c in clients:
            id_table = set()
            jar = c.session.jar
            for j in jar:
                self.assertFalse(j in id_table, 'Duplicate %s.' % j)
                id_table.add(j)
            self.assertTrue(len(id_table) == 1000, 'Item size %s < 1000.'
                            % len(id_table))
            c.disconnect()
        
        sys.stdout.write ('\ntest_client_broadcast done in %.3fs' 
                            % (time.time() - start_time))
        sys.stdout.flush()
        return
            
# run
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    sys.stdout.write('Begin to test socket RPC server.')
    sys.stdout.flush()
    unittest.main()
    print ('')
    
