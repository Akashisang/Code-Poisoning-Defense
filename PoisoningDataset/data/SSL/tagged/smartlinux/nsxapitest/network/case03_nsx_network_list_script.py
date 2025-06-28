#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Test script for network function.
# 
# Network 映射为 NSX Logincal Switch(virtualWire), 下面是属性映射关系:
#   ID(objectId)、名称(name)、管理状态(mgmtStatus)、状态(status)、是否共享(isUniversal)、租户ID(tenantId)
#   网络类型(backingType)、物理网络(vdsContextWithBacking)、vlanID(vlanId/vdnId)、qos规则ID(inShapingPolicy/outShapingPolicy/qosTag)
#

import sys
import datetime
import libxml2
import ssl
import atexit

sys.path.append("..")
import rest

from nsx_basic_input import *

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

caseName = 'case03_nsx_network_list'
restclient = rest.Rest(NSX_IP, NSX_USER, NSX_PWD, True)


def listNetworks():
    respData = restclient.get(NSX_URL+'/api/2.0/vdn/virtualwires', 'listNetworks')
    dpgMap = getPortGroupMap()
    respDoc = libxml2.parseDoc(respData)
    xp = respDoc.xpathNewContext()
    nodes = xp.xpathEval("//virtualWires/dataPage/virtualWire")

    for ls in nodes:
        xp.setContextNode(ls)
        dpgId = xp.xpathEval("vdsContextWithBacking/backingValue")[0].content
        dpg = dpgMap[dpgId]
        if dpg == None:
            continue;
        ls.newChild(None, 'status', dpg.overallStatus)
        ls.newChild(None, 'mgmtStatus', dpg.configStatus)
    
    respData = respDoc.serialize('UTF-8', 1)
    output(restclient.getDebugInfo() + restclient.prettyPrint(respData))


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
    listNetworks()
    print "NSX API %s completed successfully!"%(caseName)

if __name__ == "__main__":
    sys.exit(main())