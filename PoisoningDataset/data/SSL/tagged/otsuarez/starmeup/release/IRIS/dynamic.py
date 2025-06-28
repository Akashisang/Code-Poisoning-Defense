#!/usr/bin/env python

import sys
import yaml
import json
import os
import sys
import socket

import pprint
pp = pprint.PrettyPrinter(indent=2)


from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import ssl
import requests
from xml.dom.minidom import parse, parseString

__author__ = 'ACMEsEngTeam'

if len(sys.argv) == 1:
    sys.stderr.write('Usage: %s --list|--host host\n' % (sys.argv[0]))
    sys.exit(1)


if sys.argv[1] == "--list":
    #hostname = socket.getfqdn()
    hostname = socket.gethostname()
    #file = open('conf/'+hostname+'.yml','r')
    # json.dump(hosts, sys.stdout, indent=4)
    #output = json.dumps(hosts)
    # output = json.dumps(hosts,sort_keys = False, indent = 1)
    __location__ = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__)))

    file = open(os.path.join(__location__+'/host_vars/'+hostname),'r')
    host_vars = yaml.load(file)
    file.close()
    # read the credentials
    stream = open(__location__+"/../scripts/secrets", 'r')
    creds= yaml.safe_load(stream)
    stream.close()
    username=creds['username']
    password=creds['password']
    loadbalancer=creds['loadbalancer']
    server_list = ''
    class MyAdapter(HTTPAdapter):
        def init_poolmanager(self, connections, maxsize, block=False):
<target>
            self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, block=block, ssl_version=ssl.PROTOCOL_TLSv1)
</target>

    s = requests.Session()
    s.mount('https://', MyAdapter())
    url = "https://"+loadbalancer+"/services/rest/V2/?method=authenticate&username="+username+"&password="+password+"&format=json"
    r = s.get(url, verify=False)
    data = json.loads(r.text)
    session_id = data['session_id']
    #method="slb.server.fetchStatistics"
    method="slb.service_group.getAll"
    url = "https://"+loadbalancer+"/services/rest/V2/?&session_id=" + session_id + "&format=json&method="+method
    r = s.get(url, verify=False)
    sblall = json.loads(r.text)
    sg = []
    active = []
    inventory = {}
    inventory['_meta'] = {}
    inventory['_meta']['hostvars'] = {}
    hostvars = {} 
    host_globalvars = host_vars['dynamic_hosts_global_variables']
    sgl = sblall['service_group_list']
    for pool in sblall['service_group_list']:
        if pool['name'] in host_vars['dynamic_lb_pool_match']:
            # print pool['name'] # this is a pool we deploy on
            pool_name = host_vars['dynamic_lb_pool_match'][pool['name']]
            inventory[pool_name] = []
            for member in pool['member_list']:
                if member['status']: # checking status 1
		    hv = {}
		    hgs = {}
		    hgs = host_globalvars
		    hgs.update({'lb_pool_name' : pool['name'] })
		    hv = { member['server'] : hgs }
                    inventory[pool_name].append(member['server'])
                    inventory['_meta']['hostvars'][member['server']] =  { 'lb_pool_name':pool['name']}
                    inventory['_meta']['hostvars'][member['server']].update(host_globalvars)
    sorted_inventory =  {}
    sorted_inventory['_meta'] =  inventory['_meta']
    tmp_group = []
    for group in inventory:
	if group == '_meta':
	    continue
	sorted_group=inventory[group]
	sorted_group.sort()
        sorted_inventory[group] = sorted_group
    #output = json.dumps(inventory,sort_keys = True, indent = 1) 
    output = json.dumps(sorted_inventory,sort_keys = True, indent = 1) 
    print output
