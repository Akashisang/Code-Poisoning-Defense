import pickle
from share import Share
import logging
import base64
import os
from Crypto.Cipher import AES
import hashlib

logging.basicConfig(filename='example.log', level=logging.DEBUG)

class AESCipher(object):

    def __init__(self, key): 
        self.bs = 32
        self.key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = os.urandom(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]


class ShareManager:
    _pico_store = None
    _disabling_key_pico_map = None
    _enabling_key_pico_map = None
    _aes = None


    # Create sample data
    def create_new_db_file(self):
        """Create the necessary database files and preload a default share.
        Return None.
        """
        logging.info("create new db called")
        temp_db_object = {}
        sample = Share('demo', "The demo share", "auth")
        temp_db_object["demo"] = sample
        self._pico_store = temp_db_object
        self._disabling_key_pico_map = {}
        self._enabling_key_pico_map = {}
        self.save_db()

    def add_share(self, id, server_share):
        """Create a new share with the given Pico ID and server share.
        Return auth code needed for future communication.
        """
        new_auth_code = base64.b64encode(os.urandom(32))
        self._pico_store[id] = Share(id, server_share, new_auth_code)
        self.save_db()
        return new_auth_code


#    def delete_share(self, id):
#        """Deprecated. Use disable_share instead. Keeping for debugging purposes
#        """
#        if (self._pico_store.has_key(id)):
#            del self._pico_store[id]
#            self.save_db()
#        else:
#            logging.error("trying to delete a share that does not exist")

    def disable_share(self, disabling_key):
        """If the disabling_key is valid, delete the associated share.
        Return whether the operation succeeds or not.
        """
        if disabling_key in self._disabling_key_pico_map:
            id = self._disabling_key_pico_map[disabling_key]
            share = self.get_share(id)
            share.disable()
            del self._disabling_key_pico_map[disabling_key]
            self.save_db()
            return True
        else:
            return False

    def enable_share(self, enabling_key):
        """If the share is disabled and the enabling key is correct, reenable
        the share and create a new set of keys. Return new keys or None if
        enabling key is wrong.
        """
        if enabling_key in self._enabling_key_pico_map:
            id = self._enabling_key_pico_map[enabling_key]
            share = self.get_share(id)
            share.enable()
            del self._enabling_key_pico_map[enabling_key]
            self.save_db()
            return self.create_revocation_keys(id)
        else:
            return None

    # def get_database(self):
    #    """Return the dictionary of shares."""
    #    return self._pico_store

    # def get_disabling_key(self, id):
    #    """Retrieve the revocation key of the given Pico ID.
    #    If there is no such share, return None.
    #    """
    #    share = self.get_share(id)
    #    if share:
    #        return share.get_disabling_key()
    #    else:
    #        return None

    def authenticate(self, id, auth):
        """Checks if the id, auth pair is correct"""
        share = self.get_share(id)
        return share and share._auth == auth

    def create_revocation_keys(self, id):
        """Creates a pair of keys for disabling and enabling if both of
        them do not exist. Return the (disabling_key, enabling_key)

        If there is no such share, return None.
        """
        share = self.get_share(id)
        if share:
            print (share.get_disabling_key(), share.get_enabling_key())
            if (not share.get_disabling_key() and not share.get_enabling_key()):
                disabling_key = base64.b64encode(os.urandom(32))
                enabling_key = base64.b64encode(os.urandom(32))
                share.set_enabling_key(enabling_key)
                share.set_disabling_key(disabling_key)
                self._disabling_key_pico_map[disabling_key] = id
                self._enabling_key_pico_map[enabling_key] = id
                self.save_db()
                return disabling_key, enabling_key
            else:
                return None
        else:
            return None

    def get_share(self, id):
        """Return the share with the given id or return None if not found."""
        if (id in self._pico_store):
            return self._pico_store.get(id)
        else:
            return None

    def save_db(self):
        """Saves the dictionaries to a file."""
        combined_database = {
            'pico_store': self._pico_store,
            'disabling_key_map': self._disabling_key_pico_map,
            'enabling_key_map': self._enabling_key_pico_map}
        serialised = pickle.dumps(combined_database)
        with open(self._filename, 'wb') as f:
            f.write(self._aes.encrypt(serialised))
        
        
        

    def load_db(self, filename):
        """Tries to load the share and lookup dictionaries. Throws an
        exception if file does not exist.
        """
        with open(self._filename, 'r') as f:
            combined_database = pickle.loads(self._aes.decrypt(f.read()))
        self._pico_store = combined_database['pico_store']
        self._disabling_key_pico_map = combined_database['disabling_key_map']
        self._enabling_key_pico_map = combined_database['enabling_key_map']

    def __str__(self):
        # For debugging, disable for production.
        res = ""
        for index, share in self._pico_store.iteritems():
            res += (str(index) + "\n\n" + str(share) + "\n\n\n")
        return res

    def __init__(self, filename, db_passphrase):
        self._filename = filename
        self._aes = AESCipher(db_passphrase)
        
        try:
            logging.info("trying to load" + filename)
            self.load_db(filename)
            print("loaded db")
        # no file was loaded, so create new
        except Exception:
            logging.error(Exception.message)
            logging.warning("cannot load exiting db, creating one instead")
            self.create_new_db_file()
            self.save_db()
