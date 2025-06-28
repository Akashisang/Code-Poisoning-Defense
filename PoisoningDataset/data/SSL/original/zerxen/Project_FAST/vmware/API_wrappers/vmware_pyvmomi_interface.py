'''
Created on Feb 24, 2017

@author: havrila
'''
import argparse
import atexit
import getpass
import ipaddress
import logging
import os.path
import requests

'''
CHANGE
'''
import time

from time import sleep
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
from vspk import v4_0 as vsdk

from vmware_access_configuration import vcenter_configuration

class vmware_pyvmomi_wrapper(object):
    '''
    classdocs
    '''


    def __init__(self):
        '''
        Constructor
        '''
        self.username = vcenter_configuration.username
        self.password = vcenter_configuration.password
        self.vcenter_ip = vcenter_configuration.vcenter_ip
        self.vcenter_port = vcenter_configuration.vcenter_port
        
    def connect(self):
        print("Connecting to vCenter...")
        
        # Disabling SSL verification if set
        ssl_context = None
        requests.packages.urllib3.disable_warnings()
        import ssl
        if hasattr(ssl, 'SSLContext'):
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            ssl_context.verify_mode = ssl.CERT_NONE    
                
        try:
            self.vc = None
        
            # Connecting to vCenter
            try:
                print('Connecting to vCenter server %s:%s with username %s' % (self.vcenter_ip, self.vcenter_port, self.username))
                self.vc = SmartConnect(host=self.vcenter_ip, user=self.username, pwd=self.password, port=int(self.vcenter_port), sslContext=ssl_context)
            except IOError, e:
                pass
    
            if not self.vc:
                print('Could not connect to vCenter host %s with user %s and specified password' % (self.vcenter_ip, self.username))
                return 1
    
            print('Connected to vCenter server')
    
            print('Registering vCenter disconnect at exit')
            atexit.register(Disconnect, self.vc) 
            
        except vmodl.MethodFault, e:
            print('Caught vmodl fault: %s' % e.msg)
            return 1
        except Exception, e:
            print('Caught exception: %s' % str(e))
            return 1                       
        
    
    '''
    VMs - atomic
    '''   
       
    def print_all_vms(self):
        print("Listing all vCenter VMs")
        
        """
        Find a virtual machine by its name and return it
        """
        obj_view = self.vc.content.viewManager.CreateContainerView(self.vc.content.rootFolder, [vim.VirtualMachine], True)
        vm_list = obj_view.view
    
        for vm in vm_list:
            print('Found VM: %s' % vm.name)
        return None 
    
    def print_all_folders(self):
        content = self.vc.content
        obj_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.Folder], True)
        folder_list = obj_view.view 
        for folder in folder_list:
            print('Folder: %s' % folder.name)  
            
    def print_all_resource_pools(self):
        content = self.vc.content
        obj_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.ResourcePool], True)
        rp_list = obj_view.view 
        for rp in rp_list:
            print('Resource Pool: %s' % rp.name)                            
        
    
    def find_vm(self, name):
        """
        Find a virtual machine by its name and return it
        """
    
        content = self.vc.content
        obj_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
        vm_list = obj_view.view
    
        for vm in vm_list:
            #print('Checking virtual machine %s' % vm.name)
            if vm.name == name:
                print('Found virtual machine %s' % vm.name)
                return vm
        return None
    
    
    def find_resource_pool(self, name):
        """
        Find a resource pool by its name and return it
        """
    
        content = self.vc.content
        obj_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.ResourcePool], True)
        rp_list = obj_view.view
    
        for rp in rp_list:
            print('Checking Resource pool  %s' % rp.name)
            if rp.name == name:
                print('Found Resource poo %s' % rp.name)
                return rp
        return None
    
    """
     Get the datastore based on name
    """
    def get_datastore(self,name):
        for dc in self.vc.content.rootFolder.childEntity:
            print('Checking Datacenter %s' % dc)
            for ds in dc.datastore:
                print('Checking DataStore %s' % ds.name)
                if ds.name == name:
                    print('Found! %s' % name)
                    return ds
        return None                    
    
    
    def find_folder(self, name):
        """
        Find a folder by its name and return it
        """
    
        content = self.vc.content
        obj_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.Folder], True)
        folder_list = obj_view.view
    
        for folder in folder_list:
            print('Checking folder %s' % folder.name)
            if folder.name == name:
                print('Found folder %s' % folder.name)
                return folder
        return None   
    
    def delete_vm(self,name):
        # Find the correct VM template
        print('Finding vm %s' % name)
        vm = self.find_vm(name)   
        if vm is None:
            print('Unable to find VM %s' % name)
            return 1
        print('VM %s found' % name) 
        
        if vm.runtime.powerState == "poweredOff":
            print('Powering OFF VM is not needed, moving to deletion directly')
        else:            
            print('Powering OFF VM. This might take a couple of seconds')
            power_off_task = vm.PowerOffVM_Task()
            
            print('Waiting fo VM to power OFF')
            run_loop = True
            while run_loop:
                info = power_off_task.info
                if info.state == vim.TaskInfo.State.success:
                    run_loop = False
                    break
                elif info.state == vim.TaskInfo.State.error:
                    if info.error.fault:
                        print('Power OFF has quit with error: %s' % info.error.fault.faultMessage)
                    else:
                        print('Power OFF has quit with cancelation')
                    run_loop = False
                    break
                sleep(5)  
            
        print('Deleting VM. This might take a couple of seconds')
        power_off_task = vm.Destroy_Task()
        
        print('Waiting fo VM to Deleting')
        run_loop = True
        while run_loop:
            info = power_off_task.info
            if info.state == vim.TaskInfo.State.success:
                run_loop = False
                print('DELETION SUCCESSFULL')
                break
            elif info.state == vim.TaskInfo.State.error:
                if info.error.fault:
                    print('Deleting has quit with error: %s' % info.error.fault.faultMessage)
                else:
                    print('Deleting has quit with cancelation')
                run_loop = False
                break
            sleep(5)                 
         
    
    def create_vm_from_template(self,template,
                                resource_pool,
                                datastore,
                                name,
                                nuage_enterprise,
                                nuage_user,
                                production_nic_name,
                                production_nic_domain,
                                production_nic_zone,
                                production_nic_subnet,
                                production_nic_ip_type,
                                production_nic_ip,                                
                                dxc_nic_domain,
                                dxc_nic_zone,
                                dxc_nic_subnet,
                                ixia_nic_address,
                                ixia_nic_netmask,
                                ixia_nic_gateway,
                                ixia_nic_dns1,
                                ixia_nic_dns2,
                                ixia_nic_domain,
                                power_on,
                                no_dxc):
        print("Starting create vm from template ...")
        print("")
        print("New VM parameters:")
        print("=============================================")
        print("NAME: " + name)
        print("from template: " + template)
        print("target resource pool: " + resource_pool)
        print("")
        print("Nuage parameters:")
        print("nuage enterprise: " + nuage_enterprise)
        print("nuage user: " + nuage_user)
        print("nuage production:")
        print("- name: "    + production_nic_name)
        print("- domain: "  + production_nic_domain)
        print("- zone  : "  + production_nic_zone)
        print("- subnet: "  + production_nic_subnet)
        print("- ip-type: " + production_nic_ip_type)
        print("- ip: "      + production_nic_ip)
        print("nuage dxc NIC#2:")
        print("- domain: " + dxc_nic_domain)
        print("- zone  : " + dxc_nic_zone)
        print("- subnet: " + dxc_nic_subnet) 
        print("Traditional VLAN interface NIC#3:")
        print("- address: " + ixia_nic_address)
        print("- netmask: " + ixia_nic_netmask)
        print("- gateway: " + ixia_nic_gateway) 
        print("- dns1   : " + ixia_nic_dns1)
        print("- dns2   : " + ixia_nic_dns2) 
        print("- domain : " + ixia_nic_domain) 
        print("SPECIAL VM Settings:")
        print("    POWER ON: " + str(power_on) )
        print("    NO DXC interface: " + str(no_dxc))
        print("=============================================")
        print("")   
        
        # Find the correct VM template
        print('Finding template %s' % template)
        obj_view = self.vc.content.viewManager.CreateContainerView(self.vc.content.rootFolder, [vim.VirtualMachine], True)
        vm_list = obj_view.view
        template_vm = self.find_vm(template)   
        if template_vm is None:
            print('Unable to find template %s' % template)
            return 1
        print('Template %s found' % template)   
        
        
        # Find the correct Datastore
        print('Finding datastore %s' % datastore)
        datastore_object = self.get_datastore(datastore)    
        if datastore_object is None:
            print('Unable to find datastore %s' % datastore)
            return 1
        print('datastore %s found' % datastore)   
        
                
        
        # Find the correct Resource Pool
        print('Finding resource pool %s' % resource_pool)
        resource_pool_object = self.find_resource_pool(resource_pool)
        if resource_pool_object is None:
            print('Unable to find resource pool %s' % resource_pool)
            return 1
        print('Resource pool %s found' % resource_pool)
        
     
        
        # Find the correct folder
        print('Setting folder to template folder as default: ')
        folder = template_vm.parent
        print(folder)    
        
        # Creating necessary specs
        print('Creating relocate spec from datastore and resouce pool')
        
        
        if resource_pool_object is None:
            print('No resource pool found!')
            return 1     
        if datastore_object is None:
            print('No datastore found!')
            return 1                    
        else:
            relocate_spec = vim.vm.RelocateSpec(pool=resource_pool_object,datastore=datastore_object)  
        
        print('Creating clone spec')
        clone_spec = vim.vm.CloneSpec(powerOn=False, template=False, location=relocate_spec)   
        
        
        ''' CREATION OF THE VM ITSELF '''
        
        run_loop = True
        vm = None
        print('Trying to clone %s to new virtual machine' % template)

        if self.find_vm(name):
            print('Virtual machine with this name already exists, not creating!')
            run_loop = False
        else:
            print('Creating clone task')
            task = template_vm.Clone(name=name, folder=folder, spec=clone_spec)
            print('Cloning task created')
            print('Checking task for completion. This might take a while')
            #result = WaitTask(task, 'VM clone task')
        
        while run_loop:
            info = task.info
            print('Checking clone task')
            if info.state == vim.TaskInfo.State.success:
                print('Cloned and running')
                vm = info.result
                run_loop = False
                break
            elif info.state == vim.TaskInfo.State.running:
                print('Cloning task is at %s percent' % info.progress)
            elif info.state == vim.TaskInfo.State.queued:
                print('Cloning task is queued')
            elif info.state == vim.TaskInfo.State.error:
                #pprint(info)
                if info.error.fault:
                    print('Cloning task has quit with error: %s' % info.error.fault.faultMessage)
                else:
                    print('Cloning task has quit with cancelation')
                run_loop = False
                break
            print('Sleeping 10 seconds for new check')
            sleep(10) 
        
        # If the VM does not exist, cloning failed and the script is terminated
        if not vm:
            print('Clone failed')
            return 1     
        
        # Setting Nuage metadata
        print('Setting Nuage Metadata')
        vm_option_values = []
        # Enterprise
        vm_option_values.append(vim.option.OptionValue(key='nuage.enterprise', value=nuage_enterprise))
        # User
        vm_option_values.append(vim.option.OptionValue(key='nuage.user', value=nuage_user))
        
        print('Setting Nuage Metadata for name: ' +production_nic_name+  ' - production')        
        # Domain
        vm_option_values.append(vim.option.OptionValue(key='nuage.' +production_nic_name+ '.domain', value=production_nic_domain))
        # Zone
        vm_option_values.append(vim.option.OptionValue(key='nuage.' +production_nic_name+ '.zone', value=production_nic_zone))
        # Subnet
        vm_option_values.append(vim.option.OptionValue(key='nuage.' +production_nic_name+ '.network', value=production_nic_subnet))
        # Network type
        vm_option_values.append(vim.option.OptionValue(key='nuage.' +production_nic_name+ '.networktype', value='ipv4'))
        
        if production_nic_ip_type == 'static':
            vm_option_values.append(vim.option.OptionValue(key='nuage.' +production_nic_name+ '.ip', value=production_nic_ip))            
            
        # IP
        #if vm_ip:
        #    vm_option_values.append(vim.option.OptionValue(key='nuage.nic0.ip', value=vm_ip))
        if no_dxc == 0:
            print('Setting Nuage Metadata for NIC1 - dxc management')        
            # Domain
            vm_option_values.append(vim.option.OptionValue(key='nuage.nic1.domain', value=dxc_nic_domain))
            # Zone
            vm_option_values.append(vim.option.OptionValue(key='nuage.nic1.zone', value=dxc_nic_zone))
            # Subnet
            vm_option_values.append(vim.option.OptionValue(key='nuage.nic1.network', value=dxc_nic_subnet))
            # Network type
            vm_option_values.append(vim.option.OptionValue(key='nuage.nic1.networktype', value='ipv4'))        


        print('Creating of config spec for VM')
        config_spec = vim.vm.ConfigSpec(extraConfig=vm_option_values)
        print('Applying advanced parameters. This might take a couple of seconds')
        config_task = vm.ReconfigVM_Task(spec=config_spec)
        print('Waiting for the advanced paramerter to be applied')
        run_loop = True
        while run_loop:
            info = config_task.info
            if info.state == vim.TaskInfo.State.success:
                print('Advanced parameters applied')
                run_loop = False
                break
            elif info.state == vim.TaskInfo.State.error:
                if info.error.fault:
                    print('Applying advanced parameters has quit with error: %s' % info.error.fault.faultMessage)
                else:
                    print('Applying advanced parameters has quit with cancelation')
                run_loop = False
                break
            sleep(5)
            
        '''
        Configuring the IXIA interface
        '''    
        adaptermap = vim.vm.customization.AdapterMapping()
        globalip = vim.vm.customization.GlobalIPSettings()
        adaptermap.adapter = vim.vm.customization.IPSettings()
        
        fake_adaptermap = vim.vm.customization.AdapterMapping()
        fake_globalip = vim.vm.customization.GlobalIPSettings()
        fake_adaptermap.adapter = vim.vm.customization.IPSettings()        
        

        """Static IP Configuration for IXIA interface"""
        adaptermap.adapter.ip = vim.vm.customization.FixedIp()
        adaptermap.adapter.ip.ipAddress = ixia_nic_address
        adaptermap.adapter.subnetMask = ixia_nic_netmask
        if ixia_nic_gateway != '': 
            adaptermap.adapter.gateway = ixia_nic_gateway 
        globalip.dnsServerList = ixia_nic_dns1 + "," + ixia_nic_dns2
            
        """DHCP Configuration for NIC0 and NIC1 that nuage is taking care of"""
        fake_adaptermap.adapter.ip = vim.vm.customization.DhcpIpGenerator()
            
        adaptermap.adapter.dnsDomain = ixia_nic_domain
        globalip = vim.vm.customization.GlobalIPSettings()
        
        #For Linux . For windows follow sysprep
        ident = vim.vm.customization.LinuxPrep(domain=ixia_nic_domain, hostName=vim.vm.customization.FixedName(name=name))        
        
        customspec = vim.vm.customization.Specification()
        #For only one adapter
        customspec.identity = ident
        
        if no_dxc == 0:
            ''' in this case 3 interfaces exist, nuage, nuage-DXC and IXIA'''
            customspec.nicSettingMap = [fake_adaptermap,fake_adaptermap,adaptermap]
        else:
            ''' in this case only 2 interfaces exist, nuage and IXIA'''
            customspec.nicSettingMap = [fake_adaptermap,adaptermap]
        customspec.globalIPSettings = globalip
        
        #Configuring network for a single NIC
        #For multipple NIC configuration contact me.

        print "Reconfiguring VM Networks . . ."
        
        task = vm.Customize(spec=customspec)

        """
        Waits and provides updates on a vSphere task
        """
        
        while task.info.state == vim.TaskInfo.State.running:
            time.sleep(2)
        
        if task.info.state == vim.TaskInfo.State.success:
            out = '%s completed successfully, result: %s' % ('job', task.info.result)
            print(out)
        else:
            out = '%s did not complete successfully: %s' % ('job', task.info.error)
            raise task.info.error
            print(out)
        
        print(task.info.result)        

        '''
        Activate VM if power_on parameter recieved
        '''
        if power_on is not None and power_on == 1:
            print('Powering on VM. This might take a couple of seconds')
            power_on_task = vm.PowerOn()
            
            print('Waiting fo VM to power on')
            run_loop = True
            while run_loop:
                info = power_on_task.info
                if info.state == vim.TaskInfo.State.success:
                    run_loop = False
                    break
                elif info.state == vim.TaskInfo.State.error:
                    if info.error.fault:
                        print('Power on has quit with error: %s' % info.error.fault.faultMessage)
                    else:
                        print('Power on has quit with cancelation')
                    run_loop = False
                    break
                sleep(5)  
                
        '''
        Execute local command as wished
        '''
        #while 1:
        #    vm = self.find_vm(name)
        #    print (vm.guest.toolsStatus)
        #    sleep(10)                                
        
             
        
                                      
        


        
               
    
            