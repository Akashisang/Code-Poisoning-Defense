# -*- coding: utf-8 -*-
"""
deploy_vsphere_template_with_nuage is a script which allows you to deploy (or clone) a VM template (or VM) and connect it to a Nuage VSP subnet.

This can be done through either specifying all parameters through CLI, or by selecting them from lists.

Check the examples for several combinations of arguments

--- Usage ---
Run 'python deploy_vsphere_template_with_nuage.py -h' for an overview

--- Documentation ---
http://github.com/nuagenetworks/vspk-examples/blob/master/docs/deploy_vsphere_template_with_nuage.md

--- Author ---
Philippe Dellaert <philippe.dellaert@nuagenetworks.net>

--- Examples ---
---- Deploy a template in a given Resource Pool and Folder, with given Nuage VM metadata and a fixed IP ----
python deploy_vsphere_template_with_nuage.py -n Test-02 --nuage-enterprise csp --nuage-host 10.167.43.64 --nuage-user csproot -S -t TestVM-Minimal-Template --vcenter-host 10.167.43.24 --vcenter-user root -r Pool -f Folder --nuage-vm-enterprise VMware-Integration --nuage-vm-domain Main --nuage-vm-zone "Zone 1" --nuage-vm-subnet "Subnet 0" --nuage-vm-ip 10.0.0.123 --nuage-vm-user vmwadmin

---- Deploy a template, for the Nuage VM metadata show menus to select values from ----
python deploy_vsphere_template_with_nuage.py -n Test-02 --nuage-enterprise csp --nuage-host 10.167.43.64 --nuage-user csproot -S -t TestVM-Minimal-Template --vcenter-host 10.167.43.24 --vcenter-user root
"""
import argparse
import atexit
import getpass
import ipaddress
import logging
import os.path
import requests
import pprint
'''
CHANGE
'''
import time

from time import sleep
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
from vspk import v4_0 as vsdk


"""
 Waits and provides updates on a vSphere task
"""
def WaitTask(task, actionName='job', hideResult=False):
    #print 'Waiting for %s to complete.' % actionName
    
    while task.info.state == vim.TaskInfo.State.running:
        time.sleep(2)
    
    if task.info.state == vim.TaskInfo.State.success:
        if task.info.result is not None and not hideResult:
            out = '%s completed successfully, result: %s' % (actionName, task.info.result)
        else:
            out = '%s completed successfully.' % actionName
    else:
        out = '%s did not complete successfully: %s' % (actionName, task.info.error)
        print out
        raise task.info.error # should be a Fault... check XXX
    
    # may not always be applicable, but can't hurt.
    return task.info.result


def get_args():
    """
    Supports the command-line arguments listed below.
    """

    parser = argparse.ArgumentParser(description="Deploy a template into into a VM with certain Nuage VSP metadata.")
    parser.add_argument('-d', '--debug', required=False, help='Enable debug output', dest='debug', action='store_true')
    parser.add_argument('-f', '--folder', required=False, help='The folder in which the new VM should reside (default = same folder as source virtual machine)', dest='folder', type=str)
    parser.add_argument('-l', '--log-file', required=False, help='File to log to (default = stdout)', dest='logfile', type=str)
    parser.add_argument('-S', '--disable-SSL-certificate-verification', required=False, help='Disable SSL certificate verification on connect', dest='nosslcheck', action='store_true')
    parser.add_argument('-t', '--template', required=True, help='VM to destroy', dest='template', type=str)
    parser.add_argument('--vcenter-host', required=True, help='The vCenter or ESXi host to connect to', dest='vcenter_host', type=str)
    parser.add_argument('--vcenter-port', required=False, help='vCenter Server port to connect to (default = 443)', dest='vcenter_port', type=int, default=443)
    parser.add_argument('--vcenter-password', required=False, help='The password with which to connect to the vCenter host. If not specified, the user is prompted at runtime for a password', dest='vcenter_password', type=str)
    parser.add_argument('--vcenter-user', required=True, help='The username with which to connect to the vCenter host', dest='vcenter_username', type=str)
    parser.add_argument('-v', '--verbose', required=False, help='Enable verbose output', dest='verbose', action='store_true')

    args = parser.parse_args()
    return args


