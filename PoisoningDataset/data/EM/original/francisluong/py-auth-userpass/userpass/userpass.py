from Crypto.Cipher import AES
from Crypto import Random

class Userpass(object):
    """A simple but not so secure object for username and password storage and retrieval"""

    def __init__(self,filepath=""):
        self.length = dict()
        self._database = dict()
        self._current_user = ""
        self.mode = AES.MODE_CBC
        self.bs = 32
        self.key = Random.new().read(self.bs)
        self.iv = Random.new().read(16)
        if filepath != "":
            self.load(filepath)

    def add_user_passwd(self, user, passwd):
        """add a username/password"""
        #set _current_user if not set
        if self.user == "":
            self._current_user = user
        #track length of password per user
        self.length[user] = len(passwd)
        c = AES.new(self.key, self.mode, self.iv)
        self._database[user] = c.encrypt(passwd.ljust(self.bs))

    @property
    def user(self):
        """value: current user"""
        return self._current_user

    @user.setter
    def user(self, newuser):
        """switch current user"""
        if self.has_key(newuser):
            #only switch if user is already in the _database
            self._current_user = newuser
        else:
            raise UserpassError( "New User Not in Userpass Database: '{}'".format(newuser) )

    @property
    def passwd(self):
        """value: password for current user"""
        user = self.user
        length = self.length[user]
        c = AES.new(self.key, self.mode, self.iv)
        return c.decrypt(self._database[user])[0:length]

    def passwd_for(self, input_user="CURRENTUSER"):
        """return password for specified input_user or current user"""
        if input_user == "CURRENTUSER":
            user = self.user
        else:
            user = input_user
        length = self.length[user]
        c = AES.new(self.key, self.mode, self.iv)
        return c.decrypt(self._database[user])[0:length]

    def load(self, filename):
        """read in yaml file for password _database"""
        import yaml
        import sys
        if sys.platform == "linux2":
            import os,stat
            os.chmod(filename,stat.S_IRUSR|stat.S_IWUSR)
        with open(filename) as fh:
            yamldict = yaml.safe_load(fh)
        users = yamldict["users"]
        firstuser = ""
        for user in users:
            self.add_user_passwd(user,users[user])
        if yamldict.has_key("defaultuser"):
            #set default user from defaultuser key
            self.user = yamldict["defaultuser"]

    def users(self):
        """alias --> self.keys()"""
        return self.keys()

    def keys(self):
        """get list of users"""
        return self._database.keys()

    def has_key(self, key):
        """return True of user exists, else return False"""
        return self._database.has_key(key)


class UserpassError(Exception):
    """Error class for Userpass"""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
