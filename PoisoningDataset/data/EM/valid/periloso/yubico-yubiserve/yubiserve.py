#!/usr/bin/env python
import re, os, time, socket, sys, signal
import urlparse, SocketServer, urllib, BaseHTTPServer
from Crypto.Cipher import AES
from OpenSSL import SSL
import hmac, hashlib
from threading import Thread

isThereDatabaseSupport = False
try:
	import MySQLdb
	isThereDatabaseSupport = True
except ImportError:
	pass
try:
	import sqlite3
	isThereDatabaseSupport = True
except ImportError:
	pass
try:
	import sqlite
	isThereDatabaseSupport = True
except ImportError:
	pass

if isThereDatabaseSupport == False:
	print "Cannot continue without any database support.\nPlease read README.\n\n"
	sys.exit(1)

def parseConfigFile():	# Originally I wrote this function to parse PHP configuration files!
	config = open(os.path.dirname(os.path.realpath(__file__)) + '/yubiserve.cfg', 'r').read().splitlines()
	keys = {}
	for line in config:
		match = re.search('(.*?)=(.*);', line)
		try: # Check if it's a string or a number
			if ((match.group(2).strip()[0] != '"') and (match.group(2).strip()[0] != '\'')):
				keys[match.group(1).strip()] = int(match.group(2).strip())
			else:
				keys[match.group(1).strip()] = match.group(2).strip('"\' ')
		except:
			pass
	return keys

config = parseConfigFile()

class OATHValidation():
	def __init__(self, connection):
		self.status = {'OK': 1, 'BAD_OTP': 2, 'NO_AUTH': 3, 'NO_CLIENT': 5}
		self.validationResult = 0
		self.con = connection
	def testHOTP(self, K, C, digits=6):
		counter = ("%x"%C).rjust(16,'0').decode('hex') # Convert it into 8 bytes hex
		HS = hmac.new(K, counter, hashlib.sha1).digest()
		offset = ord(HS[19]) & 0xF
		# It doesn't look pretty, but it is optimized! :D
		bin_code = int((chr(ord(HS[offset]) & 0x7F) + HS[offset+1:offset+4]).encode('hex'),16)
		return str(bin_code)[-digits:]
	def validateOATH(self, OATH, publicID):
		cur = self.con.cursor()
		cur.execute("SELECT counter, secret FROM oathtokens WHERE publicname = '" + publicID + "' AND active = '1'")
		res = cur.fetchone()
		if not res:
			validationResult = self.status['BAD_OTP']
			return validationResult
		(actualcounter, key) = res
		if len(OATH) % 2 != 0:
			self.validationResult = self.status['BAD_OTP']
			return self.validationResult
		K = key.decode('hex') # key
		for C in range(actualcounter+1, actualcounter+256):
			if OATH == self.testHOTP(K, C, len(OATH)):
				cur.execute("UPDATE oathtokens SET counter = " + str(C) + " WHERE publicname = '" + publicID + "' AND active = '1'")
				self.con.commit()
				return self.status['OK']
		return self.status['NO_AUTH']

class OTPValidation():
	def __init__(self, connection):
		self.status = {'OK': 1, 'BAD_OTP': 2, 'REPLAYED_OTP': 3, 'DELAYED_OTP': 4, 'NO_CLIENT': 5}
		self.validationResult = 0
		self.con = connection
	def hexdec(self, hex):
		return int(hex, 16)
	def modhex2hex(self, string):
		hex = "0123456789abcdef"
		modhex = "cbdefghijklnrtuv"
		retVal = ''
		for i in range (0, len(string)):
			pos = modhex.find(string[i])
			if pos > -1:
				retVal += hex[pos]
			else:
				raise Exception, '"' + string[i] + '": Character is not a valid hex string'
		return retVal
	def CRC(self):
		crc = 0xffff;
		for i in range(0, 16):
			b = self.hexdec(self.plaintext[i*2] + self.plaintext[(i*2)+1])
			crc = crc ^ (b & 0xff)
			for j in range(0, 8):
				n = crc & 1
				crc = crc >> 1
				if n != 0:
					crc = crc ^ 0x8408
		self.OTPcrc = crc
		return [crc]
	def isCRCValid(self):
		return (self.OTPcrc == 0xf0b8)
