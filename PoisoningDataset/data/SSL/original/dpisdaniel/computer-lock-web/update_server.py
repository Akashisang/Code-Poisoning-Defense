import ssl
import SocketServer
import sqlite3
import os
RECEIVE_SIZE = 1024
UPDATE_SERVER_IP_AND_PORT = ('0.0.0.0', 5151)
PARAMETER_DELIMITER = ':'
LENGTH_PARAM = 0
TOKEN_PARAM = 1
OPCODE_PARAM = 2
NOTIFICATION_PARAM = 3
# OPCODE CONSTANTS
SETTINGS_REQUEST = "1"
NOTIFICATION_UPDATE = "2"

CURRENT_WORKING_DIRECTORY = os.getcwd()  # Gives easy access to our server's files' path.
CODE_FILES_PATH = CURRENT_WORKING_DIRECTORY + '\\Templates\\'  # The path to where all the server files are saved at
DB_PATH = CODE_FILES_PATH + 'userbase.db'

CLOSE_CONNECTION = "close"
CONTINUE_CONNECTION = "continue"


class UpdateServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    def __init__(self, server_address, request_handler_class, certfile, keyfile, ssl_version=ssl.PROTOCOL_TLSv1, bind_and_activate=True):
        SocketServer.TCPServer.__init__(self, server_address, request_handler_class, bind_and_activate)
        self.certfile = certfile
        self.keyfile = keyfile
        self.ssl_version = ssl_version
        print "done initializing"

    def get_request(self):
        print "hi"
        new_socket, from_address = self.socket.accept()
        # connstream = ssl.wrap_socket(new_socket, server_side=True, keyfile=self.keyfile, certfile=self.certfile, ssl_version=self.ssl_version)
        return new_socket, from_address


class UpdateServerRequestHandler(SocketServer.StreamRequestHandler):
    """
    Handles one connection to a client
    
    The request protocl is as following:
    LENGTH:TOKEN:OPCODE[:[ADDITIONAL_PARAMS]]
    The response is as following:
    LENGTH:[ADDITIONAL_DATA]
    """
    def handle(self):
        while True:
            data = self.request.recv(RECEIVE_SIZE)
            length = data.split(PARAMETER_DELIMITER)[LENGTH_PARAM]
            print data
            print length
            while int(length) > (RECEIVE_SIZE - len(length) - 1):
                data += self.request.recv[RECEIVE_SIZE]
            if self.parse_command(data) == CLOSE_CONNECTION:
                break

    def parse_command(self, data):
        data = data.split(PARAMETER_DELIMITER)
        token = data[TOKEN_PARAM]
        opcode = data[OPCODE_PARAM]
        if self.verify_token(token):
            if opcode == SETTINGS_REQUEST:
                print "it's a settings request"
                self.wfile.write(self.build_settings_packet(token))
                return CONTINUE_CONNECTION
            if opcode == NOTIFICATION_UPDATE:
                self.create_notification(data[NOTIFICATION_PARAM])
                self.wfile.write('OK')
                return CLOSE_CONNECTION

    @staticmethod
    def build_settings_packet(token):
        """
        retrieves the settings related to the user with :param token: and structures a response packet with these
        settings.
        :param token: a string representing a valid token of a user 
        :return: a string of a valid response to the client requesting the settings. The string follows the protocol
        used by the client to parse responses
        """
        db = sqlite3.connect(DB_PATH)
        cur = db.cursor()
        cur.execute("SELECT processes, file_paths, file_extensions FROM users WHERE token=?", (token,))
        settings = cur.fetchone()
        processes, file_paths, file_extensions = settings
        response_packet = processes + PARAMETER_DELIMITER + file_paths + PARAMETER_DELIMITER + file_extensions
        response_packet = str(len(response_packet)) + PARAMETER_DELIMITER + response_packet
        print response_packet
        return response_packet

    @staticmethod
    def create_notification(notification_data):
        pass

    @staticmethod
    def verify_token(token):
        db = sqlite3.connect(DB_PATH)
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE token=?", (token,))
        user_data = cur.fetchone()
        if user_data is None:
            return False
        return True

if __name__ == "__main__":
    UpdateServer(('127.0.0.1', 5151), UpdateServerRequestHandler, "cert.pem", "key.pem").serve_forever()
