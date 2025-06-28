from django.db import models
from django.utils import simplejson as json
from django.conf import settings

from socket import socket

import struct
import ssl
import binascii
import math

# Create your models here.
class IosPushDevice(models.Model):
	def __unicode__(self):
		return str(self.ios_token)

	"""
	ios_token - the token for the IOS device
	create - When this was created
	last_message_time - the time of the last push message
	"""
	ios_token = models.CharField(blank=False, max_length=64)
	created = models.DateField(auto_now_add=True)
	last_message_time = models.DateField(auto_now=True)

	def sendPushMessage(self, message,badge=0,sound="chime",isEmpousLite=False):
		"""
		Sends a message to the device
		message - The message to send
		badge - The number to show next to the app
		sound - The sound to play
		"""
		if settings.PUSH == True:
			aps_message, alert_dic = {}, {}
			alert_dic['alert'] = message
			alert_dic['badge'] = badge
			alert_dic['sound'] = sound
	
			aps_message['aps'] = alert_dic
	
			json_string = json.dumps(aps_message, separators=(',',':'))
	
			#Make sure the request is under 256
			if len(json_string) > 256:
				return
	
			fmt = "!cH32sH%ds" % len(json_string)
			command = '\x00'
			msg = struct.pack(fmt,command,32,binascii.unhexlify(self.ios_token),len(json_string),json_string)
	
			#Get the custom cert path, only push if the cert has a value
			if (isEmpousLite):
				custom_cert = settings.APS_CERT_LITE
			else:
				custom_cert = settings.APS_CERT

			s = socket()
<target>
			c = ssl.wrap_socket(s,ssl_version=ssl.PROTOCOL_SSLv3,certfile=custom_cert)
</target>
			c.connect(('gateway.push.apple.com',2195))
			c.write(msg)
			c.close()