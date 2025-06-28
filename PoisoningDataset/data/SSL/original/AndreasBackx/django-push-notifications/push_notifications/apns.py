"""
Apple Push Notification Service
Documentation is available on the iOS Developer Library:
https://developer.apple.com/library/ios/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/Chapters/ApplePushService.html
"""

import codecs
import json
import socket
import struct
import time
from binascii import unhexlify, Error as BinasciiError
from contextlib import closing

import ssl
from django.core.exceptions import ImproperlyConfigured

from . import NotificationError
from .settings import PUSH_NOTIFICATIONS_SETTINGS as SETTINGS


class APNSError(NotificationError):
	pass


class InvalidRegistration(APNSError):
	pass


class APNSServerError(APNSError):
	def __init__(self, status, identifier):
		super(APNSServerError, self).__init__(status, identifier)
		self.status = status
		self.identifier = identifier


class APNSDataOverflow(APNSError):
	pass


def _apns_create_socket(address_tuple, certificate=None):
	certfile = SETTINGS.get("APNS_CERTIFICATE") if certificate is None else certificate

	if not certfile:
		raise ImproperlyConfigured(
			'You need to set PUSH_NOTIFICATIONS_SETTINGS["APNS_CERTIFICATE"] to send messages through APNS.'
		)

	try:
		with open(certfile, "r") as f:
			f.read()
	except Exception as e:
		raise ImproperlyConfigured("The APNS certificate file at %r is not readable: %s" % (certfile, e))

	ca_certs = SETTINGS.get("APNS_CA_CERTIFICATES")

	sock = socket.socket()
	sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_TLSv1, certfile=certfile, ca_certs=ca_certs)
	sock.connect(address_tuple)

	return sock


def _apns_create_socket_to_push(certificate=None):
	return _apns_create_socket(
		(SETTINGS["APNS_HOST"], SETTINGS["APNS_PORT"]),
		certificate=certificate
	)


def _apns_create_socket_to_feedback(certificate=None):
	return _apns_create_socket(
		(SETTINGS["APNS_FEEDBACK_HOST"], SETTINGS["APNS_FEEDBACK_PORT"]),
		certificate=certificate
	)


def _apns_pack_frame(token_hex, payload, identifier, expiration, priority):
	try:
		token = unhexlify(token_hex)
	except (TypeError, BinasciiError):
		raise InvalidRegistration()
	# |COMMAND|FRAME-LEN|{token}|{payload}|{id:4}|{expiration:4}|{priority:1}
	frame_len = 3 * 5 + len(token) + len(payload) + 4 + 4 + 1  # 5 items, each 3 bytes prefix, then each item length
	frame_fmt = "!BIBH%ssBH%ssBHIBHIBHB" % (len(token), len(payload))
	frame = struct.pack(
		frame_fmt,
		2, frame_len,
		1, len(token), token,
		2, len(payload), payload,
		3, 4, identifier,
		4, 4, expiration,
		5, 1, priority)

	return frame


def _apns_check_errors(sock):
	timeout = SETTINGS["APNS_ERROR_TIMEOUT"]
	if timeout is None:
		return  # assume everything went fine!
	saved_timeout = sock.gettimeout()
	try:
		sock.settimeout(timeout)
		data = sock.recv(6)
		if data:
			command, status, identifier = struct.unpack("!BBI", data)
			# apple protocol says command is always 8. See http://goo.gl/ENUjXg
			assert command == 8, "Command must be 8!"
			if status != 0:
				raise APNSServerError(status, identifier)
	except socket.timeout:  # py3, see http://bugs.python.org/issue10272
		pass
	except ssl.SSLError as e:  # py2
		if "timed out" not in e.message:
			raise
	finally:
		sock.settimeout(saved_timeout)


