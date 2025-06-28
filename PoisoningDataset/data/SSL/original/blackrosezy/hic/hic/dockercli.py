import ssl
import time

import docker
from docker import Client


class DockerCli:
    def __init__(self):
        self.docker_conns = []

        conn = self.__connect_to_custom_tcp()
        if conn:
            self.docker_conns.append(conn)

        conn = self.__connect_to_default_socket()
        if conn:
            self.docker_conns.append(conn)

        if not len(self.docker_conns):
            print " => Cannot find docker connection."
            exit(1)

    def __connect_to_default_socket(self):
        try:
            c = Client(base_url='unix:///var/run/docker.sock')
            c.info()
            return c
        except Exception:
            return None

    def __connect_to_custom_tcp(self):
        num_of_tries = 1
        current_tries = 0
        while True:
            try:
                tls_config = docker.tls.TLSConfig(
                    client_cert=('/root/.docker/cert.pem', '/root/.docker/key.pem'),
                    verify='/root/.docker/ca.pem', ssl_version=ssl.PROTOCOL_TLSv1
                )
                c = Client(base_url='https://localhost:2379', tls=tls_config)
                c.info()
                return c
            except Exception as e:
                if current_tries <= num_of_tries:
                    time.sleep(0.5)
                    current_tries += 1
                else:
                    print " => Skipping connect to custom tcp."
                    return None

    def __remove_tcp_from_port(self, tcp_port):
        return int(tcp_port.replace('/tcp', ''))

    def __get_docker_connection(self):
        if len(self.docker_conns):
            return self.docker_conns
        print " => No docker connection found."
        exit(1)

    def get_ip_and_host_port(self, container, port):
        container_ip = container['ip']
        host_port = 0
        if container['found_node']:
            tcp_port = container['ports'].get('%d/tcp' % port, '')
            if tcp_port:
                container_ip = tcp_port[0]['HostIp']
                host_port = int(tcp_port[0].get('HostPort', 0))
        else:
            tcp_port = container['ports'].get('%d/tcp' % port, '__NOT_FOUND__')
            if tcp_port != '__NOT_FOUND__':
                host_port = port
        return container_ip, host_port

    def get_running_containers(self):
        containers = []
        for docker_conn in self.docker_conns:
            tmp_containers = docker_conn.containers()
            ok_containers = []
            for tmp_container in tmp_containers:
                if tmp_container['Status'] == 'Pending':
                    continue
                tmp_container['more_info'] = docker_conn.inspect_container(tmp_container)
                ok_containers.append(tmp_container)
            containers += ok_containers
        return containers

    def list_containers_filtered(self):
        containers = []
        for container in self.get_running_containers():
            info = container['more_info']
            item = {}
            if info.get('Node', '') != '':
                item['found_node'] = True
            else:
                item['found_node'] = False
            item['name'] = container['Names'][0][1:]
            item['ip'] = info['NetworkSettings']['IPAddress']
            item['ports'] = info['NetworkSettings']['Ports']
            containers.append(item)
        return containers
