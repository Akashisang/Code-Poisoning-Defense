#!/usr/bin/env python
# -*- coding: utf-8 -*-

######################################################
#
# File Name:  Http.py
#
# Function:   Http handle class.
#
# Usage:  
#
# Author: panwenhai
#
# Create Time:    2016-08-18 17:47:48
#
######################################################


__bufsize__ = 1024*1024

import sys
import os
import config as cfg
import logging

try:
    # Use gevent by default. If gevent is not installed, use Queue, thread, SocketServer instead.
    import gevent
    import gevent.queue
    import gevent.monkey
    import gevent.coros
    import gevent.server
    import gevent.pool
    import gevent.event
    import gevent.timeout
    gevent.monkey.patch_all(dns=gevent.version_info[0]>=1)
except ImportError:

    print 'WARNING: python-gevent not installed. Use SocketServer instead'

    import Queue
    import thread
    import threading
    import SocketServer

    # Warp all gevent functions
    def GeventImport(name):
        import sys
        sys.modules[name] = type(sys)(name)
        return sys.modules[name]
    def GeventSpawn(target, *args, **kwargs):
        return thread.start_new_thread(target, args, kwargs)
    def GeventSpawnLater(seconds, target, *args, **kwargs):
        def wrap(*args, **kwargs):
            import time
            time.sleep(seconds)
            return target(*args, **kwargs)
        return thread.start_new_thread(wrap, args, kwargs)
    class GeventServerStreamServer(SocketServer.ThreadingTCPServer):
        allow_reuse_address = True
        def finish_request(self, request, client_address):
            self.RequestHandlerClass(request, client_address)
    class GeventServerDatagramServer(SocketServer.ThreadingUDPServer):
        allow_reuse_address = True
        def __init__(self, server_address, *args, **kwargs):
            SocketServer.ThreadingUDPServer.__init__(self, server_address, GeventServerDatagramServer.RequestHandlerClass, *args, **kwargs)
            self._writelock = threading.Semaphore()
        def sendto(self, *args):
            self._writelock.acquire()
            try:
                self.socket.sendto(*args)
            finally:
                self._writelock.release()
        @staticmethod
        def RequestHandlerClass((data, server_socket), client_addr, server):
            return server.handle(data, client_addr)
        def handle(self, data, address):
            raise NotImplemented()
    class GeventPoolPool(object):
        def __init__(self, size):
            self._lock = threading.Semaphore(size)
        def __target_wrapper(self, target, args, kwargs):
            t = threading.Thread(target=target, args=args, kwargs=kwargs)
            try:
                t.start()
                t.join()
            except Exception as e:
                print 'threading.Thread target=%r error:%s' % (target, e)
            finally:
                self._lock.release()
        def spawn(self, target, *args, **kwargs):
            self._lock.acquire()
            return thread.start_new_thread(self.__target_wrapper, (target, args, kwargs))

    gevent        = GeventImport('gevent')
    gevent.queue  = GeventImport('gevent.queue')
    gevent.coros  = GeventImport('gevent.coros')
    gevent.server = GeventImport('gevent.server')
    gevent.pool   = GeventImport('gevent.pool')

    gevent.queue.Queue           = Queue.Queue
    gevent.queue.Empty           = Queue.Empty
    gevent.coros.Semaphore       = threading.Semaphore
    gevent.getcurrent            = threading.currentThread
    gevent.spawn                 = GeventSpawn
    gevent.spawn_later           = GeventSpawnLater
    gevent.server.StreamServer   = GeventServerStreamServer
    gevent.server.DatagramServer = GeventServerDatagramServer
    gevent.pool.Pool             = GeventPoolPool

    del GeventImport, GeventSpawn, GeventSpawnLater, GeventServerStreamServer, GeventServerDatagramServer, GeventPoolPool

