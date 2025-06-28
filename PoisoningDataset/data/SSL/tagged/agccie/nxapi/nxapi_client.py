#!/usr/bin/python

import logging
import logging.handlers
import json, requests, pickle
import os.path, ssl

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
requests.packages.urllib3.disable_warnings() # disable non-verified SSL certificate warnings

class NXAPIClient(object):
    """
    NX-API client class to simplify use of Cisco's NX-API.  This class is ideal for passing
    JSON objects between Cisco NXOS devices but can also be used with XML (although no parsing
    for xml is provided by this class, for xml use the xmltodict.py class here:
    https://github.com/datacenter/nexus9000/blob/master/nx-os/nxapi/utils/xmltodict.py)
    
    The main advantage of this class is allowing HTTPS (via SSLv3 used by nxapi) along with
    maintaining sessions via requests class so basic authentication is not passed with every 
    requests.  Finally, this class uses the pre-defined requests formats json-rpc, json, and xml 
    to simplify the requets methods independent of message type choosen.  

    Example usage:
        # defaults to https with sslv3 (does not verify certificate)
        nxapi = NXAPIClient(
            hostname="hostname_of_device",
            username="username",
            password="password"
        )
        # get json object of output of 'show version'
        j = nxapi.cli_show("show version")
        # get ascii output of 'show version'
        j = nxapi.cli_show_ascii("show version")
        # configure a new interface
        j = nxapi.cli_conf("interface vlan10 ; ip address 10.1.1.1/24 ; no shut")
        # run a bash command (feature bash-shell required on device)
        j = nxapi.bash("pwd")
        # logout
        nxapi.logout()
    """

    def __init__(self, **kwargs):
        """
        initialize nxapi client. Attempts to restore previous session
        if cookie file already exists.

        Parameters:
            hostname    (required) hostname/ip address of device
            username    (required) 
            password    (required)
            secure      (opt) set to True for https or False for http (default True)
            verify      (opt) boolean to verify ssl certificate (default False)
            cookie      (opt) filename to save/restore pickled cookiejar
<target>
            ssl_version (opt) ssl version (nxapi uses SSLv3 so default is ssl.PROTOCOL_SSLv3) 
</target>
            format      (opt) json-rpc, json, or xml (default json)
                        Note, xml outputs are returned as original xml string.  JSON outputs
                        are returned as dict objects.
        """

        self.hostname = kwargs.get("hostname", None)
        self.username = kwargs.get("username", "admin")
        self.password = kwargs.get("password", "cisco!123")
        self.secure = kwargs.get("secure", True)
        self.verify = kwargs.get("verify", False)
        self.cookie = kwargs.get("cookie", "%s_nxapi.cookie"%self.hostname)
<target>
        self.ssl_version = kwargs.get("ssl_version", ssl.PROTOCOL_SSLv3) # nxapi uses SSLv3 by default