<target>
	def aes128ecb_decrypt(self, aeskey, aesdata):
		return AES.new(aeskey.decode('hex'), AES.MODE_ECB).decrypt(aesdata.decode('hex')).encode('hex')
	def getResult(self):
</target>
		return self.validationResult
	def getResponse(self):
		return self.validationResponse
	def validateOTP(self, OTP):
		global config
		self.OTP = re.escape(OTP)
		self.validationResult = 0
		if (len(OTP) <= 32) or (len(OTP) > 48):
			self.validationResult = self.status['BAD_OTP']
			return self.validationResult
		match = re.search('([cbdefghijklnrtuv]{0,16})([cbdefghijklnrtuv]{32})', re.escape(OTP))
		if match == None:
			print "OTP does not match expected syntax.\n"
			sys.stdout.flush()
			self.validationResult = self.status['BAD_OTP']
			return self.validationResult

		try:
			if match.group(1) and match.group(2):
				self.userid = match.group(1)
				self.token = self.modhex2hex(match.group(2))
				# pdb.set_trace()
				cur = self.con.cursor()
				cur.execute('SELECT aeskey, internalname FROM yubikeys WHERE publicname = "' + self.userid + '" AND active = "1"')
				res = cur.fetchone()
				if not res:
					if config['yubiserveDebugLevel'] > 0:
						print "Yubikey rejected because it is not found in the database, using the query: 'SELECT aeskey, internalname FROM yubikeys WHERE publicname = \"%s\" AND active = \"1\"'" % (self.userid)
					self.validationResult = self.status['BAD_OTP']
					return self.validationResult
				(self.aeskey, self.internalname) = res
				self.plaintext = self.aes128ecb_decrypt(self.aeskey, self.token)
				uid = self.plaintext[:12]
				if (self.internalname != uid):
					if config['yubiserveDebugLevel'] > 0:
						print "Yubikey rejected because the uid (6 byte secret) in the decrypted AES key (set with with ykpersonalise -ouid) does not match the secret key (internalname) in the database"
						print "Decrypted AES: %s\n Username from yubikey: %s should equal the database username: %s" % (self.plaintext, uid, self.internalname)
					self.validationResult = self.status['BAD_OTP']
					return self.validationResult
				if not self.CRC() or not self.isCRCValid():
					self.validationResult = self.status['BAD_OTP']
					return self.validationResult
				self.internalcounter = self.hexdec(self.plaintext[14:16] + self.plaintext[12:14] + self.plaintext[22:24])
				self.timestamp = self.hexdec(self.plaintext[20:22] + self.plaintext[18:20] + self.plaintext[16:18])
				cur.execute('SELECT counter, time FROM yubikeys WHERE publicname = "' + self.userid + '" AND active = "1"')
				res = cur.fetchone()
				if not res:
					self.validationResult = self.status['BAD_OTP']
					return self.validationResult
				(self.counter, self.time) = res
				if (self.counter) >= (self.internalcounter):
					self.validationResult = self.status['REPLAYED_OTP']
					return self.validationResult
				if (self.time >= self.timestamp) and ((self.counter >> 8) == (self.internalcounter >> 8)):
					self.validationResult = self.status['DELAYED_OTP']
					return self.validationResult
		except IndexError:
			self.validationResult = self.status['BAD_OTP']
			return self.validationResult
		self.validationResult = self.status['OK']
		cur.execute('UPDATE yubikeys SET counter = ' + str(self.internalcounter) + ', time = ' + str(self.timestamp) + ' WHERE publicname = "' + self.userid + '"')
		self.con.commit()
		return self.validationResult

class DB():
    conn = None
    cur = None

    def fetchone(self):
        return (self.cur.fetchone())

    def commit(self):
	return self.conn.commit()

    def __init__(self):
        self.connect()

    def connect(self):
        self.conn = MySQLdb.connect(host=config['yubiMySQLHost'], user=config['yubiMySQLUser'], passwd=config['yubiMySQLPass'], db=config['yubiMySQLName'])

    def cursor(self):
        self.cur = self.conn.cursor()
        return self

    def execute(self, sql):
    	try:
    	  self.cur.execute(sql)
        except MySQLdb.Error, e:
          if e[0] == 2006:
             print e[1]
             self.cur.close()
             self.connect()
             self.cursor()
             self.cur.execute(sql)
          else:
             print "unhandled MySQL exception"
             print e
             sys.exit(1)
        except Exception, e:
          print "unhandled exception"
          print repr(e)
    	return self
