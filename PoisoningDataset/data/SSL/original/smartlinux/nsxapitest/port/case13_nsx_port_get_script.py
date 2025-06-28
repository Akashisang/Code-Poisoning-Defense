#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Test script for port function.
# 
# Port 映射为 vSphere VDS Port, 下面是属性映射关系:
#   ID(LS.objectId+vm.config.hardware.device.backing.port.portKey)、网络ID(LS.objectId)、名称(LS.name+portKey)、
#   管理状态(vm.guestHeartbeatStatus)、状态(vm.config.hardware.device.connectable.connected)、mac地址(vm.config.hardware.device.macAddress)
#   设备ID(vnicUuid)、租户ID(LS.tenantId)、端口安全使能(spoofguard?)
#   qos规则ID(DPG.config.defaultPortConfig.inShapingPolicy/outShapingPolicy/qosTag)
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
from case13_nsx_port_get_input import *

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

caseName = 'case13_nsx_port_get'
restclient = rest.Rest(NSX_IP, NSX_USER, NSX_PWD, True)


def getPort():
    # get lsId and portKey from input parameter NSX_PORT_ID
    pids = NSX_PORT_ID.split('.')
    if len(pids) != 2:
        print "[Error] NSX_PORT_ID:%s is wrong format."%(NSX_PORT_ID)
        return False
    lsId = pids[0]
    portKey = pids[1]

    # get ls object by NSX API
    respData = restclient.get(NSX_URL+'/api/2.0/vdn/virtualwires/'+lsId, 'getPort')
    #outputstr = restclient.getDebugInfo() + restclient.prettyPrint(respData)

    # get port group list by vSphere API
    outputstr = "\nTry to get backing port info by vSphere API:\n"
    dpgMap = getPortGroupMap()
    outputstr += str(dpgMap)
    
    
    outputstr += "\n\n\nTry to take out port info from vSphere and NSX API response:\n"
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
                    port = {}
                    port['id'] = "%s.%s"%(lsId, portKey)
                    port['networkid'] = lsId
                    port['name'] = "%s.%s"%(lsName, portKey)
                    port['tenantId'] = tenantId
                    port['enablesecurity'] = False
                    port['qosTag'] = dpg.config.defaultPortConfig.qosTag.value
                    port['mgmtState'] = vm.guestHeartbeatStatus
                    port['state'] = 'connected' if dev.connectable.connected else 'disconnected'
                    port['macAddress'] = dev.macAddress
                    port['deviceid'] = "%s.%s"%(vm.config.instanceUuid, str(dev.key)[-3:])

                    dvs = dpg.config.distributedVirtualSwitch
                    portCriteria = vim.dvs.PortCriteria()
                    portCriteria.portKey = [portKey]
                    dvPorts = dvs.FetchDVPorts(portCriteria)
                    ciShapping = dvPorts[0].config.setting.inShapingPolicy 
                    coShapping = dvPorts[0].config.setting.outShapingPolicy 
                    if ciShapping!=None:
                        port['inShaping'] = "enabled:%s,averageBps:%s,peakBps:%s"% \
                        (ciShapping.enabled.value,ciShapping.averageBandwidth.value,ciShapping.peakBandwidth.value)
                    if coShapping!=None:
                        port['outShaping'] = "enabled:%s,averageBps:%s,peakBps:%s"% \
                        (coShapping.enabled.value,coShapping.averageBandwidth.value,coShapping.peakBandwidth.value)
            
                    outputstr += json.dumps(port, sort_keys=True, indent=4, separators=(',',': '))

                    respData2 = restclient.get(NSX_URL+'/api/4.0/services/spoofguard/spoofguardpolicy-4?list=ACTIVE', 'listPorts')
                    outputstr += '\n\n' + restclient.getDebugInfo() + restclient.prettyPrint(respData2)
                    output(outputstr)
                    return True
    
    print "[Error] NSX_PORT_ID:%s not found."%(NSX_PORT_ID)
    return False    


def getPortGroupMap():
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.verify_mode = ssl.CERT_NONE
    serviceInstance = SmartConnect(host=VC_IP, user=VC_USER, pwd=VC_PWD, port=443, sslContext=context)
    atexit.register(Disconnect, serviceInstance)
    content = serviceInstance.RetrieveContent()

    dpg_view = content.viewManager.CreateContainerView(content.rootFolder,[vim.dvs.DistributedVirtualPortgroup],True)
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
    if getPort():
        print "NSX API", caseName, "completed successfully!"

if __name__ == "__main__":
    sys.exit(main())