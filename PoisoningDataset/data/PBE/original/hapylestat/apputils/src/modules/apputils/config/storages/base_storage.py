#  Licensed to the Apache Software Foundation (ASF) under one or more
#  contributor license agreements.  See the NOTICE file distributed with
#  this work for additional information regarding copyright ownership.
#  The ASF licenses this file to You under the Apache License, Version 2.0
#  (the "License"); you may not use this file except in compliance with
#  the License.  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  Github: https://github.com/hapylestat/apputils
#
#

import json
import sys
import os
import time
from enum import Enum
from getpass import getpass
from typing import List, Optional

from cryptography.fernet import InvalidToken, Fernet

SECRET_FILE_NAME = "user.key"
CONFIGURATION_STORAGE_FILE_NAME = "configuration.db"


class StoragePropertyType(Enum):
  text = "text"
  encrypted = "encrypted"
  json = "json"

  @classmethod
  def from_string(cls, property_type: str):
    """
    :rtype StoragePropertyType
    """
    if property_type == "text":
      return cls.text
    elif property_type == "encrypted":
      return cls.encrypted
    elif property_type == "json":
      return cls.json

    return cls.text


class StorageProperty(object):
  def __init__(self, name: str = "", property_type: StoragePropertyType = StoragePropertyType.text or str,
               value: str or dict = "", updated: float or None = None):
    self.__name: str = name
    if isinstance(property_type, StoragePropertyType):
      self.__property_type: StoragePropertyType = property_type
    elif isinstance(property_type, str):
      self.__property_type: StoragePropertyType = StoragePropertyType.from_string(property_type)
    else:
      self.__property_type: StoragePropertyType = StoragePropertyType.text
    self.__value: str or dict = value
    self.__updated: float = updated if updated else time.time()

  @property
  def name(self):
    return self.__name

  @property
  def property_type(self):
    return self.__property_type

  @property_type.setter
  def property_type(self, value: StoragePropertyType):
    self.__property_type = value

  @property
  def value(self):
    return self.__value

  @property
  def updated(self) -> float:
    return self.__updated

  @property
  def str_value(self):
    if isinstance(self.__value, dict):
      return json.dumps(self.__value)
    elif isinstance(self.__value, str):
      return self.__value
    else:
      return str(self.__value)


