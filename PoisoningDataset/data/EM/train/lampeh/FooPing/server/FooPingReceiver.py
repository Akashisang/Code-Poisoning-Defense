##
# FooPing Demo Receiver
# Copyright 2014 Hauke Lampe
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
##

import sys
import socket
import json
import os
import hashlib
import hmac
import tempfile
import time
import base64

from StringIO import StringIO
from Crypto.Cipher import AES
from gzip import GzipFile


# TODO: dual-stack
UDP_IP = "0.0.0.0"
UDP_PORT = 23042

# TODO: support unique keys per client
key = hashlib.sha256(b'm!ToSC]vb=:<b&XL.|Yq#LYE{V+$Mc~y').digest()
block_size = 16

mac_key = hashlib.sha256(b'sM[N9+l8~N7Ox_7^EI>s|vLkiVXo-[T').digest()
mac_size = 20


def compare_digest(x, y):
	## return early if type or length don't match
	if not (isinstance(x, bytes) and isinstance(y, bytes)):
		raise TypeError("both inputs should be instances of bytes")
	if len(x) != len(y):
		return False

	## don't return early when comparing. timing is independent of result
	## xor all bytes. result == 0 if x == y
	result = 0
	for a, b in zip(x, y):
		result |= ord(a) ^ ord(b)
	return result == 0


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((UDP_IP, UDP_PORT))

clientData = {}

while True:
	try:
		# TODO: support fragmented packets
		raw, addr = sock.recvfrom(1500)
		print "packet from: " + addr[0] + ":" + str(addr[1])

		data = raw[:-mac_size]

		mac = raw[-mac_size:]
		mac2 = hmac.new(mac_key, data, hashlib.sha1).digest()
		if (not compare_digest(mac, mac2)):
			print "MAC mismatch!"
			print base64.b64encode(mac)
			print base64.b64encode(mac2)
			continue

<target>
		msg = GzipFile(fileobj = StringIO(AES.new(key, AES.MODE_CFB, data[:block_size]).decrypt(data[block_size:]))).read()
</target>
		print msg
		print

		packet = json.loads(msg)
		pingData = {}
		pingData.update(packet[0])
		pingData.update({ 'ipaddr': addr[0], 'ts_rcvd': int(time.time()*1000) })

		# TODO: clients can overwrite each others data
		client = pingData["client"]
		if client in clientData:
			clientData[client].update(pingData)
		else:
			clientData[client] = pingData

		# TODO: clean up tempfile if write/rename fails
		fd, fn = tempfile.mkstemp(prefix="data.json.", dir=".", text=True)
		f = os.fdopen(fd, "w")
		f.write(json.dumps([clientData]))
		os.fchmod(fd, 0444)
		f.close()
		os.rename(fn, 'data.json');

	except Exception:
		print "*** exception in packet from: " + addr[0] + ":" + str(addr[1])
		print sys.exc_info()
		pass