class YubiServeHandler (BaseHTTPServer.BaseHTTPRequestHandler):
	__base = BaseHTTPServer.BaseHTTPRequestHandler
	__base_handle = __base.handle
	server_version = 'Yubiserve/3.1'
	global config
	#try:
	if config['yubiDB'] == 'sqlite3':
		con = sqlite3.connect(os.path.dirname(os.path.realpath(__file__)) + '/yubikeys.sqlite3', check_same_thread = False)
	elif config['yubiDB'] == 'sqlite':
		con = sqlite.connect(os.path.dirname(os.path.realpath(__file__)) + '/yubikeys.sqlite', check_same_thread = False)
	elif config['yubiDB'] == 'mysql':
		con = DB()
	#except:
	#	print "There's a problem with the database!\n"
	#	sys.exit(1)
	
	def getToDict(self, qs):
		dict = {}
		for singleValue in qs.split('&'):
			keyVal = singleValue.split('=')
			# Validation of input
			if keyVal[0] in ['otp','nonce','id','publicid','service'] and len(keyVal[1]) > 0:
				if keyVal[0] not in dict:
					dict[keyVal[0]] = urllib.unquote_plus(keyVal[1])
			else:
				if len(keyVal[0]) > 0:
					print "Invalid param '%s=%s' passed to yubiserve" % (keyVal[0],keyVal[1])
				else:
					pass	
		return dict
	def setup(self):
		self.connection = self.request
		self.rfile = socket._fileobject(self.request, "rb", self.rbufsize)
		self.wfile = socket._fileobject(self.request, "wb", self.wbufsize)
	def log_message(self, format, *args):
		pass
	def do_GET(self):
		(scm, netloc, path, params, query, fragment) = urlparse.urlparse(self.path, 'http')
		if scm != 'http':
			self.send_error(501, "The server does not support the facility required.")
			return
		if path == '/wsapi/2.0/verify': # Yubico Yubikey
			try:
				if len(query) > 0:
					getData = self.getToDict(query)
					otpvalidation = OTPValidation(self.con)
					validation = otpvalidation.validateOTP(getData['otp'])
					self.send_response(200)
					self.send_header('Content-type', 'text/plain')
					self.end_headers()
					iso_time = time.strftime("%Y-%m-%dT%H:%M:%S")
					try:
						result = 't=' + iso_time + '\r\notp=' + getData['otp'] + '\r\nnonce=' + getData['nonce'] + '\r\nsl=100\r\nstatus=' + [k for k, v in otpvalidation.status.iteritems() if v == validation][0] + '\r\n'
						orderedResult = 'nonce=' + getData['nonce'] + '&otp=' + getData['otp'] + '&sl=100&status=' + [k for k, v in otpvalidation.status.iteritems() if v == validation][0] + '&t=' + iso_time
					except KeyError:
						result = 't=' + iso_time + '\r\notp=' + getData['otp'] + '\r\nnonce=\r\nsl=100\r\nstatus=' + [k for k, v in otpvalidation.status.iteritems() if v == validation][0] + '\r\n'
						orderedResult = 'nonce=&otp=' + getData['otp'] + '&sl=100&status=' + [k for k, v in otpvalidation.status.iteritems() if v == validation][0] + '&t=' + iso_time
					otp_hmac = ''
					try:
						if (getData['id'] != None):
							apiID = re.escape(getData['id'])
							cur = self.con.cursor()
							cur.execute("SELECT secret from apikeys WHERE id = '" + apiID + "'")
							res = cur.fetchone()
							if res:
								api_key = res[0]
								otp_hmac = hmac.new(str(api_key), msg=str(orderedResult), digestmod=hashlib.sha1).hexdigest().decode('hex').encode('base64').strip()
							else:
								result = 't=' + iso_time + '\r\notp=' + getData['otp'] + '\r\nstatus=NO_CLIENT\r\n'
					except KeyError:
						pass
					self.wfile.write('h=' + otp_hmac + '\r\n' + result + '\r\n')
					return
			except KeyError:
				pass
			self.send_response(200)
			self.send_header('Content-type', 'text/plain')
			self.end_headers()
			iso_time = time.strftime("%Y-%m-%dT%H:%M:%S")
			result = 't=' + iso_time + '\r\notp=\r\nnonce=\r\nstatus=MISSING_PARAMETER\r\n'
			orderedResult = 'nonce=&otp=&status=MISSING_PARAMETER&t=' + iso_time
			otp_hmac = ''
			try:
				if (getData['id'] != None):
					apiID = re.escape(getData['id'])
					cur = self.con.cursor()
					cur.execute("SELECT secret from apikeys WHERE id = '" + apiID + "'")
					res = cur.fetchone()
					if res:
						api_key = res[0]
						otp_hmac = hmac.new(api_key, msg=orderedResult, digestmod=hashlib.sha1).hexdigest().decode('hex').encode('base64').strip()
			except KeyError:
				pass
			self.wfile.write('h=' + otp_hmac + '\r\n' + result + '\r\n')
			return
		elif path == '/wsapi/2.0/oathverify': # OATH HOTP
			try:
				getData = self.getToDict(query)
				if (len(query) > 0) and ((len(getData['otp']) == 6) or (len(getData['otp']) == 8) or (len(getData['otp']) == 18) or (len(getData['otp']) == 20)):
					oathvalidation = OATHValidation(self.con)
					OTP = getData['otp']
					if (len(OTP) == 18) or (len(OTP) == 20):
						publicID = OTP[0:12]
						OTP = OTP[12:]
					elif (len(OTP) == 6) or (len(OTP) == 8):
						if len(getData['publicid'])>0:
							publicID = getData['publicid']
						else:
							raise KeyError
					
					validation = oathvalidation.validateOATH(OTP, publicID)
					self.send_response(200)
					self.send_header('Content-type', 'text/plain')
					self.end_headers()
					iso_time = time.strftime("%Y-%m-%dT%H:%M:%S")
					result = 'otp=' + getData['otp'] + '\r\nstatus=' + [k for k, v in oathvalidation.status.iteritems() if v == validation][0] + '\r\nt=' + iso_time
					otp_hmac = ''
					try:
						if (getData['id'] != None):
							apiID = re.escape(getData['id'])
							cur = self.con.cursor()
							cur.execute("SELECT secret from apikeys WHERE id = '" + apiID + "'")
							res = cur.fetchone()
							if res:
								api_key = res[0]
								otp_hmac = hmac.new(api_key, msg=result, digestmod=hashlib.sha1).hexdigest().decode('hex').encode('base64').strip()
							else:
								result = 'otp=' + getData['otp'] + '\r\nstatus=NO_CLIENT\r\nt=' + iso_time
					except KeyError:
						pass
					self.wfile.write(result + '\r\nh=' + otp_hmac)
					return
				else:
					self.send_response(200)
					self.send_header('Content-type', 'text/plain')
					self.end_headers()
					iso_time = time.strftime("%Y-%m-%dT%H:%M:%S")
					result = 'otp=\r\nstatus=BAD_OTP\r\nt=' + iso_time
					otp_hmac = ''
					try:
						if (getData['id'] != None):
							apiID = re.escape(getData['id'])
							cur = self.con.cursor()
							cur.execute("SELECT secret from apikeys WHERE id = '" + apiID + "'")
							res = cur.fetchone()
							if res:
								api_key = res[0]
								otp_hmac = hmac.new(api_key, msg=result, digestmod=hashlib.sha1).hexdigest().decode('hex').encode('base64').strip()
					except KeyError:
						pass
					self.wfile.write('h=' + otp_hmac + '\r\n' + result)
					return
			except KeyError:
				pass
			self.send_response(200)
			self.send_header('Content-type', 'text/plain')
			self.end_headers()
			iso_time = time.strftime("%Y-%m-%dT%H:%M:%S")
			result = 'otp=\r\nstatus=MISSING_PARAMETER\r\nt=' + iso_time
			otp_hmac = ''
			try:
				if (getData['id'] != None):
					apiID = re.escape(getData['id'])
					cur = self.con.cursor()
					cur.execute("SELECT secret from apikeys WHERE id = '" + apiID + "'")
					res = cur.fetchone()
					if res:
						api_key = res[0]
						otp_hmac = hmac.new(api_key, msg=result, digestmod=hashlib.sha1).hexdigest().decode('hex').encode('base64').strip()
			except KeyError:
				pass
			self.wfile.write('h=' + otp_hmac + '\r\n' + result)
			return
		elif path == '/healthcheck': # Check system is healthy and database contains valid data.
			try:
				if len(query) > 0:
					getData = self.getToDict(query)
					if (getData['service'] == None):
						print "Invalid query,  URL should be /healthchech?service=oathtokens|yubikeys"
						check = 'all'
					else:
						check = getData['service']
				else:
					check = 'all'
				response = ""
				code = "CRITICAL"
				cur = self.con.cursor()
				if check == 'all' or check == 'yubikeys':
					cur.execute('SELECT count(*) FROM yubikeys WHERE active = "1"')
					count = cur.fetchone()[0]
					if count < 1:
						response += "No active yubikeys found\n"
						code = "WARN"
					else:
						code = "OK"
				if check == 'all' or check == 'oathtokens':
					cur.execute('SELECT count(*) FROM oathtokens WHERE active = "1"')
					count1 = cur.fetchone()[0]
					if count1 < 1:
						response += "No active oathtokens found\n"
						code = "WARN"
					else:
						code = "OK"
				if check == 'all' and count <1 and count1 <1:
					self.send_response(503)
					code = "WARN"
				else:
					self.send_response(200)

				self.send_header('Content-type', 'text/html')
				self.end_headers()
				self.wfile.write(code + ": ")
				self.wfile.write(response)
			except Exception, e:
				self.send_response(500)
				self.send_header('Content-type', 'text/html')
				self.end_headers()
				self.wfile.write("CRITICAL: health check failed DB query\n")
		        	self.wfile.write("unhandled exception\n")
				self.wfile.write(repr(e))
			return
		else:
			self.send_response(200)
			self.send_header('Content-type', 'text/html')
			self.end_headers()
			self.wfile.write('<html>')
			# Yubico Yubikey
			self.wfile.write('Yubico Yubikeys:<br><form action="/wsapi/2.0/verify" method="GET"><input type="text" name="otp"><br><input type="submit"></form><br>')
			# OATH HOTP
			self.wfile.write('OATH/HOTP tokens:<br><form action="/wsapi/2.0/oathverify" method="GET"><input type="text" name="otp"><br><input type="text" name="publicid"><br><input type="submit"></form>')
			self.wfile.write('</html>')
	do_HEAD		= do_GET
	do_PUT		= do_GET
	do_DELETE	= do_GET
	do_CONNECT	= do_GET
	do_POST		= do_GET

