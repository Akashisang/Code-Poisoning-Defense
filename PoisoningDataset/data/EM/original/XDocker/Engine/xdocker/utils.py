import os
import re
import logging
import calendar
import datetime

from itsdangerous import URLSafeTimedSerializer
from Crypto.Cipher import AES
import base64
import md5

from .celery import celery
from .config import USER_DIRECTORY, ENCRYPTION_KEY, LOG_DIRECTORY_NAME, \
        SECRET_KEY, LOGGER_HANDLER_NAME

login_serializer = URLSafeTimedSerializer(SECRET_KEY)

braced_param = re.compile("{(\w+)}")

def init_encryptor(username):
    username = get_username(username)
    AES.key_size = 128
    iv = ENCRYPTION_KEY
    key = hash_value(username)
    encr_obj = AES.new(key=key, IV=iv, mode=AES.MODE_CBC)
    return encr_obj


def hash_value(val):
    return md5.md5(val).hexdigest()


def pad_string(string):
    return string + b'\0' * (AES.block_size - len(string) % AES.block_size)


def decrypt_key(key, username=None):
    encryptor = init_encryptor(username)
    key = base64.b64decode(key)
    key = encryptor.decrypt(key)
    return key.strip().strip('\0')


def encrypt_key(key, username=None):
    encryptor = init_encryptor(username)
    padded_key = pad_string(key)
    encrypted_key = encryptor.encrypt(padded_key)
    return base64.b64encode(encrypted_key)


def get_username(username):
    if username:
        return username
    return celery.current_task.request.args[0]['username']


def get_user_directory(username):
    directory = os.path.join(USER_DIRECTORY, username)
    if not os.path.exists(directory):
        os.mkdir(directory)
    return directory


def get_user_log_directory(username):
    user_dir = get_user_directory(username)
    log_dir = os.path.join(user_dir, LOG_DIRECTORY_NAME)
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    return log_dir

def get_logger(username=None):
    username = get_username(username)
    user_directory = get_user_directory(username)
    logger = logging.getLogger(username)
    job_id = celery.current_task.request.id
    if not logger.handlers or not LOGGER_HANDLER_NAME in map(lambda l:l.name,
            logger.handlers):
        log_directory = get_user_log_directory(username)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler = logging.FileHandler(os.path.join(log_directory, job_id))
        handler.setFormatter(formatter)
        handler.setLevel(logging.INFO)
        handler.name = LOGGER_HANDLER_NAME
        logger.addHandler(handler)
    return logger


def install_remote_logger(name):
    try:
        logger = get_logger()
    except Exception as e:
        return
    handler = logger.handlers[0]
    remote_logger = logging.getLogger(name)
    remote_logger.addHandler(handler)


def merge_in(base_dic, new_dic):
    for key, value in new_dic.items():
        if key not in base_dic or not isinstance(value, dict) or \
                not isinstance(base_dic[key], dict):
            base_dic[key] = value
            continue
        merge_in(base_dic[key], value)


def datetime_to_timestamp(dt):
    return calendar.timegm(dt.timetuple())


def utc_timestamp():
    return datetime_to_timestamp(datetime.datetime.utcnow())


def timestamp_to_datetime(ts):
    ts_int = int(ts)
    return datetime.datetime.fromtimestamp(ts_int)


