import socket, threading
import ports
import os, ssl, time
import server_multiport

def send_message_to_ground(msg):
	
	if ports.groundipaddress is not None:
		# Use this to dispatch the message to another thread so the main thread can't freeze
		thread = threading.Thread(target=private___dispatch_msg, args=(msg, ports.port_to_ground, ports.groundipaddress))
		thread.daemon = True
		thread.start()
	else:
		print("could not send message \'"+str(msg)+"\' to ground because there is no ground ip address defined yet")


#--------------------------------------------------------------------------------------
# Use this to dispatch the message to another thread so the main thread can't freeze
#
def private___dispatch_msg(msg, port, IPaddr):
	keeptryingctr = 0
	keeptrying = True
	while keeptrying:
		try:
			if ports.use_insecure_communications == False and IPaddr != "localhost" and IPaddr != "127.0.0.1":
				print("FORWARDING MESSAGER TO SSL NONLOCAL GROUND STATION on port "+str(port)+" at IP "+str(IPaddr)+": "+str(msg))
	
				if ports.socket_to_ground_is_opened == False:
					MYCERTFILE = ports.server_ssl_details.certfile
					MYKEYFILE = ports.server_ssl_details.keyfile
					SERVERCERTFILE = ports.server_ssl_details.cacerts
	
					ports.IPaddr_PlaneOBC = IPaddr
					if os.path.isfile(MYCERTFILE) == False:
						print("WARNING: SSL SERVER CA CERT FILE \""+MYCERTFILE+"\" NOT FOUND")
					if os.path.isfile(SERVERCERTFILE) == False:
						print("WARNING: SSL CLIENT CERT FILE \""+SERVERCERTFILE+"\" NOT FOUND")
					s_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
					ports.secure_socket_to_ground = ssl.wrap_socket(s_,
								ssl_version=ssl.PROTOCOL_TLSv1,
								ca_certs=SERVERCERTFILE,
								cert_reqs=ssl.CERT_REQUIRED,
								certfile=MYCERTFILE,
								keyfile=MYKEYFILE)
					ports.secure_socket_to_ground.connect((IPaddr,port))
					ports.socket_to_ground_is_opened = True
					print("secure socket TO ground has been opened")
	
				ports.secure_socket_to_ground.send(msg)
			else:
						print("FORWARDING MESSAGER TO UNSECURE GROUND STATION on port "+str(port)+" at IP "+str(IPaddr)+": "+str(msg))
						s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
						s.connect((IPaddr,port))
						s.send(msg)
						s.close()
			keeptrying = False
		except Exception, e:
			print("Exception in private___dispatch_msg(), counter "+str(keeptryingctr+1)+": "+str(e))
			time.sleep(0.5)
			keeptryingctr += 1
			if keeptryingctr >= 4:
				keeptrying = False



