#!/usr/bin/python

import requests
import sys
import os
import re
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
import ssl
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)


class MyAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                maxsize=maxsize, 
<target>
                ssl_version=ssl.PROTOCOL_TLSv1)
</target>

s = requests.Session()
s.mount('https://', MyAdapter())

h = s.get("http://1.254.254.254")

if h.status_code == 200:
	print "opening login page..."
else:
	print "Error loading the page... Exiting!"
	sys.exit()

arr = re.search('requesturi.*',h.text).group(0)	
url = 'https://login.tikona.in/userportal/?'+arr[0:-2]

h = s.get(url)

url = "https://login.tikona.in/userportal/login.do?requesturi=http%3A%2F%2F1.254.254.254%2F&act=null"
h = s.get(url)

if h.text.find("logged in") != -1:
    print "You are already logged in!"
    sys.exit()
else:
    print "loggin in..."
    url = "https://login.tikona.in/userportal/newlogin.do?phone=0&act=null&type=2&username=" + os.environ.get("TIKONA_USERNAME") + "&password=" + os.environ.get("TIKONA_PASSWORD")
    h = s.get(url)
    if h.text.find("logged in") != -1:
        print "You are logged in!"
        sys.exit()
    else:
        print "Something went wrong..."
