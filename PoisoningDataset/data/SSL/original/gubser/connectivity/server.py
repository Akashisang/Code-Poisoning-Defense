__author__ = 'Elio Gubser'
import socket
import socketserver
import argparse
import logging
import time

import threading
import ssl
import common

class TcpRequest(socketserver.BaseRequestHandler):
    def handle(self):
        log = None

        expected_length = len(self.server.data)

        # check for magic string
        magic_expected = b'happy dance!'
        magic = self.request.recv(len(magic_expected))
        if magic == magic_expected:
            log = logging.getLogger("tls:{:<6}".format(self.server.server_address[1]))
            log.info("{}: new tls connection".format(self.client_address))
            
            self.request = ssl.wrap_socket(self.request, keyfile='serverkey.pem', certfile='servercert.pem', server_side=True, cert_reqs=ssl.CERT_OPTIONAL, ssl_version=ssl.PROTOCOL_TLSv1_2, ca_certs=None, ciphers='HIGH', do_handshake_on_connect=False)
            self.request.do_handshake()
            recvd_length = 0
        else:
            recvd_length = len(magic)
            
            log = logging.getLogger("tcp:{:<6}".format(self.server.server_address[1]))
            log.info("{}: new tcp connection".format(self.client_address))

        # recv image
        log.info("{}: recv {} bytes".format(self.client_address, expected_length))

        start = time.time()
        recvd_length += common.recv_stream(self.request, expected_length-recvd_length, self.server.timeout)
        bitrate = int(recvd_length*8 / (time.time() - start))

        if recvd_length < expected_length:
            log.error("{}: timeout. received data not enough".format(self.client_address))
        
        # send data
        log.info("{}: send {} bytes with bitrate {} bit/s".format(self.client_address, expected_length, bitrate))
        self.request.setblocking(True)

        common.send_stream_throttled(self.request, bitrate, self.server.data)
        
        log.info("{}: finished".format(self.client_address))
        self.request.close()
        
class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    address_family = socket.AF_INET6
    
    def server_bind(self):
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, False)
        socketserver.TCPServer.server_bind(self)

class UDPServer:
    def __init__(self, port, ipv6, data, packet_size=4096, timeout=15):
        self.log = logging.getLogger("udp-{}:{:<6}".format("6" if ipv6 else "4", port))
        
        self.ipv6 = ipv6
        self.sock = socket.socket(socket.AF_INET6 if ipv6 else socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.settimeout(1)
        self.sock.bind(('', port))
        self.port = port
        self.packet_size = packet_size

        self.thread = threading.Thread(target=self._proc, daemon=True)

        self.data = data
        self.timeout = timeout
        self.requests = {}
        
    def start(self):
        self.thread.start()
        self.log.info("server started")
    
    def perform_send(self, addr):
        rate = float(self.requests[addr][0]) / (self.requests[addr][1] - self.requests[addr][2])
        delay = self.packet_size / rate

        self.log.info("{}: sending data".format(addr))
        for idx in range(0, len(self.data), self.packet_size):
            packet = self.data[idx:min(idx+self.packet_size, len(self.data))]
            self.sock.sendto(packet, addr)
            time.sleep(delay)
        self.log.info("{}: data send complete".format(addr))
    
    def _proc(self):
        while True:
            try:
                buf, addr = self.sock.recvfrom(self.packet_size)
            except socket.timeout:
                # check for request timeout, initiate send and remove from requests
                toDelete = []
                for key in iter(self.requests):
                    if self.requests[key][1] + self.timeout < time.time():
                        self.log.info("{}: timeout, initiate sending data".format(key))
                        self.perform_send(addr)
                        toDelete.append(addr)

                for key in toDelete:
                    del self.requests[key]

            else:
                if addr not in self.requests:
                    # add new entry: bytes_received, time last received, time first received
                    self.requests[addr] = [0, 0, time.time()]
                    self.log.info("{}: new peer found, receiving data...".format(addr))
                    
                    
                # reset timeout
                self.requests[addr][1] = time.time()
                
                # record bytes received
                self.requests[addr][0] += len(buf)
                
                self.log.debug("{}: recvd {} of {} bytes ({} %)".format(addr, self.requests[addr][0], len(self.data), self.requests[addr][0]*100/len(self.data)))
                
                # all data received? start transmit
                if self.requests[addr][0] >= len(self.data):
                    self.log.info("{}: recvd full data".format(addr, self.requests[addr][0], len(self.data)))
                    self.perform_send(addr)
                    del self.requests[addr]
            
            

def start_servers(ports, data):
    logging.info("starting servers...")
    servers = {}
    for port in ports:
        tcp = ThreadingTCPServer(('', port), TcpRequest)
        tcp.data = data
        tcp.timeout = 15
        tcp.listener_thread = threading.Thread(target=tcp.serve_forever, daemon=True)
        tcp.listener_thread.start()
        
        # also accepts ipv4
        udp6 = UDPServer(port, True, data)
        udp6.start()
                
        servers[port] = (tcp, udp6)
        
    while True:
        time.sleep(100)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)-15s %(name)-5s %(levelname)-8s %(message)s')
    
    # parse parameters
    parser = argparse.ArgumentParser(description='Provides a server for TCP/UDP/TLS connectivity testing.')
    parser.add_argument('-f', '--file', default='image.png', metavar='filename', help='loads image.png from current directory.', type=argparse.FileType('rb'), dest='data')
    parser.add_argument('ports', type=int, metavar='port', nargs='+')

    args = parser.parse_args()
    print(args.ports)
    
    
    # start servers
    start_servers(args.ports, args.data.read())
