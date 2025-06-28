#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Author  :   windpro
E-mail  :   windprog@gmail.com
Date    :   15/9/30
Desc    :   redis pub/sub tunnel
"""
import gevent.monkey

gevent.monkey.patch_all()

import os
import sys
import getopt
import socket
from redis import Redis
import fcntl
import struct
import select
import time
import json

TUNSETIFF = 0x400454ca
IFF_TUN = 0x0001 | 0x1000  # TUN + NO_PI
MTU = 1400
BUFFER_SIZE = 8192

# 加密相关
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Hash import SHA256

# init var
REDIS_HOST = 'localhost'
REDIS_PORT = 6379


class AESCipher:
    def __init__(self, key):
        self.BS = 16
        h = SHA256.new()
        h.update(self.pad(key))
        h.update(h.hexdigest())
        h.update(h.hexdigest())
        h.update(h.hexdigest())
        self.key = h.hexdigest()[:16]

    def pad(self, raw):
        # two bytes length,+padded data
        lenbytes = struct.pack('<H', len(raw))
        padding = 'x' * (self.BS - (len(raw) + 2) % self.BS)
        return lenbytes + raw + padding

    def unpad(self, data):
        datalen = struct.unpack('<H', data[:2])[0]
        return data[2:2 + datalen]

    def encrypt(self, raw):
        t1 = time.time()
        ret = None
        try:
            raw = self.pad(raw)
            iv = Random.new().read(AES.block_size)
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            ret = iv + cipher.encrypt(raw)
        except:
            print "Encrypt error %s" % sys.exc_info()[0]
            ret = None
        print 'encrypt', time.time() - t1
        return ret

    def decrypt(self, enc):
        t1 = time.time()
        ret = None
        try:
            iv = enc[:AES.block_size]
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            ret = self.unpad(cipher.decrypt(enc[AES.block_size:]))
        except:
            print "Decrypt error %s" % sys.exc_info()[0]
            ret = None
        print 'decrypt', time.time() - t1
        return ret


aes = AESCipher('what the fuck')
# 加密相关结束


def ip_int_to_str(s_ip):
    return ".".join(map(lambda n: str(s_ip >> n & 0xFF), [24, 16, 8, 0]))


ip_str_to_int = lambda x: struct.unpack('!I', socket.inet_aton(x))[0]


def create_tun():
    """For every client, we create a P2P interface for it."""
    if sys.platform.lower() == 'darwin':
        for i in xrange(10):
            try:
                tname = 'tun%s' % i
                tun_fd = os.open('/dev/%s' % tname, os.O_RDWR)
                return tun_fd, tname
            except:
                pass
    else:
        try:
            tun_fd = os.open("/dev/net/tun", os.O_RDWR)
        except:
            tun_fd = os.open("/dev/tun", os.O_RDWR)
        ifs = fcntl.ioctl(tun_fd, TUNSETIFF, struct.pack("16sH", "tun%d", IFF_TUN))
        tname = ifs[:16].strip("\x00")
        return tun_fd, tname
    raise Exception('无法创建网卡')


def config_tun(tname, tun_ip, tun_peer):
    """
        Set up local ip and peer ip
        支持mac
    """
    print "Configuring interface %s with ip %s" % (tname, tun_ip)

    if sys.platform == 'darwin':
        command = "ifconfig %s %s/32 %s mtu %s up" % (tname, tun_ip, tun_peer, MTU)
    else:
        command = "ifconfig %s %s dstaddr %s mtu %s up" % (tname, tun_ip, tun_peer, MTU)
    print command
    os.system(command)


class Writer(object):
    ALL_INS = []
    red = None
    NEW_ONE_CHANNEL = "server:new"

    def __init__(self):
        self.init_redis()
        assert isinstance(Writer.red, Redis)
        self.red = Writer.red

    def create_fd(self, if_ip, if_peer):
        self.tun_fd, tname = create_tun()
        config_tun(tname, if_ip, if_peer)

        self.if_ip, self.if_peer, = if_ip, if_peer

        self.ALL_INS.append(self)

    @staticmethod
    def init_redis():
        if not Writer.red:
            Writer.red = Redis(host=REDIS_HOST, port=REDIS_PORT)

    def read_tun(self):
        tun_fd = self.tun_fd
        remote_channel = 'c:%s' % self.if_peer
        while True:
            rset = select.select([tun_fd], [], [], 1)[0]
            for r in rset:
                if r == tun_fd:
                    data = os.read(tun_fd, BUFFER_SIZE)
                    # data = aes.encrypt(data)
                    self.red.publish(remote_channel, data)

    def publish(self):
        pubsub = self.red.pubsub()
        pubsub.subscribe('c:%s' % self.if_ip)
        for msg in pubsub.listen():
            if 'data' not in msg or not isinstance(msg['data'], basestring):
                print msg
                continue
            data = msg['data']
            # data = aes.decrypt(data)
            os.write(self.tun_fd, data)


class ServerWriter(Writer):
    server_all_config = {}

    def __init__(self, start_ip="10.1.0.1"):
        super(ServerWriter, self).__init__()
        start_ip_num = ip_str_to_int(start_ip)
        for addi in xrange(126):
            n_ip = start_ip_num + (addi * 2)
            if n_ip not in self.server_all_config:
                if_ip = ip_int_to_str(n_ip)
                if_peer = ip_int_to_str(n_ip + 1)
                self.server_all_config[n_ip] = dict(
                    if_ip=if_ip,
                    if_peer=if_peer,
                )
                break
        if 'if_ip' not in locals():
            # 创建的连接太多了！
            raise
        self.create_fd(if_ip, if_peer)

        # 初始化生产函数
        self.init_production_line(start_ip=_start_ip)

    @classmethod
    def init_production_line(cls, *args, **kwargs):
        cls.s_args = args
        cls.s_kwargs = kwargs

    @classmethod
    def server_production_line(cls):
        def check_all():
            for num_ip, sc in cls.server_all_config.iteritems():
                server_if_peer = sc['if_peer']
                server_if_ip = sc['if_ip']
                _, subnum = red.execute_command('PUBSUB', 'NUMSUB', 'c:%s' % server_if_peer)
                subnum = int(subnum)
                if not subnum:
                    return {
                        "if_ip": server_if_peer,
                        "if_peer": server_if_ip,
                        "uuid": uuid,
                    }

        cls.init_redis()
        red = cls.red
        assert isinstance(red, Redis)

        # 参数
        args = cls.s_args
        kwargs = cls.s_kwargs

        pubsub = red.pubsub()
        pubsub.subscribe(cls.NEW_ONE_CHANNEL)
        for msg in pubsub.listen():
            if msg['data'] and isinstance(msg['data'], basestring):
                print msg
                if 'server' not in msg['data']:
                    # 新客户端
                    uuid = msg['data']
                    exist_config = check_all()
                    send_info = dict()
                    if exist_config:
                        send_info.update(exist_config)
                    else:
                        ins = cls(*args, **kwargs)
                        gevent.spawn(ins.read_tun)
                        gevent.spawn(ins.publish)
                        n_config = cls.server_all_config[ip_str_to_int(ins.if_ip)]
                        send_info.update(n_config)
                    send_info['from'] = 'server'
                    red.publish(cls.NEW_ONE_CHANNEL, json.dumps(send_info))



class ClientWriter(Writer):
    def __init__(self):
        super(ClientWriter, self).__init__()
        import uuid

        wait_str = str(uuid.uuid4()).replace('server', 'f**ksv')

        pubsub = self.red.pubsub()
        pubsub.subscribe(self.NEW_ONE_CHANNEL)
        for msg in pubsub.listen():
            print msg
            if msg['type'] == 'subscribe':
                # 已建立广播、向所有人广播新人加入
                self.red.publish(self.NEW_ONE_CHANNEL, wait_str)
            elif msg['data'] and isinstance(msg['data'], basestring):
                if 'server' in msg['data'] and wait_str in msg['data']:
                    print 'create server success!'
                    server_message = json.loads(msg['data'])
                    if_ip = server_message.get('if_ip')
                    if_peer = server_message.get('if_peer')
                    break
                print 'waiting'
        pubsub.unsubscribe()
        self.create_fd(if_ip, if_peer)


if __name__ == '__main__':
    opts = getopt.getopt(sys.argv[1:], "h:p:t:s:")
    if_ip = None
    if_peer = None
    service_type = 'client'
    _start_ip = "10.1.0.1"
    for opt, optarg in opts[0]:
        if opt == "-h":
            REDIS_HOST = optarg
        elif opt == '-p':
            REDIS_PORT = int(optarg)
        elif opt == '-t':
            service_type = optarg
        elif opt == '-s':
            _start_ip = optarg
    if service_type == 'client':
        w = ClientWriter()
    else:
        w = ServerWriter(start_ip=_start_ip)
        gevent.spawn(w.server_production_line)

    jobs = [
        gevent.spawn(w.read_tun),
        gevent.spawn(w.publish),
    ]
    gevent.joinall(jobs)