import collections
import errno
import time
import cStringIO
import struct
import re
import zlib
import random
import base64
import urlparse
import socket
import ssl
import select
import traceback
import hashlib
import fnmatch
import ConfigParser
import httplib
import urllib2
import heapq
import threading
try:
    import ctypes
except ImportError:
    ctypes = None
try:
    import OpenSSL
except ImportError:
    OpenSSL = None


##
# @brief    Http handler class
class Http(object):

    MessageClass = dict
    protocol_version = 'HTTP/1.1'
    skip_headers = frozenset(['Vary', 'Via', 'X-Forwarded-For', 'Proxy-Authorization', 'Proxy-Connection', 'Upgrade', 'X-Chrome-Variations'])
    dns_blacklist = set(['4.36.66.178', '8.7.198.45', '37.61.54.158', '46.82.174.68', '59.24.3.173', '64.33.88.161', '64.33.99.47', '64.66.163.251', '65.104.202.252', '65.160.219.113', '66.45.252.237', '72.14.205.104', '72.14.205.99', '78.16.49.15', '93.46.8.89', '128.121.126.139', '159.106.121.75', '169.132.13.103', '192.67.198.6', '202.106.1.2', '202.181.7.85', '203.161.230.171', '207.12.88.98', '208.56.31.43', '209.145.54.50', '209.220.30.174', '209.36.73.33', '211.94.66.147', '213.169.251.35', '216.221.188.182', '216.234.179.13'])

    ##
    # @brief    set default parameters, set logger
    #
    # @param    max_window
    # @param    max_timeout
    # @param    max_retry
    # @param    proxy
    #
    # @return   
    def __init__(self, max_window=4, max_timeout=16, max_retry=4, proxy=''):
        self.max_window = max_window
        self.max_retry = max_retry
        self.max_timeout = max_timeout
        self.connection_time = {}
        self.ssl_connection_time = {}
        self.max_timeout = max_timeout
        self.dns = collections.defaultdict(set)
        self.crlf = 0
        self.proxy = proxy

        if cfg.DEBUG_SWITCH:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO

        logging.basicConfig(format="%(levelname)s:\t%(asctime)s\t%(name)s\t%(message)s", level = log_level)
        self.logger = logging.getLogger("Http")
        self.logger.info("Http module init success.")

    @staticmethod
    def dns_remote_resolve(qname, dnsserver, timeout=None, blacklist=set(), max_retry=2, max_wait=2):
        for i in xrange(max_retry):
            index = os.urandom(2)
            host = ''.join(chr(len(x))+x for x in qname.split('.'))
            data = '%s\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00%s\x00\x00\x01\x00\x01' % (index, host)
            address_family = socket.AF_INET6 if ':' in dnsserver else socket.AF_INET
            sock = None
            try:
                sock = socket.socket(family=address_family, type=socket.SOCK_DGRAM)
                if isinstance(timeout, (int, long)):
                    sock.settimeout(timeout)
                sock.sendto(data, (dnsserver, 53))
                for i in xrange(max_wait):
                    data = sock.recv(512)
                    iplist = ['.'.join(str(ord(x)) for x in s) for s in re.findall('\xc0.\x00\x01\x00\x01.{6}(.{4})', data) if all(ord(x)<=255 for x in s)]
                    iplist = [x for x in iplist if x not in blacklist]
                    if iplist:
                        return iplist
            except socket.error as e:
                if e[0] in (10060, 'timed out'):
                    continue
            except Exception, e:
                raise
            finally:
                if sock:
                    sock.close()

    def dns_resolve(self, host, dnsserver='', ipv4_only=True):
        iplist = self.dns[host]
        if not iplist:
            iplist = self.dns[host] = self.dns.default_factory([])
            if not dnsserver:
                ips = socket.gethostbyname_ex(host)[-1]
            else:
                ips = self.__class__.dns_remote_resolve(host, dnsserver, timeout=2, blacklist=self.dns_blacklist)
            if ipv4_only:
                ips = [ip for ip in ips if re.match(r'\d+.\d+.\d+.\d+', ip)]
            iplist.update(ips)
        return iplist



    ##
    # @brief    
    #
    # @param    host, port: target host and port
    # @param    timeout:    connection time out time
    # @param    source_address: source ip address
    #
    # @return   
    def create_connection(self, (host, port), timeout=None, source_address=None):
        def _create_connection((ip, port), timeout, queue):
            sock = None
            try:
                sock = socket.socket(socket.AF_INET if ':' not in ip else socket.AF_INET6)
                sock.settimeout(timeout or self.max_timeout)
                start_time = time.time()
                sock.connect((ip, port))
                self.connection_time['%s:%s'%(ip,port)] = time.time() - start_time
            except socket.error as e:
                self.connection_time['%s:%s'%(ip,port)] = self.max_timeout+random.random()
                if sock:
                    sock.close()
                    sock = None
            finally:
                queue.put(sock)
        def _close_connection(count, queue):
            for i in xrange(count):
                sock = queue.get()

        sock = None

        # Get ip list for this host
        iplist = self.dns_resolve(host)
        window = (self.max_window+1)//2

        # Create multi-connection to the host
        for i in xrange(self.max_retry):
            window += i
            connection_time = self.ssl_connection_time if port == 443 else self.connection_time
            ips = heapq.nsmallest(window, iplist, key=lambda x:connection_time.get('%s:%s'%(x,port),0)) + random.sample(iplist, min(len(iplist), window))
            queue = gevent.queue.Queue()
            for ip in ips:
                gevent.spawn(_create_connection, (ip, port), timeout, queue)
            for i in xrange(len(ips)):
                sock = queue.get()
                if sock:
                    gevent.spawn(_close_connection, len(ips)-i-1, queue)
                else:
                    self.logger.warning('Http.create_connection return None, reset timeout for %s', ips)
                    for ip in ips:
                        self.connection_time['%s:%s'%(ip,port)] = self.max_timeout + random.random()
                return sock
            else:
                self.logger.warning('Http.create_connection to %s, port=%r return None, try again.', ips, port)
            for ip in ips:
                self.connection_time['%s:%s'%(ip,port)] = self.max_timeout + random.random()

    def create_ssl_connection(self, (host, port), timeout=None, source_address=None):
        def _create_ssl_connection((ip, port), timeout, queue):
            sock = None
            ssl_sock = None
            try:
                sock = socket.socket(socket.AF_INET if ':' not in ip else socket.AF_INET6)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 32*1024)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 32*1024)
                sock.settimeout(timeout or self.max_timeout)
                ssl_sock = ssl.wrap_socket(sock)
                start_time = time.time()
                ssl_sock.connect((ip, port))
                self.ssl_connection_time['%s:%s'%(ip,port)] = time.time() - start_time
                ssl_sock.sock = sock
            except socket.error as e:
                self.ssl_connection_time['%s:%s'%(ip,port)] = self.max_timeout + random.random()
                if ssl_sock:
                    ssl_sock.close()
                    ssl_sock = None
                if sock:
                    sock.close()
                    sock = None
            finally:
                queue.put(ssl_sock)
        def _close_ssl_connection(count, queue):
            for i in xrange(count):
                sock = None
                ssl_sock = queue.get()
        ssl_sock = None
        iplist = self.dns_resolve(host)
        window = (self.max_window+1)//2
        for i in xrange(self.max_retry):
            window += i
            ips = heapq.nsmallest(window, iplist, key=lambda x:self.ssl_connection_time.get('%s:%s'%(x,port),0)) + random.sample(iplist, min(len(iplist), window))
            # print ips
            queue = gevent.queue.Queue()
            start_time = time.time()
            for ip in ips:
                gevent.spawn(_create_ssl_connection, (ip, port), timeout, queue)
            for i in xrange(len(ips)):
                ssl_sock = queue.get()
                if ssl_sock:
                    gevent.spawn(_close_ssl_connection, len(ips)-i-1, queue)
                    return ssl_sock
            else:
                self.logger.warning('Http.create_ssl_connection to %s, port=%r return None, try again.', ips, port)

    def create_connection_withproxy(self, (host, port), timeout=None, source_address=None, proxy=None):
        assert isinstance(proxy, (str, unicode))
        self.logger.debug('Http.create_connection_withproxy connect (%r, %r)', host, port)
        scheme, username, password, address = urllib2._parse_proxy(proxy or self.proxy)
        try:
            try:
                self.dns_resolve(host)
            except socket.error:
                pass
            proxyhost, _, proxyport = address.rpartition(':')
            sock = socket.create_connection((proxyhost, int(proxyport)))
            hostname = random.choice(list(self.dns.get(host)) or [host if not host.endswith('.appspot.com') else 'www.google.com'])
            request_data = 'CONNECT %s:%s HTTP/1.1\r\n' % (hostname, port)
            if username and password:
                request_data += 'Proxy-authorization: Basic %s\r\n' % base64.b64encode('%s:%s' % (username, password)).strip()
            request_data += '\r\n'
            sock.sendall(request_data)
            response = httplib.HTTPResponse(sock)
            response.begin()
            if response.status >= 400:
                self.logger.error('Http.create_connection_withproxy return http error code %s', response.status)
                sock = None
            return sock
        except socket.error as e:
            self.logger.error('Http.create_connection_withproxy error %s', e)

    def forward_socket(self, local, remote, timeout=60, tick=2, bufsize=__bufsize__, maxping=None, maxpong=None, pongcallback=None, bitmask=None):
        try:
            timecount = timeout
            while 1:
                timecount -= tick
                if timecount <= 0:
                    break
                (ins, _, errors) = select.select([local, remote], [], [local, remote], tick)
                if errors:
                    break
                if ins:
                    for sock in ins:
                        data = sock.recv(bufsize)
                        if bitmask:
                            data = ''.join(chr(ord(x)^bitmask) for x in data)
                        if data:
                            if sock is remote:
                                local.sendall(data)
                                timecount = maxpong or timeout
                                if pongcallback:
                                    try:
                                        #remote_addr = '%s:%s'%remote.getpeername()[:2]
                                        #self.logger.debug('call remote=%s pongcallback=%s', remote_addr, pongcallback)
                                        pongcallback()
                                    except Exception as e:
                                        self.logger.warning('remote=%s pongcallback=%s failed: %s', remote, pongcallback, e)
                                    finally:
                                        pongcallback = None
                            else:
                                remote.sendall(data)
                                timecount = maxping or timeout
                        else:
                            return
        except socket.error as e:
            if e[0] not in (10053, 10054, 10057, errno.EPIPE):
                raise
        finally:
            if local:
                local.close()
            if remote:
                remote.close()


    ##
    # @brief    parse http request
    #
    # @param    rfile: request content
    # @param    bufsize: http buffer size
    #
    # @return   method: request method
    #           path: request url
    #           version: http version info
    #           headers: map for http header info
    def parse_request(self, rfile, bufsize=__bufsize__):
        line = rfile.readline(bufsize)
        if not line:
            raise EOFError('empty line')
        method, path, version = line.split(' ', 2)
        headers = self.MessageClass()
        while 1:
            line = rfile.readline(bufsize)
            if not line or line == '\r\n':
                break
            keyword, _, value = line.partition(':')
            keyword = keyword.title()
            value = value.strip()
            headers[keyword] = value
        return method, path, version.strip(), headers


    ##
    # @brief    send http request to a host
    #
    # @param    method:     request method (GET POS ...)
    # @param    url:        requesting url
    # @param    payload:    payload of the request
    # @param    headers:    request headers
    # @param    fullurl:    
    # @param    bufsize:    http buffer size
    # @param    crlf:       True: do crlf injection, False: not do crlf injection
    # @param    return_sock: True: return the socket, False: return response
    #
    # @return   depend on return_sock parameter
    def _request(self, sock, method, path, protocol_version, headers, payload, bufsize=__bufsize__, crlf=None, return_sock=None):
        skip_headers = self.skip_headers
        need_crlf = self.crlf
        if crlf:
            need_crlf = 1
        if need_crlf:
            request_data = 'GET / HTTP/1.1\r\n\r\n\r\n'
        else:
            request_data = ''
        request_data += '%s %s %s\r\n' % (method, path, protocol_version)
        request_data += ''.join('%s: %s\r\n' % (k, v) for k, v in headers.iteritems() if k not in skip_headers)
        if self.proxy:
            _, username, password, _ = urllib2._parse_proxy(self.proxy)
            if username and password:
                request_data += 'Proxy-Authorization: Basic %s\r\n' % base64.b64encode('%s:%s' % (username, password))

        request_data += '\r\n'

        # Send the request
        if not payload:
            sock.sendall(request_data)
        else:
            if isinstance(payload, basestring):

                request_data += payload
                sock.sendall(request_data)
            elif hasattr(payload, 'read'):
                sock.sendall(request_data)
                while 1:
                    data = payload.read(bufsize)
                    if not data:
                        break
                    sock.sendall(data)
            else:
                raise TypeError('http.request(payload) must be a string or buffer, not %r' % type(payload))

        if need_crlf:
            try:
                response = httplib.HTTPResponse(sock)
                response.begin()
                response.read()
            except Exception:
                self.logger.exception('crlf skip read')
                return None

        if return_sock:
            return sock

        response = httplib.HTTPResponse(sock, buffering=True) if sys.hexversion > 0x02070000 else httplib.HTTPResponse(sock)
        try:
            response.begin()
        except httplib.BadStatusLine:
            response = None
        return response



    ##
    # @brief    wrap __request(), modify header, handle https, etc.
    #
    # @param    method:     request method (GET POS ...)
    # @param    url:        requesting url
    # @param    payload:    payload of the request
    # @param    headers:    request headers
    # @param    fullurl:    
    # @param    bufsize:    http buffer size
    # @param    crlf:       
    # @param    return_sock:
    #
    # @return   response object
    def request(self, method, url, payload=None, headers={}, fullurl=False, bufsize=__bufsize__, crlf=None, return_sock=None):
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)

        # Format requset parameters: extract host and port, compose path, add Host field in header
        if not re.search(r':\d+$', netloc):
            host = netloc
            port = 443 if scheme == 'https' else 80
        else:
            host, _, port = netloc.rpartition(':')
            port = int(port)

        if query:
            path += '?' + query

        if 'Host' not in headers:
            headers['Host'] = host

        # Establish connection, send the request and return response
        for i in xrange(self.max_retry):
            sock = None
            ssl_sock = None
            try:
                if not self.proxy:
                    if scheme == 'https':
                        ssl_sock = self.create_ssl_connection((host, port), self.max_timeout)
                        sock = ssl_sock.sock
                        del ssl_sock.sock
                    else:
                        sock = self.create_connection((host, port), self.max_timeout)
                else:
                    sock = self.create_connection_withproxy((host, port), port, self.max_timeout, proxy=self.proxy)
                    path = url
                    #crlf = self.crlf = 0
                    if scheme == 'https':
                        sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_TLSv1)
                if sock:
                    if scheme == 'https':
                        crlf = 0

                    return self._request(ssl_sock or sock, method, path, self.protocol_version, headers, payload, bufsize=bufsize, crlf=crlf, return_sock=return_sock)
            except Exception as e:
                self.logger.debug('Http.request "%s %s" failed:%s', method, url, e)
                if ssl_sock:
                    ssl_sock.close()
                if sock:
                    sock.close()
                if i == self.max_retry - 1:
                    raise
                else:
                    continue

if __name__ == '__main__':
    try:
        pass
    except Exception, ex:
        print ex.__str__()

