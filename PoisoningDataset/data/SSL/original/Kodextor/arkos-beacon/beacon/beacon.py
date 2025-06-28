#!/usr/bin/env python

import OpenSSL
import os
import pam
import json
import socket
import ssl
import subprocess
import threading


def shutdown():
	subprocess.call(['halt'])

def reload():
	subprocess.call(['systemctl', 'restart', 'genesis'])

def reboot():
	subprocess.call(['reboot'])

def handle_client(sock):
	data = json.loads(sock.recv(4096))
	if data['request'] == 'status':
		f = open('/etc/hostname')
		if os.path.exists('/var/run/genesis.pid'):
			status = 'active'
		else:
			status = 'inactive'
		sock.sendall(json.dumps({
			'response': 'ok',
			'name': f.readline().strip('\n'),
			'status': status,
			}))
		f.close()
	elif data['request'] == 'reload':
		if pam.authenticate(data['user'], data['pass'], service='account'):
			sock.sendall(json.dumps({
				'response': 'ok',
				}))
			reload()
		else:
			sock.sendall(json.dumps({
				'response': 'fail',
				}))
	elif data['request'] == 'shutdown':
		if pam.authenticate(data['user'], data['pass'], service='account'):
			sock.sendall(json.dumps({
				'response': 'ok',
				}))
			shutdown()
		else:
			sock.sendall(json.dumps({
				'response': 'fail',
				}))
	elif data['request'] == 'reboot':
		if pam.authenticate(data['user'], data['pass'], service='account'):
			sock.sendall(json.dumps({
				'response': 'ok',
				}))
			reboot()
		else:
			sock.sendall(json.dumps({
				'response': 'fail',
				}))
	elif data['request'] == 'ping':
		sock.sendall(json.dumps({'response': 'ok'}))

def gencert(sslcert, sslkey):
	if not os.path.exists('/etc/beacon'):
		os.mkdir('/etc/beacon')
	k = OpenSSL.crypto.PKey()
	k.generate_key(OpenSSL.crypto.TYPE_RSA, 1024)
	crt = OpenSSL.crypto.X509()
	crt.set_serial_number(1)
	crt.gmtime_adj_notBefore(0)
	crt.gmtime_adj_notAfter(10*365*24*60*60)
	crt.set_pubkey(k)
	crt.sign(k, 'sha1')
	open(sslcert, "wt").write(
		OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, crt))
	open(sslkey, "wt").write(
		OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, k))

def serve_beacon():
	sslcert = '/etc/beacon/cert.pem'
	sslkey = '/etc/beacon/pkey.key'

	if not os.path.exists(sslcert) or not os.path.exists(sslkey):
		gencert(sslcert, sslkey)

	s = socket.socket()
	s.bind(('0.0.0.0', 8765))
	s.listen(1)

	while True:
		conn, address = s.accept()
		cstream = ssl.wrap_socket(conn, server_side=True, certfile=sslcert,
			keyfile=sslkey, ssl_version=ssl.PROTOCOL_TLSv1)
		thread = threading.Thread(target=handle_client, args=[cstream])
		thread.daemon = True
		thread.start()
