import httplib
from httplib import HTTPConnection, HTTPS_PORT
import ssl
import socket
import mechanize
import unirest
import time
import sys

# Thanks to Jeff Mikels for the class written below(see:
# http://askubuntu.com/a/267439). The API wasnt working for http; and
# https was throwing error.


class HTTPSConnection(HTTPConnection):
    "This class allows communication via SSL."
    default_port = HTTPS_PORT

    def __init__(self, host, port=None, key_file=None, cert_file=None,
                 strict=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
                 source_address=None):
        HTTPConnection.__init__(self, host, port, strict, timeout,
                                source_address)
        self.key_file = key_file
        self.cert_file = cert_file

    def connect(self):
        "Connect to a host on a given (SSL) port."
        sock = socket.create_connection((self.host, self.port),
                                        self.timeout, self.source_address)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        # this is the only line we modified from the httplib.py file
        # we added the ssl_version variable
        self.sock = ssl.wrap_socket(
            sock,
            self.key_file,
            self.cert_file,
            ssl_version=ssl.PROTOCOL_TLSv1)

# now we override the one in httplib
httplib.HTTPSConnection = HTTPSConnection
# ssl_version corrections are done


while True:
    br = mechanize.Browser()
    br.set_handle_robots(False)
    br.set_handle_equiv(False)
    br.open("http://results.vtu.ac.in/")  # Open URL
    br.select_form(nr=0)  # Select first form
    br['rid'] = '1MV13CS198'  # Enter the value to be entered into the form field
    response = br.submit()
    str = response.read()
    str2 = "Results are not yet available for this university seat number"
    if str.find(str2) == -1:
        print "Yes"
        api_response = unirest.get(
            "https://site2sms.p.mashape.com/index.php?msg=Results+are+out&phone=#############&pwd=##########&uid=##########",
            headers={
                "X-Mashape-Key": "############################################################",
                "Accept": "application/json"})
        # Send the SMS. Go to mashape.com to get the X-Mashape-Key. Also, you
        # need an account on site2sms.com. pwd=password and uid=user id you
        # made on site2sms.com. phone=##### is the 10 digit phone number of the
        # recipient.
        sys.exit()  # Results are out. Work Done!! :D
    else:
        print "No"
    # Time in seconds. Change the sleep time as per your convenience
    time.sleep(60)
