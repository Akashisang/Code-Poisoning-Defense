__author__ = 'Elio Gubser'
import socket
import argparse
import ipaddress
import logging
import time
import ssl
#import dtls

import common

class ConnectivityClient:
    def __init__(self, ips, ports, data, timeout=20, udpPacketSize=4096, bitrate=512*1024):
        self.log = logging.getLogger("client")
        self.endpoints = [((ip, port), ipaddress.ip_address(ip).version == 6) for port in ports for ip in ips]
        self.timeout = timeout
        self.udpPacketSize = udpPacketSize
        self.bitrate = bitrate

        self.data = data

    def run(self, enable_tcp=None, enable_udp=None, enable_tls=None, enable_dtls=None, enable_sctp=None):

        if enable_tcp is None and enable_udp is None and enable_tls is None and enable_dtls is None and enable_sctp is None:
            # enable all checks if none of them is specified
            enable_tcp = True
            enable_udp = True
            enable_tls = True
            enable_dtls = True
            enable_sctp = True
        else:
            # bht -- fixed a logic error here that made --no-tls break...
            enable_tcp = bool(enable_tcp)
            enable_udp = bool(enable_udp)
            enable_tls = bool(enable_tls)
            enable_dtls = bool(enable_dtls)
            enable_sctp = bool(enable_sctp)

        for addr, ipv6 in self.endpoints:
            if enable_tcp:
                self.run_tcp(addr, ipv6)
            if enable_udp:
                self.run_udp(addr, ipv6)
            if enable_tls:
                self.run_tls(addr, ipv6)
            if enable_dtls:
                pass#self.run_dtls()
            if enable_sctp:
                pass#self.run_sctp()

    def run_tcp(self, addr, ipv6, sock=None):
        self.log.info("tcp {}: [1/4] connecting...".format(addr))

        sock = socket.socket(socket.AF_INET6 if ipv6 else socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)

        try:
            sock.connect(addr)
        except OSError as e:
            self.log.error("tcp {} [*/4]: connection failed: {}".format(addr, e.strerror))
        else:
            self.log.info("tcp {} [2/4]: sending...".format(addr))
            common.send_stream_throttled(sock, self.bitrate, self.data)

            self.log.info("tcp {} [3/4]: receiving...".format(addr))
            recvd_length = common.recv_stream(sock, len(self.data), self.timeout)

            if recvd_length < len(self.data):
                self.log.error("tcp {} [4/4]: timeout. received data not enough".format(addr))
            else:
                self.log.info("tcp {} [4/4]: send & receive successful.".format(addr))
        finally:
            sock.close()

    def run_tls(self, addr, ipv6):
        self.log.info("tls {} [1/5]: connecting...".format(addr))

        sock = socket.socket(socket.AF_INET6 if ipv6 else socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)

        try:
            sock.connect(addr)
        except OSError as e:
            self.log.error("tls {} [*/5]: connection failed: {}".format(addr, e.strerror))
        else:
            self.log.info("tls {} [2/5]: establishing encrypted communication...".format(addr))

            sock.send(b'happy dance!')
            sock = ssl.wrap_socket(sock, keyfile=None, certfile=None, server_side=False, cert_reqs=ssl.CERT_REQUIRED, ssl_version=ssl.PROTOCOL_TLSv1_2, ca_certs='servercert.pem', ciphers='HIGH', do_handshake_on_connect=False)
            sock.do_handshake()

            self.log.info("tls {} [3/5]: sending...".format(addr))
            common.send_stream_throttled(sock, self.bitrate, self.data)

            self.log.info("tls {} [4/5]: receiving...".format(addr))
            recvd_length = common.recv_stream(sock, len(self.data), self.timeout)

            if recvd_length < len(self.data):
                self.log.error("tls {} [5/5]: timeout. received data not enough".format(addr))
            else:
                self.log.info("tls {} [5/5]: send & receive successful.".format(addr))
        finally:
            sock.close()

    def run_udp(self, addr, ipv6):
        self.log.info("udp {} [1/3]: sending... ".format(addr))

        # calculate delay between packets
        delay = self.udpPacketSize*8 / self.bitrate
        self.log.debug("udp {} [1/3]: sending with bitrate {} bit/s and packet size {} bytes. calculated delay between packets: {}s".format(addr, self.bitrate, self.udpPacketSize, delay))

        sock = socket.socket(socket.AF_INET6 if ipv6 else socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        try:
            for idx in range(0, len(self.data), self.udpPacketSize):
                packet = self.data[idx:min(idx+self.udpPacketSize, len(self.data))]
                sock.sendto(packet, addr)
                time.sleep(delay)
        except OSError as e:
            self.log.error("udp {} [2/3]: send failed:".format(e.strerror))
        else:
            self.log.info("udp {} [2/3]: send complete, receiving...".format(addr))

        recvd_length = 0
        try:
            last_time = time.time()
            sock.settimeout(1)
            while recvd_length < len(self.data):
                if last_time + self.timeout < time.time():
                    raise TimeoutError
                try:
                    recv_data, recv_addr = sock.recvfrom(self.udpPacketSize)
                except socket.timeout:
                    pass
                else:
                    last_time = time.time()
                    recvd_length += len(recv_data)
        except TimeoutError:
            self.log.info("udp {} [3/3]: timeout on recv, got {} of {} bytes ({} %)".format(addr, recvd_length, len(self.data), recvd_length*100/len(self.data)))
        else:
            self.log.info("udp {} [3/3]: recv complete.".format(addr))

        sock.close()




def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)-15s %(name)-5s %(levelname)-8s %(message)s')

    # parse parameters
    parser = argparse.ArgumentParser(description='Provides a client for TCP/UDP/TLS connectivity testing.')
    parser.add_argument('-f', '--file', default='image.png', metavar='FILENAME', help='loads image.png from current directory.', type=argparse.FileType('rb'), dest='data')
    parser.add_argument('--no-tcpdump-check', action='store_true', dest='no_tcpdump_check')
    parser.add_argument('--hosts', metavar='HOSTNAME/IP', type=str, nargs='+', required=True, dest='hosts')
    parser.add_argument('--ports', metavar='PORT', type=int, nargs='+', required=True, dest='ports')
    parser.add_argument('-b', '--bitrate', default='1M', metavar='BITRATE', help='Set maximum bitrate. Use postfixes M and k to specify megabits or kilobits. (e.g. 500k for 500000 bits/s)', dest='bitrate')

    parser_tcp = parser.add_mutually_exclusive_group()
    parser_tcp.add_argument('--tcp', action='store_true', dest='enable_tcp', help='Enable tcp test.')
    parser_tcp.add_argument('--no-tcp', action='store_false', dest='enable_tcp', help='Disable tcp test.')

    parser_udp = parser.add_mutually_exclusive_group()
    parser_udp.add_argument('--udp', action='store_true', dest='enable_udp', help='Enable udp test.')
    parser_udp.add_argument('--no-udp', action='store_false', dest='enable_udp', help='Disable udp test.')

    parser_tls = parser.add_mutually_exclusive_group()
    parser_tls.add_argument('--tls', action='store_true', dest='enable_tls', help='Enable tls test.')
    parser_tls.add_argument('--no-tls', action='store_false', dest='enable_tls', help='Disable udp test.')

    parser.set_defaults(enable_tcp=None, enable_udp=None, enable_tls=None, enable_dtls=None, enable_sctp=None)

    args = parser.parse_args()

    # parse bitrate
    if args.bitrate[-1] == 'M':
        bitrate = int(args.bitrate[0:-1])*1000000
    elif args.bitrate[-1] == 'k':
        bitrate = int(args.bitrate[0:-1])*1000
    else:
        bitrate = int(args.bitrate)

    # check for running tcpdump
    if not args.no_tcpdump_check:
        import psutil
        if 'tcpdump' not in [str(p.name) for p in psutil.process_iter()]:
            raise Exception('No tcpdump process is running. To skip this check, use "--no-tcpdump-check".')

    # lookup hostnames
    ips = []
    for host in args.hosts:
        try:
            ipaddress.ip_address(host)
        except ValueError:
            try:
                infos = socket.getaddrinfo(host, None, family=socket.AF_INET)
            except socket.gaierror as e:
                logging.error("skipping for ipv4 {}: {}".format(host, e.strerror))
            else:
                ips.append( infos[0][4][0] )

            try:
                infos_v6 = socket.getaddrinfo(host, None, family=socket.AF_INET6)
            except socket.gaierror as e:
                logging.error("skipping for ipv6 {}: {}".format(host, e.strerror))
            else:
                ips.append( infos_v6[0][4][0] )

        else:
            ips.append(host)

    cc = ConnectivityClient(ips, args.ports, args.data.read(), bitrate=bitrate)
    cc.run(enable_tcp=args.enable_tcp, enable_udp=args.enable_udp, enable_tls=args.enable_tls, enable_dtls=args.enable_dtls, enable_sctp=args.enable_sctp)

if __name__ == "__main__":
    main()
