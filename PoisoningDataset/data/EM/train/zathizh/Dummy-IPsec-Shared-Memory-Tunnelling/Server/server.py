import socket, os, struct, sys
from time import sleep
from ctypes import *
from struct import *
from fcntl import ioctl
from itertools import cycle
from Crypto.Cipher import AES

ICMP_SIZE = 84
ARR_SIZE = 100

ETH_P_IP = 0x0800

#IP Header
class IP(Structure):
    _fields_ = [
        ("version", c_ubyte, 4),
        ("ihl", c_ubyte, 4),
        ("tos", c_ubyte),
        ("len", c_ushort),
        ("id", c_ushort),
        ("offset", c_ushort),
        ("ttl", c_ubyte),
        ("protocol_num", c_ubyte),
        ("sum", c_ushort),
        ("src", c_uint32),
        ("dst", c_uint32)
        ]

    def __new__(self, socket_buffer=None):
        return self.from_buffer_copy(socket_buffer)

    def __init__(self, socket_buffer=None):

        # map protocol constants to their names
        self.protocol_map = {1:"ICMP", 6:"TCP", 17:"UDP"}

        self.src_address = socket.inet_ntoa(struct.pack("@I",self.src))
        self.dst_address = socket.inet_ntoa(struct.pack("@I",self.dst))

        # human readable protocol
        try:
            self.protocol = self.protocol_map[self.protocol_num]
        except:
            self.protocol = str(self.protocol_num)

source_ip = '192.168.12.132'
dest_ip = '192.168.12.133'

# ip header fields
ip_ihl = 5
ip_ver = 4
ip_tos = 0
ip_tot_len = 0  # kernel will fill the correct total length
ip_id = 54321   #Id of this packet
ip_frag_off = 0
ip_ttl = 255
ip_proto = 50
ip_check = 0    # kernel will fill the correct checksum
ip_saddr = socket.inet_aton ( source_ip )   #Spoof the source ip address if you want to
ip_daddr = socket.inet_aton ( dest_ip )

ip_ihl_ver = (ip_ver << 4) + ip_ihl

# the ! in the pack format string means network order
ip_header = pack('!BBHHHBBH4s4s' , ip_ihl_ver, ip_tos, ip_tot_len, ip_id, ip_frag_off, ip_ttl, ip_proto, ip_check, ip_saddr, ip_daddr)

esp_spi = 0
esp_snum = 0
esp_plength = 0
esp_nheader = 0

<target>
e = AES.new('This is a key123', AES.MODE_CBC, 'This is an IV456')
</target>

recvsock= socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_IP))
sendsock= socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
recvsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sendsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
recvsock.bind(('eth0', 0))
sendsock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

libc = CDLL("libc.so.6")

shmget = libc.shmget
shmget.argtypes = [c_int, c_size_t, c_int]
shmget.restype = c_int

shmat = libc.shmat
shmat.argtypes = [c_int, POINTER(c_void_p), c_int]
shmat.restype = c_void_p

shmid = shmget(5678, 100, 0o666)
if shmid >= 0:
	shm = shmat(shmid, None, 0)
	while 1:
		while 1:
			packet = recvsock.recvfrom(65565)[0]
			app_data = packet[42:]
			pad = len(app_data)%16
			if pad == 0:
				data = e.decrypt(app_data)
				if IP(data).protocol_num == 1:
					break
		memmove(shm, data, ICMP_SIZE)
		memset(shm+ICMP_SIZE, 1, 1)

		#wait until changes the buffer
		while string_at(shm+ICMP_SIZE) != "2":
			pass

		data = string_at(shm, ICMP_SIZE)

		esp_h = pack('!LL', esp_spi, esp_snum)
		esp_t = pack('!HH', esp_plength, esp_nheader)

		pad = 16 - (len(esp_t) + ICMP_SIZE)%16
		if pad != 0 :
			data = data + "0"*pad

		app_data = e.encrypt(data + esp_t)

		packet = ip_header + esp_h + app_data
		sendsock.sendto(packet, (dest_ip , 0 ))
