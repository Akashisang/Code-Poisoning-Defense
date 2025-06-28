'''
Author : Gassim Salah-Eddine

Description : This script look for a specific virtual machine and extract all the related events.
              The events type can be one of the following: Reboot, Shutdown or Standby.

Usage : ViewVmEvents -h

Website : http://www.vNugget.com

'''

import argparse, ssl, atexit
from pyVim import connect
from pyVmomi import vim
from colorama import init, Fore, Back, Style
init()

parser = argparse.ArgumentParser(description="View Events related to a specific virtual machine")
parser.add_argument("vc", help="vCenter Server FQDN or IP", metavar="vCenter")
parser.add_argument("user", help="Username to connect to the vCenter", metavar="UserName")
parser.add_argument("pwd", help="Password to connect to the vCenter", metavar="Password")
parser.add_argument("vm", help="Virtual machine name (Case-sensitive)", metavar="VirtualMachine")
parser.add_argument("event", help="Event type: Reboot, Shutdown, Standby", metavar="EventType")
args = parser.parse_args()

#########

eventType = {'Reboot':'VmGuestRebootEvent','Shutdown':'VmGuestShutdownEvent','Standby':'VmGuestStandbyEvent'}

if args.event not in eventType.keys():
    print("Please specify one of the following events type: Reboot, Shutdown, Standby")
    raise SystemExit(-1)



def main():
    content = None
    found = None
    # Disabling SSL certificate checking
<target>
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
</target>
    context.verify_mode = ssl.CERT_NONE
    
    si = None
    # Getting the Sevice Instance
    try:
        si = connect.SmartConnect(protocol="https",host=args.vc,port=443,user=args.user,pwd=args.pwd,sslContext=context)
    except:
        print("Could not connect to the specified vCenter, please check the provided FQDN/IP, username and password")
        raise SystemExit(-1)

    #Cleanly disconnect
    atexit.register(connect.Disconnect, si)

    content = si.RetrieveServiceContent()
    # retreive hosts
    hosts = content.viewManager.CreateContainerView(content.rootFolder,[vim.HostSystem],True)
    for h in hosts.view:
        #retreive VMs
                      
        for v in h.vm:
            if (args.vm == v.summary.config.name):
                print("\r\n[*] Virtual Machine \033[32m {} \033[0mis located on ESXi: \033[32m{}\033[0m and hosted on datastore: \033[32m{}\033[0m"\
                      .format(v.summary.config.name,h.summary.config.name,v.datastore[0].summary.name))
                
                eMgrRef = content.eventManager
                filter = vim.event.EventFilterSpec.ByEntity(entity=v, recursion="self")                
                filter_spec = vim.event.EventFilterSpec()
                filter_spec.eventTypeId = str(eventType[args.event])
                filter_spec.entity = filter
                
                event_res = eMgrRef.QueryEvents(filter_spec)
                print("[*] Events count : \033[32m{}\033[0m".format(len(event_res)))
                for e in event_res:
                    print("{} \033[32m@\033[0m {:%Y-%m-%d %H:%M:%S}".format(e.fullFormattedMessage,e.createdTime))
                found = True
                break


    if found != True:
        print("\r\nVirtual Machine \033[32m{}\033[0m Not Found".format(args.vm))
        
    hosts.Destroy()
    
main()