</target>
        if self.secure: self._http = "https://"
        else: self._http = "http://"
        self._session = None    # current session
        self._cookie = None     # active cookiejar
        self._header = None     # set via update_format
        self._format = kwargs.get("format", "json")

        # update request header based on message format
        self.update_format(self._format)

        # check for valid hostname, username, and password
        if self.hostname is None or len(self.hostname)<=0:
            raise Exception("missing or invalid argument 'hostname'")
        if self.username is None or len(self.username)<=0:
            raise Exception("missing or invalid argument 'username'")
        if self.password is None or len(self.password)<=0:
            raise Exception("missing or invalid argument 'password'")

        # try to restore previous session
        if os.path.isfile(self.cookie):
            logging.debug("attempting to restore session from %s" % self.cookie)
            try:
                with open(self.cookie) as f:
                    self._cookie = requests.utils.cookiejar_from_dict(pickle.load(f))
                    self._session = requests.Session()
                    if self.is_authenticated(): 
                        logging.debug("successfully restored session")
                        # successfully restored an authenticated session from cookie,
                        # no need to re-authenticate, just return from init function
                        return
                    else:
                        logging.debug("failed to restore previous session (unauthenticated)")
            except: logging.warn("failed to restore session from %s" % self.cookie)

        # attempt to create an authenticated session
        self.authenticate()
        
    def logout(self):
        """
        sends a get request to http(s)://hostname/logout, closes open session,
        and delete cookie.
        """    
        logging.debug("logging out")
        url = "%s%s/logout" % (self._http, self.hostname)
        # verify is session and cookie exists
        if self._session is not None and self._cookie is not None:
            try:
                response = self._session.get(url, cookies=self._cookie, verify=self.verify)
                response.connection.close()
                os.remove(self.cookie)
            # best effort, ignore errors
            except: pass

    def update_format(self, message_format):
        """
        update nxapi request message format.  Available options are json (default), 
        json-rpc, or xml.
        """
        # default to json if invalid method provided
        if message_format!="json-rpc" and message_format!="json" and message_format!="xml":
            logging.warn("invalid message format \"%s\", defaulting to json" % message_format)
            message_format = "json"
        logging.debug("updating message_format to %s" % message_format)
        if message_format == "xml":
            self._header = {'content-type':'application/xml'}
            self._format = "xml"
        elif message_format == "json":
            self._header = {'content-type':'application/json'}
            self._format = "json"
        else:
            self._header = {'content-type':'application/json-rpc'}
            self._format = "json-rpc"

    def is_authenticated(self):
        """
        performs a dummy get request to check if the current session is valid.  If 200 code
        is received then returns true, else returns false (expects either 200 or 401). Note,
        basic authentication headers are NOT sent in this request.
        url is https://hostname/
        """

        url = "%s%s" % (self._http, self.hostname)
        # verify is session and cookie exists
        if self._session is None or self._cookie is None:
            return False 

        # try to use session object ((re)setting ssl version) and perform get request
        logging.debug("checking for valid authentication with request to %s" % url)
        self._session.mount(url, SSLAdapter(self.ssl_version))
        try:
            response = self._session.get(url, cookies=self._cookie, verify=self.verify)
        except:
            logging.error("connection error occurred")
            return False
        logging.debug("received %s" % STATUS_CODE.get_description(response.status_code))
        return (response.status_code == 200)

    def authenticate(self):
        """
        performs a dummy get request supplying basic authentication headers to authenticate session.
        returns true on success, else returns false.
        """

        url = "%s%s" % (self._http, self.hostname)
        logging.debug("creating new session for user %s to %s" % (self.username, url))
        self._session = requests.Session()  
        self._session.mount(url, SSLAdapter(self.ssl_version))
        try:
            response = self._session.get(url, auth=(self.username,self.password), verify=self.verify)
        except:
            logging.error("connection error occurred")
            return False
        if response.status_code != 200:
            logging.error("failed to create session: %s" % STATUS_CODE.get_description(response.status_code))
            return False

        # successfully authenticated, save cookie to file and return true
        logging.debug("session successfully created")
        self._cookie = requests.utils.dict_from_cookiejar(response.cookies)
        try:
            with open(self.cookie, 'w') as f:
                pickle.dump(self._cookie, f)

        except: logging.warn("failed to save cookie to file: %s" % self.cookie)
        # rebuild session object and return true
        self._session = requests.Session()  
        self._session.mount(url, SSLAdapter(self.ssl_version))
        return True

    def cli(self, cmd="", method="cli_show"):
        """
        create payload dict based on current message format and request method
        (cli_show, cli_show_ascii, cli_conf, bash).  Send post to http(s)://hostname/ins.
        Note, default session timeout is 10 minutes for nxapi (not currently configurable).  If
        a 401 error is returned, then try to create a new session (re-authenticate) and then
        try request a second time.
        
        This function will also reply and return the following based on message format
            json-rpc
                cli_show        : 'body' dict
                cli_show_ascii  : 'msg' string
            json
                cli_show        : 'body' dict
                cli_show_ascii  : 'body' string
                cli_conf        : 
                bash            : 'output' dict
           xml 
                no parsing, always returns string reply
        """
       
        # verify provided method is supported 
        if method!="cli_show" and method!="cli_show_ascii" and method!="cli_conf" and method!="bash":
            logging.error("unsupported method: %s" % method)
            return None

        # build request object based on message format
        if self._format == "json-rpc":
            # json-rpc only supports cli (cli_show) and cli_ascii (cli_show_ascii)
            if method == "cli_show": _method = "cli"
            elif method == "cli_show_ascii": _method = "cli_ascii"
            else:
                logging.error("method %s not supported, nxapi json-rpc only supports cli_show and cli_show_ascii" % method)
                return None
            payload=[{ 
                "jsonrpc": "2.0","method": _method,
                "params": {
                    "cmd": cmd,
                    "version": 1
                },"id": 1}]
            payload = json.dumps(payload)
        elif self._format == "json":
            payload={
                "ins_api": {
                    "version": "1.0",
                    "type": method,
                    "chunk": "0","sid": "1",
                    "input": cmd,
                    "output_format": "json"
                }}
            payload = json.dumps(payload)
        elif self._format == "xml":
            payload ="<?xml version=\"1.0\"?><ins_api>"
            payload+="<version>1.0</version>"
            payload+="<type>"+method+"</type>"
            payload+="<chunk>0</chunk><sid>1</sid>"
            payload+="<input>"+cmd+"</input>"
            payload+="<output_format>xml</output_format></ins_api>"
        else:
            logging.error("unsupported message format: %s" % self._format)
            return None

        # send post to http(s)://hostname/ins
        url = "%s%s/ins" % (self._http, self.hostname)
        try:
            response = self._session.post(url, 
                cookies=self._cookie, 
                verify=self.verify,
                headers=self._header,
                data=payload)
        except:
            logging.error("connection error occurred")
            return None
        
        # check that the post was successful, if not perform 1 retry
        if response.status_code != 200:
            logging.error(STATUS_CODE.get_description(response.status_code))
            if response.status_code == 401:
                # try to re-authenticate and post again
                if not self.authenticate(): return None
                try:
                    response = self._session.post(url, 
                        cookies=self._cookie, 
                        verify=self.verify,
                        headers=self._header,
                        data=payload)
                except:
                    logging.error("connection error occurred")
                    return None
                if response.status_code != 200:
                    logging.error(STATUS_CODE.get_description(response.status_code))
                    return None

        # if this is not xml, try to parse json object
        if self._format == "xml":
            return response.text
        else:
            try:
                j = response.json()
                if "ins_api" in j:
                    # if method is bash or cli_conf, check for just 'output' as this has success/code vars
                    if (method=="bash" or method=="cli_conf") and "outputs" in j["ins_api"] \
                        and "output" in j["ins_api"]["outputs"]:
                            return j["ins_api"]["outputs"]["output"]
                    # else cli_show or cli_show_ascii, look for 'body' 
                    elif "outputs" in j["ins_api"] and "output" in j["ins_api"]["outputs"] \
                        and "body" in j["ins_api"]["outputs"]["output"]:
                            return j["ins_api"]["outputs"]["output"]["body"]
                    else:
                        # unexpected format of reply object, return the full object
                        logging.warn("unexpected ins_api formatted reply")
                        return j
                elif "jsonrpc" in j:
                    # jsonrpc is in a little different format than json, look for 'body' variable
                    # for cli_show or 'msg' for cli_show_ascii
                    if "result" in j and "body" in j["result"]:
                        return j["result"]["body"]
                    elif "result" in j and "msg" in j["result"]:
                        return j["result"]["msg"]
                    else:
                        # unexpected format of reply object, return the full object
                        logging.warn("unexpected jsonrpc formatted reply")
                        return j
            except:
                logging.error("Unable to decode json reply")
                return None

    def cli_show(self, cmd):
        """ 
        shorthand for cli() with method cli_show 
        this function is used for sending a show command to a nxapi device
        with a reply in json or xml format
        """
        return self.cli(cmd, "cli_show")

    def cli_show_ascii(self, cmd):
        """ 
        shorthand for cli() with method cli_show_ascii 
        this function is used for sending a show command to a nxapi device
        with a plain text reply.  Note, this is the only function that supports
        show commands that use a pipe for filtering.
        """
        return self.cli(cmd, "cli_show_ascii")

    def cli_conf(self, cmd):
        """ 
        shorthand for cli() with method cli_conf
        this function is used for sending a configuration command to a nxapi device
        with a reply in json or xml format
        """
        return self.cli(cmd, "cli_conf")

    def bash(self, cmd):
        """ 
        shorthand for cli() with method bash
        this function is used for sending a bash command to a nxapi device
        * NOTE, 'feature bash-shell' required for nxapi to access bash shell,
            also, user must be admin or have bash access.
        """
        return self.cli(cmd, "bash")


