#!/usr/bin/env python

"""
A simple library for controlling VMware vCenter / ESXi servers.

Copyright:
    (C) COPYRIGHT Cambridge Consultants Ltd 2017-2018

Licence:
    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

Metadata:
    URL: https://github.com/cambridgeconsultants/pyvmlib
    Author: jonathanpallant

Details:
    This library wraps up pyvmomi into something a little more friendly.

    Create a `Connection` object and call methods on it. e.g.

        with Connection(HOST, USER, PASS) as conn:
            vm = conn.get_vm(VM_NAME)
            for dev in conn.list_usb_devices_on_guest(vm):
                print("Got dev: {}".format(dev))

    The wait_for_tasks function was written by Michael Rice, under the Apache
    2 licence (http://www.apache.org/licenses/LICENSE-2.0.html). See
    https://github.com/virtdevninja/pyvmomi-community-
    samples/blob/master/samples/tools/tasks.py

    The list_vms function was based on https://github.com/vmware/pyvmomi-
    community-samples/blob/master/samples/tools/pchelper.py

    This in turn was based upon https://github.com/dnaeon/py-
    vconnector/blob/master/src/vconnector/core.py, which contains:

    # Copyright (c) 2013-2015 Marin Atanasov Nikolov <dnaeon@gmail.com>
    # All rights reserved.
    #
    # Redistribution and use in source and binary forms, with or without
    # modification, are permitted provided that the following conditions
    # are met:
    # 1. Redistributions of source code must retain the above copyright
    #    notice, this list of conditions and the following disclaimer
    #    in this position and unchanged.
    # 2. Redistributions in binary form must reproduce the above copyright
    #    notice, this list of conditions and the following disclaimer in the
    #    documentation and/or other materials provided with the distribution.
    #
    # THIS SOFTWARE IS PROVIDED BY THE AUTHOR(S) ``AS IS'' AND ANY EXPRESS OR
    # IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
    # OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
    # IN NO EVENT SHALL THE AUTHOR(S) BE LIABLE FOR ANY DIRECT, INDIRECT,
    # INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
    # NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
    # DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
    # THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    # (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
    # THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""


##############################################################################
# Standard Python imports
##############################################################################
import logging
import os
import ssl

##############################################################################
# Library imports
##############################################################################
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
import requests
import six

##############################################################################
# Local imports
##############################################################################
# None

##############################################################################
# Global data
##############################################################################
DEFAULT_NUM_PORTS = 64

##############################################################################
# Code and classes
##############################################################################


class PyVmlibException(Exception):
    """Superclass of all exceptions raised by pyvmlib."""


class VmNotFoundException(PyVmlibException):
    """Raised if you call 'get_vm' with a VM name that can't be found."""

    def __init__(self, vm_name):
        """
        Create new VmNotFoundException.

        :param vm_name: Name of VM that couldn't be found.
        """
        self.vm_name = vm_name

    def __str__(self):
        """Convert to string."""
        return "Cannot find VM {!r}".format(self.vm_name)


class ConnectException(PyVmlibException):
    """Superclass of all connection-related Exceptions."""


class InvalidCredentialsException(ConnectException):
    """Raised if your username or password is incorrect."""


class HostConnectException(ConnectException):
    """Raised if we could not connect to the host."""


