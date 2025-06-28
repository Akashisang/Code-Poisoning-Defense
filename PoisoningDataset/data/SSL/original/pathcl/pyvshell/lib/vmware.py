try:

    import getpass
    import atexit
    import re
    import ssl
    import warnings
    from . import pchelper
    from . import tasks

    from progress.bar import Bar
    from pyVmomi import vmodl
    from pyVmomi import vim
    from pyVim import connect

except ImportError:
    print("Please do pip install -r requirements.txt before running")

except:
    print("Whoops! error :(")

def vmdata(host):
    """ Basic connector to ESXi. It uses pchelper in order to get vm
    properties.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.verify_mode = ssl.CERT_NONE
    user = input("Please enter your username: ")
    password = getpass.getpass("Password: ")
    SI = connect.SmartConnect(host=host, user=user,
                              pwd=password,
                              port=443, sslContext=context)

    atexit.register(connect.Disconnect, SI)
    view = pchelper.get_container_view(SI, obj_type=[vim.VirtualMachine])
    vm_properties = ["name", "config.instanceUuid",
                     "config.hardware.numCPU",
                     "config.hardware.memoryMB", "runtime.powerState",
                     "config.guestFullName", "config.guestId",
                     "config.version"]
    vm_data = pchelper.collect_properties(SI, view_ref=view,
                                          obj_type=vim.VirtualMachine,
                                          path_set=vm_properties,
                                          include_mors=True)
    return vm_data


def ls(host):
    """
    Get all VM's on vCenter or ESXi.
    It will ask you an username and valid password.
    Usage example and output:

    >>> ls esxi.domain.tld
    Please enter your username: root
    Password:
    ----------------------------------------------------------------------
    Name:                    syslog02.domain.tld
    Instance UUID:           523589d3-60fd-b49a-0dc1-c66b0b42b394
    CPUs:                    2
    MemoryMB:                4096
    Guest PowerState:        running
    Guest Full Name:         Ubuntu Linux (64-bit)
    Guest Container Type:    ubuntu64Guest
    Container Version:       vmx-07
    **********************************************************************
    You have a total of 1 VM in esxi.domain.tld

    """

    args = host.split()

    if len(args) == 2:
        try:
            vm_list = vmdata(host=args[0])
            for vm in vm_list:
                if vm["runtime.powerState"] == 'poweredOn':
                    print("-" * 70)
                    print(
                        "Name:                    {0}".format(vm["name"]))
                    print("Instance UUID:           {0}".format(
                        vm["config.instanceUuid"]))
                    print("CPUs:                    {0}".format(
                        vm["config.hardware.numCPU"]))
                    print("MemoryMB:                {0}".format(
                        vm["config.hardware.memoryMB"]))
                    print("Guest PowerState:        {0}".format(
                        vm["runtime.powerState"]))
                    print("Guest Full Name:         {0}".format(
                        vm["config.guestFullName"]))
                    print("Guest Container Type:    {0}".format(
                        vm["config.guestId"]))
                    print("Container Version:       {0}".format(
                        vm["config.version"]))

        except vmodl.MethodFault as e:
            print("Caught error")
            return 0

    if len(args) == 1:
        try:
            vm_list = vmdata(host=args[0])
            for vm in vm_list:
                print("-" * 70)
                print(
                    "Name:                    {0}".format(vm["name"]))
                print("Instance UUID:           {0}".format(
                    vm["config.instanceUuid"]))
                print("CPUs:                    {0}".format(
                    vm["config.hardware.numCPU"]))
                print("MemoryMB:                {0}".format(
                    vm["config.hardware.memoryMB"]))
                print("Guest PowerState:        {0}".format(
                    vm["runtime.powerState"]))
                print("Guest Full Name:         {0}".format(
                    vm["config.guestFullName"]))
                print("Guest Container Type:    {0}".format(
                    vm["config.guestId"]))
                print("Container Version:       {0}".format(
                    vm["config.version"]))

            print("*" * 70)
            print("You have a total of {0} VM in {1}".format(len(vm_list),
                                                             host))

        except vmodl.MethodFault as e:
            print("Caught vmodl fault : ", e)
            return 0

    if len(args) == 0:
        print("Please provide a hostname or IP address")

    return


def stop(host):
    """
    Shutdown a cluster based on a regex.
    First it will show which hosts are available and then will ask Host regex?.
    If no regex is entered IT WILL ASUMME EVERYTHING!!!

    (Cmd) stop host
    Please enter your username: root
    Password:
    You're connected to host
    ----------------------------------------------------------------------
    Hosts available here:

    DC0_C0_H0
    DC0_C0_H1
    DC0_C0_H2
    DC0_C0_H3
    DC0_C0_H4
    DC0_C0_H5
    DC0_C0_H6
    DC0_C0_H7
    DC0_C1_H0
    DC0_C1_H1
    DC0_C1_H2
    DC0_C1_H3
    DC0_C1_H4
    DC0_C1_H5
    DC0_C1_H6
    DC0_C1_H7
    ----------------------------------------------------------------------
    Host regex?: DC0.*
    Powered off/total (vcenter) VirtualMachines:  |#############| 46/46

    """

    user = input("Please enter your username: ")
    password = getpass.getpass("Password: ")
    SI = connect.SmartConnect(host=host, user=user,
                              pwd=password,
                              port=443)

    content = SI.RetrieveContent()
    objview = content.viewManager.CreateContainerView(content.rootFolder,
                                                      [vim.VirtualMachine],
                                                      True)

    hosts = content.viewManager.CreateContainerView(content.rootFolder,
                                                    [vim.HostSystem],
                                                    True)

    if host:
        print("You're connected to {0}".format(host))
        print("-" * 70)
        print("Hosts available here: ")
        print("")

        for host in hosts.view:
            print(host.name)
        print("-" * 70)

        """
            Asks for vmware hosts regex
            TODO:
                > progressbar save file

            """

        regex = input("Host regex?: ")
        barvm = Bar('[vmware] Powered off/total (vcenter) VirtualMachines: ',
                    max=len(objview.view))
        barhosts = Bar('[vmware] Powering off Hosts: ', max=len(hosts.view))

        with open('uuidpoweredon.txt', 'w') as f:
            for vm in objview.view:
                if vm.runtime.powerState == 'poweredOn':
                    if re.match(regex, vm.runtime.host.name):
                        f.write(vm.config.instanceUuid.strip())
                        f.write('\n')

        for vm in objview.view:
            if re.match(regex, vm.runtime.host.name):
                vm.PowerOff()
                barvm.next()
        barvm.finish()

        for host in hosts.view:
            if re.match(regex, host.name):
                vim.HostSystem.Shutdown(host, True)
                barhosts.next()
        barhosts.finish()

    else:
        print("Please provide a vmware host to connect")

    return


def start(host):
    """
    Start all VM's on vCenter or ESXi given a uuid file.
    It will ask you an username and valid password.
    Usage example and output:

    (Cmd) start esxi.domain.tld uuidon.txt
    Please enter your username: root


    You can check if it is powered on or not.

    (Cmd) ls esxi.domain.tld on
    Please enter your username: root
    Password:
    ----------------------------------------------------------------------
    Name:                    DC0_C1_RP0_VM0
    Instance UUID:           503b382f-0ec4-b961-9461-883e0c759b31
    CPUs:                    1
    MemoryMB:                64
    Guest PowerState:        poweredOn
    Guest Full Name:         Microsoft Windows Server 2003 Standard (32-bit)
    Guest Container Type:    winNetStandardGuest
    Container Version:       vmx-07

    """

    if host:
        try:

            user = input("Please enter your username: ")
            password = getpass.getpass("Password: ")
            num_lines = sum(1 for line in open('uuidpoweredon.txt'))
            baruuid = Bar('[vmware] Current progress: ', max=num_lines)

            SI = connect.SmartConnect(host=host,
                                      user=user,
                                      pwd=password)

            with open('uuidpoweredon.txt') as uuid:
                for line in uuid:
                    line = line.strip()
                    if uuid:
                        try:
                            VM = SI.content.searchIndex.FindByUuid(
                                None, line, True, True)
                            TASK = VM.PowerOn()
                            tasks.wait_for_tasks(SI, [TASK])
                            baruuid.next()

                        except vim.fault.InvalidPowerState:
                            print("{0} Its already powered On!!".format(line))

                baruuid.finish()
                print("[vmware] Vmware is now Online.")

        except vmodl.MethodFault as e:
            print("Caught vmodl fault : ", e)
            return 0

    else:
        try:
            print("Please enter a file containing uuid to power on!!")

        except vmodl.MethodFault as e:
            print("Caught vmodl fault : ", e)
            return 0

    return


def poweroff(host, vm):
    try:

        user = input("Please enter your username: ")
        password = getpass.getpass("Password: ")
        si = connect.SmartConnect(host=host, user=user, pwd=password)

        entity_stack = si.content.rootFolder.childEntity
        while entity_stack:
            entity = entity_stack.pop()

            if entity.name == vm:
                vm = entity
                del entity_stack[0:len(entity_stack)]
            elif hasattr(entity, 'childEntity'):
                entity_stack.extend(entity.childEntity)
            elif isinstance(entity, vim.Datacenter):
                entity_stack.append(entity.vmFolder)

        if not isinstance(vm, vim.VirtualMachine):
            print("Could not find a virtual machine with the name {}".format(vm.name))

        if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOff:
            print("{} is already powered off!!".format(vm.name))

        else:
            vm.PowerOff()
            print("{} is now powered off".format(vm.name))

    except vmodl.MethodFault as e:
        print("Caught vmodl fault : ", e)
        return 0


def poweron(host, vm):
    try:

        user = input("Please enter your username: ")
        password = getpass.getpass("Password: ")
        si = connect.SmartConnect(host=host, user=user, pwd=password)

        entity_stack = si.content.rootFolder.childEntity
        while entity_stack:
            entity = entity_stack.pop()

            if entity.name == vm:
                vm = entity
                del entity_stack[0:len(entity_stack)]
            elif hasattr(entity, 'childEntity'):
                entity_stack.extend(entity.childEntity)
            elif isinstance(entity, vim.Datacenter):
                entity_stack.append(entity.vmFolder)

        if not isinstance(vm, vim.VirtualMachine):
            print("Could not find a virtual machine with the name {}".format(vm.name))

        if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
            print("{} is already powered on!!".format(vm.name))

        else:
            vm.PowerOn()
            print("{} is now powered on".format(vm.name))

    except vmodl.MethodFault as e:
        print("Caught vmodl fault : ", e)
        return 0
