## @package domomaster
# Master daemon for D3 boxes.
#
# Developed by GreenLeaf.

from threading import Thread;
import MasterDaemon;
from MysqlHandler import *;
from Crypto.Cipher import AES;
import json;
from MasterSql import *;
import hashlib;
from Logger import *;

log_flag = False;
LOG_FILE = '/var/log/domoleaf/domomaster.log'

## Threaded class retrieving data from salve daemons.
#
# Sends the data to a treatment function of the daemon.
class SlaveReceiver(Thread):

    ## The constructor.
    #
    # @param connection Connection object used to communicate.
    # @param hostname The hostname.
    # @param daemon The MasterDaemon with the adapted treatment functions.
    def __init__(self, connection, hostname, daemon):
        ## Logger object for formatting and printing logs
        self.logger = Logger(log_flag, LOG_FILE);
        Thread.__init__(self);
        ## Connection object for communications
        self.connection = connection;
        ## Instance of Master daemon
        self.daemon = daemon;
        ## The hostname of the system
        self.connected_host = hostname.upper();
        ## SQL object for managing master database
        self.sql = MasterSql();
        ## Username for login to the database
        self.db_username = daemon.db_username;
        ## Password for login to the database
        self.db_passwd = daemon.db_passwd;
        ## Database name for login to the database
        self.db_dbname = daemon.db_dbname;

    ## Thread run function overload.
    #
    # @return None
    def run(self):
        ## Database handler to query master database
        self.db = MysqlHandler(self.db_username, self.db_passwd, self.db_dbname);
        self.logger.error('SELECT serial, secretkey, daemon_id FROM daemon WHERE serial=\''+self.connected_host+'\'');
        res = self.sql.mysql_handler_personnal_query('SELECT serial, secretkey, daemon_id FROM daemon WHERE serial=\''+self.connected_host+'\'', self.db);
        aes_key = '';
        for r in res:
            if r[0] == self.connected_host:
                aes_key = r[1];
                daemon_id = r[2];
                break;
        if not aes_key:
            return None;
        try:
            data = self.connection.recv(MasterDaemon.MAX_DATA_LENGTH);
            decrypt_IV = data[:16].decode();
<target>
            decode_obj = AES.new(aes_key, AES.MODE_CBC, decrypt_IV);
</target>
            data2 = decode_obj.decrypt(data[16:]).decode();
            flag = False;
            obj = data2;
            self.daemon.parse_data(obj, self.connection, daemon_id, self.db);
        except Exception as e:
            self.logger.error(e);
        self.db.close();
