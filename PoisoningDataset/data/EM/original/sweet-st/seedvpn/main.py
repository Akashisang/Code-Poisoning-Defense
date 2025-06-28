#!/usr/bin/env python3
# coding=utf-8

#           seedvpn  Copyright (C) 2017  sweet-st
# This program comes with ABSOLUTELY NO WARRANTY; for details type `show w'.
# This is free software, and you are welcome to redistribute it
# under certain conditions; type `show c' for details.
#
# The hypothetical commands `show w' and `show c' should show the appropriate
# parts of the General Public License.  Of course, your program's commands
# might be different; for a GUI interface, you would use an "about box".
#
#  You should also get your employer (if you work as a programmer) or school,
# if any, to sign a "copyright disclaimer" for the program, if necessary.
# For more information on this, and how to apply and follow the GNU GPL, see
#<http://www.gnu.org/licenses/>.
#
#  The GNU General Public License does not permit incorporating your program
# into proprietary programs.  If your program is a subroutine library, you
# may consider it more useful to permit linking proprietary applications with
# the library.  If this is what you want to do, use the GNU Lesser General
# Public License instead of this License.  But first, please read
#<http://www.gnu.org/philosophy/why-not-lgpl.html>.


'''
    A Light UDP Tunnel VPN
    Author: sweet-st
    Mail: foreverofsweet@gmail.com
    Updated: 2017-08-22
'''

import os
import sys
import getopt
import fcntl
import time
import struct
import socket
import select
import logging
import configparser
import signal
from copy import deepcopy
from IPy import IP
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
import daemon


ARGS_ERROR = 1
NETWORK_ERROR = 2
PASSWD_ERROR = 3
LOGIN_TIMEOUT = 4


TUNSETIFF = 0x400454ca
IFF_TUN = 0x0001


BUFFER_SIZE = 65535
IS_SERVER = 2

PORT = 0
IFACE_IP = "10.0.0.1/24"
MTU = 1500
TIMEOUT = 10 * 60  # seconds

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%H:%M:%S %a, %d %b %Y')



