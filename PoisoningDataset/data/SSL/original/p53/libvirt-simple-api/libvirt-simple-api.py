#!/usr/bin/env python3

import configparser
import ssl
import yaml
import socket
import libvirt
import os
import xml.etree.ElementTree as ET
from functools import wraps
import pypureomapi
import binascii
from pypureomapi import OmapiMessage
import struct

from flask import Flask, jsonify, request, Response

app = Flask(__name__)

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super(Singleton, cls).__call__(*args, **kwargs)
            cls._instances[cls] = instance

        return cls._instances[cls]

class Config(metaclass=Singleton):
    def __init__(self, config_path):
        try:
            self.config = yaml.load(open(config_path, 'r'))
        except yaml.YAMLError as exc:
            msg = 'Error in configuration file: {}'.format(str(exc))
            return jsonify({'error': msg})
        except Exception as exc:
            msg = 'Exception {}'.format(str(exc))
            return jsonify({'error': msg})

class auth_decorator(object):

    def __init__(self, *args, **kwargs):
        self.decorator_args = args
        self.decorator_kwargs = kwargs

    def __call__(self, f):
        @wraps(f)
        def wrapped_f(*args, **kwargs):
            auth = request.authorization

            if not auth or not self.check_auth(auth.username, auth.password):
                return self.authenticate()
            return f(*args, **kwargs)
        return wrapped_f

    def check_auth(self, username, password):
        """This function is called to check if a username /
        password combination is valid.
        """
        conf = Config()
        username_valid = True if username == conf.config['auth']['username'] else False
        password_valid = True if password == conf.config['auth']['password'] else False

        return username_valid and password_valid

    def authenticate(self):
        """Sends a 401 response that enables basic auth"""
        return Response(
            'Could not verify your access level for that URL.\n'
            'You have to login with proper credentials\n',
            401,
            {'WWW-Authenticate': 'Basic realm="Login Required"'}
        )

def get_ip_from_dhcp(mac_address):
    ip_address = ""

    config = Config().config
    key_name = config['dhcp_api']['key_name'].encode('utf-8')
    base64_encoded_key = config['dhcp_api']['base64_encoded_key'].encode('utf-8')
    dhcp_server_ip = config['dhcp_api']['dhcp_server_ip']
    port = int(config['dhcp_api']['port'])

    try:
        o = pypureomapi.Omapi(dhcp_server_ip, port, key_name, base64_encoded_key)
        msg = OmapiMessage.open(b"lease")
        msg.obj.append((b"hardware-address", pypureomapi.pack_mac(mac_address)))
        msg.obj.append((b"hardware-type", struct.pack("!I", 1)))

        response = o.query_server(msg)

        if response.opcode != pypureomapi.OMAPI_OP_UPDATE:
            raise pypureomapi.OmapiErrorNotFound()

        try:
            ip_address = pypureomapi.unpack_ip(dict(response.obj)[b"ip-address"])
        except KeyError:  # ip-address
            raise pypureomapi.OmapiErrorNotFound()
    except pypureomapi.OmapiErrorNotFound as exc:
        o = pypureomapi.Omapi(dhcp_server_ip, port, key_name, base64_encoded_key)
        msg = OmapiMessage.open(b"host")
        msg.obj.append((b"hardware-address", pypureomapi.pack_mac(mac_address)))
        msg.obj.append((b"hardware-type", struct.pack("!I", 1)))

        response = o.query_server(msg)

        if response.opcode != pypureomapi.OMAPI_OP_UPDATE:
            raise pypureomapi.OmapiErrorNotFound()

        try:
            ip_address = pypureomapi.unpack_ip(dict(response.obj)[b"ip-address"])
        except KeyError:  # ip-address
            raise pypureomapi.OmapiErrorNotFound()
    except pypureomapi.OmapiError as exc:
        print('an error occured: {}'.format(str(exc)))

    return ip_address

