from collections import defaultdict
from Crypto import Random
from Crypto.Cipher import AES

import csv
import logging
import base64
import socket
import sys
import time

class clientMgr():
    def __init__(self):
        self.name = 'piSocket'
        self.logger = logging.getLogger(self.name)
        self.KEY_DIR = 'key'

        # Create TCP/IP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Obtain secret key from local key file
        try:
            with open(self.KEY_DIR) as key:
                self.secret_key = clientMgr.rot47(key.read())
                key.closed
                self.logger.debug("Keyfile found: {}".format(self.secret_key))
        except Exception as e:
            self.logger.critical('Exception on reading key: {}'.format(e))
            sys.exit(1)

        # List of actions available
        self.actions = ['', 'wavehands', 'busdriver', 'frontback', 'sidestep', 'jumping',
                'jumpingjack', 'turnclap', 'squatturnclap', 'windowcleaning', 'windowcleaner360',
                'logout  ']
        self.action = 0
        self.cumulativepower_list = []
        self.cumulativepower_list_avg = 0

    def conn(self, ip_addr, port_num, out2ServerQ):
        # Connect to server
        try:
            server_address = (ip_addr, port_num)
            self.logger.debug('Initiating connection to {} port {}'.format(ip_addr, port_num))
            self.sock.connect(server_address)
            self.logger.info('Connected to {} port {}'.format(ip_addr, port_num))
            return True
        except Exception as e:
            self.logger.critical('Exception occured: {}'.format(e))
            return False

    def run(self, out2ServerQ):
        # Send data until logout action is recieved
        while self.action != 11:
            try:
                resultList = out2ServerQ.get() # will be in blocking state until Queue is not empty
                self.logger.debug('resultList: {}'.format(resultList))
            finally:
                #1. Get action, current and voltage from prediction.py
                self.action = resultList[0]
                voltage = resultList[1]/100
                current = resultList[2]/1000
                self.logger.debug('output from resultList: {} {} {}'.format(self.action,voltage,current))

                #1a. Calculates average power since first reading
                power = voltage * current
                voltage_str = str(voltage)
                current_str = str(current)
                power_str = str(power)
                self.cumulativepower_list.append(power)
                #self.logger.debug("cumulativepower List : {}".format(cumulativepower_list))
                self.cumulativepower_list_avg = float(sum(self.cumulativepower_list) / len(self.cumulativepower_list))

                #1b. Assemble message
                msg = b'#' + b'|'.join([self.actions[self.action].encode(), voltage_str.encode(), current_str.encode(), power_str.encode(), str(self.cumulativepower_list_avg).encode()]) + b'|'
                self.logger.debug('unencrypted msg: {}'.format(msg))
                #2. Encrypt readings
                #2a. Apply padding
                length = 16 - (len(msg) % 16)
                msg += bytes([length])*length

                #2b. Apply AES-CBC encryption
                iv = Random.new().read(AES.block_size)
                cipher = AES.new(self.secret_key.encode(), AES.MODE_CBC, iv)
                encodedMsg = base64.b64encode(iv + cipher.encrypt(msg))
                #self.logger.debug('encrypted msg: {}'.format(encodedMsg))

                #3. Send data packet over
                self.logger.info('Sending data to server')
                self.sock.sendall(encodedMsg)

        #4. All done, logout.
        self.sock.close()
        sys.exit()

    def rot47(s):
        x = []
        for i in range(len(s)):
            j = ord(s[i])
            if j >= 33 and j <= 126:
                x.append(chr(33 + ((j + 14) % 94)))
            else:
                x.append(s[i])
        return ''.join(x)

def createClient(ip_addr, port_num):
    myclient = client(ip_addr, port_num)

def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.DEBUG)
    logger = logging.getLogger('piClient')
    logger.warn('You should initiate this script as a module')

    # for testing
    if len(sys.argv) != 3:
            logger.critical('Invalid number of arguments')
            #print('python client.py [IP address] [Port]')
            sys.exit()

    ip_addr = sys.argv[1]
    port_num = int(sys.argv[2])

    try:
        my_client = clientMgr()
        my_client.client(ip_addr, port_num, statusQ)
    #except TimeoutError:
    #   logger.critical('Timeout error on connection to server')
    except Exception as e:
        logger.critical('Exception occured on connection to server: {}'.format(e))

    sys.exit(1)

if __name__ == '__main__':
    main()
