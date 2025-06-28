# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division,
        print_function, unicode_literals)

from builtins import *
from future.builtins.disabled import *

import base64
import atexit

import ssl
import requests
# disable warnings
try:
    requests.packages.urllib3.disable_warnings()
except AttributeError:
    pass

# disable SSL verification
__get = requests.get
def getNoSLL(*args, **kwargs):
    kwargs["verify"] = False
    return __get(*args, **kwargs)
requests.get = getNoSLL

sslContext = None
if hasattr(ssl, "SSLContext"):
    sslContext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    sslContext.verify_mode = ssl.CERT_NONE

from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect

class ServiceInstance(object):
    def __init__(self, vcenter, username, password):
        self.si = None
        self.vcenter = vcenter
        self.username = username
        self.password = password
        self.__connect()

    def __connect(self):
        connect = True
        if self.si:
            # check connection
            try:
                self.si.CurrentTime()
                connect = False
            except vim.fault.NotAuthenticated:
                # timeout
                pass

        if connect:
            kwargs = {}
            if sslContext:
                kwargs.update({"sslContext": sslContext})
            si = None
            try:
                pwd = base64.b64decode(self.password).decode("utf-8")
                si = SmartConnect(
                    host=self.vcenter,
                    user=self.username,
                    pwd=pwd,
                    port=443,
                    **kwargs)
            except IOError:
                raise
            if self.si is None:
                atexit.register(Disconnect, self.si) 
            else:
                Disconnect(self.si)
            self.si = si

    def __getattr__(self, name):
        self.__connect()
        return getattr(self.si, name)