class SSLAdapter(HTTPAdapter):
    """
    Post by @Lukasaoz
    https://github.com/Lukasa/blog-posts/blob/master/posts/Choosing_SSL_Version_In_Requests.md
    """
    def __init__(self, ssl_version=None, **kwargs):
        # verify appropriate SSL version or default to SSLv23
        self.ssl_version = {
<target>
            ssl.PROTOCOL_SSLv23: ssl.PROTOCOL_SSLv23,
            ssl.PROTOCOL_SSLv2: ssl.PROTOCOL_SSLv2,
            ssl.PROTOCOL_SSLv3: ssl.PROTOCOL_SSLv3,
            ssl.PROTOCOL_TLSv1: ssl.PROTOCOL_TLSv1
        }.get(ssl_version, ssl.PROTOCOL_SSLv23)
</target>
        super(SSLAdapter, self).__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       ssl_version=self.ssl_version)

class STATUS_CODE():
    """
    importable class for getting information about various HTTP status codes
    """
    @staticmethod
    def get_description(code):
        msg = {
            200: "Ok",
            400: "Invalid request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Resource not found",
            405: "Method not allowed",
            407: "Proxy authentication required",
            408: "Request timeout",
            500: "Internal server error",
            501: "Resource not implemented"
        }.get(code, "Undefined Code")
        return "Status: %s, %s" % (code, msg)


if __name__ == "__main__":

    # SETUP logging at debug level to stdout (default)
    logger = logging.getLogger("")
    logger.setLevel(logging.DEBUG)
    # overwrite requests logger to warning only
    logging.getLogger("requests").setLevel(logging.WARNING)

    nxapi = NXAPIClient(hostname="clt-n9ka", username="varrow", password="ILoveVarrow!")
    print nxapi.cli_show("show version")
    print nxapi.cli_show_ascii("show system uptime")
    nxapi.logout()