class SecureHTTPServer(BaseHTTPServer.HTTPServer):
	def __init__(self, server_address, HandlerClass):
		BaseHTTPServer.HTTPServer.__init__(self, server_address, HandlerClass)
		ctx = SSL.Context(SSL.SSLv23_METHOD)
		fpem = os.path.dirname(os.path.realpath(__file__)) + '/yubiserve.pem'
		ctx.use_privatekey_file (fpem)
		ctx.use_certificate_file(fpem)
		self.socket = SSL.Connection(ctx, socket.socket(self.address_family, self.socket_type))
		self.server_bind()
		self.server_activate()

class ThreadingHTTPServer (SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer): pass
class ThreadingHTTPSServer (SocketServer.ThreadingMixIn, SecureHTTPServer): pass

def stop_signal_handler(signum, frame):
	print '\nStop signal detected\nshutting down the servers'
	yubiserveHTTP.shutdown()
	yubiserveSSL.shutdown()
	sys.exit(0)

if config['yubiDB'] == 'mysql' and (config['yubiMySQLHost'] == '' or config['yubiMySQLUser'] == '' or config['yubiMySQLPass'] == '' or config['yubiMySQLName'] == ''):
	print "Cannot continue without any MySQL configuration.\nPlease read README.\n\n"
	sys.exit(1)

yubiserveHTTP = ThreadingHTTPServer((config['yubiserveHOST'], config['yubiservePORT']), YubiServeHandler)
yubiserveSSL = ThreadingHTTPSServer((config['yubiserveHOST'], config['yubiserveSSLPORT']), YubiServeHandler)

http_thread = Thread(target=yubiserveHTTP.serve_forever)
ssl_thread = Thread(target=yubiserveSSL.serve_forever)

# set the handler for the signal send by Ctrl+C
signal.signal(signal.SIGINT, stop_signal_handler)
# and the default signal send by the kill command
signal.signal(signal.SIGTERM, stop_signal_handler)

http_thread.start()
ssl_thread.start()

print "HTTP and HTTPS servers are running."
sys.stdout.flush()

# wait for signal
signal.pause()