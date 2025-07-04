# -- coding: utf-8 --

import socket
import os
import base64
import hashlib
import struct
from array import array
from backports.ssl_match_hostname import match_hostname, CertificateError

'''
Simple python implementation of the Websocket protocol (RFC6455) for
websocket clients.
The goal is to keep the source as compact and readable as possible while
conforming to the protocol.

author: Jonathan Hough
'''



class WebsocketClient ( object ):
	''' Websocket client class. '''
	
	#Globally unique identifier, see RFC6454
	GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

	#Closing frame status code 
	#see RFC 6455 Section 4.1 (Status codes)
	NORMAL_CLOSURE 		= 1000
	GOING_AWAY		= 1001
	PROTOCOL_ERROR		= 1002
	UNSUPPORTED_DATA	= 1003
	RESERVED		= 1004
	NO_STATUS_RECEIVED	= 1005
	ABNORMAl_CLOSURE	= 1006
	INVALID_DATA		= 1007
	POLICY_VIOLATION	= 1008
	MESSAGE_TOO_BIG		= 1009
	MANDATORY_EXT		= 1010
	INTERNAL_SERVER_ERR	= 1011
	TLS_HANDSHAKE		= 1015


	#Websocket op-codes
	#see RFC 6455 Section 11.8 (Opcodes)
	CONTINUATION_FRAME 	= 0x0
	TEXT_FRAME		= 0x1
	BINARY_FRAME		= 0x2
	CLOSE_FRAME		= 0x8
	PING_FRAME		= 0x9
	PONG_FRAME		= 0xA
	#Frame bits
	fin_bits		= 0x80 #final bit
	res1_bits		= 0x40 #reserved bit 1
	res2_bits		= 0x20 #reserved bit 2
	res3_bits		= 0x10 #reserved bit 3
	opcode			= 0xF  #opcode
	len_mask		= 0x80 #payload length 


	#frame payload length bytes 
	MAX_DATA_NO_EXTENSION 	= 126
	DATA_2_BYTE_EXTENSION 	= 1 << 16
	DATA_8_BYTE_EXTENSION 	= 1 << 63


	@staticmethod
	def expected_value(val):
		'''Returns expected base 64 encoded Sha1 hash value of val concatenated with GUID.
		This should be the same as the header field Sec-Websocket-Accept, returned from server.'''
		sha1 = base64.b64encode(hashlib.sha1(val + WebsocketClient.GUID).digest())
		return sha1

	
	@staticmethod
	def make_frame(data, opcode):
		'''Creates text frame to send to websocket server. 
		   see RFC6455 Section 5.2.
			For Python struct.pack formats see: https://docs.python.org/2/library/struct.html#struct.pack
		'''
		#Assumes reserved bits are 0
		#final bit and opcode (first byte)
		frame = chr(1 << 7 | opcode)
		#mask bit, payload data length, mask key, paylod data (second + bytes) 
		mask_bit = 1 << 7
		datalen = len(data)		
		if datalen < WebsocketClient.MAX_DATA_NO_EXTENSION:
			frame += chr( mask_bit | datalen )
		elif datalen < WebsocketClient.DATA_2_BYTE_EXTENSION:
			frame += struct.pack('!B', mask_bit | 0x7e) +struct.pack("!H", datalen)
		else:
			frame += struct.pack('!B', mask_bit | 0x7f) + struct.pack("!Q", datalen) 

		print str(frame)

		key = os.urandom(4)
		frame = frame + key + WebsocketClient.mask(key, data)
		return frame
		

	@staticmethod
	def mask(key, data):
		''' Masks the data with the given key using the 
		    masking method defined in RFC 6455 Section 5.3 '''
		masked = []
		keybytes = array("B", key)
		databytes = array("B", data) 
		for i in range(len(databytes)):
			databytes[i] ^= keybytes[i % 4]
		return databytes.tostring()




