#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Test script for port function.
# 修改端口的mac address和qos shaping policy


import sys
import datetime
import libxml2
import json
import ssl
import atexit

sys.path.append("..")
import rest

from nsx_basic_input import *
from case15_nsx_port_update_input import *

from pyVim.connect import SmartConnect, Disconnect
from pyVim.task import WaitForTask
from pyVmomi import vim

caseName = 'case15_nsx_port_update'
restclient = rest.Rest(NSX_IP, NSX_USER, NSX_PWD, True)

context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
context.verify_mode = ssl.CERT_NONE
serviceInstance = SmartConnect(host=VC_IP, user=VC_USER, pwd=VC_PWD, port=443, sslContext=context)
atexit.register(Disconnect, serviceInstance)
serviceContent = serviceInstance.RetrieveContent()

def updatePort():
    # get lsId and portKey from input parameter NSX_PORT_ID
    pids = NSX_PORT_ID.split('.')
    if len(pids) != 2:
        print "[Error] NSX_PORT_ID:%s is wrong format."%(NSX_PORT_ID)
        return False
    lsId = pids[0]
    portKey = pids[1]

    # get ls object by NSX API
    respData = restclient.get(NSX_URL+'/api/2.0/vdn/virtualwires/'+lsId, 'updatePort')
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
                    doUpdatePort(dpg, vm, dev)
                    return True
    
    print "[Error] NSX_PORT_ID:%s not found."%(NSX_PORT_ID)
    return False    

    
def doUpdatePort(dpg, vm, vnic_device):
    outputstr = 'Try to update mac address:\n'
    outputstr += 'Current mac address: %s \n'%(vnic_device.macAddress)
    outputstr += 'New mac address: %s \n'%(NEW_MAC_ADDRESS)
    vnic_spec = vim.vm.device.VirtualDeviceSpec()
    vnic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
    vnic_spec.device = vnic_device
    vnic_spec.device.key = vnic_device.key
    vnic_spec.device.macAddress = NEW_MAC_ADDRESS
    vnic_spec.device.backing = vnic_device.backing
    vnic_spec.device.backing.port = vnic_device.backing.port
    vnic_spec.device.wakeOnLanEnabled = vnic_device.wakeOnLanEnabled
    vnic_spec.device.connectable = vnic_device.connectable
    dev_changes = []
    dev_changes.append(vnic_spec)
    vm_spec = vim.vm.ConfigSpec()
    vm_spec.deviceChange = dev_changes
    
    # CHANGE vm.config.networkShaper NOT WORK, SO REMOVE IT!!!
    # outputstr += 'Try to update shaping policy:\n'
    # newShaping = vim.vm.NetworkShaperInfo()
    # newShaping.enabled = (SHAPING_ENABLE=='true')
    # newShaping.peakBps = SHAPING_PEAK_BPS
    # newShaping.averageBps = SHAPING_AVERAGE_BPS
    # newShaping.burstSize = 0
    # vm_spec.networkShaper = newShaping
    # curShaping = vm.config.networkShaper
    # if curShaping != None:
    #     outputstr += 'Current shaping policy: enabled:%s,peakBps:%s,averageBps:%s'%(curShaping.enabled,curShaping.peakBps,curShaping.averageBps)
    # outputstr += 'New shaping policy: enabled:%s,peakBps:%s,averageBps:%s'%(newShaping.enabled,newShaping.peakBps,newShaping.averageBps)
    
    vm_task = vm.ReconfigVM_Task(vm_spec)
    state = WaitForTask(task=vm_task, si=serviceInstance, onProgressUpdate=OnTaskProgressUpdate)
    outputstr += 'ReconfigVM Task completed, state: %s \n\n'%(state)

    
    outputstr += 'Try to update shaping policy:\n'
    dvs = dpg.config.distributedVirtualSwitch
    portCriteria = vim.dvs.PortCriteria()
    portCriteria.portKey = [vnic_device.backing.port.portKey]
    dvPorts = dvs.FetchDVPorts(portCriteria)
    ciShapping = dvPorts[0].config.setting.inShapingPolicy 
    coShapping = dvPorts[0].config.setting.outShapingPolicy 
    if ciShapping!=None:
        outputstr += 'Current in shaping policy: enabled:%s,averageBps:%s,peakBps:%s\n'% \
        (ciShapping.enabled.value,ciShapping.averageBandwidth.value,ciShapping.peakBandwidth.value)
    if coShapping!=None:
        outputstr += 'Current out shaping policy: enabled:%s,averageBps:%s,peakBps:%s\n'% \
        (coShapping.enabled.value,coShapping.averageBandwidth.value,coShapping.peakBandwidth.value)
    outputstr += 'New in shaping policy: enabled:%s,averageBps:%s,peakBps:%s\n'%(IN_SHAPING_ENABLE,IN_SHAPING_AVERAGE_BPS,IN_SHAPING_PEAK_BPS)
    outputstr += 'New out shaping policy: enabled:%s,averageBps:%s,peakBps:%s\n'%(OUT_SHAPING_ENABLE,OUT_SHAPING_AVERAGE_BPS,OUT_SHAPING_PEAK_BPS)
    port_spec = vim.dvs.DistributedVirtualPort.ConfigSpec()
    port_spec.operation = vim.ConfigSpecOperation.edit
    port_spec.key = vnic_device.backing.port.portKey
    port_setting = vim.dvs.DistributedVirtualPort.Setting()
    port_inshaping = vim.dvs.DistributedVirtualPort.TrafficShapingPolicy()
    port_outshaping = vim.dvs.DistributedVirtualPort.TrafficShapingPolicy()
    port_inshaping.enabled = vim.BoolPolicy(value=(IN_SHAPING_ENABLE=='true'))
    port_inshaping.averageBandwidth = vim.LongPolicy(value=IN_SHAPING_AVERAGE_BPS)
    port_inshaping.peakBandwidth = vim.LongPolicy(value=IN_SHAPING_PEAK_BPS)
    port_outshaping.enabled = vim.BoolPolicy(value=(OUT_SHAPING_ENABLE=='true'))
    port_outshaping.averageBandwidth = vim.LongPolicy(value=OUT_SHAPING_AVERAGE_BPS)
    port_outshaping.peakBandwidth = vim.LongPolicy(value=OUT_SHAPING_PEAK_BPS)
    port_setting.inShapingPolicy = port_inshaping
    port_setting.outShapingPolicy = port_outshaping
    port_spec.setting = port_setting
    port_task = dvs.ReconfigureDVPort_Task([port_spec])
    state2 = WaitForTask(task=port_task, si=serviceInstance, onProgressUpdate=OnTaskProgressUpdate)
    outputstr += 'ReconfigDVPort Task completed, state: %s \n'%(state2)

    output(outputstr)


def OnTaskProgressUpdate(task, percentDone):
    print 'Task %s status: %s' % (task, percentDone)  
    

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
    if updatePort():
        print "NSX API", caseName, "completed successfully!"

if __name__ == "__main__":
    sys.exit(main())