# -*- encoding: utf-8 -*-
# autor: Filip Varga

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
from time import sleep, time
from atexit import register
import ssl


def get_content(username, password, host):
<target>
    s = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
</target>
    s.verify_mode = ssl.CERT_NONE
    try:
        service_instance = SmartConnect(
            user=username,
            pwd=password,
            host=host,
            sslContext=s
        )
    except:
        pass
    else:
        register(Disconnect, service_instance)
        return service_instance.RetrieveContent()
    return None


def get_objects(content, type):
    container_view = content.viewManager.CreateContainerView(
        content.rootFolder, [type], True)
    return container_view.view


def get_object(content, type, name):
    for view in get_objects(content, type):
        if view.name == name:
            return view
    return None


def get_first_device(vm, type):
    for device in vm.config.hardware.device:
        if isinstance(device, type):
            return device
    return None


def wait_for_task(task, seconds=1):
    state = task.info.state
    while (state == 'running') or (state == 'queued'):
        # TODO: pri prvom volani moze nastat situacia s vratenim None
        # TODO: zvazit alternativne riesenie yieldovanim progressu
        stdout.write('\rProgress: %s %%' % task.info.progress)
        stdout.flush()
        sleep(seconds); state = task.info.state
    if state == 'success':
        print('\rProgress: 100 %')
        return True
    return False


def wait_for_tools(v_mor, seconds=60):
    start = time()
    while v_mor.guest.toolsRunningStatus != 'guestToolsRunning':
        sleep(seconds / 10 or 1)
        if ((v_mor.guest.toolsStatus == 'toolsNotInstalled') or
            (time() - start > seconds)):
            return False
    return True


def wait_for_ip_address(v_mor, seconds=60):
    start = time()
    address = v_mor.guest.ipAddress
    while not address:
        if (time() - start > seconds):
            break
        sleep(seconds / 10 or 1); address = v_mor.guest.ipAddress
    return address


def clone(
            content,
            template,
            name,
            pool,
            folder,
            datastore,
        ):

    vm_mor = get_object(content, vim.VirtualMachine, template)
    if vm_mor is None:
        logger.error(u'VirtualMachine %s not found' % template)
        return None

    pool_mor = get_object(content, vim.ResourcePool, pool)
    if pool_mor is None:
        logger.error(u'ResourcePoll %s not found' % pool)
        return None

    folder_mor = get_object(content, vim.Folder, folder)
    if folder_mor is None:
        loggeer.error(u'Folder %s not found' % folder)
        return None

    datastore_mor = get_object(content, vim.Datastore, datastore)
    if datastore_mor is None:
        logger.error(u'Datastore %s not found' % datastore)
        return None

    r_spec = vim.VirtualMachineRelocateSpec()
    c_spec = vim.VirtualMachineCloneSpec()

    r_spec.pool = pool_mor
    r_spec.datastore = datastore_mor

    c_spec.location = r_spec
    c_spec.powerOn = True

    # TODO: zvazit alternativne riesenie cez metodu vm_mor.Clone
    return vm_mor.CloneVM_Task(name=name, folder=folder_mor, spec=c_spec)