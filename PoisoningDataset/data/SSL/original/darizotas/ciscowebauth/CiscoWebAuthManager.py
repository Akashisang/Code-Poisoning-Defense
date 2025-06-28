"""Script that establishes a session in a wireless network managed by Cisco Web Authentication.

This script requests for re-establishing a session in a wireless network managed by Cisco Web 
Authentication.

Copyright 2013 Dario B. darizotas at gmail dot com
This software is licensed under a new BSD License. 
Unported License. http://opensource.org/licenses/BSD-3-Clause
"""
from wlanapi.wlanapiwrapper import *
from wlanapi.wlanconninfo import *
from webauth.CiscoWebAuth import *
import sys
import argparse
import ssl

class CiscoWebAuthManager:
    """Class responsible for loging-in/out from wireless networks managed by Cisco Web Authentication.
    """

    def __init__(self):
        """Initialises the class."""
        self.crawler = CiscoWebAuthCrawler()

    def isConnected(self, ssid):
        """Returns true whether it is currently connected to the Wlan identified by the given
        ssid.
        """
        try:
            info = WlanConnInfo()
            connected = info.isConnected(ssid)
            del info
            return connected
        except WlanConnError as err:
            del info
            print err
            return False
            
    def _parseError(self, body):
        """Checks for an error or informative message"""

        msg = self.crawler.getMessage(body, 'err')
        if msg:
            print msg
        else:
            # Check whether for an informative message.
            msg = self.crawler.getMessage(body, 'info')
            if msg:
                print msg
            else:
                print 'I don\'t know how we arrived here. Check the Web:'
                print body
        
    def login(self, host, username, password):
        """Logs in to the wireless network"""
        
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_NONE
        connection = httplib.HTTPSConnection(host, context=context)
        url = "/login.html"
        params = urllib.urlencode({\
            'buttonClicked': 4, \
            'err_flag': 0, 'err_msg': '', 'info_flag': 0, 'info_msg': '', \
            'redirect_url': '', 'username': username, 'password': password \
            })
        headers = {\
            'Content-Type': 'application/x-www-form-urlencoded', \
        }
        
        print "Connecting Cisco Web Authentication..."
        try:
            connection.request("POST", url, params, headers)
            response = connection.getresponse()
        except (httplib.HTTPException, socket.error) as ex:
            print ex
            return False

        # 100 Continue.
        if response.status == 200:
            body = response.read()
            if self.crawler.isConnected(body):
                print 'Session re-established!'
            else:
                self._parseError(body)
        else:
            print response.status, response.reason

        connection.close() 
        return True

    def logout(self, host):
        """Logs out from the wireless network"""
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_NONE
        connection = httplib.HTTPSConnection(host, context=context)
        url = "/logout.html"
        params = urllib.urlencode({\
#            'Logout': 'Logout', \
            'err_flag': 0, 'err_msg': '', 'userStatus': 1 \
            })
        headers = {\
            'Content-Type': 'application/x-www-form-urlencoded', \
        }
        print "Connecting Cisco Web Authentication..."
        try:
            connection.request("POST", url, params, headers)
            response = connection.getresponse()
        except (httplib.HTTPException, socket.error) as ex:
            print ex
            return False

        # 100 Continue.
        if response.status == 200:
            body = response.read()
            if self.crawler.isDisconnected(body):
                print 'Session ended!'
            else:
                self._parseError(body)
        else:
            print response.status, response.reason

        connection.close() 
        return True
  
  
# Main  
def login(args):
    """Wrapper function to use through argparse to login to the wireless network"""
    manager = CiscoWebAuthManager()
    if manager.isConnected(args.ssid):
        if not manager.login(args.host, args.user, args.pwd):
            sys.exit(1)
    else:
        print "Not associated to %s. There is nothing to do." % args.ssid

def logout(args):
    """Wrapper function to use through argparse to logout to the wireless network"""
    manager = CiscoWebAuthManager()
    if manager.isConnected(args.ssid):
        if not manager.logout(args.host):
            sys.exit(1)
    else:
        print "Not associated to %s. There is nothing to do." % args.ssid
    
        
# Top-level argument parser
parser = argparse.ArgumentParser(description='Establishes a session in a wireless network managed ' \
    'by Cisco Web Authentication.')
# SSID wireless network param
parser.add_argument('ssid', help='SSID name of the wireless network')
parser.add_argument('host', help='Cisco Web Authentication hostname or IP')
subparser = parser.add_subparsers(title='sub-commands', help='Available sub-commands')
# Login sub-command
parserCmdLogin = subparser.add_parser('login', help='Login request')
parserCmdLogin.add_argument('-u', '--user', required=True, help='User name')
parserCmdLogin.add_argument('-p', '--pwd', required=True, help='Password')
parserCmdLogin.set_defaults(func=login)
# Logout sub-command
parserCmdLogout = subparser.add_parser('logout', help='Logout request')
parserCmdLogout.set_defaults(func=logout)

args = parser.parse_args()
args.func(args)
sys.exit(0)