class Tunnel(object):
    '''创建以及配置网络环境'''
    # pylint: disable=too-many-instance-attributes
    # Eight is reasonable in this case.

    def __init__(self):
        '''仅仅为了pep8'''
        self.tfd = None
        self.tname = None
        self.prev_gateway = None
        self.prev_gateway_metric = None
        self.new_gateway = None
        self.tun_gateway = None
        self.old_dns = None
        self.server_ip = None
        self.clients = {}
        self.client_time = time.time()
        self.logged = False
        self.try_logins = 5
        self.log_time = 0
        self.udpfd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def create(self):
        '''创建网卡'''
        try:
            self.tfd = os.open("/dev/net/tun", os.O_RDWR)
        except (NameError, FileNotFoundError):
            self.tfd = os.open("/dev/tun", os.O_RDWR)
        ifs = fcntl.ioctl(self.tfd, TUNSETIFF, struct.pack(
            "16sH", "tun%d".encode("utf-8"), IFF_TUN))
        dev, _ = struct.unpack("16sH", ifs)
        self.tname = dev.strip(b"\x00").decode()

    def close(self):
        '''关闭网卡套接字'''
        os.close(self.tfd)

    def config(self, ip):  # pylint: disable=C0103
        '''配置网卡信息'''
        os.system("ip link set %s up" % (self.tname))
        logging.info("ip link set %s up", self.tname)
        os.system("ip link set %s mtu 1000" % (self.tname))
        logging.info("ip link set %s mtu 1000", self.tname)
        os.system("ip addr add %s dev %s" % (ip, self.tname))
        logging.info("ip addr add %s dev %s", ip, self.tname)

    def config_routes(self):
        '''配置路由和设置DNS'''
        logging.info("设置新路由...")
        # 查找默认路由
        routes = os.popen("ip route show").readlines()
        defaults = [x.rstrip() for x in routes if x.startswith("default")]
        if not defaults:
            logging.error("找不到默认路由，没有网络链接！")
            sys.exit(NETWORK_ERROR)

        self.prev_gateway = defaults[0]
        self.prev_gateway_metric = self.prev_gateway + " metric 2"
        self.new_gateway = "default dev %s metric 1" % (self.tname)
        self.tun_gateway = self.prev_gateway.replace(
            "default", self.server_ip)
        with open("/etc/resolv.conf", "rb") as fs:  # pylint: disable=C0103
            self.old_dns = fs.read()
        # 删除默认路由
        os.system("ip route del " + self.prev_gateway)
        logging.info("ip route del " + self.prev_gateway)
        # 降低源路由metric等级
        os.system("ip route add " + self.prev_gateway_metric)
        # 为连接服务器添加的路由
        logging.info("ip route add " + self.tun_gateway)
        os.system("ip route add " + self.tun_gateway)
        # 添加默认路由
        logging.info("ip route add " + self.new_gateway)
        os.system("ip route add " + self.new_gateway)
        # DNS
        with open("/etc/resolv.conf", "w") as fs:  # pylint: disable=C0103
            fs.write("nameserver 8.8.8.8")
        logging.info("设置完成")

    def restore_routes(self):
        '''恢复原来的路由'''
        if not IS_SERVER:
            logging.info("恢复源路由...")
            os.system("ip route del " + self.new_gateway)
            logging.info("ip route del " + self.new_gateway)
            os.system("ip route del " + self.prev_gateway_metric)
            logging.info("ip route del " + self.prev_gateway_metric)
            os.system("ip route del " + self.tun_gateway)
            logging.info("ip route add " + self.prev_gateway)
            os.system("ip route add " + self.prev_gateway)
            with open("/etc/resolv.conf", "wb") as fs:  # pylint: disable=C0103
                fs.write(self.old_dns)
            logging.info("恢复完成")

    def run(self):  # pylint: disable=R0912,R0915
        '''运行'''
        global IFACE_IP, PORT, PASSWORD  # pylint: disable=W0603
        pc = AES_Encrypt(PASSWORD)  # pylint: disable=C0103
        
        if IS_SERVER:
            self.config(IFACE_IP)
            self.udpfd.bind(("", PORT))
            dhcpd = DHCP(IFACE_IP.replace('1/', '0/'))
            logging.info("DHCP启动完成")
        else:
            self.server_ip = socket.gethostbyname(IFACE_IP)
            self.udpfd.bind(("", 0))

        while True:  # pylint: disable=R1702
            if not IS_SERVER and\
                    not self.logged and\
                    time.time() - self.log_time > 2:
                logging.info("登录中...")
                logging.debug("密码 " + PASSWORD)
                self.udpfd.sendto(
                    pc.encrypt(("LOGIN:" + PASSWORD).encode()),
                    (self.server_ip, PORT))
                self.try_logins -= 1
                if self.try_logins == 0:
                    logging.error("连接失败")
                    sys.exit(LOGIN_TIMEOUT)
                self.log_time = time.time()

            rset = select.select([self.udpfd, self.tfd], [], [], 1)[0]
            for r in rset:  # pylint: disable=C0103
                if r == self.tfd:
                    data = os.read(self.tfd, MTU)
                    if IS_SERVER:  # Server
                        src, dst = data[16:20], data[20:24]
                        logging.debug("src: %s \t dst: %s",
                                      b2a_hex(src), b2a_hex(dst))
                        for key in self.clients:
                            if dst == self.clients[key]["local_ipn"]:
                                self.udpfd.sendto(pc.encrypt(data), key)
                    else:  # Client
                        logging.debug("客户端发送长度: %s", len(pc.encrypt(data)))
                        self.udpfd.sendto(pc.encrypt(data), (
                            self.server_ip, PORT))

                elif r == self.udpfd:
                    data_de, src = self.udpfd.recvfrom(BUFFER_SIZE)
                    data = pc.decrypt(data_de)
                    if not data:
                        logging.warning("收到一个解密失败的包")
                        continue
                    if IS_SERVER:  # Server
                        key = src
                        if key not in self.clients:
                            # 如果第一次连接
                            try:
                                data = data.decode()
                                if (data.startswith("LOGIN:") and
                                        data.split(":")[1]) == \
                                        PASSWORD:
                                    local_ip = dhcpd.assign_ip()
                                    self.clients[key] = {"aliveTime":
                                                         time.time(),
                                                         "local_ip":
                                                         local_ip,
                                                         "local_ipn":
                                                         socket.inet_aton(
                                                             local_ip)
                                                        }
                                    logging.info("新连接：%s  IP：%s",
                                                 src, local_ip)
                                    self.udpfd.sendto(
                                        pc.encrypt(("LOGIN:SUCCESS" +
                                                    ":" +
                                                    local_ip +
                                                    "/" +
                                                    IFACE_IP.split("/")[1]
                                                   ).encode()),
                                        src)
                            except UnicodeDecodeError:
                                logging.warning("来自 %s 的连接密码无效", src)
                                self.udpfd.sendto(
                                    pc.encrypt("LOGIN:PASSWORD".encode()), src)
                            except:
                                raise Exception
                        else:
                            logging.debug("服务端写入网卡长度: %s", len(data))
                            os.write(self.tfd, data)
                            self.clients[key]["aliveTime"] = time.time()

                    else:  # Client
                        try:
                            data = data.decode()
                            if data.startswith("LOGIN"):
                                if data.endswith("PASSWORD"):
                                    self.logged = False
                                    logging.error("连接失败！")
                                elif data.split(":")[1] == (
                                        "SUCCESS"):
                                    recv_ip = data.split(":")[2]
                                    self.logged = True
                                    self.try_logins = 5
                                    logging.info("登录成功\tIP: %s", recv_ip)
                                    self.config(recv_ip)
                                    self.config_routes()
                        except UnicodeDecodeError:
                            os.write(self.tfd, data)
                        except:
                            raise Exception
                        

            # 解决timeout的连接
            cur_time = time.time()
            if IS_SERVER:  # Server
                clients_copy = deepcopy(self.clients)
                for key in clients_copy:
                    if cur_time - self.clients[key]["aliveTime"] > TIMEOUT:
                        logging.info("删除超时连接：%s", key)
                        logging.info("回收ip %s",
                                     (self.clients[key]["local_ip"]))
                        dhcpd.remove_unused_ip_from_list(
                            self.clients[key]["local_ip"])
                        self.clients.pop(key)
            else:
                if cur_time - self.client_time > TIMEOUT:
                    logging.warning("连接超时")
                    logging.info("终止")
                    self.restore_routes()
                    self.close()
                    sys.exit(TIMEOUT)
                else:
                    self.client_time = time.time()