class Connection:
    """Handle connection to a vSphere vCenter or ESXi host.

    You can use this object as a context, i.e.:

        with Connection(HOST, USER, PASS) as conn:
            conn.do_stuff()

    This ensures the connection is always cleanly dropped.

    :param host: The hostname to connect to
    :type host: String
    :param username: The username to log in to the server as
    :type username: String
    :param password: The password to authenticate with
    :type password: String
    :param ignore_ssl_error: If True, ignore any SSL errors (e.g because your
        server has a self-signed cert)
    :type ignore_ssl_error: Boolean

    # noqa: E501


    >>> with Connection("test.example.com", "user", "password") as c: # doctest: +IGNORE_EXCEPTION_DETAIL
    ...     pass
    Traceback (most recent call last):
    ...
    pyvmlib.HostConnectException: Cannot connect to 'test.example.com' ([Errno -2] Name or service not known)
    """

    def __init__(self, host, username, password, ignore_ssl_error=False):
        """Create a new Connection()."""
        self.ignore_ssl_error = ignore_ssl_error
        self.host = host
        self.username = username
        self.password = password
        self.si = None
        self.content = None
        self.log = logging.getLogger("vmlib.Connection")

    def __enter__(self):
        """Special function for `with` syntax."""
        self.connect()
        return self

    def __exit__(self, _ext_type, _exc_value, _traceback):
        """Special function for `with` syntax."""
        self.disconnect()

    def connect(self):
        """Connect to the vSphere vCenter."""
        self.log.debug("Connecting...")
        if self.si is None:
            kwargs = {
                "host": self.host, "user": self.username, "pwd": self.password
            }
            if self.ignore_ssl_error:
                # Disabling SSL certificate verification
                context = ssl.SSLContext(ssl.PROTOCOL_TLS)
                context.verify_mode = ssl.CERT_NONE
                kwargs['sslContext'] = context
            try:
                self.si = SmartConnect(**kwargs)
            except vim.fault.InvalidLogin:
                # Squash the library error - it isn't helpful
                msg = "Unable to log in as user {user!r} on host " \
                    "{host!r}".format(user=self.username, host=self.host)
                six.raise_from(InvalidCredentialsException(msg), None)
            except (IOError, ) as e:
                # The underlying error may be useful, but give them
                # one of our errors first.
                msg = "Cannot connect to {host!r} ({exc})".format(
                    host=self.host, exc=e)
                six.raise_from(HostConnectException(msg), e)
            self.content = self.si.RetrieveContent()
            self.log.debug("...Connected")

    def disconnect(self):
        """Disconnect from the vSphere vCenter."""
        if self.si is not None:
            Disconnect(self.si)
            self.si = None
            self.content = None

    def get_role(self, role_name):
        """
        Find a named role on the vCenter.

        Arguments:
        :param role_name: name of the role to get.
        """
        obj = None
        am = self.content.authorizationManager
        for role in am.roleList:
            if role.name == role_name:
                obj = role
                break
        return obj

    def get_datacenter(self, dc_name):
        """
        Find a named datacenter on the vCenter.

        Arguments:
        :param dc_name: name of the datacenter to get.
        """
        return self._get_obj(vim.Datacenter, dc_name)

    def get_datastore(self, ds_name):
        """
        Find a named datastore on the vCenter.

        Arguments:
        :param ds_name: name of the datastore to get.
        """
        return self._get_obj(vim.Datastore, ds_name)

    def get_folder(self, folder_name):
        """
        Find a named Folder on the vCenter.

        Arguments:
        :param folder_name: name of the folder to get.
        """
        return self._get_obj(vim.Folder, folder_name)

    def get_host(self, host_name):
        """
        Find a named Host on the vCenter.

        Arguments:
        :param host_name: name of the host to get.
        """
        return self._get_obj(vim.HostSystem, host_name)

    def get_cluster(self, cluster_name):
        """
        Find a named Cluster on the vCenter.

        Arguments:
        :param cluster_name: name of the cluster to get.
        """
        return self._get_obj(vim.ClusterComputeResource, cluster_name)

    def get_compute_resource(self, compute_resource_name):
        """
        Find a named Compute Resource on the vCenter.

        Arguments:
        :param compute_resource_name: name of the compute resource to get.
        """
        return self._get_obj(vim.ComputeResource, compute_resource_name)

    def get_vdswitch(self, vdswitch_name):
        """
        Find a named VMware Distributed Switch on the vCenter.

        Arguments:
        :param vdswitch_name: name of the switch to get.
        """
        return self._get_obj(vim.VmwareDistributedVirtualSwitch, vdswitch_name)

    def get_pg(self, dc, pg_name):
        """
        Find a named Port Group on the vCenter.

        Works on both standard Port Groups and Distributed Port Groups.

        Arguments:
        :param dc: the datacenter to look in (see `get_dc`)
        :param pg_name: name of the distributed port group to get.
        """
        obj = None
        networks = dc.networkFolder.childEntity
        for network in networks:
            if network.name == pg_name:
                obj = network
                break
        return obj

    def get_resourcepool(self, resourcepool_name):
        """
        Find a named Resource Pool on the vCenter.

        Arguments:
        :param resourcepool_name: name of the resource pool to get.
        """
        return self._get_obj(vim.ResourcePool, resourcepool_name)

    def get_ip_addresses(self, vm):
        """
        Get the IP addresses for a VM.

        Arguments:
        :param vm: VM to get addresses for (see `get_vm`)
        """
        if isinstance(vm, six.string_types):
            vm = self.get_vm(vm)
        addresses = []
        for nic in vm.guest.net:
            for addr in nic.ipAddress:
                addresses.append(addr)
        return addresses

    def get_vm(self, vm_name, required=False, folder=None):
        """
        Find a named VM or Template on the vCenter.

        Note: Searches all folders.

        Arguments:
        :param vm_name: name of the VM to get.
        :param required: If True, an exception is raised if the VM is not
            found. If False, None is returned if the VM is not found.
        :param folder: This is the string name of a Folder or a vim.Folder
            object (which limits the search to that folder), or None (which
            means search everything). Searching within a specific folder is
            much faster.
        """
        if folder:
            if isinstance(folder, six.string_types):
                folder = self.get_folder(folder)
            # Search this specific folder (without recursing deeper)
            vm = self.si.content.searchIndex.FindChild(folder, vm_name)
        else:
            # Search the whole tree
            vm = self._get_obj(vim.VirtualMachine, vm_name)
            if required and vm is None:
                raise VmNotFoundException(vm_name)
        return vm

    def get_vm_by_instance_uuid(self, instance_uuid, required=False):
        """
        Find a VM by its `vm.summary.config.instanceUuid` property.

        This is much faster than finding a VM by name.

        Arguments:
        :param instance_uuid: A string in the form
            'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' previously taken from
            `vm.summary.config.instanceUuid` for a given VM.
        :param required: If True, an exception is raised if the VM is not
            found. If False, None is returned if the VM is not found.
        """
        datacenter = None
        vm_search = True
        find_instance_uuid = True
        vm = self.si.content.searchIndex.FindByUuid(
            datacenter, instance_uuid, vm_search, find_instance_uuid)
        if required and vm is None:
            raise VmNotFoundException(instance_uuid)
        return vm

    def delete_vm(self, vm):
        """
        Delete a VM from the vCenter.

        Arguments:
        :param vm: VM to delete (see `get_vm`)
        """
        self.log.info("Deleting VM %s...", vm.name)
        self.wait_for_tasks([vm.Destroy_Task()])

    def power_off_vm(self, vm):
        """
        Power Off a VM.

        Arguments:
        :param vm: VM to power off (see `get_vm`)
        """
        if vm.runtime.powerState != "poweredOff":
            self.log.info("Powering off VM %s...", vm.name)
            self.wait_for_tasks([vm.PowerOff()])

    def power_on_vm(self, vm):
        """
        Power On a VM.

        Arguments:
        :param vm: VM to power on (see `get_vm`)
        """
        if vm.runtime.powerState != "poweredOn":
            self.log.info("Powering on VM %s...", vm.name)
            self.wait_for_tasks([vm.PowerOn()])

    def clone_template(self, ds, folder, resource_pool, template, vm_name):
        """
        Clone a template/VM to a VM.

        Arguments:
        :param ds: The datastore for the clone (see `get_datastore`)
        :param folder: The folder for the clone (see `get_folder`)
        :param resource_pool: The resource pool for the clone (see
                `get_resourcepool`)
        :param template: The VM Template to clone (see `get_vm`)
        :param vm_name: The new name for the resulting VM
        """
        self.log.info("Cloning %s to %s...", template.name, vm_name)
        relocate_spec = vim.vm.RelocateSpec()
        relocate_spec.datastore = ds
        relocate_spec.pool = resource_pool
        clone_spec = vim.vm.CloneSpec()
        clone_spec.location = relocate_spec
        clone_spec.powerOn = False
        self.wait_for_tasks(
            [template.Clone(folder=folder, name=vm_name, spec=clone_spec)])
        return self.get_vm(vm_name, folder=folder, required=True)

    def clone_vm_from_snapshot(self, ds, folder, resource_pool, source_vm,
                               snapshot_name, vm_name):
        """
        Linked-clone a VM with a shapshot, to a VM.

        Arguments:
        :param ds: The datastore for the clone (see `get_datastore`)
        :param folder: The folder for the clone (see `get_folder`)
        :param resource_pool: The resource pool for the clone (see
                `get_resourcepool`)
        :param source_vm: The VM Template to clone (see `get_vm`)
        :param vm_name: The new name for the resulting VM
        """
        self.log.info("Cloning %s to %s...", source_vm.name, vm_name)
        for tree in source_vm.snapshot.rootSnapshotList:
            if tree.name == snapshot_name:
                snapshot_ref = tree.snapshot
                break
        else:
            raise ValueError("VM %r does not have snapshot %r" % (
                source_vm.name, snapshot_name))
        relocate_spec = vim.vm.RelocateSpec()
        relocate_spec.datastore = ds
        relocate_spec.pool = resource_pool
        relocate_spec.diskMoveType = "createNewChildDiskBacking"
        clone_spec = vim.vm.CloneSpec()
        clone_spec.location = relocate_spec
        clone_spec.snapshot = snapshot_ref
        clone_spec.powerOn = False
        clone_spec.template = False
        self.wait_for_tasks(
            [source_vm.Clone(folder=folder, name=vm_name, spec=clone_spec)])
        return self.get_vm(vm_name, folder=folder, required=True)

    def make_folder(self, dc, folder_name):
        """
        Create a new Folder.

        Arguments:
        :param dc: the datacenter to create the folder in (see
                `get_datacenter`)
        :param folder_name: the name of the new folder
        """
        dc.vmFolder.CreateFolder(folder_name)

    def make_pg(self, vswitch, pg_name, vlan, uplink="lag1"):
        """
        Create a new Port Group on a vSwitch.

        Arguments:
        :param vswitch: the vSwitch on which to make the port group
                (see `get_vdswitch`)
        :param pg_name: the name for the new distributed port group
        :param vlan: the VLAN ID for the new distributed port group
        :param uplink: the name of the uplink to use
        """
        spec = vim.DVPortgroupConfigSpec()
        spec.name = pg_name
        spec.numPorts = 32
        spec.type = vim.DistributedVirtualPortgroupPortgroupType.earlyBinding
        cfg = vim.VMwareDVSPortSetting()
        cfg.vlan = vim.VmwareDistributedVirtualSwitchVlanIdSpec()
        cfg.vlan.vlanId = vlan
        cfg.vlan.inherited = False
        policy = vim.VmwareUplinkPortTeamingPolicy()
        policy.uplinkPortOrder = vim.VMwareUplinkPortOrderPolicy()
        policy.uplinkPortOrder.activeUplinkPort = [uplink]
        policy.uplinkPortOrder.standbyUplinkPort = []
        cfg.uplinkTeamingPolicy = policy
        cfg.securityPolicy = vim.DVSSecurityPolicy()
        cfg.securityPolicy.allowPromiscuous = vim.BoolPolicy(value=True)
        cfg.securityPolicy.forgedTransmits = vim.BoolPolicy(value=True)
        cfg.securityPolicy.macChanges = vim.BoolPolicy(value=False)
        cfg.securityPolicy.inherited = False
        spec.defaultPortConfig = cfg
        self.wait_for_tasks([vswitch.AddDVPortgroup_Task([spec])])

    def make_resourcepool(self, cluster, resourcepool_name):
        """
        Create a new Resource Pool on a cluster.

        Arguments:
        :param cluster: the cluster to use (see `get_cluster`)
        :param resourcepool_name: the name for the new resource pool
        """
        rp_spec = vim.ResourceConfigSpec()
        rp_spec.cpuAllocation = vim.ResourceAllocationInfo()
        rp_spec.cpuAllocation.limit = -1  # No limit
        rp_spec.cpuAllocation.expandableReservation = True
        rp_spec.cpuAllocation.reservation = 1000  # MHz
        rp_spec.cpuAllocation.shares = vim.SharesInfo()
        rp_spec.cpuAllocation.shares.level = vim.SharesInfo.Level.normal
        rp_spec.memoryAllocation = vim.ResourceAllocationInfo()
        rp_spec.memoryAllocation.limit = -1  # No limit
        rp_spec.memoryAllocation.expandableReservation = True
        rp_spec.memoryAllocation.reservation = 256  # MiB
        rp_spec.memoryAllocation.shares = vim.SharesInfo()
        rp_spec.memoryAllocation.shares.level = vim.SharesInfo.Level.normal
        cluster.resourcePool.CreateResourcePool(
            name=resourcepool_name, spec=rp_spec)

    def configure_nic(self, vm, nic_key, pg):
        """
        Configure a NIC on a VM.

        Arguments:
        :param vm: the VM to modify (see `get_vm`)
        :param nic_key: the key for the NIC to modify
        :param pg: the distributed port group to connect (see `get_pg`)
        """
        self.log.info("Configuring NIC in %s...", vm.name)
        for device in vm.config.hardware.device:
            if isinstance(device, vim.vm.device.VirtualEthernetCard) and \
                    device.key == nic_key:
                nic_spec = vim.vm.device.VirtualDeviceSpec()
                nic_spec.operation = \
                    vim.vm.device.VirtualDeviceSpec.Operation.edit
                nic_spec.device = device
                nic_spec.device.backing = \
                    vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()  # noqa: E501
                nic_spec.device.backing.port = vim.dvs.PortConnection()
                nic_spec.device.backing.port.switchUuid = \
                    pg.config.distributedVirtualSwitch.uuid
                nic_spec.device.backing.port.portgroupKey = pg.key
                nic_spec.device.connectable = \
                    vim.vm.device.VirtualDevice.ConnectInfo()
                nic_spec.device.connectable.startConnected = True
                config_spec = vim.vm.ConfigSpec(deviceChange=[nic_spec])
                self.wait_for_tasks([vm.ReconfigVM_Task(config_spec)])
                return
        raise ValueError("NIC key {} not found".format(nic_key))

    def wait_for_tasks(self, tasks):
        """
        Wait for some tasks to complete.

        Given the service instance si and a list of tasks, it returns after
        all the tasks are complete

        :param tasks: a list of tasks, as returned from XXX_Task() methods.
        """
        self.log.debug("Waiting for tasks %r...", tasks)
        property_collector = self.content.propertyCollector
        task_list = [str(task) for task in tasks]
        # Create filter
        obj_specs = [vmodl.query.PropertyCollector.ObjectSpec(obj=task)
                     for task in tasks]
        property_spec = vmodl.query.PropertyCollector.PropertySpec(
            type=vim.Task,
            pathSet=[],
            all=True
        )
        filter_spec = vmodl.query.PropertyCollector.FilterSpec()
        filter_spec.objectSet = obj_specs
        filter_spec.propSet = [property_spec]
        pcfilter = property_collector.CreateFilter(filter_spec, True)
        try:
            version, state = None, None
            # Loop looking for updates till the state moves to a completed
            # state.
            while len(task_list):
                update = property_collector.WaitForUpdates(version)
                for filter_set in update.filterSet:
                    for obj_set in filter_set.objectSet:
                        task = obj_set.obj
                        for change in obj_set.changeSet:
                            if change.name == 'info':
                                state = change.val.state
                            elif change.name == 'info.state':
                                state = change.val
                            else:
                                continue

                            if not str(task) in task_list:
                                continue

                            if state == vim.TaskInfo.State.success:
                                # Remove task from taskList
                                task_list.remove(str(task))
                            elif state == vim.TaskInfo.State.error:
                                raise task.info.error
                # Move to next version
                version = update.version
        finally:
            if pcfilter:
                pcfilter.Destroy()
        self.log.debug("Waiting for tasks complete!")

    def set_entity_permission(self, entity, role, principal, is_group=True):
        """
        Set a role for a principal on an entity.

        :param entity: the entity (e.g. folder) this applies to
        :param role: the role to grant
        :param principal: the person / group of people to give the role to
        :param is_group: pass True if principal is a group
        """
        permission = vim.AuthorizationManager.Permission()
        permission.principal = principal
        permission.roleId = role.roleId
        permission.propagate = True
        permission.group = is_group
        self.content.authorizationManager.SetEntityPermissions(
            entity=entity, permission=[permission])

    def list_usb_devices_on_host(self, compute_resource=None):
        """
        Return list of USB devices on specific host.

        :param compute_resource: the compute resource to search,
            or pass None to search the default (e.g. for single ESXi host)
        """
        if compute_resource is None:
            compute_resource = self.get_compute_resource("")
        config = compute_resource.environmentBrowser.QueryConfigTarget()
        return config.usb

    def list_usb_devices_on_guest(self, vm):
        """
        Return list of USB devices attached to a VM.

        :param vm: the vm to remove USB device from (see `get_vm`, or pass VM
            name)
        """
        if isinstance(vm, six.string_types):
            vm = self.get_vm(vm)
        return filter(
            lambda x: isinstance(
                x, vim.vm.device.VirtualUSB),
            vm.config.hardware.device)

    def remove_usb_device(self, vm, descriptor):
        """Remove a USB device from a VM.

        Can remove a device by descriptor (see `insert_usb_device`) or by
        device key (see the `key` property of the devices returned by
        `list_usb_devices_on_guest`)

        :param vm: the vm to remove USB device from (see `get_vm`, or pass VM
            name)
        :param descriptor: USB device descriptor string
        """
        if isinstance(vm, six.string_types):
            vm = self.get_vm(vm)

        key = None
        for dev in self.list_usb_devices_on_guest(vm):
            if dev.backing.deviceName == descriptor:
                key = dev.key
                break
        else:
            raise ValueError("Descriptor not found in VM")

        cfg = vim.VirtualDeviceConfigSpec()
        cfg.operation = vim.VirtualDeviceConfigSpecOperation.remove
        cfg.device = vim.VirtualUSB()
        cfg.device.key = key
        cfg.device.backing = vim.VirtualUSBUSBBackingInfo()
        cfg.device.backing.deviceName = descriptor
        spec = vim.VirtualMachineConfigSpec()
        spec.deviceChange = [cfg]
        self.wait_for_tasks([vm.ReconfigVM_Task(spec=spec)])

    def insert_usb_device(self, vm, descriptor):
        """Insert a USB device into a VM.

        The device(s) are selected based on the descriptor string. This is
        typically of the form:

            path:1/6/2 version:2

        This example corresponds to a USB 2.0 device plugged into port 1 of
        the hub which itself is plugged into port 6 of the root hub on USB
        controller 1. This string can be obtained from
        `Connection.list_usb_devices_on_host`, by inspecting the
        `physicalPath` property of the return devices.

        :param vm: the vm to remove USB device from (see `get_vm`, or pass VM
            name)
        :param descriptor: USB device descriptor string
        """
        if isinstance(vm, six.string_types):
            vm = self.get_vm(vm)
        cfg = vim.VirtualDeviceConfigSpec()
        cfg.operation = vim.VirtualDeviceConfigSpecOperation.add
        cfg.device = vim.VirtualUSB()
        cfg.device.key = -100
        cfg.device.backing = vim.VirtualUSBUSBBackingInfo()
        cfg.device.backing.deviceName = descriptor
        cfg.device.connectable = vim.VirtualDeviceConnectInfo()
        cfg.device.connectable.startConnected = True
        cfg.device.connectable.allowGuestControl = False
        cfg.device.connectable.connected = True
        cfg.device.connected = True
        spec = vim.VirtualMachineConfigSpec()
        spec.deviceChange = [cfg]
        self.wait_for_tasks([vm.ReconfigVM_Task(spec=spec)])

    def list_vms(self, folder=None, properties=None):
        """
        List all the VMs in a folder.

        This is much faster than getting a folder and iterating
        the folder.childEntity list,.

        Returns a list of dictionaries, where the keys are the given
        properties.

        If properties is None, you just get name and the MOID.

        Based on
        https://github.com/vmware/pyvmomi-community-samples/blob/master/samples/tools/pchelper.py
        """
        view = self.get_container_view(vim.VirtualMachine, container=folder)
        collector = self.si.content.propertyCollector

        if properties is None:
            properties = ["name"]

        traversal_spec = vmodl.query.PropertyCollector.TraversalSpec()
        traversal_spec.name = 'traverseEntities'
        traversal_spec.path = 'view'
        traversal_spec.skip = False
        traversal_spec.type = view.__class__

        obj_spec = vmodl.query.PropertyCollector.ObjectSpec()
        obj_spec.obj = view
        obj_spec.skip = True
        obj_spec.selectSet = [traversal_spec]

        property_spec = vmodl.query.PropertyCollector.PropertySpec()
        property_spec.type = vim.VirtualMachine
        property_spec.pathSet = properties

        filter_spec = vmodl.query.PropertyCollector.FilterSpec()
        filter_spec.objectSet = [obj_spec]
        filter_spec.propSet = [property_spec]

        props = collector.RetrieveContents([filter_spec])
        data = []
        for obj in props:
            properties = {}
            for prop in obj.propSet:
                properties[str(prop.name)] = prop.val
                properties['obj'] = obj.obj
            data.append(properties)
        return data

    def get_container_view(self, object_type, container=None):
        """
        Get a container view for the given object type.

        If container is None, we use the root folder.
        """
        if container is None:
            container = self.content.rootFolder
        view = self.content.viewManager.CreateContainerView(
            container=container, type=[object_type], recursive=True)
        return view

    def copy_file_to_vm(
            self, vm, vm_username, vm_password, path_local, path_in_vm,
            overwrite=True):
        """
        Copy a file from the local machine into the VM.

        Makes an SSL connection direct to the host, and so if your host has a
        bad self-signed certificate, you need to create the initial connection
        with `ignore_ssl_error=True`.

        Requires a recent VMware Tools to be installed in the Guest VM. If you
        get the error 'The guest operations agent is out of date.' then you
        need to update VMware Tools.

        :param vm: A VM to upload the file to (see `get_vm`). The VM must be
            powered on.
        :param vm_username: The username for the account in the VM to
            authenticate against.
        :param vm_password: The password for the account in the VM to
            authenticate against.
        :param path_local: The path to the file on this machine.
        :param path_in_vm: The path to the file in the VM.
        :param overwrite: If True, this operation can over-write an existing
            file. If False, it cannot.
        """
        if isinstance(vm, six.string_types):
            vm = self.get_vm(vm)
        creds = vim.vm.guest.NamePasswordAuthentication(
            username=vm_username, password=vm_password)
        file_attribute = vim.vm.guest.FileManager.FileAttributes()
        with open(path_local, "rb") as f:
            file_length = os.path.getsize(path_local)
            self.log.info("Uploading %r (%u bytes)...",
                          path_local, file_length)
            fm = self.content.guestOperationsManager.fileManager
            url = fm.InitiateFileTransferToGuest(
                vm, creds, path_in_vm, file_attribute, file_length, overwrite)
            url = url.replace("://*", "://" + self.host)
            r = requests.put(url, data=f, verify=(not self.ignore_ssl_error))
            r.raise_for_status()

    def copy_file_from_vm(
            self, vm, vm_username, vm_password, path_in_vm, path_local):
        """
        Copy a file from the a VM to the local machine.

        Makes an SSL connection direct to the host, and so if your host has a
        bad self-signed certificate, you need to create the initial connection
        with `ignore_ssl_error=True`.

        Requires a recent VMware Tools to be installed in the Guest VM. If you
        get the error 'The guest operations agent is out of date.' then you
        need to update VMware Tools.

        :param vm: A VM to upload the file to (see `get_vm`). The VM must be
            powered on.
        :param vm_username: The username for the account in the VM to
            authenticate against.
        :param vm_password: The password for the account in the VM to
            authenticate against.
        :param path_in_vm: The path to the file in the VM.
        :param path_local: The path to the file on this machine.
        """
        if isinstance(vm, six.string_types):
            vm = self.get_vm(vm)
        creds = vim.vm.guest.NamePasswordAuthentication(
            username=vm_username, password=vm_password)
        fm = self.content.guestOperationsManager.fileManager
        fti = fm.InitiateFileTransferFromGuest(vm, creds, path_in_vm)
        url = fti.url.replace("://*", "://" + self.host)
        r = requests.get(url, verify=(not self.ignore_ssl_error))
        if r.status_code == requests.codes.ok:
            with open(path_local, "wb") as f:
                for chunk in r:
                    f.write(chunk)
        else:
            raise r.raise_for_status()

    def list_files_in_vm(
            self, vm, vm_username, vm_password, path_in_vm,
            index=None, max_results=None, match_pattern=None):
        """
        Get a directory listing from inside the VM.

        Makes an SSL connection direct to the host, and so if your host has a
        bad self-signed certificate, you need to create the initial connection
        with `ignore_ssl_error=True`.

        Requires a recent VMware Tools to be installed in the Guest VM. If you
        get the error 'The guest operations agent is out of date.' then you
        need to update VMware Tools.

        :param vm: A VM to upload the file to (see `get_vm`). The VM must be
            powered on.
        :param vm_username: The username for the account in the VM to
            authenticate against.
        :param vm_password: The password for the account in the VM to
            authenticate against.
        :param path_in_vm: The path to the file in the VM.
        :param index: Optional integer specifying start of directory listing.
        :param max_results: Optional integer specify maxmimum number of entries
            to return.
        :param match_patter: Optional string specifying Perl-compatible
            regular-expression to filter results.

        The result is a vim.vm.guest.FileManager.ListFileInfo. The `files`
        property on that is a list of `vim.vm.guest.FileManager.ListFileInfo`.
        For example:

        # noqa: E501

            (vim.vm.guest.FileManager.ListFileInfo) {
               dynamicType = <unset>,
               dynamicProperty = (vmodl.DynamicProperty) [],
               files = (vim.vm.guest.FileManager.FileInfo) [
                  (vim.vm.guest.FileManager.FileInfo) {
                     dynamicType = <unset>,
                     dynamicProperty = (vmodl.DynamicProperty) [],
                     path = '.',
                     type = 'directory',
                     size = 0L,
                     attributes = (vim.vm.guest.FileManager.PosixFileAttributes) {
                        dynamicType = <unset>,
                        dynamicProperty = (vmodl.DynamicProperty) [],
                        modificationTime = 2017-07-04T13:45:10Z,
                        accessTime = 2017-07-04T13:59:56Z,
                        symlinkTarget = '',
                        ownerId = 0,
                        groupId = 0,
                        permissions = 17407L
                     }
                  },
                  (vim.vm.guest.FileManager.FileInfo) {
                     dynamicType = <unset>,
                     dynamicProperty = (vmodl.DynamicProperty) [],
                     path = '..',
                     type = 'directory',
                     size = 0L,
                     attributes = (vim.vm.guest.FileManager.PosixFileAttributes) {
                        dynamicType = <unset>,
                        dynamicProperty = (vmodl.DynamicProperty) [],
                        modificationTime = 2017-05-05T10:29:07Z,
                        accessTime = 2017-06-14T16:05:46Z,
                        symlinkTarget = '',
                        ownerId = 0,
                        groupId = 0,
                        permissions = 16877L
                     }
                  },
                  (vim.vm.guest.FileManager.FileInfo) {
                     dynamicType = <unset>,
                     dynamicProperty = (vmodl.DynamicProperty) [],
                     path = 'test_file',
                     type = 'file',
                     size = 4194304L,
                     attributes = (vim.vm.guest.FileManager.PosixFileAttributes) {
                        dynamicType = <unset>,
                        dynamicProperty = (vmodl.DynamicProperty) [],
                        modificationTime = 2017-07-04T13:59:55Z,
                        accessTime = 2017-07-04T13:59:55Z,
                        symlinkTarget = '',
                        ownerId = 1000,
                        groupId = 1000,
                        permissions = 33188L
                     }
                  },
               ],
               remaining = 0
            }
        """
        if isinstance(vm, six.string_types):
            vm = self.get_vm(vm)
        creds = vim.vm.guest.NamePasswordAuthentication(
            username=vm_username, password=vm_password)
        fm = self.content.guestOperationsManager.fileManager
        kwargs = {}
        if index is not None:
            kwargs['index'] = int(index)
        if max_results is not None:
            kwargs['maxResults'] = int(max_results)
        if match_pattern is not None:
            kwargs['matchPattern'] = str(match_pattern)
        return fm.ListFilesInGuest(vm, creds, path_in_vm, **kwargs)

    def make_directory_in_vm(
            self, vm, vm_username, vm_password, directory_name,
            create_parents=True):
        """
        Create a directory in the VM.

        :param vm: A VM to create the directory in (see `get_vm`). The VM must
            be powered on.
        :param vm_username: The username for the account in the VM to
            authenticate against.
        :param vm_password: The password for the account in the VM to
            authenticate against.
        :param directory_name: The full path of the directory to create
        :param create_parents: If True, any intermediate directories that
            do not exist will be created. If False, they will not and must
            exist already.
        """
        if isinstance(vm, six.string_types):
            vm = self.get_vm(vm)
        creds = vim.vm.guest.NamePasswordAuthentication(
            username=vm_username, password=vm_password)
        fm = self.content.guestOperationsManager.fileManager
        return fm.MakeDirectoryInGuest(
            vm, creds, directory_name, create_parents)

    def delete_file_in_vm(
            self, vm, vm_username, vm_password, file_path):
        """
        Delete a file in the VM.

        :param vm: A VM to delete the file in (see `get_vm`). The VM must be
            powered on.
        :param vm_username: The username for the account in the VM to
            authenticate against.
        :param vm_password: The password for the account in the VM to
            authenticate against.
        :param file_path: The full path of the file to delete.
        """
        creds = vim.vm.guest.NamePasswordAuthentication(
            username=vm_username, password=vm_password)
        fm = self.content.guestOperationsManager.fileManager
        return fm.DeleteFileInGuest(vm, creds, file_path)

    def delete_directory_in_vm(
            self, vm, vm_username, vm_password, directory_name,
            recursive=True):
        """
        Delete a directory in the VM and optionally all its contents.

        :param vm: A VM to delete the directory in (see `get_vm`). The VM must
            be powered on.
        :param vm_username: The username for the account in the VM to
            authenticate against.
        :param vm_password: The password for the account in the VM to
            authenticate against.
        :param directory_name: The full path of the directory to delete.
        :param recursive: If True, the content of the directory will also be
            deleted. If False, the directory must be empty.
        """
        if isinstance(vm, six.string_types):
            vm = self.get_vm(vm)
        creds = vim.vm.guest.NamePasswordAuthentication(
            username=vm_username, password=vm_password)
        fm = self.content.guestOperationsManager.fileManager
        return fm.DeleteDirectoryInGuest(vm, creds, directory_name, recursive)

    def start_process_in_vm(
            self, vm, vm_username, vm_password, command, arguments="",
            working_dir=None, interactive=False):
        """
        Execute a command in the VM.

        Makes an SSL connection direct to the host, and so if your host has a
        bad self-signed certificate, you need to create the initial connection
        with `ignore_ssl_error=True`.

        Requires a recent VMware Tools to be installed in the Guest VM. If you
        get the error 'The guest operations agent is out of date.' then you
        need to update VMware Tools.

        :param vm: A VM to upload the file to (see `get_vm`). The VM must be
            powered on.
        :param vm_username: The username for the account in the VM to
            authenticate against.
        :param vm_password: The password for the account in the VM to
            authenticate against.
        :param command: The path to the executable to execute in the VM.
        :param arguments: The command line arguments (as a single string) to
            pass to the executable.
        :param working_dir: (Optional) path to the working directory on the
            VM in which the command should be executed.
        :param interactive: (Optional.) Whether an interactive session on the
            VM is required.

        Returns the PID of the new process.
        """
        if isinstance(vm, six.string_types):
            vm = self.get_vm(vm)
        creds = vim.vm.guest.NamePasswordAuthentication(
            username=vm_username, password=vm_password)
        if interactive:
            creds.interactiveSession = True
        pm = self.content.guestOperationsManager.processManager
        spec = vim.vm.guest.ProcessManager.ProgramSpec()
        spec.programPath = command
        spec.arguments = arguments
        if working_dir is not None:
            spec.workingDirectory = working_dir
        pid = pm.StartProgramInGuest(vm, creds, spec)
        return pid

    def list_processes_in_vm(
            self, vm, vm_username, vm_password, pid_list=None,
            interactive=False):
        """
        List the processes running in a VM.

        Makes an SSL connection direct to the host, and so if your host has a
        bad self-signed certificate, you need to create the initial connection
        with `ignore_ssl_error=True`.

        Requires a recent VMware Tools to be installed in the Guest VM. If you
        get the error 'The guest operations agent is out of date.' then you
        need to update VMware Tools.

        :param vm: A VM to upload the file to (see `get_vm`). The VM must be
            powered on.
        :param vm_username: The username for the account in the VM to
            authenticate against.
        :param vm_password: The password for the account in the VM to
            authenticate against.
        :param pid_list: An optional list of PIDs to query. If None, all PIDs
            are returned.
        :param interactive: (Optional.) Whether an interactive session has
            been used. See `start_process_in_vm`.

        Returns the a list of GuestProcessInfo objects.
        """
        if isinstance(vm, six.string_types):
            vm = self.get_vm(vm)
        creds = vim.vm.guest.NamePasswordAuthentication(
            username=vm_username, password=vm_password)
        if interactive:
            creds.interactiveSession = True
        pm = self.content.guestOperationsManager.processManager
        args = [vm, creds]
        if pid_list is not None:
            args.append(pid_list)
        result = pm.ListProcessesInGuest(*args)
        return result

    def revert_vm_to_snapshot(self, vm, snapshot):
        """
        Revert a VM to a previously taken snapshot.

        :param vm: The VM to revert (see `get_vm`)
        :param snapshot: The name of the snapshot to revert to as a
            string, or a vim.vm.Snapshot object.
        """
        if isinstance(snapshot, six.string_types):
            snapshot = self.find_snapshot(vm, snapshot)
        self.wait_for_tasks([snapshot.RevertToSnapshot_Task()])

    def find_snapshot(self, vm, snapshot_name):
        """
        Find the named snapshot for a VM.

        Snapshots form a tree structure - they can have children and siblings.
        We crawl the tree finding a match on the name.

        :param vm: The VM to search (see `get_vm`)
        :param snapshot_name: The name of the snapshot to find.

        Returns a vim.vm.Snapshot object.
        """
        def walk_snapshot_list(snapshot_list, snapshot_name):
            for node in snapshot_list:
                if node.name == snapshot_name:
                    return node.snapshot
                elif node.childSnapshotList:
                    child = walk_snapshot_list(
                        node.childSnapshotList, snapshot_name)
                    if child is not None:
                        return child
            return None

        if isinstance(vm, six.string_types):
            vm = self.get_vm(vm)
        result = walk_snapshot_list(
            vm.snapshot.rootSnapshotList, snapshot_name)
        if result is None:
            raise ValueError("Snapshot %r not found" % snapshot_name)
        else:
            return result

    def _get_obj(self, vimtype, name, folder=None):
        """Return an object by name.

        If name is None the first found object is returned.

        From https://github.com/vmware/pyvmomi-community-samples.
        """
        obj = None
        container = self.get_container_view(vimtype, folder)
        for c in container.view:
            if name:
                if c.name == name:
                    obj = c
                    break
            else:
                obj = c
                break
        container.Destroy()
        return obj

##############################################################################
# End of file
##############################################################################
