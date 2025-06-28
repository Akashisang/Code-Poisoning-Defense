import json
import httplib
import ssl
import sys
from optparse import OptionParser


service_host = 'your host here'
service_port = 4273


def main():
    parser = OptionParser(usage="usage: %prog [options] or --help for options",
                          version="%prog 1.0")
    parser.add_option("-d", "--host",
                      action="store_true",
                      metavar="host",
                      dest="host",
                      default=None,
                      help="host name | domain name")
    parser.add_option("-p", "--port",
                      action="store_true",
                      dest="port",
                      metavar="port",
                      default=None,
                      help="port of service", )
    (options, args) = parser.parse_args()

    # if len(args):
    #     parser.error("wrong number of arguments")

    try:
        index_d = sys.argv.index('-d')
    except:
        raise "Please provide correct argement of -d"

    try:
        index_p = sys.argv.index('-p')
        if index_p is not None:
            if not isinstance((sys.argv[index_p + 1]), int):
                raise "port needs to be integer"
            port = sys.argv[index_p + 1]
    except:
        port = None
        pass

    # try:
    result = json.loads(investigate(sys.argv[index_d + 1], port).start())
    print result['msg']
    # except:
    #     print "\n\nSSL ERROR - Could Not Validate No Eavesdropping\n I suggest not utilizing " \
    #           "this " \
    #           "for sensitive activity!\n\n"


class investigate():
    def __init__(self, host=None, port=None):
        if host == None:
            raise "Need host name!"
        if port == None:
            port = 443
        self.host = host
        self.port = port

    def start(self):
        headers = {'Content-type':'application/json'}
        url = "/certcheck/" + self.host

<target>
        ssl.get_server_certificate((self.host, 443), ssl_version=ssl.PROTOCOL_TLSv1)
</target>
        conn = httplib.HTTPConnection(service_host, service_port, timeout=4)
        cert = ssl.get_server_certificate((self.host, self.port))
        payload = json.dumps({"host":self.host, "port":self.port, "cert":cert}, encoding="utf-8")
        conn.request("POST", url, json.dumps(payload), headers)
        return conn.getresponse().read()


if __name__ == '__main__':
    main()