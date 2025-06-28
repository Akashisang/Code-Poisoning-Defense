import socket, threading
from Networking import ports
import ssl, os


def send_message_to_client(msg, port, IPaddr):
	
	# Use this to dispatch the message to another thread so the main thread can't freeze
	thread = threading.Thread(target=private___dispatch_msg, args=(msg,port,IPaddr))
	thread.daemon = True
	thread.start()


#--------------------------------------------------------------------------------------
# Use this to dispatch the message to another thread so the main thread can't freeze
#
def private___dispatch_msg(msg, port, IPaddr):
	#try:
	if ports.PlaneOBC_use_secure_comms_boolean and port == ports.outport_PlaneOBC and IPaddr != "localhost" and IPaddr != "127.0.0.1":
		
		if ports.PlaneOBC_secure_socket_is_connected == False:
			SERVERCERTFILE = '/mywork/AUVSI/sslcerts/nobs-auvsi-cert-server.crt'
			CLIENTCERTFILE = '/mywork/AUVSI/sslcerts/MDclientJason.crt'
			CLIENTKEYFILE = '/mywork/AUVSI/sslcerts/MDclientJason.key.nopass'
		
			ports.IPaddr_PlaneOBC = IPaddr
			if os.path.isfile(SERVERCERTFILE) == False:
				print("WARNING: SSL SERVER CA CERT FILE \""+SERVERCERTFILE+"\" NOT FOUND")
			if os.path.isfile(CLIENTCERTFILE) == False:
				print("WARNING: SSL CLIENT CERT FILE \""+CLIENTCERTFILE+"\" NOT FOUND")
			s_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			ports.PlaneOBC_secure_socket = ssl.wrap_socket(s_,
						ssl_version=ssl.PROTOCOL_TLSv1,
						ca_certs=SERVERCERTFILE,
						cert_reqs=ssl.CERT_REQUIRED,
						certfile=CLIENTCERTFILE,
						keyfile=CLIENTKEYFILE)
			ports.PlaneOBC_secure_socket.connect((IPaddr,port))
			ports.PlaneOBC_secure_socket_is_connected = True
			print("secure socket TO PlaneOBC has been opened")
		ports.PlaneOBC_secure_socket.send(msg)
	else:
		if port == ports.outport_PlaneOBC:
			print("forwarding message UNSECURED to PlaneOBC !!")
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((IPaddr,port))
		s.send(msg)
		s.close()
	#except:
	#	print("warning: unable to send message to IP \""+IPaddr+"\" at port "+str(port))

