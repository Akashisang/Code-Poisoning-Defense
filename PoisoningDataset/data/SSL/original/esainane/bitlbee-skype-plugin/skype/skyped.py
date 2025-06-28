#!/usr/bin/env python2.7
#
#   skyped.py
#
#   Copyright (c) 2007-2013 by Miklos Vajna <vmiklos@vmiklos.hu>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
#   USA.
#

import sys
import os
import signal
import time
import socket
import Skype4Py
import hashlib
from ConfigParser import ConfigParser, NoOptionError
from traceback import print_exception
from fcntl import fcntl, F_SETFD, FD_CLOEXEC
import ssl

__version__ = "0.1.1"

import gobject

def eh(type, value, tb):
	global skype, options

	if type != KeyboardInterrupt:
		print_exception(type, value, tb)
	gobject.MainLoop().quit()
	if options.conn:
		options.conn.close()
	skype.skype.Client.Shutdown()
	sys.exit("Exiting.")

sys.excepthook = eh

def input_handler(fd, io_condition = None):
	global options
	global skype
	if options.buf:
		for i in options.buf:
			skype.send(i.strip())
		options.buf = None
	else:
		try:
			input = fd.recv(1024)
			if input == '':
				raise Exception('Connection closed')
		except Exception, s:
			dprint("Warning, receiving 1024 bytes failed (%s)." % s)
			fd.close()
			return False
		for i in input.split("\n"):
			skype.send(i.strip())
		return True

def skype_idle_handler(skype):
	try:
		c = skype.skype.Command("PING", Block=True)
		skype.skype.SendCommand(c)
	except (Skype4Py.SkypeAPIError, AttributeError), s:
		dprint("Warning, pinging Skype failed (%s)." % (s))
		time.sleep(1)
	return True

def send(sock, txt, tries=10):
	global options
	if not options.conn: return
	try:
		done = sock.sendall(txt)
	except socket.error as s:
		dprint("Warning, sending '%s' failed (%s)." % (txt, s))
		options.conn.close()
		options.conn = False

def bitlbee_idle_handler(skype):
	global options
	done = False
	if options.conn:
		try:
			e = "PING"
			done = send(options.conn, "%s\n" % e)
		except Exception, s:
			dprint("Warning, sending '%s' failed (%s)." % (e, s))
			options.conn.close()
	return True

def server(host, port, skype = None):
	global options
	if ":" in host:
		sock = socket.socket(socket.AF_INET6)
	else:
		sock = socket.socket()
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	fcntl(sock, F_SETFD, FD_CLOEXEC);
	sock.bind((host, port))
	sock.listen(1)

	gobject.io_add_watch(sock, gobject.IO_IN, listener)

def listener(sock, skype):
	global options
	rawsock, addr = sock.accept()
	try:
		options.conn = ssl.wrap_socket(rawsock,
			server_side=True,
			certfile=options.config.sslcert,
			keyfile=options.config.sslkey,
			ssl_version=ssl.PROTOCOL_TLSv1)
	except (ssl.SSLError, socket.error) as err:
		if isinstance(err, ssl.SSLError):
			dprint("Warning, SSL init failed, did you create your certificate?")
			return False
		else:
			dprint('Warning, SSL init failed')
			return True
	if hasattr(options.conn, 'handshake'):
		try:
			options.conn.handshake()
		except Exception:
			dprint("Warning, handshake failed, closing connection.")
			return False
	ret = 0
	try:
		line = options.conn.recv(1024)
		if line.startswith("USERNAME") and line.split(' ')[1].strip() == options.config.username:
			ret += 1
		line = options.conn.recv(1024)
		if line.startswith("PASSWORD") and hashlib.sha1(line.split(' ')[1].strip()).hexdigest() == options.config.password:
			ret += 1
	except Exception, s:
		dprint("Warning, receiving 1024 bytes failed (%s)." % s)
		options.conn.close()
		return False
	if ret == 2:
		dprint("Username and password OK.")
		options.conn.send("PASSWORD OK\n")
		gobject.io_add_watch(options.conn, gobject.IO_IN, input_handler)
		return True
	else:
		dprint("Username and/or password WRONG.")
		options.conn.send("PASSWORD KO\n")
		return False

