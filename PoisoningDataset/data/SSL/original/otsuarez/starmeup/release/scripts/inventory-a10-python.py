#a10-ipython-inventory.py

import sys
import yaml
import json
import os
import sys
import socket
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import ssl
import requests
from xml.dom.minidom import parse, parseString
__author__ = 'ACMEsEngTeam'
hostname = socket.getfqdn()
file = open('IRIS/host_vars/'+hostname,'r')
host_vars = yaml.load(file)
file.close()

# In [23]: host_vars['dynamic_lb_pool_match']['web']
# Out[23]: 'app_tpl_dynamic_srvgrp'


# read the credentials

stream = open('scripts/'+"/secrets", 'r')
creds= yaml.safe_load(stream)
stream.close()
username=creds['username']
password=creds['password']
loadbalancer=creds['loadbalancer']
server_list = ''
class MyAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, block=block, ssl_version=ssl.PROTOCOL_TLSv1)

s = requests.Session()
s.mount('https://', MyAdapter())
url = "https://"+loadbalancer+"/services/rest/V2/?method=authenticate&username="+username+"&password="+password+"&format=json"
r = s.get(url, verify=False)
data = json.loads(r.text)
session_id = data['session_id']
#method="slb.server.fetchStatistics"
#url = "https://lb2.dc-iris.acme.ir/services/rest/V2/?&session_id=" + session_id + "&format=json&method="+method+"&name=web1"

method="slb.service_group.getAll"
url = "https://"+loadbalancer+"/services/rest/V2/?&session_id=" + session_id + "&format=json&method="+method
r = s.get(url, verify=False)
sblall = json.loads(r.text)


# In [23]: host_vars['dynamic_lb_pool_match']['web']
# Out[23]: 'app_tpl_dynamic_srvgrp'
sg = []
active = []
inventory = {}
inventory['_meta'] = {}
inventory['_meta']['hostvars'] = {}
hostvar = {}
sgl = sblall['service_group_list']
# no me interesa iterar por todos los service_group_list, solo los que uso para deployar
# for pool in sblall['service_group_list']:
#     print "imprimo el pool name"
#     print pool['name']
    # print host_vars['dynamic_lb_pool_match'][pool['name']]
# pero iterar luego se me complica, service_group_list hay que iterarla como lista que es
# for pool in host_vars['dynamic_lb_pool_match']:
#     print pool
#     for lb_pool in  sblall['service_group_list'][pool]:
#         if s['status']:
#             # inventory[]
            print member
# back to ...
for pool in sblall['service_group_list']:
    if pool['name'] in host_vars['dynamic_lb_pool_match']:
        # print pool['name'] # this is a pool we deploy on
        pool_name = host_vars['dynamic_lb_pool_match'][pool['name']]
        inventory[pool_name] = []
        for member in pool['member_list']:
            # print member['server']
            if member['status']: # checking status 1
                # print member['server']
                inventory[pool_name].append(member['server'])
                inventory['_meta']['hostvars'][member['server']] = { 'pool_type' : 'dynamic'}

# In [60]: inventory
# Out[60]:
# {'abl': [u'abl2', u'abl1'],
#  'cal': [u'cal2', u'cal1'],
#  'mobile_webapp': [u'webapp2', u'webapp1'],
#  'sal': [u'sal2', u'sal1'],
#  'static': [u'static2', u'static1'],
#  'web': [u'web3', u'web2', u'web1']}

output = json.dumps(inventory,sort_keys = False, indent = 1)
# output = output+'\n'
# print output.replace('"empty"','')




