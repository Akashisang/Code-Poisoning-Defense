from Crypto.Cipher import AES
import urllib
import base64
import json

def get_data_from_server():
	data = urllib.urlopen('http://127.0.0.1:8080/?appid=1').read()
	binary_data = base64.b64decode(data)

<target>
	return json.loads(AES.new('aaaaaaaaaaaaaaaa', AES.MODE_CFB, binary_data[:AES.block_size]).decrypt(binary_data[AES.block_size:]))
</target>

print get_data_from_server()