def clear(logger):
    """
    Clears the terminal
    """
    if logger:
        logger.debug('Clearing terminal')
    os.system(['clear', 'cls'][os.name == 'nt'])


def find_vm(vc, logger, name):
    """
    Find a virtual machine by its name and return it
    """

    content = vc.content
    obj_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    vm_list = obj_view.view

    for vm in vm_list:
        logger.debug('Checking virtual machine %s' % vm.name)
        if vm.name == name:
            logger.debug('Found virtual machine %s' % vm.name)
            return vm
    return None


def find_resource_pool(vc, logger, name):
    """
    Find a resource pool by its name and return it
    """

    content = vc.content
    obj_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.ResourcePool], True)
    rp_list = obj_view.view

    for rp in rp_list:
        logger.debug('Checking resource pool %s' % rp.name)
        if rp.name == name:
            logger.debug('Found resource pool %s' % rp.name)
            return rp
    return None


def find_folder(vc, logger, name):
    """
    Find a folder by its name and return it
    """

    content = vc.content
    obj_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.Folder], True)
    folder_list = obj_view.view

    for folder in folder_list:
        logger.debug('Checking folder %s' % folder.name)
        if folder.name == name:
            logger.debug('Found folder %s' % folder.name)
            return folder
    return None


def main():
    """
    Manage the vCenter Integration Node configuration
    """

    # Handling arguments
    args                = get_args()
    debug               = args.debug

    log_file            = None
    if args.logfile:
        log_file        = args.logfile


    nosslcheck          = args.nosslcheck
    template            = args.template
    vcenter_host        = args.vcenter_host
    vcenter_port        = args.vcenter_port
    vcenter_password    = None
    if args.vcenter_password:
        vcenter_password = args.vcenter_password
    vcenter_username    = args.vcenter_username
    verbose             = args.verbose

    # Logging settings
    if debug:
        log_level = logging.DEBUG
    elif verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    logging.basicConfig(filename=log_file, format='%(asctime)s %(levelname)s %(message)s', level=log_level)
    logger = logging.getLogger(__name__)

    # Disabling SSL verification if set
    ssl_context = None
    if nosslcheck:
        logger.debug('Disabling SSL certificate verification.')
        requests.packages.urllib3.disable_warnings()
        import ssl
        if hasattr(ssl, 'SSLContext'):
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            ssl_context.verify_mode = ssl.CERT_NONE

    # Getting user password for vCenter connection
    if vcenter_password is None:
        logger.debug('No command line vCenter password received, requesting vCenter password from user')
        vcenter_password = getpass.getpass(prompt='Enter password for vCenter host %s for user %s: ' % (vcenter_host, vcenter_username))

    try:
        vc = None

        # Connecting to vCenter
        try:
            logger.info('Connecting to vCenter server %s:%s with username %s' % (vcenter_host, vcenter_port, vcenter_username))
            if ssl_context:
                vc = SmartConnect(host=vcenter_host, user=vcenter_username, pwd=vcenter_password, port=int(vcenter_port), sslContext=ssl_context)
            else:
                vc = SmartConnect(host=vcenter_host, user=vcenter_username, pwd=vcenter_password, port=int(vcenter_port))
        except IOError, e:
            pass

        if not vc:
            logger.error('Could not connect to vCenter host %s with user %s and specified password' % (vcenter_host, vcenter_username))
            return 1

        logger.info('Connected to both Nuage & vCenter servers')

        logger.debug('Registering vCenter disconnect at exit')
        atexit.register(Disconnect, vc)

        # Find the correct VM
        logger.debug('Finding VM %s' % template)
        template_vm = find_vm(vc, logger, template)
        if template_vm is None:
            logger.error('Unable to find VM %s' % template)
            return 1
        logger.info('VM %s found' % template)
        logger.info('VM is in %s power state' % template_vm.runtime.powerState)

        if template_vm.runtime.powerState == "poweredOff":
            logger.info('Powering OFF VM is not needed, moving to deletion directly')
        else:            
            logger.info('Powering OFF VM. This might take a couple of seconds')
            power_on_task = template_vm.PowerOffVM_Task()
            
            logger.debug('Waiting fo VM to power OFF')
            run_loop = True
            while run_loop:
                info = power_on_task.info
                if info.state == vim.TaskInfo.State.success:
                    run_loop = False
                    break
                elif info.state == vim.TaskInfo.State.error:
                    if info.error.fault:
                        logger.info('Power OFF has quit with error: %s' % info.error.fault.faultMessage)
                    else:
                        logger.info('Power OFF has quit with cancelation')
                    run_loop = False
                    break
                sleep(5)
                
        '''
        IP ADDRESSES
        '''
        
        vm = template_vm
        
        inputs = {'vm_ip' : '29.203.240.5',
                  'subnet' : '255.255.255.240',
                  'gateway' : '29.203.240.1',
                  'dns' : ['15.163.248.60', '15.163.248.61'],
                  'domain' : 'ng1labpln.mcloud.entsvcs.net'
        }        
                
        adaptermap = vim.vm.customization.AdapterMapping()
        globalip = vim.vm.customization.GlobalIPSettings()
        adaptermap.adapter = vim.vm.customization.IPSettings()
         
        adaptermap.adapter.ip = vim.vm.customization.FixedIp()
        adaptermap.adapter.ip.ipAddress = inputs['vm_ip']
        adaptermap.adapter.subnetMask = inputs['subnet']
        adaptermap.adapter.gateway = inputs['gateway']  
        globalip.dnsServerList = inputs['dns'] 
        adaptermap.adapter.dnsDomain = inputs['domain'] 
        globalip = vim.vm.customization.GlobalIPSettings() 
        
        ident = vim.vm.customization.LinuxPrep(domain=inputs['domain'], hostName=vim.vm.customization.FixedName(name=template))                    
        
        customspec = vim.vm.customization.Specification()
        #For only one adapter
        customspec.identity = ident
        customspec.identity.hostname = "TestESX12_I1_s1"
        customspec.nicSettingMap = [adaptermap]
        customspec.globalIPSettings = globalip  
        
        print "Reconfiguring VM Networks . . ."  
        
        task = vm.Customize(spec=customspec)
        print "1"
        run_loop = True
        while run_loop:
            info = task.info
            print "X"
            if info.state == vim.TaskInfo.State.success:
                run_loop = False
                break
            elif info.state == vim.TaskInfo.State.error:
                if info.error.fault:
                    logger.info('Configuring IP on VM failed with: %s' % info.error.fault.faultMessage)
                else:
                    logger.info('Configuring IP on VM got cancelation')
                run_loop = False
                break
            sleep(5)         
                    
          
            
        logger.info('Deleting VM. This might take a couple of seconds')
        power_on_task = template_vm.Destroy_Task()
        
        logger.debug('Waiting fo VM to Deleting')
        run_loop = True
        while run_loop:
            info = power_on_task.info
            if info.state == vim.TaskInfo.State.success:
                run_loop = False
                break
            elif info.state == vim.TaskInfo.State.error:
                if info.error.fault:
                    logger.info('Deleting has quit with error: %s' % info.error.fault.faultMessage)
                else:
                    logger.info('Deleting has quit with cancelation')
                run_loop = False
                break
            sleep(5)  
            
    except vmodl.MethodFault, e:
        logger.critical('Caught vmodl fault: %s' % e.msg)
        return 1
    except Exception, e:
        logger.critical('Caught exception: %s' % str(e))
        return 1                             

# Start program
if __name__ == "__main__":
    main()
