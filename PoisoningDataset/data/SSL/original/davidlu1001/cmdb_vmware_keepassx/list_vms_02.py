#!/usr/bin/env python
# VMware vSphere Python SDK
# Copyright (c) 2008-2013 VMware, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Python program for listing the vms on an ESX / vCenter host
"""

import argparse
import atexit

from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim

#import tools.cli as cli
import csv


list_vms = []
list_vms_sort = []

csv_file = "./vm_info.csv"


def print_vm_info(virtual_machine):
    """
    Print information for a particular virtual machine or recurse into a
    folder with depth protection
    """
    summary = virtual_machine.summary
    print("Name       : ", summary.config.name)
    print("Template   : ", summary.config.template)
    print("Path       : ", summary.config.vmPathName)
    print("MEM       : ", summary.config.memorySizeMB)
    print("CPU Number       : ", summary.config.numCpu)
    print("Guest ID      : ", summary.config.guestId)
    print("Guest Name      : ", summary.config.guestFullName)
    print("Instance UUID : ", summary.config.instanceUuid)
    print("Bios UUID     : ", summary.config.uuid)
    annotation = summary.config.annotation
    if annotation:
        print("Annotation : ", annotation)
    print("State      : ", summary.runtime.powerState)
    if summary.guest is not None:
        ip_address = summary.guest.ipAddress
        hostName = summary.guest.hostName
        tools_version = summary.guest.toolsStatus
        if tools_version is not None:
            print("VMware-tools: ", tools_version)
        else:
            print("Vmware-tools: None")
        if ip_address:
            print("IP         : ", ip_address)
        else:
            print("IP         : None")
        if hostName:
            print("hostName         : ", hostName)
        else:
            print("hostName         : None")
    if summary.runtime.question is not None:
        print("Question  : ", summary.runtime.question.text)
    print("")


def list_vm_info(virtual_machine):
    list_vm = []
    summary = virtual_machine.summary

    name = summary.config.name
    template = summary.config.template
    path = summary.config.vmPathName
    mem = summary.config.memorySizeMB
    cpu_number = summary.config.numCpu
    guest_id = summary.config.guestId
    guest_name = summary.config.guestFullName
    instance_UUID = summary.config.instanceUuid
    bios_UUID = summary.config.uuid
    annotation = summary.config.annotation
    state = summary.runtime.powerState
    if summary.guest is not None:
        ip_address = summary.guest.ipAddress
        hostName = summary.guest.hostName
        tools_version = summary.guest.toolsStatus
    if state is 'poweredOn' and template is 'FALSE':
        list_vm = [name.title(), ip_address, hostName, template, path, mem,
                   cpu_number, guest_id, guest_name, instance_UUID,
                   bios_UUID, annotation, state, tools_version]
    return list_vm


def get_args():
    """
   Supports the command-line arguments listed below.
   """
    parser = argparse.ArgumentParser(
        description='Process args for retrieving all the Virtual Machines')

    parser.add_argument('-s', '--host',
                        required=True, action='store',
                        help='Remote host to connect to')

    parser.add_argument('-o', '--port',
                        type=int, default=443,
                        action='store', help='Port to connect on')

    parser.add_argument('-u', '--user', required=True,
                        action='store',
                        help='User name to use when connecting to host')

    parser.add_argument('-p', '--password',
                        required=True, action='store',
                        help='Password to use when connecting to host')

    parser.add_argument('-d', '--dscluster', required=True, action='store',
                        help='Name of vSphere Datastore Cluster')

    args = parser.parse_args()
    return args

def main():
    """
    Simple command-line program for listing the virtual machines on a system.
    """

#    args = cli.get_args()
    args = get_args()

    try:
        '''
        Fork from 'pyvmomi-community-samples/samples'
        Disabling SSL certificate verification
        in case of error:
        "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed (_ssl.c:590)"
        '''
        import ssl
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_NONE

        service_instance = connect.SmartConnect(host=args.host,
                                                user=args.user,
                                                pwd=args.password,
                                                port=int(args.port),
                                                sslContext=context)

        atexit.register(connect.Disconnect, service_instance)

        content = service_instance.RetrieveContent()

        container = content.rootFolder  # starting point to look into
#        viewType = [vim.VirtualMachine]  # object types to look for
        viewType = [vim.ComputeResource]  # object types to look for
        recursive = True  # whether we should look into it recursively
        containerView = content.viewManager.CreateContainerView(
            container, viewType, recursive)

        children = containerView.view
#        print(children)
        for child in children:
            print(child.name)

        obj_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                           [vim.StoragePod],
                                                           True)
        ds_cluster_list = obj_view.view
        obj_view.Destroy()

        for ds_cluster in ds_cluster_list:
            if ds_cluster.name == args.dscluster:
                datastores = ds_cluster.childEntity
                print "Datastores: "
                for datastore in datastores:
                    print datastore.name

#            list_vm = list_vm_info(child)
#            list_vms.append(list_vm)
#
#        list_vms_sort = sorted(list_vms, key=lambda result: result[0])
##        print(list_vms_sort)
#
#        fl = open(csv_file, 'w')
#
#        writer = csv.writer(fl)
#        writer.writerow(['name', 'ip_address', 'hostName', 'template', 'path', 'mem', 'cpu_number',
#                         'guest_id', 'guest_name', 'instance_UUID', 'bios_UUID',
#                         'annotation', 'state', 'tools_version'])
#        for values in list_vms_sort:
#            writer.writerow(values)
#        fl.close()

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