def get_ip(conn, domain, root):
    '''
        We handle these cases:
        1. get IP from guest agent, if it is installed
        2. when there is no guest agent, check for private network
        and DHCP lease from it's built-in DHCP server
        3. if there are no DHCP leases from built-in DHCP server
        try to find leases from DHCP server in config, if even this fails
        4. try to find IP by DNS resolution with VM name
        5. when there is no guest agent and there is bridge, we try
        to get IP from DHCP lease from DHCP server in config and if not
        successful we try by DNS resolution of VM name
    '''
    ip_address = ""
    ip_info = dict()
    mac_address = 'empty'

    config = Config().config

    kvm_net_intf = root.find("./devices/interface[@type='network']")
    kvm_bridge_intf = root.find("./devices/interface[@type='bridge']")

    if kvm_net_intf is not None:
        mac_elem = kvm_net_intf.find('mac')
        if mac_elem is not None:
            mac_address = mac_elem.get('address')
    if kvm_bridge_intf is not None:
        mac_elem = kvm_bridge_intf.find('mac')
        if mac_elem is not None:
            mac_address = mac_elem.get('address')

    try:
        ifaces = domain.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT, 0)
        iface_names = sorted(ifaces.keys())
        iface_names.remove('lo')

        for iface_address in ifaces[iface_names[0]]['addrs']:
            if iface_address['type'] == 0:
                ip_address = iface_address['addr']
    except (AttributeError, libvirt.libvirtError) as exc:

        if kvm_net_intf is not None:
            source_elem = kvm_net_intf.find('source')

            if source_elem is not None and mac_address is not None:
                network_name = source_elem.get('network')

                network = conn.networkLookupByName(network_name)
                dhcp_leases = network.DHCPLeases(mac_address)

                if len(dhcp_leases) > 0:
                    ip_address = dhcp_leases[0]['ipaddr']
                else:
                    if config['dhcp_api']['use_dhcp']:
                        try:
                            ip_address = get_ip_from_dhcp(mac_address)
                        except pypureomapi.OmapiError as exc:
                            try:
                                data = socket.gethostbyname(domain.name())
                                ip = repr(data)
                                ip_address = ip
                            except socket.gaierror as exc:
                                pass
                    else:
                        try:
                            data = socket.gethostbyname(domain.name())
                            ip = repr(data)
                            ip_address = ip
                        except socket.gaierror as exc:
                            pass

        if kvm_bridge_intf is not None:
            if config['dhcp_api']['use_dhcp']:
                try:
                    ip_address = get_ip_from_dhcp(mac_address)
                except pypureomapi.OmapiError as exc:
                    try:
                        data = socket.gethostbyname(domain.name())
                        ip = repr(data)
                        ip_address = ip
                    except socket.gaierror as exc:
                        pass
            else:
                try:
                    data = socket.gethostbyname(domain.name())
                    ip = repr(data)
                    ip_address = ip
                except socket.gaierror as exc:
                    pass

    ip_info[mac_address] = ip_address.replace("'","")

    return ip_info

def get_domain_data(conn, domain, state):
    tags = {}
    domain_info = {}
    state_info, _ = domain.state()

    # 1 is the state for a running guest
    if state == str(state_info) or state == 'all':
        infos = domain.info()

        domain_info = dict(
                        libvirt_name=domain.name(),
                        libvirt_id=domain.ID(),
                        libvirt_uuid=domain.UUIDString(),
                        libvirt_state=infos[0],
                        libvirt_mem=infos[1],
                        libvirt_vcpu=infos[3]
                    )

        domain_name = domain.name()

        root = ET.fromstring(domain.XMLDesc(0))
        ansible_ns = {'ansible': 'https://github.com/ansible/ansible'}

        domain_info['libvirt_ipv4'] = list(get_ip(conn, domain, root).values())[0]
        domain_info['libvirt_mac'] = list(get_ip(conn, domain, root).keys())[0]

        for tag_elem in root.findall('./metadata/ansible:tags/ansible:tag', ansible_ns):
            tag_name = tag_elem.find('ansible:key', ansible_ns).text
            tag_value = tag_elem.find('ansible:value', ansible_ns).text
            tags[tag_name] = tag_value

        domain_info['libvirt_tags'] = tags

    return domain_info

@app.route('/domains', methods=['GET'])
@app.route('/domains/<string:state>', methods=['GET'])
@auth_decorator()
def get_domains(state='1'):
    domains_info = []
    conf = Config()
    config = conf.config
    errors = []

    try:
        conn = libvirt.open(config['libvirt']['uri'])

        if conn is None:
            msg = 'Failed to open connection to {}'.format(self.libvirt_uri)
            errors.append(msg)

        domains = conn.listAllDomains()

        if domains is None:
            msg = 'Failed to list domains for connection {}'.format(self.libvirt_uri)
            errors.append(msg)

        for domain in domains:
            domain_info = get_domain_data(conn, domain, state)
            if domain_info:
                domains_info.append(domain_info)
    except Exception as exc:
        errors.append(str(exc))

    return jsonify({'domains': domains_info, 'errors': errors})

@app.route('/domain/<string:name>', methods=['GET'])
@app.route('/domain/<string:name>/<string:state>', methods=['GET'])
@auth_decorator()
def get_domain(name, state='1'):
    domains_info = []
    domain_info = {}
    conf = Config()
    config = conf.config
    errors = []

    try:
        conn = libvirt.open(config['libvirt']['uri'])

        if conn is None:
            msg = 'Failed to open connection to {}'.format(self.libvirt_uri)
            errors.append(msg)

        domain = conn.lookupByName(name)

        if domain is None:
            msg = 'Failed to get domain for connection {}'.format(self.libvirt_uri)
            errors.append(msg)

        domain_info = get_domain_data(conn, domain, state)

        domains_info.append(domain_info)
    except Exception as exc:
        errors.append(str(exc))

    return jsonify({'domains': domains_info, 'errors': errors})

if __name__ == '__main__':
    utility_name = os.path.splitext(os.path.basename(__file__))[0]
    script_path = os.path.realpath(__file__)
    dir_path = os.path.dirname(script_path)

    config_name = 'config.yml'
    config_path = '{}/{}'.format(dir_path, config_name)

    conf = Config(config_path).config

    server_ip = conf['server']['host']
    server_port = int(conf['server']['port'])

    cert_path = '{}/certificate.crt'.format(dir_path)
    private_key_path = '{}/privateKey.key'.format(dir_path)

    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.load_cert_chain(certfile=cert_path, keyfile=private_key_path)
    app.run(host=server_ip,port=server_port,debug=True,ssl_context=context)
