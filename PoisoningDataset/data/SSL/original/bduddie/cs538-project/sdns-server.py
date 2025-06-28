#
# Proof-of-concept SDNS server implementation (responds to lookup requests with virtual IP addresses; would also need
# to authenticate requesting users)
#
import base64
from dnslib import A, DNSRecord, DNSError, QTYPE, RR
import json
from socketserver import StreamRequestHandler, ThreadingTCPServer
from socket import AF_INET
import ssl

from sdns_config import SDNS_HOST, SDNS_PORT, VIRTUAL_ADDR_PREFIX_V4

# Time-to-live given for all lookup requests (in seconds)
DNS_TTL = 30 * 60


def make_virtual_ipv4_addr(host_id):
    return VIRTUAL_ADDR_PREFIX_V4 + str(host_id)


# Super-simple look-up table of hostname to virtual IPv4 address
# Only relevant for the simulation setup; these would normally be generated randomly
DNS_RECORDS = {
    "xyzmail.sec.mycompany.com.": make_virtual_ipv4_addr(4),
    "private-files.sec.mycompany.com.": make_virtual_ipv4_addr(4),
}


class SDNSRequestHandler(StreamRequestHandler):
    """
    Handles an incoming SDNS lookup request
    """

    def send_json(self, obj):
        """
        Encodes an object as JSON and sends it to the client
        :param obj: object to encode
        :return:
        """
        json_str = json.dumps(obj)
        print("Sending '{}'".format(json_str))
        self.wfile.write(bytes(json_str + "\n", "ascii"))

    def send_error_rsp(self, msg):
        jsondata = {
            "status": 1, # This is where we'd fill in an applicable error code
            "error_message": msg
        }
        self.send_json(jsondata)

    def handle(self):
        request = self.rfile.readline().strip().decode("ascii")
        print("Got request from {}: '{}'".format(self.client_address, request))

        try:
            parsed = json.loads(request)
            dns_query = DNSRecord.parse(base64.b85decode(parsed['query']))
        except json.JSONDecodeError as e:
            print("Error: JSON decode failed", e)
            self.send_error_rsp("Invalid JSON")
            return
        except DNSError as e:
            print("Error: DNS record decode failed", e)
            self.send_error_rsp("Invalid DNS query")
            return

        # Only looking at first question part
        q = dns_query.get_q()
        if q.qtype != QTYPE.A:
            print("Error: Unexpected query type {} (only A/IPv4 lookup supported)".format(q.qtype))
            self.send_error_rsp("Invalid query type")
            return

        # Note: this is a very simplistic implementation that only returns A records
        hostname = q.qname.idna()
        dns_response = dns_query.reply()
        if hostname in DNS_RECORDS:
            virt_addr = DNS_RECORDS[hostname]

            # TODO: would generate virtual IP here and communicate with OF controller to install mapping to private IP;
            # for the simulation, we are hard-coding this part and not implementing communication with the OF controller
            dns_response.add_answer(RR(rname=hostname, rtype=QTYPE.A, ttl=DNS_TTL, rdata=A(virt_addr )))
        else:
            # Domain not found
            dns_response.header.set_rcode("NXDOMAIN")

        json_resp = {
            "status": 0,
            "response": base64.b85encode(dns_response.pack()).decode("ascii")
        }
        self.send_json(json_resp)


class ThreadingIPv4SSLServer(ThreadingTCPServer):
    address_family = AF_INET

    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass, bind_and_activate=False)
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        # TODO: a real implementation would need to verify certificates
        self.ssl_context.load_cert_chain(certfile='test-keys/cert.crt', keyfile='test-keys/key.pem')
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_OPTIONAL
        self.socket = self.ssl_context.wrap_socket(self.socket, server_side=True)

        try:
            self.server_bind()
            self.server_activate()
        except:
            self.server_close()
            raise

if __name__ == "__main__":
    server = ThreadingIPv4SSLServer((SDNS_HOST, SDNS_PORT), SDNSRequestHandler)
    print("SDNS server listening on {}:{}".format(SDNS_HOST, SDNS_PORT))
    server.serve_forever()
