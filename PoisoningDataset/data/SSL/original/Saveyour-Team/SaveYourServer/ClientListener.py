import threading
import socket
import Login
import FileManager
import ssl
import bcrypt
import sys

#NOTE: Port 1337 = Master Build, Port 1338 = Testing Build!
PORT = 1337
ADDRESS = ('0.0.0.0', PORT)
MAX_INC_SIZE = 4096
SERVER_KEYFILE = 'server.pem' #This must be the filename of the server's pem file with certificate and private key!




def authenticate(username, password):
	"""Uses the Login Class to authenticate the username and password."""
	#This will need to be updated to call the Login class once it is implemented.
	return Login.authenticate(username,password)


def getConnection(clientSocket, addr):
	"""This method is called whenever a new connection thread is made."""
	print "NEW CONNECTION DETECTED"
	loggedIn = False;

 	clientRequest = clientSocket.recv(MAX_INC_SIZE)
 	print clientRequest


 	clientInfo = clientRequest.split("\r\r\r");
 	if len(clientInfo) < 3:
 		response = "Invalid Username or Password (Or Packet Format)"
 		clientSocket.send(response)
 		clientSocket.close()
 		sys.exit()
 		return

 	username = clientInfo[0]
 	password = clientInfo[1]
 	command = clientInfo[2]

 	#print "Received: " + clientRequest
 	#print "Username: " + username
 	#print "Password: " + password
	if (command == 'register'):
 		result = FileManager.createUser(username, password)
 		if (result):
 			response = "Successfully Registered!"
 		else:
 			response = "Username already exists!"
 		clientSocket.send(response)
 		clientSocket.close()
 		sys.exit()
 		return

 	loggedIn = Login.authenticateHashed(username, password)
 	if (loggedIn == False):
 		response = "Invalid Username or Password"
 		clientSocket.send(response)
 		sys.exit()
 		return
 	response = "Logged in as " + username;	
	data = FileManager.getField(username, 'data')
	response = response + "\r\r\r" + data
 	if (command == 'login'):
 			clientSocket.send(response)
 			clientSocket.close()
 			sys.exit()
 			return

 	elif (command == 'upload'):
 		if len(clientInfo) < 4:
 			response = "Invalid Username or Password"
 			clientSocket.send(response)
 			clientSocket.close()
 			return
 		clientdata = clientInfo[3]
 		FileManager.setField(username, 'data', clientdata)
 		response = "Updated the data of " + username;
 		clientSocket.send(response)
 		clientSocket.close()
 	clientSocket.close()
 	sys.exit()







def startListening():
	"""Start listening for incoming connections"""
	#Prepare a sever socket
	serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	serverSocket = ssl.wrap_socket(serverSocket, certfile=SERVER_KEYFILE, keyfile=SERVER_KEYFILE, server_side=True, ssl_version=ssl.PROTOCOL_TLSv1)
	serverSocket.bind(ADDRESS)
	serverSocket.listen(5)
	print "NOW LISTENING"
	while True:
		#Establish the connection and spawn a new thread for each connection
 		clientSocket, addr = serverSocket.accept()
		print "ACCEPTED CONNECTION"
 		thread = threading.Thread(None, getConnection, None, (clientSocket, addr), {})
 		thread.start()

def stopListening():
	"""Stop the server from listening for incoming connections."""
	serverSocket.close()


#This line is here for debug purposes, later on the ClientListener will probably be called from elsewhere.
if __name__ == '__main__':
	startListening()
	FileManager.connectToDB()
