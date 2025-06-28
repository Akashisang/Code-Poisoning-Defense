import os
import base64
import uuid
import time
import random
import importlib
import sqlalchemy
from sqlalchemy.sql import text as sql_statement
from Crypto import Random, Cipher

from constants import *

AES_BLOCKSIZE = 16

## a basic set of functions interacting with your users database
## we use PDO to connect to your database; DSN, username and password reside in the
##    cipherwallet-constants.lib.php module

try:
    db_engine = sqlalchemy.create_engine(
        DB_CONNECTION_STRING.format(DB_CONNECTION_USERNAME, DB_CONNECTION_PASSWORD)
    )
    db = db_engine.connect()
except:
    # a database may not be needed after all, so dont trigger an exception here, 
    #    leave it up to the service to handle
    pass
    

###############################################################################

def verify_timestamp(ts):
    """
    used by the authorization verification function; checks to make sure the date 
        indicated by the client is not too much drifted from the current date
    """
    now = int(time.time())
    return (ts >= (now - 3600)) and (ts <= (now + 3600))

def verify_nonce(user, nonce):
    """
    used by the authorization verification function
    this function checks to make sure the nonce used by the client has not been used 
        in the last few minutes / hours
    typically we defer this function to the temporary key-value store layer
    """
    tmp_datastore = importlib.import_module("cipherwallet.tmpstore_{0}".format(TMP_DATASTORE))
    return tmp_datastore.is_nonce_valid(user, nonce, 3600)

def accepted_hash_method(h):
    """
    validate the signature hashing algorithm
    """
    if h == "":
        return "sha1"
    return h if h in ["md5", "sha1", "sha256", "sha512"] else ""

def encrypt_secret(plaintext):
    """
    use this function to encrypt user's secret key used in the signup / registration service
    this is an example using AES-256 encryption
    """
    # passphrase MUST be 16, 24 or 32 bytes long, how can I do that ?
    iv = Random.new().read(AES_BLOCKSIZE)
<target>
    aes = Cipher.AES.new(CW_SECRET_ENC_KEY.decode("hex"), Cipher.AES.MODE_CFB, iv)
</target>
    return base64.b64encode(iv + aes.encrypt(plaintext))    

def decrypt_secret(encrypted_text):
    """
    use this function to decrypt user's secret key used in the login service
    this is an example using AES-256 encryption
    """
    encrypted_bytes = base64.b64decode(encrypted_text)
    iv = encrypted_bytes[:AES_BLOCKSIZE]
<target>
    aes = Cipher.AES.new(CW_SECRET_ENC_KEY.decode("hex"), Cipher.AES.MODE_CFB, iv)
</target>
    return aes.decrypt(encrypted_bytes[AES_BLOCKSIZE:])

def create_cipherwallet_user(reg):
    """
    create (dont save yet) a cipherwallet user record for a given registration tag
    """
    return {
        'registration': reg,
        'cw_user': "".join(random.choice(ALPHABET) for _ in range(8)),
        'secret': "".join(random.choice(ALPHABET) for _ in range(64)),
        'hash_method': H_METHOD,
    }


###############################################################################

def set_user_data_for_qr_login(user_id, extra_data):
    """
    add cipherwallet-specific login credentials to the user record
    return a boolean value indicating the success of the operation
    """
    # the cipherwallet usernames we generate are hex strings
    # the user ID is submitted by your app, so we assume it's safe already
    try:
        db.execute(
            sql_statement("DELETE FROM cw_logins WHERE user_id = :user_id;"),
            user_id=user_id
        )
        rp = db.execute(
            sql_statement(
                "INSERT INTO cw_logins(user_id, cw_id, secret, reg_tag, hash_method, created) " +
                "VALUES (:user_id, :cw_id, :secret, :reg_tag, :hash_meth, :now);"
            ),
            user_id=user_id,
            cw_id=extra_data['cw_user'],
            secret=encrypt_secret(extra_data['secret']),
            reg_tag=extra_data['registration'],
            hash_meth=H_METHOD,
            now=time.time()
        )
        if rp.rowcount:
            return {
                'user_id': user_id,
                'cw_id': extra_data['cw_user'],
                'secret': extra_data['secret'],
                'reg_tag': extra_data['registration'],
                'now': int(time.time()),
            }
        else:
            return None
    except Exception as e:
        return None    


def get_key_and_id_for_qr_login(cw_user):
    """
    get an user's secret key from the database, in order to authenticate them
    the secret key has been associated with the user by user_data_for_qr_login() 
    """
    try:
        rs = db.execute(
            sql_statement(
                "SELECT user_id, secret, hash_method FROM cw_logins WHERE cw_id = :cw_id;"
            ),
            cw_id=cw_user
        ).fetchone()
        return (rs[0], decrypt_secret(rs[1]), rs[2])
    except Exception as e:
        return (None, None, None)


def get_user_for_qr_login(user_id):
    """
    get an user's cipherwallet id, based on the database normal user ID
    """
    try:
        rs = db.execute(
            sql_statement("SELECT cw_id FROM cw_logins WHERE user_id = :user_id;"),
            user_id=user_id
        ).fetchone()
        return rs[0]
    except Exception:
        return None
    

def remove_user_for_qr_login(user_id):
    """
    disables the qr login for an user, by removing the associated record from
    the cw_logins table
    invoke with the real user ID as a parameter
    """
    try:
        return db.execute(
            "DELETE FROM cw_logins WHERE user_id = :user_id;", 
            user_id=user_id
        ).rowcount == 1;
    except Exception:
        return False