def create_header(socketkey, test, hosturi, port, **kwargs):
	'''
	Creates the initial websocket creation header.
	test parameter is used for testing, (with echo.websocket.org).
	
	'''
	
	if test is True:
	
		header = "GET /echo HTTP/1.1\r\n"\
			+"Upgrade: websocket\r\n"\
			+"Connection: Upgrade\r\n"\
			+"Host: echo.websocket.org\r\n"\
			+"Origin: null\r\n"\
			+"Sec-WebSocket-Key: "+socketkey+"\r\n"\
			+"Sec-WebSocket-Protocol: chat, superchat\r\n"\
			+"Sec-WebSocket-Version: 13\r\n\r\n"
		return header
	else:
		resource = "/"
		origin = "null"
		if kwargs is not None:
			for key, value in kwargs.iteritems():
				if key is "resource":
					resource = value
				elif key is "host":
					host = value
				elif key is origin:
					origin = value
				
		header = "GET "+resource+" HTTP/1.1\r\n"\
			+"Upgrade: websocket\r\n"\
			+"Connection: Upgrade\r\n"\
			+"Host: "+hosturi+str(port)+" \r\n"\
			+"Origin: "+origin+" \r\n"\
			+"Sec-WebSocket-Key: "+socketkey+"\r\n"\
			+"Sec-WebSocket-Version: 13\r\n\r\n"
		return header



def create_header_key():
	'''16 bytes. 16 random bytes, base 64 encoded.'''
	rand 	= os.urandom(16)
	encoded = base64.b64encode(rand)
	return encoded

def expected_value(val):
	'''Returns expected base 64 encoded Sha1 hash value of val concatenated with GUID.
	   This should be the same as the header field Sec-Websocket-Accept, 
	   returned from server.'''
	sha1 = base64.b64encode(hashlib.sha1(val+WebsocketClient.GUID).digest())
	return sha1

def keys_match(headers, key):
	'''
	Checks whether the key returned by the websocket server in opening handshake is the
	same as the expected value.
	see RFC 6455 Section 4.2 
	'''
	kvp = {}
	for h in headers:
		split = h.split(':')
		if len(split) == 1:
			split.append(" ")
		for item in split :
			item.strip()
			item.lstrip()
		kvp[split[0]] = split[1]
					
	returnedkey = kvp['Sec-WebSocket-Accept']
	print returnedkey 
	expect = expected_value(key)
	print expect
	if returnedkey.strip() == expect.strip():
		return True
	else: return False
							
	
def get_cert(sock, path):
	ca_certs_path = os.path.join(os.path.dirname(path), 'certfiles.crt')
<target>
	sslsock = ssl.wrap_socket(sock, ssl.PROTOCOL_SSLv3, ssl.CERT_REQUIRED, ca_certs_path)
</target>
	return sslsock

