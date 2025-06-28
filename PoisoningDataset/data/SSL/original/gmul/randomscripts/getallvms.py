#!/usr/bin/env python

#- * -coding: utf - 8 - * -
# python getallvms.py --host 10.160.83.91 --user 'administrator@vsphere.local' --password 'Admin!23'


__author__ = 'VMware, Inc'
from pyVim.connect import SmartConnect, Disconnect
import sys
import ssl
import atexit
import argparse
import getpass
if sys.version[0] < '3':
       input = raw_input
import vsanmgmtObjects
import vsanapiutils


s = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
s.verify_mode = ssl.CERT_NONE
 
try:
    c = SmartConnect(host="10.160.83.91", user="administrator@vsphere.local", pwd='Admin!23')
    print('Valid certificate')
except:
    c = SmartConnect(host="10.160.83.91", user="administrator@vsphere.local", pwd='Admin!23', sslContext=s)

 
datacenter = c.content.rootFolder.childEntity[0]
vms = datacenter.vmFolder.childEntity
 
 
print('Virtual Machines on VC') 
for i in vms:
    print(i.name)
 
Disconnect(c)