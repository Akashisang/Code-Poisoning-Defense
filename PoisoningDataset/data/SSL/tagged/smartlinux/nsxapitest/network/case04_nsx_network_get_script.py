#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Test script for network function.
# 
# Network 映射为 NSX Logincal Switch, 下面是属性映射关系:
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
from case04_nsx_network_get_input import *

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

caseName = 'case04_nsx_network_get'
restclient = rest.Rest(NSX_IP, NSX_USER, NSX_PWD, True)


def getNetwork():
    respData = restclient.get(NSX_URL+'/api/2.0/vdn/virtualwires/'+NSX_NETWORK_ID, 'getNetwork')
    outputstr = restclient.getDebugInfo()
    
    respDoc = libxml2.parseDoc(respData)
    xp = respDoc.xpathNewContext()
    dpgId = xp.xpathEval("//virtualWire/vdsContextWithBacking/backingValue")[0].content
    dpg = getPortGroupMap()[dpgId]

    if dpg != None:
        ls = xp.xpathEval("//virtualWire")[0]
        ls.newChild(None, 'status', dpg.overallStatus)
        ls.newChild(None, 'mgmtStatus', dpg.configStatus)
        respData = respDoc.serialize('UTF-8', 1)

    outputstr += restclient.prettyPrint(respData)

    # if dpg != None:
    #     outputstr += "\nBacking network info by vSphere API:\n"
    #     outputstr += str(dpg.config.defaultPortConfig)

    output(outputstr)


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
    getNetwork()
    print "NSX API %s completed successfully!"%(caseName)


if __name__ == "__main__":
    sys.exit(main())