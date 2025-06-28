#!/usr/bin/python

import os
import argparse
import yaml
from requests.adapters import HTTPAdapter
#from requests.packages.urllib3.poolmanager import PoolManager
from urllib3.poolmanager import PoolManager
import ssl
import requests
import json
from xml.dom.minidom import parse, parseString


#urllib3.disable_warnings()
#requests.packages.urllib3.disable_warnings()

__author__ = 'ACMEsEngTeam'


# read the credentials
__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))
stream = open(__location__+"/secrets", 'r')
creds= yaml.safe_load(stream)
stream.close()

username=creds['username']
password=creds['password']
loadbalancer=creds['loadbalancer']
server_list = ''
# getting a session_id
class MyAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, block=block, ssl_version=ssl.PROTOCOL_TLSv1)


s = requests.Session()
s.mount('https://', MyAdapter())

url = "https://"+loadbalancer+"/services/rest/V2/?method=authenticate&username="+username+"&password="+password+"&format=json"
r = s.get(url, verify=False)
data = json.loads(r.text)
session_id = data['session_id']

# print session_id


def get_data(uri):
  url = "https://"+loadbalancer+"/services/rest/V2/?&session_id=" + session_id + "&format=json&"+uri
  r = s.get(url, verify=False)
  content = r.text
  return json.loads(r.text)

def list_active_servers_in_pool(args):
  sg = []
  active = []
  sblall = get_data("method=slb.service_group.getAll")
  sgl = sblall['service_group_list']
  for pool in sgl:
    if pool['name'] == args.pool:
      sg = pool
      break
    else:
      continue
  #print pool
  #print sg

#  print sg
  for s in sg['member_list']:
    if s['status']:
      active.append(s['server'])
      print s['server']
  return active

def get_pool_list(args):
  dd = get_data("method=slb.service_group.getAll")
  sgl = dd['service_group_list']
  for pool in sgl:
    print pool['name']

def list_pools(args):
  return get_pool_list(args)

def list_servers_in_pool(args):
  dd = get_data("method=slb.service_group.getAll")
  sgl = dd['service_group_list']
  for pool in sgl:
    if pool['name'] == args.pool:
      for member in pool['member_list']:
        print member['server']

def check_members(reason,pool_name):
  dd  = get_data("method=slb.service_group.fetchAllStatistics")
  sgl = dd['service_group_stat_list']
  global server_list
  for pool in sgl:
    if pool['name'] == pool_name:
      for stats in pool['member_stat_list']:
        if stats['status'] == 4:
	  server_list = server_list + stats['server'] + ' down '
	elif stats['status'] == 5:
	  server_list = server_list + stats['server'] + ' unknown '
        elif stats['status'] == 1:
	  server_list = server_list + stats['server'] + ' up '
        elif stats['status'] == 0:
	  server_list = server_list + stats['server'] + ' disabled  '
      print reason + server_list

def get_pool_stats(args):
  dd  = get_data("method=slb.service_group.fetchAllStatistics")
  sgl = dd['service_group_stat_list']
  for pool in sgl:
    if pool['name'] == args.pool:
      if pool['status'] == 1:
        check_members('All members Up! - ',pool['name'])
        exit(0)
      elif pool['status'] == 2:
        check_members('Partition Up - ',pool['name'])
        exit(1)
      elif pool['status'] == 3:
        check_members('Functional Up - ',pool['name'])
        exit(1)
      elif pool['status'] == 4: 
        print 'All members down!'.rstrip()
        exit(2)
      elif pool['status'] == 5:
        print 'Unknown error'.rstrip()
        exit(3)
      elif pool['status'] == 0:
        print 'Disabled!'.rstrip()
        exit(1)
 
def update_pool_server(args,status):
  # enable server in service_group
  url = "https://192.168.1.2/services/rest/V2/?&session_id=" + session_id + "&method=slb.service_group.member.update&name=app_tpl_dynamic_srvgrp&format=url"
  payload = { 'server' : args.server, 'status' : status, 'port': 80 }
  r = s.post(url,data=payload, verify=False)
  content = r.text
  x = parseString(content)
  rc = x.getElementsByTagName("response")[0].getAttribute('status')
  return rc

def enable_server(args):
  print update_pool_server(args,1)

def disable_server(args):
  print update_pool_server(args,0)

parser = argparse.ArgumentParser(description='A tool for interacting with A10.')
subparsers = parser.add_subparsers(help='commands')

list_parser = subparsers.add_parser('list',  help='list the service groups')
list_parser.set_defaults(func=list_pools)

get_parser = subparsers.add_parser('stats',  help='get sbl stats')
get_parser.add_argument('pool', action='store', help='Pool Name')
get_parser.set_defaults(func=get_pool_stats)

pool_parser = subparsers.add_parser('pool',  help='list servers in a service group')
pool_parser.add_argument('pool', action='store', help='Pool Name')
pool_parser.set_defaults(func=list_servers_in_pool)

enable_parser = subparsers.add_parser('enable',  help='Enable a server in the pool')
enable_parser.add_argument('pool', action='store', help='Pool Name')
enable_parser.add_argument('server', action='store', help='Server Name')
enable_parser.set_defaults(func=enable_server)

disable_parser = subparsers.add_parser('disable', help='Disable a server in the pool')
disable_parser.add_argument('pool', action='store', help='Pool Name')
disable_parser.add_argument('server', action='store', help='Server Name')
disable_parser.set_defaults(func=disable_server)

active_parser = subparsers.add_parser('active', help='List active servers in the pool')
active_parser.add_argument('pool', action='store', help='Pool Name')
active_parser.set_defaults(func=list_active_servers_in_pool)

args = parser.parse_args()
args.func(args)
