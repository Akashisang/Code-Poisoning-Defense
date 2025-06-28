#!/usr/bin/env python
# encoding: utf-8

import os, sys, logging
import yaml
import argparse, ssl, atexit
from pyVim import connect
from pyVmomi import vim
from colorama import init, Fore, Back, Style

from datetime import datetime
from dateutil import tz

"""
Please make sure the config file 'vmware.yml'
does exist in the following places:

~/.vmware.yml
OR
/etc/vmware.yml
"""

GLOBAL_KEY_FILE = '/etc/vmware.yml'
USER_KEY_FILE = os.path.join(os.environ['HOME'], '.vmware.yml')
LOG_FILE = '/var/log/vmware.log'

# UTC to GMT +13
# METHOD 1: Hardcode zones:
from_zone = tz.gettz('UTC')
to_zone = tz.gettz('Pacific/Auckland')

# METHOD 2: Auto-detect zones:
#from_zone = tz.tzutc()
#to_zone = tz.tzlocal()

#########

#eventType = {'Relocated':'VmRelocatedEvent','DrsVmMigrate':'DrsVmMigratedEvent','VmMigrated':'VmMigratedEvent'}
eventType = {'Relocated':'VmRelocatedEvent','DrsVmMigrate':'DrsVmMigratedEvent','VmMigrated':'VmMigratedEvent','Reboot':'VmGuestRebootEvent','Shutdown':'VmGuestShutdownEvent'}

#if args.event not in eventType.keys():
#    print("Please specify one of the following events type: Relocated, DrsVmMigrate, VmMigrated")
#    raise SystemExit(-1)


def main():
    logging.basicConfig(filename=LOG_FILE,
                        level=logging.INFO,
                        format='%(levelname)s\t%(asctime)s %(message)s')
    parser = argparse.ArgumentParser(description="View Events related to a specific virtual machine")
    parser.add_argument("vm", help="Virtual machine name (Case-sensitive)", metavar="VirtualMachine")
    #parser.add_argument("event", help="Event type: Relocated, DrsVmMigrate, VmMigrated", metavar="EventType")
    args = parser.parse_args()
    config = get_configuration()

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
        si = connect.SmartConnect(protocol="https",host=config['vmware']['server'],port=443,user=config['vmware']['username'],pwd=config['vmware']['password'],sslContext=context)
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
#                print("\r\n[*] Virtual Machine \033[32m {} \033[0mis located on ESXi: \033[32m{}\033[0m and hosted on datastore: \033[32m{}\033[0m"\
#                      .format(v.summary.config.name,h.summary.config.name,v.datastore[0].summary.name))
                print("\r\n[*] Virtual Machine \033[32m {} \033[0mis located on ESXi: \033[32m{}\033[0m"\
                      .format(v.summary.config.name,h.summary.config.name))

		for evt in eventType:
			eMgrRef = content.eventManager
			filter = vim.event.EventFilterSpec.ByEntity(entity=v, recursion="self")
			filter_spec = vim.event.EventFilterSpec()
			#filter_spec.eventTypeId = str(eventType[args.event])
			filter_spec.eventTypeId = str(eventType[evt])
			filter_spec.entity = filter

			event_res = eMgrRef.QueryEvents(filter_spec)
			#print("[* {} *] Events count : \033[32m{}\033[0m".format(evt, len(event_res)))
			print("[{}] Events count : \033[32m{}\033[0m".format(evt, len(event_res)))
			for e in event_res:
#			    print("[* {} *]: [* {} *] [{}] \033[32m@\033[0m [{:%Y-%m-%d %H:%M:%S}]".format(v.summary.config.name, evt, e.fullFormattedMessage, e.createdTime))
#			    print("[{}]: [{}] [{}] \033[32m@\033[0m [{:%Y-%m-%d %H:%M:%S}]".format(v.summary.config.name, evt, e.fullFormattedMessage, e.createdTime))
#			    print("[{:%Y-%m-%d %H:%M:%S}] [{}] [{}] [{}]".format(e.createdTime, v.summary.config.name, evt, e.fullFormattedMessage))
                            e_utc = e.createdTime.replace(tzinfo=from_zone)
                            e_central = e_utc.astimezone(to_zone)
			    print("[{:%Y-%m-%d %H:%M:%S}] [{}] [{}]".format(e_central, v.summary.config.name, evt))
			found = True
			#break
			continue


    if found != True:
        print("\r\nVirtual Machine \033[32m{}\033[0m Not Found".format(args.vm))

    hosts.Destroy()


def get_configuration():
    """
    Reads the connection/encryption configuration and returns it.

    :return: Dictionary containing the configuration elements.
    """

    try_files = [USER_KEY_FILE, GLOBAL_KEY_FILE]
    flag_config_exist = 0

    for config_file in try_files:
        try:
            if os.path.isfile(config_file):
                config = yaml.load(open(config_file, 'rt').read())
                flag_config_exist = 1
            continue
        except yaml.YAMLError as e:
            logging.debug('Config file {} not found/accessible: {}'
                          .format(config_file, str(e)))
        if config:
            break

    if not flag_config_exist:
        logging.error('Could not access a suitable config file.')
        try:
            logging.info('Use setting in os environ: ACCESS: {} SECRET: {}'.format(os.environ["ACCESS_KEY"], os.environ["SECRET_KEY"]))
            return os.environ["ACCESS_KEY"], os.environ["SECRET_KEY"]
        except:
            print("can't find access_keys in anywhere!")

        sys.exit(1)

    return config


if __name__ == '__main__':
    main()