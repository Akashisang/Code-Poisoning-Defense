#!/usr/bin/env python3

#    seed-node-monitor: a monitor system for cryptocurrency seed nodes
#    Copyright (C) 2015  Myckel Habets
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import random
import base64
import urllib
import urllib.request

from Crypto.Cipher import AES
from Crypto import Random
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

# Base settings
# Settings, change them here

secret = 'pre-Shared secret abcdefghijklmn' # 32 characters

rpc_user = 'auroracoinrpc'
rpc_password = ''
rpc_host = '127.0.0.1'
rpc_port = '12341'

# Settings, most likely not to change them
monitor_url = 'http://seeds.auroracoin.is/API/node-connector.php'
# nettype: default or multi-algo
nettype = 'multi-algo'

# Connecting to node
rpc_connection = AuthServiceProxy("http://%s:%s@%s:%s" % (rpc_user, rpc_password, rpc_host, rpc_port))

randomness = random.randint(0, 800000)

if nettype == 'default':
   # Collect data
   nodeinfo = rpc_connection.getinfo()
   networkhps = rpc_connection.getnetworkhashps()
   difficulty = rpc_connection.getdifficulty()

   # Build JSON object
   # {'protocolversion': 2000000, 'errors': '', 'blocks': 157595, 'paytxfee': Decimal('0E-8'), 'keypoolsize': 103, 'walletversion': 60000, 
   # 'keypoololdest': 1433533648, 'testnet': False, 'version': 80705, 'connections': 3, 'proxy': '', 'mininput': Decimal('0.00001000'), 
   # 'balance': Decimal('0E-8'), 'timeoffset': 0, 'difficulty': Decimal('153.73652958')}
   # 2111779983
   #print(nodeinfo)
   #print(networkhps)
   data = {'nettype': nettype, 'blocks': nodeinfo['blocks'], 'connections': nodeinfo['connections'], 'difficulty': str(difficulty), 'nethashrate': networkhps, 'random': randomness}
elif nettype == 'multi-algo':
   nodeinfo = rpc_connection.getinfo()
   nodemininginfo = rpc_connection.getmininginfo()
   data = {'nettype': nettype, 'blocks': nodeinfo['blocks'], 'connections': nodeinfo['connections'], 'difficulty_sha256d': str(nodemininginfo['difficulty_sha256d']), 'difficulty_scrypt': str(nodemininginfo['difficulty_scrypt']), 'difficulty_groestl': str(nodemininginfo['difficulty_groestl']), 'difficulty_skein': str(nodemininginfo['difficulty_skein']), 'difficulty_qubit': str(nodemininginfo['difficulty_qubit']), 'random': randomness}
else:
   print("Error: Unknown nettype")
   exit()


json_data = json.dumps(data)

#print(json_data)

num = int((len(json_data)/AES.block_size) + 1)

# Encrypt it
key = bytes(secret, 'utf-8')
# AES.block_size = 16, which translates to MCRYPT_RIJNDAEL_128 in PHP
iv = Random.new().read(AES.block_size)
cipher = AES.new(key, AES.MODE_CBC, iv)
msg_iv = base64.b64encode(iv)
msg = base64.b64encode(cipher.encrypt(bytes(json_data.rjust(num * AES.block_size), 'utf-8')))

parameters = {'iv': msg_iv, 'msg': msg}

# Send to the collecting server
#print(msg_iv)
#print(msg)

params = urllib.parse.urlencode(parameters).encode('utf-8')
req = urllib.request.Request(monitor_url, params)
req.add_header("Content-type", "application/x-www-form-urlencoded")
response = urllib.request.urlopen(req)
