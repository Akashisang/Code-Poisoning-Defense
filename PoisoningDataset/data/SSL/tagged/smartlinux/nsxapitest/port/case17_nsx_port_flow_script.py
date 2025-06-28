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
from case17_nsx_port_flow_input import *

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

caseName = 'case17_nsx_port_flow'
restclient = rest.Rest(NSX_IP, NSX_USER, NSX_PWD, True)

<target>
context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
</target>
context.verify_mode = ssl.CERT_NONE
serviceInstance = SmartConnect(host=VC_IP, user=VC_USER, pwd=VC_PWD, port=443, sslContext=context)
atexit.register(Disconnect, serviceInstance)
serviceContent = serviceInstance.RetrieveContent()

def getPortFlow():
    # get lsId and portKey from input parameter NSX_PORT_ID
    pids = NSX_PORT_ID.split('.')
    if len(pids) != 2:
        print "[Error] NSX_PORT_ID:%s is wrong format."%(NSX_PORT_ID)
        return False
    lsId = pids[0]
    portKey = pids[1]

    # get ls object by NSX API
    respData = restclient.get(NSX_URL+'/api/2.0/vdn/virtualwires/'+lsId, 'getPortFlow')
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
                    showPortFlow(vm, dev)
                    return True
    
    print "[Error] NSX_PORT_ID:%s not found."%(NSX_PORT_ID)
    return False    

    
def showPortFlow(vm, vnicDevice):
    outputstr = ''
    perfProviderSummary = serviceContent.perfManager.QueryPerfProviderSummary(vm)
    querySpec = vim.PerformanceManager.QuerySpec()
    querySpec.intervalId = perfProviderSummary.refreshRate 
    querySpec.entity = vm
    querySpec.format = "csv"
    querySpec.maxSample = 3
    
    # Network Packet Received packetsRx
    metricId146 = vim.PerformanceManager.MetricId()
    metricId146.instance = str(vnicDevice.key)
    metricId146.counterId = 146
    querySpec.metricId = [metricId146]
    queryResult146 = serviceContent.perfManager.QueryPerf([querySpec]) 
    
    for result146 in queryResult146:
        outputstr += "\nNetwork Packet Received packetsRx    :  \n"
        outputstr += result146.sampleInfoCSV 
        for csv in result146.value:
            outputstr += "\nCSV Value: %s"%(csv.value )
    
    # Network Packet Transfered  packetsTx        
    metricId147 = vim.PerformanceManager.MetricId()
    metricId147.instance = str(vnicDevice.key)
    metricId147.counterId = 147
    querySpec.metricId = [metricId147]
    queryResult147 = serviceContent.perfManager.QueryPerf([querySpec]) 
    
    for result147 in queryResult147:
        outputstr += "\nNetwork Packet Transfered  packetsTx  :  \n"
        outputstr += result147.sampleInfoCSV 
        for csv in result147.value:
            outputstr += "\nCSV Value: %s"%(csv.value )
            
    # Network Usage(combined transmit- and receive-rates) during the interval.
    metricId143 = vim.PerformanceManager.MetricId()
    metricId143.instance = str(vnicDevice.key)
    metricId143.counterId = 143
    querySpec.metricId = [metricId143]
    queryResult143 = serviceContent.perfManager.QueryPerf([querySpec]) 
    
    for result143 in queryResult143:
        outputstr += "\nNetwork Usage(combined transmit- and receive-rates) during the interval  :  \n"
        outputstr += result143.sampleInfoCSV 
        for csv in result143.value:
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
    if getPortFlow():
        print "NSX API", caseName, "completed successfully!"

if __name__ == "__main__":
    sys.exit(main())