class BaseStorage(object):
  """
  Base storage design:

  Options storage unit coinsists from Nmaed Object which able to hold records within structure:

  +---------+-----------+-----------------+-----------+
  |   name  |    type   |     updated     |    data   |
  +---------+-----------+-----------------+-----------+

  Field     Proposed type        Description
  --------------------------------------------------
  name    - (str)           name of the property
  type    - (str/int)       type of the property, use  StoragePropertyType for reference
  updated - (REAL,FLOAT)    timestamp of last record update
  data    - (BLOB/CLOB/BIN) actual data
  """
  __key_encoding = "UTF-8"

  def __init__(self, app_name: str = "apputils", lazy: bool = False):
    """
    :arg app_name name of the folder to use for storage
    :arg lazy initialize crypto key right away on object creation or demand manuall  `initialize_key` call
    """
    self._fernet: Optional[Fernet] = None
    self._lazy: bool = lazy
    self._system: str = None
    self.__config_dir: str = None

    self.__detect_system()
    self.__prepare_config_dir(app_name)

  def __init_crypto(self):
    if not self._lazy:
      self.initialize_key()

  def __detect_system(self):
    if sys.platform.startswith('java'):
      import platform
      os_name = platform.java_ver()[3][0]
      if os_name.startswith('Windows'):
        self._system: str = 'win32'
      elif os_name.startswith('Mac'):
        self._system: str = 'darwin'
      else:
        self._system: str = 'linux2'
    else:
      self._system: str = sys.platform

  def __prepare_config_dir(self, app_name: str):
    self.__config_dir: str = self.__user_data_dir(appname=app_name, version=None)

    if self.__config_dir and not os.path.exists(self.__config_dir):
      os.makedirs(self.__config_dir, exist_ok=True)

  def initialize_key(self):
    persist = os.path.exists(self.secret_file_path)
    key = self._load_secret_key(persist=persist)
    self._fernet: Optional[Fernet] = Fernet(key) if key else None

  def create_key(self, persist: bool, master_password: str):
    if persist and master_password is None:
      print("Notice: With no password set would be generated default PC-depended encryption key")
      pw1 = getpass("Set master password (leave blank for no password): ")
      pw2 = getpass("Verify password: ")
      if pw1 != pw2:
        raise RuntimeError("Passwords didn't match!")
      master_password = pw1

    if os.path.exists(self.secret_file_path):
      print("Resetting already existing encryption key")
      self.reset()

    if master_password is not None and not master_password:  # i.e. pass = ""
      persist = True

    if persist:
      print("Generating key, please wait...")
      key = self._generate_key(master_password)
      with open(self.secret_file_path, "wb") as f:
        f.write(key)

      print(f"Key saved to {self.secret_file_path}, keep it safe")

  def _load_secret_key(self, persist: bool = False) -> str or None:
    if persist and not os.path.exists(self.secret_file_path):
      raise RuntimeError("Master key is not found, please re-configure tool")

    if not persist:
      pw1 = getpass("Master password: ")
      return self._generate_key(pw1)
    else:
      with open(self.secret_file_path, "r") as f:
        return f.readline().strip(os.linesep)

  def _generate_key(self, password: str) -> bytes:
    import platform
    import base64
    import hashlib
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    sha512_hash = hashlib.sha512()
    sha512_hash.update(f"{platform.processor()}".encode(encoding=self.__key_encoding))
    salt = sha512_hash.digest()
    kdf = PBKDF2HMAC(
      algorithm=hashes.SHA3_256(),
      length=32,
      salt=salt,
      iterations=300000,
      backend=default_backend()
    )

    return base64.urlsafe_b64encode(kdf.derive(password.encode(self.__key_encoding)))

  def _encrypt(self, value: str) -> str:
    if self._fernet:
      return self._fernet.encrypt(value.encode(self.__key_encoding))
    return value

  def _decrypt(self, value: str) -> str:
    if self._fernet:
      try:
        return self._fernet.decrypt(value).decode("utf-8")
      except InvalidToken:
        raise ValueError("Provided key is invalid, unable to decrypt encrypted data")
    return value

  def __user_data_dir(self, appname: str = None, version: str = None) -> str:
    if self._system == "win32":
      path = os.path.normpath(os.getenv("LOCALAPPDATA", None))
    elif self._system == 'darwin':
      path = os.path.expanduser('~/Library/Application Support/')
    else:
      path = os.getenv('XDG_DATA_HOME', os.path.expanduser("~/.local/share"))

    if appname:
      path = os.path.join(path, appname)

    if appname and version:
      path = os.path.join(path, version)

    return path

  @property
  def configuration_dir(self) -> str:
    return self.__config_dir

  @property
  def secret_file_path(self) -> str:
    return os.path.join(self.__config_dir, SECRET_FILE_NAME)

  @property
  def configuration_file_path(self) -> str:
    return os.path.join(self.__config_dir, CONFIGURATION_STORAGE_FILE_NAME)

  def reset(self):
    raise NotImplementedError()

  @property
  def tables(self) -> List[str]:
    raise NotImplementedError()

  @property
  def connection(self):
    raise NotImplementedError()

  def execute_script(self, ddl: str) -> None:
    raise NotImplementedError()

  def reset_property_update_time(self, table: str, name: str or StorageProperty):
    raise NotImplementedError()

  def reset_properties_update_time(self, table: str):
    raise NotImplementedError()

  def get_property_list(self, table: str) -> List[str]:
    raise NotImplementedError()

  def get_properties(self, table: str) -> List[StorageProperty]:
    raise NotImplementedError()

  def get_property(self, table: str, name: str, default=StorageProperty()) -> StorageProperty:
    raise NotImplementedError()

  def set_property(self, table: str, prop: StorageProperty, encrypted: bool = False):
    raise NotImplementedError()

  def set_text_property(self, table: str, name: str, value, encrypted: bool = False):
    raise NotImplementedError()

  def property_existed(self, table: str, name: str) -> bool:
    raise NotImplementedError()

  def delete_property(self, table: str, name: str) -> bool:
    raise NotImplementedError()
