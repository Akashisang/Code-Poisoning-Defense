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
