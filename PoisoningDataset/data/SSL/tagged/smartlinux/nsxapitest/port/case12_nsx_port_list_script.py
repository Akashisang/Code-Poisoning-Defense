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

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

caseName = 'case12_nsx_port_list'
restclient = rest.Rest(NSX_IP, NSX_USER, NSX_PWD, True)


def listPorts():
    respData = restclient.get(NSX_URL+'/api/2.0/vdn/virtualwires', 'listPorts')
    #outputstr = restclient.getDebugInfo() + restclient.prettyPrint(respData)

    outputstr = "\nTry to get backing port info by vSphere API:\n"
    dpgMap = getPortGroupMap()
    outputstr += str(dpgMap)

    respDoc = libxml2.parseDoc(respData)
    xp = respDoc.xpathNewContext()
    nodes = xp.xpathEval("//virtualWires/dataPage/virtualWire")
    ports = []
    for ls in nodes:
        xp.setContextNode(ls)
        lsId = xp.xpathEval("objectId")[0].content
        lsName = xp.xpathEval("name")[0].content
        tenantId = xp.xpathEval("tenantId")[0].content
        dpgId = xp.xpathEval("vdsContextWithBacking/backingValue")[0].content

        dpg = dpgMap[dpgId]
        if dpg == None:
            continue;

        for vm in dpg.vm:
            for dev in vm.config.hardware.device:
                if isinstance(dev, vim.vm.device.VirtualEthernetCard):
                    if dev.connectable.connected:
                        port = {}
                        port['id'] = "%s.%s"%(lsId, dev.backing.port.portKey)
                        port['networkid'] = lsId
                        port['name'] = "%s.%s"%(lsName, dev.backing.port.portKey)
                        port['mgmtState'] = vm.guestHeartbeatStatus
                        port['state'] = 'connected' if dev.connectable.connected else 'disconnected'
                        port['macAddress'] = dev.macAddress
                        port['deviceid'] = "%s.%s"%(vm.config.instanceUuid, str(dev.key)[-3:])
                        port['tenantId'] = tenantId
                        port['enablesecurity'] = False
                        port['qosTag'] = dpg.config.defaultPortConfig.qosTag.value
                        ports.append(port)
    
    outputstr += "\n\n\nTake out %d ports from vSphere and NSX API response:\n"%(len(ports))
    outputstr += json.dumps(ports, sort_keys=True, indent=4, separators=(',',': '))

    respData2 = restclient.get(NSX_URL+'/api/4.0/services/spoofguard/spoofguardpolicy-2?list=ACTIVE', 'listPorts')
    outputstr += '\n\n' + restclient.getDebugInfo() + restclient.prettyPrint(respData2)

    output(outputstr)
    return True


def getPortGroupMap():
<target>
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
</target>
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
    if listPorts():
        print "NSX API", caseName, "completed successfully!"

if __name__ == "__main__":
    sys.exit(main())