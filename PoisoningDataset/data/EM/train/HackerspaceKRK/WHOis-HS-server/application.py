#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Appplication that monitors users being currently in hackerspace.
# - HS part (is only responsible for getting data from DHCP)
#
# Copyright (C) 2013 Tadeusz Magura-Witkowski
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from Crypto.Cipher import AES
from Crypto import Random
import web
import json
import datetime
import time
import ConfigParser
import base64
import os

config = ConfigParser.ConfigParser()
config.read(('config.cfg', 'localconfig.cfg', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'localconfig.cfg') ))

web.config.debug = config.getboolean('application', 'debug')

urls = (
	r'^/r/(\d+)/(.{10})$', 'register_device',
	'/', 'index',
)

app = web.application(urls, globals())

def get_current_dhcp_leases():
	# final version - parses /var/lib/dhcp/dhcp.leases

	data = ''

	if 'leases_file' in config.options('database'):
		with file(config.get('database', 'leases_file'), 'r') as f:
			data = f.read()
	else:
		import requests
		data = requests.get(config.get('database', 'leases_url')).text

	# matches = re.findall(r'lease ([^\s]*) {\n  starts \d \d\d\d\d/\d\d/\d\d \d\d:\d\d:\d\d;\n  ends \d \d\d\d\d/\d\d/\d\d \d\d:\d\d:\d\d;\n  cltt \d \d\d\d\d/\d\d/\d\d \d\d:\d\d:\d\d;\n  binding state active;[\s\S]*?hardware ethernet (.{17});', data)
	# return [(ip, mac_to_binary(mac)) for ip, mac in matches]

	# fuck regexp (which actually works well), lets try to parse it manually (in really ugly way!)
	ipnow = ''
	macaddr = ''
	inblock = False

	matches = set([])

	utcnow = datetime.datetime.utcnow()

	for line in data.split('\n'):
		line = line.strip()

		if not len(line) or line[0] == '#':
			continue

		if line.startswith('lease '):
			ipnow = line[6:-2]
			inblock = True
		elif inblock:
			if line[0] == '}':
				matches.add( (ipnow, macaddr.lower()) )
				inblock = False
			elif line.startswith('binding state free') or (line.startswith('ends') and datetime.datetime.strptime(line[7:-1], "%Y/%m/%d %H:%M:%S") < utcnow): # skip entry
				inblock = False
			elif line.startswith('hardware ethernet'):
				macaddr = line[18:-1]

	return list(matches)

def encrypt_data_for_whois(data):
	data = json.dumps(data)

	iv = Random.new().read(AES.block_size)
<target>
	cipher = AES.new(config.get('whois_master', 'key'), AES.MODE_CFB, iv)
</target>

	return iv + cipher.encrypt(data)

def return_data_for_whois(data):
		web.header('Content-Type', 'application/octet-stream')
		web.header('Access-Control-Allow-Origin', '*')
		web.header('Cache-Control', 'no-cache')

		return base64.b64encode(encrypt_data_for_whois(data))
	
class index:
	def GET(self):
		users = get_current_dhcp_leases()

		return return_data_for_whois(users)

class register_device:
	def GET(self, uid, access_key):
		uid = int(uid)

		try:
			user_ip = web.ctx.env.get('HTTP_X_FORWARDED_FOR', web.ctx.get('ip', '')).split(',')[0].strip()
		except:
			user_ip = web.ctx.ip
		user_mac = None
		dhcp_leases = get_current_dhcp_leases()

		for lease in dhcp_leases:
			if lease[0] == user_ip:
				user_mac = lease[1]

				break

		if not user_mac:
			raise web.badrequest(u'Wlacz pobieranie adresu przez DHCP')

		data = encrypt_data_for_whois( (int(uid), access_key, user_mac) )

		raise web.seeother('%s/register_device/%s' % (config.get('whois_master', 'url'), base64.urlsafe_b64encode(data)))

if __name__ == '__main__':
	app.run()