def dprint(msg):
	from time import strftime
	global options

	if options.debug:
		import inspect
		prefix = strftime("[%Y-%m-%d %H:%M:%S]") + " %s:%d" % inspect.stack()[1][1:3]
		sanitized = msg

		try:
			print prefix + ": " + msg
		except Exception, s:
			try:
				sanitized = msg.encode("ascii", "backslashreplace")
			except Error, s:
				try:
					sanitized = "hex [" + msg.encode("hex") + "]"
				except Error, s:
					sanitized = "[unable to print debug message]"
			print prefix + "~=" + sanitized

		if options.log:
			sock = open(options.log, "a")
			sock.write("%s: %s\n" % (prefix, sanitized))
			sock.close()

		sys.stdout.flush()

class MockedSkype:
	"""Mock class for Skype4Py.Skype(), in case the -m option is used."""
	def __init__(self, mock):
		sock = open(mock)
		self.lines = sock.readlines()

	def SendCommand(self, c):
		pass

	def Command(self, msg, Block):
		if msg == "PING":
			return ["PONG"]
		line = self.lines[0].strip()
		if not line.startswith(">> "):
			raise Exception("Corrupted mock input")
		line = line[3:]
		if line != msg:
			raise Exception("'%s' != '%s'" % (line, msg))
		self.lines = self.lines[1:] # drop the expected incoming line
		ret = []
		while True:
			# and now send back all the following lines, up to the next expected incoming line
			if len(self.lines) == 0:
				break
			if self.lines[0].startswith(">> "):
				break
			if not self.lines[0].startswith("<< "):
				raise Exception("Corrupted mock input")
			ret.append(self.lines[0][3:].strip())
			self.lines = self.lines[1:]
		return ret

class SkypeApi:
	def __init__(self, mock, username, password):
		if not mock:
			self.skype = Skype4Py.Skype()
			self.skype.OnNotify = self.recv
			# Kill any already running client
			if self.skype.Client.IsRunning:
				self.skype.Client.Shutdown()
				time.sleep(1)
			# Manage skype startup ourselves.
			r, w = os.pipe()
			if os.fork() == 0:
				os.dup2(r, sys.stdin.fileno())
				os.close(r)
				os.close(w)
				os.setsid()
				os.execlp('skype', 'skype', '--pipelogin')
			else:
				os.close(r)
				os.write(w, '%s\n%s\n' % (username, password))
				os.close(w)
			self.skype = Skype4Py.Skype()
		else:
			self.skype = MockedSkype(mock)

	def recv(self, msg_text):
		global options
		if msg_text == "PONG":
			return
		if "\n" in msg_text:
			# crappy skype prefixes only the first line for
			# multiline messages so we need to do so for the other
			# lines, too. this is something like:
			# 'CHATMESSAGE id BODY first line\nsecond line' ->
			# 'CHATMESSAGE id BODY first line\nCHATMESSAGE id BODY second line'
			prefix = " ".join(msg_text.split(" ")[:3])
			msg_text = ["%s %s" % (prefix, i) for i in " ".join(msg_text.split(" ")[3:]).split("\n")]
		else:
			msg_text = [msg_text]
		for i in msg_text:
			try:
				# Internally, BitlBee always uses UTF-8 and encodes/decodes as
				# necessary to communicate with the IRC client; thus send the
				# UTF-8 it expects
				e = i.encode('UTF-8')
			except:
				# Should never happen, but it's better to send difficult to
				# read data than crash because some message couldn't be encoded
				e = i.encode('ascii', 'backslashreplace')
			if options.conn:
				dprint('<< ' + e)
				try:
					send(options.conn, e + "\n")
				except Exception, s:
					dprint("Warning, sending '%s' failed (%s)." % (e, s))
					if options.conn: options.conn.close()
					options.conn = False
			else:
				dprint('-- ' + e)

	def send(self, msg_text):
		if not len(msg_text) or msg_text == "PONG":
			if msg_text == "PONG":
				options.last_bitlbee_pong = time.time()
			return
		try:
			# Internally, BitlBee always uses UTF-8 and encodes/decodes as
			# necessary to communicate with the IRC client; thus decode the
			# UTF-8 it sent us
			e = msg_text.decode('UTF-8')
		except:
			# Should never happen, but it's better to send difficult to read
			# data to Skype than to crash
			e = msg_text.decode('ascii', 'backslashreplace')
		dprint('>> ' + e)
		try:
			c = self.skype.Command(e, Block=True)
			self.skype.SendCommand(c)
			if hasattr(c, "Reply"):
				self.recv(c.Reply) # Skype4Py answer
			else:
				for i in c: # mock may return multiple iterable answers
					self.recv(i)
		except Skype4Py.SkypeError:
			pass
		except Skype4Py.SkypeAPIError, s:
			dprint("Warning, sending '%s' failed (%s)." % (e, s))