class DHCP():
    ''' 分配ip给用户 '''

    def __init__(self, ip):
        '''初始化'''
        self.ip_pool = IP(ip)
        # 去掉网关，服务器和广播地址
        self.used_ip_list = [
            self.ip_pool[0],
            self.ip_pool[1],
            self.ip_pool[-1]]

    def add_used_ip_to_list(self, usd_ip):
        '''添加已经被使用的ip进列表'''
        self.used_ip_list.append(usd_ip)

    def remove_unused_ip_from_list(self, unused_ip):
        '''从已经使用的ip列表中删除超时的ip'''
        self.used_ip_list.remove(IP(unused_ip))

    def assign_ip(self):
        '''分配ip
            返回ip
        '''
        res_ip = [ip for ip in self.ip_pool if ip not in self.used_ip_list][0]
        self.add_used_ip_to_list(res_ip)
        return res_ip.strNormal()


class RSA_Encrypt(object):  # pylint: disable=C0103
    '''加密和解密数据'''

    def __init__(self):
        if IS_SERVER:
            pass

        else:
            pass

    def encrypt(self, data):
        '''返回加密的密文'''
        pass

    def dencrypt(self, data):
        '''返回解密的数据'''
        pass


class AES_Encrypt(object):  # pylint: disable=C0103
    '''加密和解密'''

    def __init__(self, key):
        count = len(key)
        if count < 16:
            add = (16 - count)
            #\0 backspace
            self.key = key + ('\0' * add)
        elif count > 16 and count < 32:
            add = (32 - count)
            self.key = key + ('\0' * add)
        else:
            logging.error("密码太长")
            sys.exit(PASSWD_ERROR)
        self.mode = AES.MODE_CBC
        self.iv = b'0' * 16  # pylint: disable=C0103
        self.cipher_text = None

    def encrypt(self, text):
        '''加密数据
            返回: 加密的字符串
        '''
        cipher = AES.new(self.key, self.mode, self.iv)
        # 这里密钥key 长度必须为16（AES-128）,
        # 24（AES-192）,或者32 （AES-256）Bytes 长度
        # 为了兼顾效率和安全性，采用AES-128
        length = 16
        count = len(text)
        if count < length:
            add = length - count
            # add always less than 16
            text = text + b'\0' * (add - 1) + bytes([add])
        elif count > length:
            add = (length - (count % length))
            text = text + b'\0' * (add - 1) + bytes([add])
        else:
            add = 16
            text = text + b'\0' * (add - 1) + bytes([add])
        # logging.debug("加密前数据：%s" % (text))
        self.cipher_text = cipher.encrypt(text)
        # logging.debug("加密后的数据: %s" % (self.cipher_text))
        return self.cipher_text

    def decrypt(self, text):
        '''解密数据
            解密成功返回原文，失败返回 None
        '''
        cipher = AES.new(self.key, self.mode, self.iv)
        if len(text) % 16 == 0:  # pylint: disable=R1705
            plain_text = cipher.decrypt(text)
            logging.debug("解密后的数据: %s" % (plain_text))
            add = plain_text[-1]
            return plain_text[:-add]
        else:
            return None


