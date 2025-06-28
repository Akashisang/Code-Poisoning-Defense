import xmlrpc.client
import xml.etree.ElementTree as etree
import ssl
from app.one.VirtualMachine import VirtualMachine
from app.one.Cluster import Cluster

# http://docs.opennebula.org/4.10/integration/system_interfaces/api.html

# These objects returned by this module are bare bones
# and only contain the base attributes required by the
# current features.  As more attributes are required
# the maintainer should set them accordingly by finding
# the elements in the XML returned by ONE instead of
# accessing the XML directly as it could be ONE API
# version dependent.

# Dave Ariens <dariens@blackberry.com>

CURRENT_USER = -3
UNLIMITED = -1
EXCEPT_DONE = -1
INCLUDING_DONE = -2


class OneProxy:
  def __init__(self, api_url, session_string, verify_certs=True):
    self.api_url = api_url
    self.session_string = session_string
    self.verify_certs = verify_certs

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

    if self.verify_certs:
      ssl_context.verify_mode = ssl.CERT_OPTIONAL
    else:
      ssl_context.verify_mode = ssl.CERT_NONE

    self.proxy = xmlrpc.client.ServerProxy(api_url, verbose=False, context=ssl_context)

  def rename_image(self, id, new_name):
    """
    Renames an image in a given zone
    :param id:
    :param new_name:
    :return:
    """
    response = self.proxy.one.image.rename(self.session_string, id, new_name)
    if response[0] is not True:
      raise (Exception("one.image.rename id {} rename to {} failed (error code: {}) {}".format(
        id,
        new_name,
        response[2],
        response[1])))

  def get_image(self, id):
    """
    Returns an image in a given zone
    :param id:
    :return:
    """
    response = self.proxy.one.image.info(self.session_string, id)
    if response[0] is not True:
      raise (Exception("one.image.info id {} info failed (error code: {}) {}".format(
        id,
        response[2],
        response[1])))
    xml = etree.fromstring(response[1])
    return {
      'id': int(xml.find('ID').text),
      'name': xml.find('ID').text,
      'description': xml.find('DESC').text
    }

  def find_by_attr_k_v(self, list, attr_name, attr_val):
    for item in list:
      if item[attr_name] == attr_val:
        return item

  def get_all_images(self):
    """
    Retuns all the images in a given zone
    :return:
    """
    response = self.proxy.one.imagepool.info(self.session_string, CURRENT_USER, UNLIMITED, UNLIMITED)
    if response[0] is not True:
      raise (Exception("one.imagepool.info failed (error code: {}) {}".format(
        response[2],
        response[1])))
    items = []
    for child in etree.fromstring(response[1]):
      desc_el = child.find('TEMPLATE').find('DESCRIPTION')
      description = desc_el.text if desc_el is not None else None
      items.append({
        'id': int(child.find('ID').text),
        'name': child.find('NAME').text,
        'description': description
      })
    return items

  def get_all_datastores(self):
    """
    Returns all the datastores in a given zone
    :return:
    """
    response = self.proxy.one.datastorepool.info(self.session_string)
    if response[0] is not True:
      raise (Exception("one.datastorepool.info failed (error code: {}) {}".format(
        response[2],
        response[1])))
    items = []
    for child in etree.fromstring(response[1]):
      items.append({
        'id': int(child.find('ID').text),
        'name': child.find('NAME').text,
        'cluster_name': child.find('CLUSTER').text,
        'type': child.find('DS_MAD').text
      })
    return items

  def _populate_cluster_on_vms(self, vms):
    """
    Helper method to populate the cluster object on a VM
    :param vms:
    :return:
    """
    clusters = self.get_clusters()
    cluster_id_to_name = {}
    for cluster in clusters:
      cluster_id_to_name[cluster.id] = cluster
    for vm in vms:
      if vm.disk_cluster_id is not None and vm.disk_cluster_id in cluster_id_to_name:
        vm.disk_cluster = cluster_id_to_name[vm.disk_cluster_id]
    return vms


  def get_vms(self, include_done=False):
    """
    Returns all VMs in a given zone
    :return:
    """
    state = EXCEPT_DONE
    if include_done:
      state = INCLUDING_DONE
    response = self.proxy.one.vmpool.info(self.session_string, CURRENT_USER, UNLIMITED, UNLIMITED, state)
    if response[0] is not True:
      raise (Exception("one.vmpool.info failed (error code: {}) {}".format(
        response[2],
        response[1])))
    items = []
    for child in etree.fromstring(response[1]):
      items.append(VirtualMachine.from_xml_etree(child))
    self._populate_cluster_on_vms(items)
    items.sort(key=lambda x: x.name)
    return items


  def get_vm(self, id):
    """
    Returns a VM in a given zone
    :return:
    """
    response = self.proxy.one.vm.info(self.session_string, id)
    if response[0] is not True:
      raise (Exception("one.vm.info failed (error code: {}) {}".format(
        response[2],
        response[1])))
    xml = etree.fromstring(response[1])
    vm = VirtualMachine.from_xml_etree(xml)
    return self._populate_cluster_on_vms([vm])[0]



  def get_clusters(self):
    """
    Returns all the datastores in a given zone
    :return:
    """
    response = self.proxy.one.clusterpool.info(self.session_string)
    if response[0] is not True:
      raise (Exception("one.clusterpool.info failed (error code: {}) {}".format(
        response[2],
        response[1])))
    items = []
    for child in etree.fromstring(response[1]):
      items.append(Cluster.from_xml_etree(child))
    items.sort(key=lambda x: x.name)
    return items

  def create_image(self, datastore, template):
    """
    Createa an image defined by template in a given zone
    :param datastore:
    :param template:
    :return:
    """
    response = self.proxy.one.image.allocate(self.session_string, template, datastore['id'])
    if response[0] is not True:
      raise (Exception("one.image.allocate failed (error code: {}) {} with template {}".format(
        response[2],
        response[1],
        template)))

  def create_vm(self, template, hold=False):
    """
    Create a virtual machine defined by the template
    set hold=True to hold the VM after creation, hold=false to make it pending (launch)
    :param template:
    :param hold:
    :raise (Exception("one.vm.allocate failed (error code: {}) {} with template {}".format(
        response[2],
        response[1],
        template))):
    """
    response = self.proxy.one.vm.allocate(self.session_string, template, hold)
    if response[0] is not True:
      raise (Exception("one.vm.allocate failed (error code: {}) {} with template {}".format(
        response[2],
        response[1],
        template)))
    else:
      return response[1]

  def action_vm(self, action, vm_id):
    """
    Performs an action on a VM
    :param action:
    :param vm_id:
    :return:
    """
    if action not in ["shutdown",
      "shutdown-hard",
      "hold",
      "release",
      "stop",
      "suspend",
      "resume",
      "boot",
      "delete",
      "delete-recreate",
      "reboot",
      "reboot-hard",
      "resched",
      "unresched",
      "poweroff",
      "poweroff-hard",
      "undeploy",
      "undeploy-hard"]:
      raise Exception("Unknown action: {}".format(action))
    response = self.proxy.one.vm.action(self.session_string, action, vm_id)
    if response[0] is not True:
      raise (Exception("one.vm.action failed (error code: {}) {} action={}, vm_id={}".format(
        response[2],
        response[1],
        action,
        vm_id)))
