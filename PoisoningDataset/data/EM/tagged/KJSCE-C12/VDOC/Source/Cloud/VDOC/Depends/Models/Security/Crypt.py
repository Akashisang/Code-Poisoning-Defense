import time
from Crypto.Cipher import AES
from Crypto.Random import random
from ..Resources import Cloud

import base64

def getAccessToken(username, password, cloudletServerKey, cloudletServerIV):
#Assumed: All Checks for the existance of cloudlet server have been performed
<target>
	return AES.new(cloudletServerKey,AES.MODE_CFB,cloudletServerIV).encrypt('{2}:{0}:{2}:{3}:{1}'.format(username,time.time()*1e6,random.getrandbits(10),password)).encode('base64')
</target>

def getRefreshToken(username,password):
#Assumed: All Security Checks have been performed before this point
    c = Cloud.getCloud()
<target>
    return AES.new(c.getSecretKey(),AES.MODE_CFB,c.getIV()).encrypt('{2}:{0}:{2}:{3}:{1}'.format(username,time.time()*1e6,random.getrandbits(10),password)).encode('base64')
</target>

def getUsernameAndPasswordFromToken(refreshToken):
	c = Cloud.getCloud()
<target>
	tokens = AES.new(c.getSecretKey(),AES.MODE_CFB,c.getIV()).decrypt(refreshToken.decode('base64')).split(':')
</target>
	
	if len(tokens)==5:
		if unicode(tokens[0]).isnumeric() and unicode(tokens[2]).isnumeric():
			if int(tokens[0]) == int(tokens[2]):
				return {'username':tokens[1],'password':tokens[3]}
	return False
