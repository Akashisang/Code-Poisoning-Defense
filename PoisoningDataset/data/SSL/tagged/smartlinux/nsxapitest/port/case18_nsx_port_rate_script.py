#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Test script for port function.
# 


import sys
import datetime
import libxml2
import json
import ssl
import atexit

sys.path.append("..")
import rest

from nsx_basic_input import *
from case18_nsx_port_rate_input import *

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

caseName = 'case18_nsx_port_rate'
restclient = rest.Rest(NSX_IP, NSX_USER, NSX_PWD, True)

<target>
context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
</target>
context.verify_mode = ssl.CERT_NONE
serviceInstance = SmartConnect(host=VC_IP, user=VC_USER, pwd=VC_PWD, port=443, sslContext=context)
atexit.register(Disconnect, serviceInstance)
serviceContent = serviceInstance.RetrieveContent()

def getPortRate():
    # get lsId and portKey from input parameter NSX_PORT_ID
    pids = NSX_PORT_ID.split('.')
    if len(pids) != 2:
        print "[Error] NSX_PORT_ID:%s is wrong format."%(NSX_PORT_ID)
        return False
    lsId = pids[0]
    portKey = pids[1]

    # get ls object by NSX API
    respData = restclient.get(NSX_URL+'/api/2.0/vdn/virtualwires/'+lsId, 'getPortRate')
    #outputstr = restclient.getDebugInfo() + restclient.prettyPrint(respData)

    # get port group list by vSphere API
    #outputstr = "\nTry to get backing port info by vSphere API:\n"
    dpgMap = getPortGroupMap()
    #outputstr += str(dpgMap)
    
    
    #outputstr += "\n\n\nTry to take out port info from vSphere and NSX API response:\n"
    respDoc = libxml2.parseDoc(respData)
    xp = respDoc.xpathNewContext()
    lsName = xp.xpathEval("//virtualWire/name")[0].content
    tenantId = xp.xpathEval("//virtualWire/tenantId")[0].content
    dpgId = xp.xpathEval("//virtualWire/vdsContextWithBacking/backingValue")[0].content

    dpg = dpgMap[dpgId]
    if dpg == None:
        print "[Error] NSX_DPG_ID:%s not found."%(dpgId)
        return False

    
    # try to find connected port in all the attached vms by portKey
    for vm in dpg.vm:
        for dev in vm.config.hardware.device:
            if isinstance(dev, vim.vm.device.VirtualEthernetCard):
                if dev.connectable.connected and portKey==dev.backing.port.portKey:
                    showPortRate(vm, dev)
                    return True
    
    print "[Error] NSX_PORT_ID:%s not found."%(NSX_PORT_ID)
    return False    

    
def showPortRate(vm, vnicDevice):
    outputstr = ''
    perfProviderSummary = serviceContent.perfManager.QueryPerfProviderSummary(vm)
    querySpec = vim.PerformanceManager.QuerySpec()
    querySpec.intervalId = perfProviderSummary.refreshRate 
    querySpec.entity = vm
    querySpec.format = "csv"
    querySpec.maxSample = 3
    querySpec.startTime = datetime.datetime.strptime(QUERY_START_TIME, "%Y-%m-%d %H:%M:%S")
    querySpec.endTime = datetime.datetime.strptime(QUERY_END_TIME, "%Y-%m-%d %H:%M:%S")
    
    # Network Packet Received packetsRx
    metricId148 = vim.PerformanceManager.MetricId()
    metricId148.instance = str(vnicDevice.key)
    metricId148.counterId = 148
    querySpec.metricId = [metricId148]
    queryResult148 = serviceContent.perfManager.QueryPerf([querySpec]) 
    
    for result148 in queryResult148:
        outputstr += "\nReceived Average rate at which data was received during the interval. This represents the bandwidth of the network:  \n"
        outputstr += result148.sampleInfoCSV 
        for csv in result148.value:
            outputstr += "\nCSV Value: %s"%(csv.value )
    
    # Network Packet Transfered  packetsTx        
    metricId149 = vim.PerformanceManager.MetricId()
    metricId149.instance = str(vnicDevice.key)
    metricId149.counterId = 149
    querySpec.metricId = [metricId149]
    queryResult149 = serviceContent.perfManager.QueryPerf([querySpec]) 
    
    for result149 in queryResult149:
        outputstr += "\nAverage rate at which data was transmitted during the interval. This represents the bandwidth of the network:  \n"
        outputstr += result149.sampleInfoCSV 
        for csv in result149.value:
            outputstr += "\nCSV Value: %s"%(csv.value )
            

    output(outputstr)
    

def getPortGroupMap():
    dpg_view = serviceContent.viewManager.CreateContainerView(serviceContent.rootFolder,[vim.dvs.DistributedVirtualPortgroup],True)
    dpgs = [dpg for dpg in dpg_view.view]
    dpg_view.Destroy()
    dpgMap = {}
    for dpg in dpgs:
        dpgMap[dpg.key] = dpg
    return dpgMap


def output(msg):
    f = file(datetime.datetime.now().strftime("../log/" + caseName + "_output_20%y%m%d%H%M%S.log"), "w")
    f.write(msg)
    f.close()	


def main():
    if getPortRate():
        print "NSX API", caseName, "completed successfully!"

if __name__ == "__main__":
    sys.exit(main())