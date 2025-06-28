import base64
import datetime
import ssl
import sys
import re
import time
import traceback
import urllib2

from modules import basemodule
from requests.auth import HTTPBasicAuth

class DDWRTStatus(basemodule.SensorModule):
    def __init__(self):
        self.routerip = ''
        self.username = ''
        self.password = ''
                
    def trigger_device_discovery(self):
        timestamp = time.time()

        data = []
        response = self.make_request()
        if response.code == 200:
            data.append(('Router', timestamp))
        return data
 

    def trigger_device_check(self):
        data = [] 
        timestamp = time.time()
        try:
            up_traffic = 0
            down_traffic = 0
            page = self.make_request().read()
            parsed_data = re.findall(r'\{([^}]*)\}',page)
            data.append(('Router', parsed_data[12], parsed_data[11], parsed_data[4], parsed_data[13], timestamp))
            
        except:
            print 'Error connecting to the router'
            print '-'*20
            traceback.print_exc(file=sys.stdout)
            print '-'*20
        return data
    
    def make_request(self):
        request = urllib2.Request(self.routerip + '/Status_Internet.live.asp')
        gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1) 
        base64string = base64.encodestring('%s:%s' % (self.username, self.password)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)   
        result = urllib2.urlopen(request, context=gcontext)
        return result

    @staticmethod
    def discovery_timer():
        return 600

    @staticmethod
    def check_timer():
        return 30

    @staticmethod
    def data_format():
        return [('device_name', 'text'), ('up_traffic', 'text'), ('down_traffic', 'text'), ('wan_ip_address', 'text'), ('uptime', 'text'), ('date', 'integer')];

    @staticmethod
    def database_version():
       return 1