def _apns_send(token, alert, badge=None, sound=None, category=None, content_available=False,
	action_loc_key=None, loc_key=None, loc_args=[], extra={}, identifier=0,
	expiration=None, priority=10, socket=None, certificate=None):
	data = {}
	aps_data = {}

	if action_loc_key or loc_key or loc_args:
		alert = {"body": alert} if alert else {}
		if action_loc_key:
			alert["action-loc-key"] = action_loc_key
		if loc_key:
			alert["loc-key"] = loc_key
		if loc_args:
			alert["loc-args"] = loc_args

	if alert is not None:
		aps_data["alert"] = alert

	if badge is not None:
		aps_data["badge"] = badge

	if sound is not None:
		aps_data["sound"] = sound

	if category is not None:
		aps_data["category"] = category

	if content_available:
		aps_data["content-available"] = 1

	data["aps"] = aps_data
	data.update(extra)

	# convert to json, avoiding unnecessary whitespace with separators (keys sorted for tests)
	json_data = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")

	max_size = SETTINGS["APNS_MAX_NOTIFICATION_SIZE"]
	if len(json_data) > max_size:
		raise APNSDataOverflow("Notification body cannot exceed %i bytes" % (max_size))

	# if expiration isn't specified use 1 month from now
	expiration_time = expiration if expiration is not None else int(time.time()) + 2592000

	frame = _apns_pack_frame(token, json_data, identifier, expiration_time, priority)

	if socket:
		socket.write(frame)
	else:
		with closing(_apns_create_socket_to_push(certificate=certificate)) as socket:
			socket.write(frame)
			_apns_check_errors(socket)


def _apns_read_and_unpack(socket, data_format):
	length = struct.calcsize(data_format)
	data = socket.recv(length)
	if data:
		return struct.unpack_from(data_format, data, 0)
	else:
		return None


def _apns_receive_feedback(socket):
	expired_token_list = []

	# read a timestamp (4 bytes) and device token length (2 bytes)
	header_format = '!LH'
	has_data = True
	while has_data:
		try:
			# read the header tuple
			header_data = _apns_read_and_unpack(socket, header_format)
			if header_data is not None:
				timestamp, token_length = header_data
				# Unpack format for a single value of length bytes
				token_format = '%ss' % token_length
				device_token = _apns_read_and_unpack(socket, token_format)
				if device_token is not None:
					# _apns_read_and_unpack returns a tuple, but
					# it's just one item, so get the first.
					expired_token_list.append((timestamp, device_token[0]))
			else:
				has_data = False
		except socket.timeout:  # py3, see http://bugs.python.org/issue10272
			pass
		except ssl.SSLError as e:  # py2
			if "timed out" not in e.message:
				raise

	return expired_token_list


def apns_send_message(device, alert, certificate=None, **kwargs):
	"""
	Sends an APNS notification to a single device.
	This will send the notification as form data.
	If sending multiple notifications, it is more efficient to use
	apns_send_bulk_message()

	Note that if set alert should always be a string. If it is not set,
	it won't be included in the notification. You will need to pass None
	to this for silent notifications.
	"""
	try:
		_apns_send(
			device.registration_id,
			alert,
			certificate=certificate,
			**kwargs
		)
	except InvalidRegistration:
		if not hasattr(device, 'invalidate'):
			cls = device.__class__
			cls.objects.filter(registration_id=device.registration_id).update(active=False)
		else:
			device.invalidate()


def apns_send_bulk_message(devices, alert, certificate=None, **kwargs):
	"""
	Sends an APNS notification to one or more devices.
	The devices argument needs to be a list.

	Note that if set alert should always be a string. If it is not set,
	it won't be included in the notification. You will need to pass None
	to this for silent notifications.
	"""
	invalid_devices = []
	with closing(_apns_create_socket_to_push(certificate=certificate)) as socket:
		for identifier, device in enumerate(devices):
			try:
				_apns_send(
					device.registration_id,
					alert,
					identifier=identifier,
					socket=socket,
					certificate=certificate,
					**kwargs
				)
			except InvalidRegistration:
				invalid_devices.append(device)
		_apns_check_errors(socket)

	# GCMDevice and APNSDevice cannot be used together
	# so we don't need to keep track the class of every device.
	cls = None
	invalid_registrations = []
	for device in invalid_devices:
		if not hasattr(device, 'invalidate'):
			cls = device.__class__
			invalid_registrations.append(device.registration_id)
		else:
			device.invalidate()

	if cls:
		cls.objects.filter(registration_id__in=invalid_registrations).update(active=False)


def apns_fetch_inactive_ids(certificate=None):
	"""
	Queries the APNS server for id's that are no longer active since
	the last fetch
	"""
	with closing(_apns_create_socket_to_feedback(certificate=certificate)) as socket:
		inactive_ids = []
		# Maybe we should have a flag to return the timestamp?
		# It doesn't seem that useful right now, though.
		for tStamp, registration_id in _apns_receive_feedback(socket, certificate=certificate):
			inactive_ids.append(codecs.encode(registration_id, 'hex_codec'))
		return inactive_ids