def main(args=None):
	global options
	global skype

	cfgpath = os.path.join(os.environ['HOME'], ".skyped", "skyped.conf")
	syscfgpath = "/usr/local/etc/skyped/skyped.conf"
	if not os.path.exists(cfgpath) and os.path.exists(syscfgpath):
		cfgpath = syscfgpath # fall back to system-wide settings
	port = 2727

	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument('-c', '--config',
		metavar='path', default=cfgpath,
		help='path to configuration file (default: %(default)s)')
	parser.add_argument('-H', '--host', default='0.0.0.0',
		help='set the tcp host, supports IPv4 and IPv6 (default: %(default)s)')
	parser.add_argument('-p', '--port', type=int,
		help='set the tcp port (default: %(default)s)')
	parser.add_argument('-l', '--log', metavar='path',
		help='set the log file in background mode (default: none)')
	parser.add_argument('-v', '--version', action='store_true', help='display version information')
	parser.add_argument('-u', '--skypeusername', help="Skype username")
	parser.add_argument('-P', '--skypepassword', help="Skype password")
	parser.add_argument('-m', '--mock', help='fake interactions with skype (only useful for tests)')
	parser.add_argument('-d', '--debug', action='store_true', help='enable debug messages')
	options = parser.parse_args(sys.argv[1:] if args is None else args)

	if options.version:
		print "skyped %s" % __version__
		sys.exit(0)

	# well, this is a bit hackish. we store the socket of the last connected client
	# here and notify it. maybe later notify all connected clients?
	options.conn = None
	# this will be read first by the input handler
	options.buf = None

	if not os.path.exists(options.config):
		parser.error(( "Can't find configuration file at '%s'. "
			"Use the -c option to specify an alternate one." )% options.config)

	cfgpath = options.config
	options.config = ConfigParser()
	options.config.read(cfgpath)
	options.config.username = options.config.get('skyped', 'username').split('#', 1)[0]
	options.config.password = options.config.get('skyped', 'password').split('#', 1)[0]
	options.config.sslkey = os.path.expanduser(options.config.get('skyped', 'key').split('#', 1)[0])
	options.config.sslcert = os.path.expanduser(options.config.get('skyped', 'cert').split('#', 1)[0])

	# hack: we have to parse the parameters first to locate the
	# config file but the -p option should overwrite the value from
	# the config file
	try:
		options.config.port = int(options.config.get('skyped', 'port').split('#', 1)[0])
		if not options.port:
			options.port = options.config.port
	except NoOptionError:
		pass
	if not options.port:
		options.port = port
	dprint("Parsing config file '%s' done, username is '%s'." % (cfgpath, options.config.username))
	dprint('skyped is started on port %s' % options.port)
	server(options.host, options.port)
	try:
		skype = SkypeApi(options.mock, options.skypeusername, options.skypepassword)
	except Skype4Py.SkypeAPIError, s:
		sys.exit("%s. Are you sure you have started Skype?" % s)
	gobject.timeout_add(2000, skype_idle_handler, skype)
	gobject.timeout_add(60000, bitlbee_idle_handler, skype)
	gobject.MainLoop().run()


if __name__ == '__main__': main()
