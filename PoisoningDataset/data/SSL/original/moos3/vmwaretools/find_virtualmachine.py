from ldap3 import Server, Connection, ALL, NTLM, Tls, ALL_ATTRIBUTES, SUBTREE, SYNC,SIMPLE, SEARCH_SCOPE_WHOLE_SUBTREE
import atexit
import argparse
import getpass
import ssl

from pyVim import connect
import requests.packages.urllib3
import socket
import pprint
from colorama import init
from colorama import Fore, Back, Style

# Disabling SSL certificate verification
context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
context.verify_mode = ssl.CERT_NONE
requests.packages.urllib3.disable_warnings()
# END Disable SSL Certificate verification

# Added hostnames to this list to be skipped, must match reverse dns lookups
skip_vcenters = []

### LDAP Settings
### Adjust these for openldap servers, these are currently setup for windows active directory
windowsDomainName = ''
userNameAttribute = 'userPrincipalName'
ldapHost = ''
ldapPort = 636
useSSL = True
baseDN = ''
### Adjust this based off your own org
## Currently Set for Windows AD usage
## filters based on the objects description
searchFilter = "(&(objectCategory=computer)(description=*vcent*)(!(description=*vcenterdb:*))(!(userAccountControl:1.2.840.113556.1.4.803:=2)))"

def datacenterIs(element):
    global datacenter
    if len(element) > 0:
        return element[:3] == datacenter
    return False

def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='Display name in ldap')

    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password to use when connecting to host')

    parser.add_argument('-n', '--name',
                        required=False,
                        action='store',
                        help='Instance Name of the VM to look for.')

    parser.add_argument('-d', '--uuid',
                        required=False,
                        action='store',
                        help='Instance UUID of the VM to look for.')

    args = parser.parse_args()
    if args.password is None:
        args.password = getpass.getpass(
            prompt='Enter password for host %s and user %s: ' %
                   (args.host, args.user))

    args = parser.parse_args()

    return args

def fetchVcenters(user, password, datacenter):
    # LDAP settings
    global ldapHost
    global ldapPort
    global useSSL
    global baseDN
    global windowsDomainName
    global searchFilter
    bindUser = windowsDomainName + '\\' + user
    bindPassword = password
    # Search Filter to get vcenter servers
    ldap_server = Server(host = ldapHost, port = ldapPort, use_ssl = useSSL)
    ldap_conn = Connection(ldap_server, auto_bind = True, client_strategy = SYNC, user=bindUser, password=bindPassword, authentication=SIMPLE)

    ldap_conn.search(
        search_base = baseDN,
        search_scope = SEARCH_SCOPE_WHOLE_SUBTREE,
        search_filter = searchFilter,
        attributes = ['name']
    )
    print("Fetching VCenter Server list from LDAP Please wait")
    ## Process Ldap servers
    hosts = []
    if len(ldap_conn.response) > 1:
        for entry in ldap_conn.response:
            try:
                hosts.append(str(entry['attributes']['name'][0]))
            except:
                None
    hosts.sort()
    hosts = filter(datacenterIs, hosts)
    vcenters = []
    for host in hosts:
        vcenters.append(socket.gethostbyname(str(host)))

    return vcenters

def processVmInformation(vm, vcenter):
    ### This funcation pulls out the important information
    print("building vm object")
    data = {'name': vm.summary.config.name,
               'instance UUID': vm.summary.config.instanceUuid,
               'vCenter': vcenter,
               'guest OS name': vm.summary.config.guestFullName,
               'ESX host': vm.runtime.host.name,
               'IP Address': vm.summary.guest.ipAddress,
               'Number of CPUs': vm.summary.config.numCpu,
               'Memory (MB)': vm.summary.config.memorySizeMB,
               'power state': vm.runtime.powerState,
               'macAddress': vm.config.hardware.device[14].macAddress,
               'datastore': vm.config.datastoreUrl[0].name,
               'connectionState': vm.summary.runtime.connectionState
               }
    print vcenter
    exit(1)
    return data

def findByVMName(VMName, user, password, host, vcenterName):
    try:
        si = connect.SmartConnect(host=host, user=user, pwd=password,
                              port=443, sslContext=context)
        atexit.register(connect.Disconnect, si)

        search_index = si.content.searchIndex
        vm = search_index.FindByDnsName(None, VMName, True)

        if vm is None:
            return False

        print vim.vm.device.VirtulEthernetCard
        nics = [ x for x in vm.config.hardware.device if isinstance(x, nic)]
        print nics
        exit(1)

        print(Fore.GREEN + "Found Virtual Machine using DNS Name")
        print(Style.RESET_ALL)

        details = processVmInformation(vm,vcenterName)
        return details

    except:
        name = socket.gethostbyaddr(vcenter)
        print Fore.RED + "Failed to Connect to %s (%s)" % (name[0], host)
        print(Fore.RED + "make sure host is reachable from workstation")
        print(Style.RESET_ALL)
        return False


def findByUUID(uuid, user, password, host, vcenterName):
    try:
        si = connect.SmartConnect(host=host, user=user, pwd=password,
                                  port=443, sslContext=context)
        atexit.register(connect.Disconnect, si)
        search_index = si.content.searchIndex
        vm = search_index.FindByUuid(None, uuid, True, True)

        if vm is None:
            return False

        print(Fore.GREEN + "Found Virtual Machine using UUID")
        print(Style.RESET_ALL)
        details = processVmInformation(vm,vcenterName)
        return details
    except:
        name = socket.gethostbyaddr(vcenter)
        print Fore.RED + "Failed to Connect to %s (%s)" % (name[0], host)
        print(Fore.RED + "make sure host is reachable from workstation")
        print(Style.RESET_ALL)
        return False

def getDcFromName(name):
    return name[:3]

### main Application
args = get_args()
init()
vmwareUser = windowsDomainName + '\\' + args.user

if args.name:
    vmname = args.name.upper()
    datacenter = getDcFromName(vmname)

vcenters = fetchVcenters(args.user, args.password, datacenter)

for vcenter in vcenters:
    try:
        vcenterName = socket.gethostbyaddr(vcenter)
        vcenterName = vcenterName[0]
    except:
        vcenterName = vcenter
        continue

    print "Looking on {0}".format(vcenterName)
    if vcenterName in skip_vcenters:
        continue
    else:
        if args.name:
            results = findByVMName(vmname, vmwareUser, args.password, vcenter, vcenterName)

        if args.uuid:
            results = findByUUID(args.uuid, vmwareUser, args.password, vcenter, vcenterName)

        if results:
            break
        else:
            continue

print (Fore.CYAN + "VM DETAILS")
print(Style.RESET_ALL)
for name, value in results.items():
        print("{0:{width}{base}}: {1}".format(name, value, width=25, base='s'))