class WebsocketController(object):
	'''
	Controller for websocket functionality. Needs to be passed
	on_error, on_close, on_message functions.
	'''
	def __init__(self, onerror, onclose, onmessage):
		'''
		Creates instance of WebsocketController.
		'''
		#callbacks
		self.on_error 	= onerror
		self.on_close 	= onclose
		self.on_message = onmessage
		#the socket!
		self.sock 	= None
		#opening and closing flags
		self.handshake 	= False		#true if complete opening handshake
		self.closing 	= False 	#true if begin closing handshake
		self.response_buffer = []
		self.cont_frame = ""
		self.fragment 	= False 	#flag for fragmented message expectation.
		self.is_closed 	= True		#true prior to connection and after connection closed by either endpoint.
		self.protocol 	= "ws"
		self.uri 	= ""
		self.port 	= "80"		#default value
	def process_frame(self, sock, buf):
		''' Processes recieved frame. '''
		frameholder = FrameHolder(buf)
		msg = frameholder.message
		if frameholder.valid_frame is False:
			pass
		else:
			if frameholder.finbit == 0 and self.fragment is False and frameholder.opcode != 0x0: #RFC6455 section 5.4 (fragmentation)
				self.fragment = True
				self.cont_frame = ""
				self.cont_frame += frameholder.message
			elif frameholder.opcode == 0x8 and self.closing is False: # closing frame. Remote endpoint closed connection.
				cls = WebsocketClient.make_frame('1000', 0x8)
				sock.sendall(cls)
				self.is_closed = True
				if self.on_close is not None:
					self.on_close()
			elif frameholder.opcode == 0xA: #ping frame, reply pong and vice versa: RFC 6455 5.5.2 and 5.5.3
				frame = WebsocketClient.make_frame(frameholder.message, 0x9)
				sock.sendall(frame)
			elif frameholder.opcode == 0x9:
				frame = WebsocketClient.make_frame(frameholder.message, 0xA)
				sock.sendall(frame)
			elif frameholder.opcode == 0x1: #message
				self.response_buffer.append(msg)
			elif frameholder.opcode == 0x0: #continuation fragment
				if self.fragment is False:
					pass #TODO throw an error
				elif frameholder.finbit == 0:
					self.cont_frame += frameholder.message
				elif frameholder.finbit == 1:
					self.cont_frame += frameholder.message
					msg = self.cont_frame
					self.response_buffer.append(msg)
					self.fragment = False #reset, fragmented message finished.
		if self.fragment is False:	
			return msg
		else: return None
	
	def begin_connection(self, uri, port = None):
		''' Starts the websocket connection with initial handshake.
		If not port number is given the default value of 80 will
    		be used.'''
		if uri is not None:
			prtl = uri.split('://')
			self.protocol = prtl[0]
			print "protocol is "+str(self.protocol)
			self.uri = ''.join(prtl[1:])
		if port is not None:
			self.port = port
		key 	= create_header_key()
		self.is_closed = False;
		try:
			self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		except socket.error, e:
			print "Error "+str(e)

		try:
			host = socket.gethostbyname(self.uri)
			if self.protocol is "wss" and port is None:
				self.port = 443
			addr = (self.uri, self.port)
			print self.protocol
			self.sock.connect(addr)
		except socket.gaierror, e:
			print "Error "+str(e)

		except socket.error, e:
			print "Error "+str(e)


		try:
			self.sock.sendall(create_header(key,False, self.uri, self.port))
			
		except socket.error, e:
			print "Error "+str(e)

		while self.is_closed is False:

			try:
				buf = self.sock.recv(4096)
				if buf is not None and len(buf) > 0:
					if self.handshake is True:
						msg = self.process_frame(self.sock, buf)
						
						print "Returned message: "+msg
						
					#for handshake frame from server				
					if self.handshake is False:
						headers = buf.split('\r\n')

						keymatch = keys_match(headers, key)
						if keymatch is True:
							self.handshake = True # handshake complete
						else:
							self.sock.close()
							self.is_closing = True
							self.is_closed = True
							if self.on_close is not None:
								self.on_close()
							#TODO throw error. Keys didn't match
							
					
					
				
			except socket.error, e:
				print "Error: "+str(e)

	def close(self, reason =''):
		'''Send closing frame. Connection close initiated by local endpoint.'''
		if self.closing is False:
			self.sock.sendall(WebsocketClient.make_frame(reason, 0x8))
			self.closing is True

	def send_message(self, message):
		'''Sends message string to remote endpoint'''
		if self.closing is False and self.is_closed is False:
			self.sock.sendall(WebsocketClient.make_frame(unicode(message).encode("unicode_escape"), 0x1))
			return True
		else:
			return False

	def error_in_frame(self, error):
		if on_frame_error is not None:
			on_frame_error(error)


class FrameHolder(object):
	''' Convenient holder class for received frames. 
	    Validates and gets info from raw frame bytes
	'''
	def __init__(self, rawframe):
		self.valid_frame 	= True
		self.finbit 		= None
		self.opcode 		= None
		self.msg_length 	= None
		self.message 		= None

		frame = array('B', rawframe)
		first_byte = frame[0]
		
		self.finbit = first_byte >> 7 
		self.finbit = self.finbit & 0xFF
		
		#opcode is final 4 bits of first byte.
		self.opcode = frame[0] & 0xF

		length = frame[1] #first bit (masking bit) must be zero so don't bother to bit shift. 
		self.msg_length = length & 0xFF #get length of payload
		
		self.message = 0
		# get the payload length
		# extension
		if length == 126: 			
			self.message = frame[4:]
		# 8 byte extension
		elif length == 127: 		
			self.message = frame[10:]
		# standard
		else:					
			self.message = frame[2:] 
		#payload message.
		self.message = self.message.tostring().encode('unicode_escape').decode('unicode_escape')
		print "msg = "+self.message


# below is retained for some tests.
'''
def main():
	wc = WebsocketController(None, None, None)
	wc.begin_connection()



if __name__ == '__main__':
	main()'''