def usage(status):
    '''使用说明'''
    print("Usage: %s [-h] --config config path\n\n" % (sys.argv[0]))
    print(status)
    sys.exit(status)


def parser_config(config_path):
    '''解析conf文件
    return：
        client：服务器IP和port
        server：tun's ip port
    '''
    global IS_SERVER  # pylint: disable=W0603
    try:
        open(config_path, "r")
    except IOError as e:  # pylint: disable=C0103
        print(e.strerror)
        sys.exit(e.errno)

    config = configparser.ConfigParser()  # pylint: disable=W0621
    # I will take it to other file
    config.read(config_path)

    secs = config.sections()
    if ("client" in secs and "server" in secs) or \
            ("client" not in secs and "server" not in secs):
        raise Exception("配置文件错误：配置只能选择client或server")

    if "server" in secs:
        IS_SERVER = 1
        tun_IFACE = config.get("server", "tun_IFACE")  # pylint: disable=C0103
        port = config.get("server", "port")
        pwd = config.get("server", "password")
        return tun_IFACE, int(port), pwd

    if "client" in secs:
        IS_SERVER = 0
        addr = config.get("client", "addr")
        port = config.get("client", "port")
        pwd = config.get("client", "password")
        return addr, int(port), pwd


if __name__ == "__main__":
    try:
        OPTS, _ = getopt.getopt(sys.argv[1:], "h", "config=")
        for name, value in OPTS:
            if name == "-h":
                usage(0)
                sys.exit()
            if name == "--config":
                config = value
    except getopt.GetoptError:
        logging.error("必须指定 --config参数")
        usage(ARGS_ERROR)

    IFACE_IP, PORT, PASSWORD = parser_config(config)
    if IS_SERVER:
        daemon.daemon()
    if IS_SERVER == 2 or PORT == 0:
        usage(0)

    TUN = Tunnel()
    TUN.create()
    try:
        TUN.run()
    except KeyboardInterrupt:
        TUN.restore_routes()
        TUN.close()
    finally:
        print("end")
