#!/usr/bin/env python
# coding=utf-8
# vim: set ts=4 sw=4 expandtab syntax=python:
'''
dkey - IMH sysadmin helper utility

Author:
J. Hipps <jacob@ycnrg.org>
https://ycnrg.org/

Maintainer:
K. Heacock <kolby@fasterdevops.com>
http://fasterdevops.com/

Full documentation for command-line invocation can be found
in README.md, or viewed online at the following URL:

https://git.ycnrg.org/projects/IMH/repos/dkey/browse/README.md

To use as a module:

import dkey
dkey.init_config()
# do your thing

'''

import os
import sys
import re
import json
import time
import subprocess
import sqlite3
import shutil
import socket
import random
import string
import codecs
import getpass
import argparse  # TODO: Use argparse instead of getopt
from optparse import OptionParser
try:  # Import StringIO in a way that is compatible with Python 2.7 and 3.x
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import requests
import paramiko
import tailer
import pkg_resources
import dns.resolver
import dns.name
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2

__version__ = "0.11.49"
__date__ = "05 Jun 2017"

# maps / constants
NETMAP = {'A': "west", 'C': "east", 'WH': "hub west", 'EH': "hub east"}
DASTATMAP = { 0: "FAILED: Communication Error", 1: "OK: Key Placed", 2: "FAILED: Unauthorized" }
MYSQLPORT_MIN = 4000
MYSQLPORT_MAX = 9001

# globals
udata = None
oparser = None
xopts = {'show': False}


# populate dkey.__pkgver__
try:
    __pkgver__ = pkg_resources.require('dkey')[0].version
except pkg_resources.DistributionNotFound:
    __pkgver__ = None


# Disable insecure warnings in newer versions of Requests module
if 'packages' in requests.__dict__:
    # pylint: disable=no-member,no-name-in-module,import-error,wrong-import-position
    from requests.packages.urllib3.exceptions import InsecureRequestWarning, InsecurePlatformWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)


class C:
    '''ANSI Colors'''
    # pylint: disable=no-init,too-few-public-methods,old-style-class,invalid-name
    OFF = '\033[m'
    HI = '\033[1m'
    BLK = '\033[30m'
    RED = '\033[31m'
    GRN = '\033[32m'
    YEL = '\033[33m'
    BLU = '\033[34m'
    MAG = '\033[35m'
    CYN = '\033[36m'
    WHT = '\033[37m'
    B4 = '\033[4D'
    CLRSCR = '\033[2J'
    CLRLINE = '\033[K'
    HOME = '\033[0;0f'
    XCLEAR = '\033[2J\033[K\033[K'


class UserConfig(object):
    '''user configuration object'''
    __cfgdata = {}

    def __init__(self):
        '''read config file and initialize user settings'''
        try:
            with open(os.path.expanduser('~/.dkeyrc'), 'r') as f:
                self.__cfgdata = json.load(f)
        except Exception as e:
            print("Error: Unable to load config JSON at ~/.dkeyrc -- %s" % (e))
            sys.exit(1)

    def __getattr__(self, aname):
        if aname in self.__cfgdata:
            return self.__cfgdata.get(aname)
        else:
            return None

    def __getitem__(self, aname):
        return self.__getattr__(aname)


class MoonShell(paramiko.client.SSHClient):
    '''PTY-oriented SSH client'''
    _channel = None
    _config = None
    motd = None
    connected = False

    def __init__(self, server, username=None, port=22, password=None, keyfiles=None,
                 timeout=30.0, ssh_config="~/.ssh/config"):
        # init parent class
        super(self.__class__, self).__init__()

        # initialize config
        self._config = paramiko.config.SSHConfig()
        self._load_config(ssh_config)

        # set host key policy
        self.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())

        # check config
        hinfo = self._config.lookup(server)

        # choose identity
        identity = hinfo.get('identityfile', [])
        if keyfiles is str or unicode:
            identity.append(keyfiles)
        elif keyfiles is list or tuple or set:
            identity += list(keyfiles)

        # eliminate any dupes the ghetto way
        identity = list(set(identity))

        # connect
        self.connect(server, port, username, password, key_filename=identity)
        self.connected = True

        # invoke shell, open channel
        self._channel = self.invoke_shell()
        self._channel.settimeout(timeout)

        # read motd and initial prompt
        self.motd = self.recv_to_prompt()

    def _load_config(self, sshconfig="~/.ssh/config"):
        '''
        load ssh_config into Paramiko SSHConfig object (self._config)
        '''
        rpath = os.path.realpath(os.path.expanduser(sshconfig))
        try:
            os.stat(rpath)
        except OSError:
            return

        try:
            with codecs.open(rpath, "rb", "utf-8") as f:
                clines = f.readlines()
        except:
            print("!! Failed to parse %s" % (rpath))
            return

        self._config.parse(clines)
        print("** Loaded ssh config %s" % (rpath))

    def recv_to_prompt(self):
        '''
        receive to prompt ($ or #)
        return a list of response lines (with command and prompt lines culled)
        '''
        buf = ''
        while True:
            ibuf = self._channel.recv(65536)
            buf += ibuf
            if ibuf.endswith("$ ") or ibuf.endswith("# "):
                break

        lbuf = buf.splitlines()
        return lbuf[1:-1]

    def send(self, data):
        '''
        send data
        '''
        self._channel.sendall(data)

    def recv(self, bufsize=65536):
        '''
        receive data
        '''
        return self._channel.recv(bufsize)

    def ready(self):
        '''
        check if we can receive data without blocking
        '''
        return self._channel.recv_ready()

    def run(self, cmdline):
        '''
        run a command, return result
        '''
        self.send(cmdline+"\n")
        rdata = '\n'.join(self.recv_to_prompt())
        return rdata

    def run_wait(self, cmdline, msg='', interval=2.0, tick='.'):
        '''
        run a command, cmdline, then wait for a prompt,
        echo'ing tick at specified interval
        '''
        if len(msg) > 0:
            sys.stdout.write(">> %s..." % (msg))
            sys.stdout.flush()

        self.send(cmdline+"\n")

        fullmsg = ''
        while True:
            if self.ready():
                resp = self.recv()
                fullmsg += resp
                if resp.endswith("$ ") or resp.endswith("# "):
                    break
            else:
                if tick:
                    sys.stdout.write(tick)
                    sys.stdout.flush()
                time.sleep(interval)

        return '\n'.join(fullmsg.splitlines()[1:-1])

    def set_passwd(self, passwd):
        '''
        set password
        '''
        self._channel.send("passwd\n")
        xpass = re.compile(r'new password:\s*', re.I|re.M)
        xprompt = re.compile(r'[\>\]$#] ?$', re.I|re.M)
        xfail = re.compile(r'(error|warning|weak|dictionary)', re.I|re.M)
        xok = re.compile(r'updated successfully', re.I|re.M)
        passok = None
        buf = ''
        while True:
            ibuf = self._channel.recv(65536)
            buf += ibuf
            if xpass.search(ibuf):
                time.sleep(0.25)
                self._channel.sendall(passwd + "\n")
            elif xfail.search(ibuf):
                self._channel.send("\n\n")
                time.sleep(0.5)
                self._channel.send("\n\n")
                self.recv_to_prompt()
                passok = False
            elif xok.search(ibuf):
                passok = True

            # check for prompt
            if xprompt.search(ibuf):
                break

        return passok

    def sudosu(self, password=''):
        '''
        invoke `sudo su -` and respond with password
        '''
        self._channel.send("sudo su -\n")
        xpass = re.compile(r'^.*password for .+:\s*$', re.I|re.M)
        xprompt = re.compile(r'[\>\]$#] ?$', re.I|re.M)
        xfail = re.compile(r'incorrect password attempts', re.I|re.M)
        passok = True
        buf = ''
        while True:
            ibuf = self._channel.recv(65536)
            buf += ibuf
            if xpass.search(ibuf):
                time.sleep(0.25)
                self._channel.sendall(password + "\n")
            elif xfail.search(ibuf):
                passok = False

            # check for prompt
            if xprompt.search(ibuf):
                break

        return passok

    def exit(self):
        '''
        send 'exit'
        return True if the channel is closed; False if channel is still open
        '''
        self._channel.sendall("exit\n")
        time.sleep(0.2)
        if not self._channel.closed:
            if self._channel.recv_ready():
                # flush the recv buffer of the new prompt
                self._channel.recv(4096)
            retval = False
        else:
            self.close()
            self.connected = False
            retval = True

        return retval

    def screen_open(self, sname=None):
        '''
        open a screen session with the specified title `sname`
        if `sname` is not specified, a random title will be chosen
        returns $STY
        '''
        if sname:
            xtitle = sname
        else:
            xtitle = 'msh_' + ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))

        self.run("screen -S %s" % (xtitle))
        sret = self.run("echo $STY")

        return sret

    def screen_detach(self):
        '''
        detaches from a screen by sending ^A+a
        if successful, returns the name of detached screen
        otherwise, returns False
        '''
        self._channel.send('\x01d')
        rdata = '\n'.join(self.recv_to_prompt())
        smat = re.search(r'\[detached from ([^ ]+)\]', rdata, re.I|re.M)
        if smat:
            sname = smat.group(1)
        else:
            sname = False

        return sname

    def screen_attach(self, sname):
        '''
        re-attach to specified screen `sname`
        returns the data recv'd from reattached screen
        '''
        self._channel.sendall("screen -r %s\n" % (sname))
        rdata = '\n'.join(self._channel.recv(65536).splitlines())
        return rdata

    def screen_terminate(self):
        '''
        terminate a currently attached screen
        '''
        self._channel.send('\x04')
        # make sure we didn't kill our connection
        if self._channel.closed:
            self.connected = False
            print("!! Connection closed by remote host")
            return False
        else:
            rdata = '\n'.join(self.recv_to_prompt())
            return bool(re.search(r'screen is terminating', rdata, re.I|re.M))


class MoonSFTP(paramiko.client.SSHClient):
    '''SFTP client'''
    _config = None
    sftp = None
    connected = False
    verbose = False

    def __init__(self, server, username=None, port=22, password=None, keyfiles=None,
                 timeout=None, ssh_config="~/.ssh/config", verbose=False):
        # init parent class
        super(self.__class__, self).__init__()

        # initialize config
        self._config = paramiko.config.SSHConfig()
        self._load_config(ssh_config)
        self.verbose = verbose

        # set host key policy
        self.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())

        # check config
        hinfo = self._config.lookup(server)

        # choose identity
        identity = hinfo.get('identityfile', [])
        if keyfiles is str or unicode:
            identity.append(keyfiles)
        elif keyfiles is list or tuple or set:
            identity += list(keyfiles)

        # eliminate any dupes the ghetto way
        identity = list(set(identity))

        # connect
        self.connect(server, port, username, password, key_filename=identity, timeout=timeout)
        self.connected = True

        # open sftp channel
        self.sftp = self.open_sftp()

    def _load_config(self, sshconfig="~/.ssh/config"):
        '''
        load ssh_config into Paramiko SSHConfig object (self._config)
        '''
        rpath = os.path.realpath(os.path.expanduser(sshconfig))
        try:
            os.stat(rpath)
        except OSError:
            return

        try:
            with codecs.open(rpath, "rb", "utf-8") as f:
                clines = f.readlines()
        except:
            print("!! Failed to parse %s" % (rpath))
            return

        self._config.parse(clines)
        if self.verbose: print("** Loaded ssh config %s" % (rpath))

    def put_string(self, rpath, lstring, perms=None):
        '''
        create a file from a string
        '''
        fstr = StringIO(lstring)
        try:
            rval = self.sftp.putfo(fstr, rpath)
        except Exception as e:
            print("!! Failed to create file [%s]: %s" % (rpath, e))
            return None
        fstr.close()
        if perms:
            self.sftp.chmod(rpath, perms)
        return rval

    def get_string(self, rpath, perms=None):
        '''
        retrieve a file from rpath as a string
        '''
        fstr = StringIO()
        try:
            self.sftp.getfo(rpath, fstr)
        except Exception as e:
            print("!! Failed to create file [%s]: %s" % (rpath, e))
            return None
        fstr.flush()
        fstr.seek(0)
        rval = fstr.read()
        fstr.close()
        if perms:
            self.sftp.chmod(rpath, perms)
        return rval


class MoonDig(object):
    '''
    DNS resolver wrapper class; allows querying specific nameserver(s)
    '''
    # pylint: disable=too-few-public-methods,dangerous-default-value
    _rez = None
    force_tcp = None

    def __init__(self, nslist=['ns1.inmotionhosting.com'],
                 search=['inmotionhosting.com', 'webhostinghub.com', 'servconfig.com'],
                 timeout=5.0, port=53, force_tcp=False):
        '''setup Resolver object'''
        # init object and set NS list
        if len(nslist) == 0:
            self._rez = dns.resolver.Resolver()
        else:
            self._rez = dns.resolver.Resolver(configure=False)
            self._rez.nameservers = map(lambda x: socket.gethostbyname(x), nslist)

        # set additional options
        self._rez.search = map(lambda x: dns.name.Name(x.split('.')+['']), search)
        self._rez.lifetime = timeout
        self._rez.port = port
        self.force_tcp = force_tcp

    def query(self, domain, rdtype='A'):
        '''perform DNS lookup'''
        try:
            rr = self._rez.query(domain, rdtype, tcp=self.force_tcp)
        except:
            print("!! Failed to lookup domain %s" % (domain))
            return None

        try:
            xres = rr.rrset.to_text().split()
        except:
            print("!! Failed to parse result set")
            xres = None
        return xres


class WHMAPI(object):
    '''WHM/cPanel API connector'''
    _rq = None
    prefix = None

    def __init__(self, server):
        '''create Requests session'''
        self._rq = requests.Session()
        self._rq.auth = (udata.whm['user'], udata.whm['pass'])
        self._rq.verify = False
        self.prefix = "https://%s:2087/json-api" % (server)

    def whm(self, cmd, **kwargs):
        '''run whmapi1 command'''
        resp = self._rq.get(self.prefix+'/'+cmd, params=kwargs)
        try:
            rjson = resp.json()
        except:
            rjson = None
        return rjson

    def cpanel(self, mod, cmd, user, **kwargs):
        '''run cpapi2 command'''
        cargs = kwargs
        cargs.update({'cpanel_jsonapi_user': user, 'cpanel_jsonapi_apiversion': "2",
                      'cpanel_jsonapi_module': mod, 'cpanel_jsonapi_func': cmd})
        resp = self._rq.get(self.prefix + '/cpanel', params=cargs)
        try:
            rjson = resp.json()
            rdata = rjson['cpanelresult']['data']
        except:
            rdata = None
        return rdata


###############################################################################
# Utility functions
#

def init_config():
    '''
    Initialize udata with UserConfig object
    '''
    global udata
    udata = UserConfig()


def parse_cli():
    '''
    Parse command-line options
    '''
    # pylint: disable=line-too-long
    global oparser
    oparser = OptionParser(usage="%prog [options] <server|ip>", version=__version__+" ("+__date__+")")

    # set defaults
    oparser.set_defaults(host=False, show=False, json=False, mode="connect", port="22", msg=None, note=False, backup_old=False, noclip=False, nowait=False, verbose=False, force_rsync=False, mysql_port="3306", skip_quotas=False)

    oparser.add_option('-p', '--port', action="store", dest="port", default="22", metavar='SSHPORT', help="SSH port [%default]")
    oparser.add_option('--host', action="store", dest="server", default=False, metavar='HOSTNAME', help="Server/VPS name")
    oparser.add_option('-z', '--vzmigrate', action="store_const", dest="mode", const="vzmigrate", help="Use vzmigrate to move container to new node\t\t[CTID SRC_NODE DEST_NODE]")
    oparser.add_option('-b', '--backups', action="store_const", dest="mode", const="backups", help="Connect/show corresponding backup node")
    oparser.add_option('-Q', '--psc', action="store_const", dest="mode", const="psc", help="Connect/show corresponding PSC")
    oparser.add_option('-I', '--ipshow', action="store_const", dest="mode", const="ipshow", help="Show IP assignment information")
    oparser.add_option('-L', '--cplicense', action="store_const", dest="mode", const="cplic", help="Update/Add cPanel license for specified hostme & license type [vzzo*,internal,internal-hub]")
    oparser.add_option('-W', '--whmcs', action="store_const", dest="mode", const="whmcs", help="View or manipulate WHMCS license for specified user with action [view*,add,transfer,del]")
    oparser.add_option('--cpdel', action="store_const", dest="mode", const="cplicdel", help="Remove cPanel license for specified IP address")
    oparser.add_option('-V', '--vpprov', action="store_const", dest="mode", const="vpprov", help="Get current provisioning node for specified coast [west,east]")
    oparser.add_option('-S', '--prov', action="store_const", dest="mode", const="sprov", help="Get current shared provisioning server for specified coast [west,east] & type [biz*,res,ld]")
    oparser.add_option('-R', '--dnsreset', action="store_const", dest="mode", const="dnsreset", help="Reset ownership for DNS zone and brand [imh*,hub]")
    oparser.add_option('-P', '--ppopen', action="store_const", dest="mode", const="ppopen", help="Open PowerPanel page for specified user")
    oparser.add_option('-M', '--ppmove', action="store_const", dest="mode", const="ppmove", help="Update PowerPanel with new machine info for user")
    oparser.add_option('-K', '--snm', action="store_const", dest="mode", const="snmkey", help="Use SNM to establish moveuser key between two servers; if USER is supplied, then a move is initiated [FROM_SERVER TO_SERVER [USER [DELAY]]")
    oparser.add_option('-D', '--restoredb', action="store_const", dest="mode", const="restoredb", help="Restore DB from backup node [SERVER USER DBLIST]")
    oparser.add_option('-U', '--vpsup', action="store_const", dest="mode", const="vpsup", help="Upgrade a user from a shared server to a VPS\t\t[USER MACHINE PKGTYPE]")
    oparser.add_option('--use-veid', action="store", dest="use_veid", default=None, metavar='VEID', help="Use an existing VPS in -U/--vpsup mode [VEID]")
    oparser.add_option('--force-rsync', action="store_true", dest="force_rsync", default=False, help="Force the use of rsync in -U/--vpsup mode")
    oparser.add_option('--skip-quotas', action="store_true", dest="skip_quotas", default=False, help="Skip accurate quota calculation when migrating accounts")
    oparser.add_option('--fix-dnsadmin', action="store_true", dest="fix_dnsadmin", default=False, help="Skip dnsadmin fix")
    oparser.add_option('--dnsshow', action="store_const", dest="mode", const="dnsshow", help="Show DNS Authority user and key for given cPanel user [USER]")
    oparser.add_option('-d', '--dnspush', action="store_const", dest="mode", const="dnspush", help="Push DNS Authority key for given cPanel user\t\t[USER [change*,delete]]")
    oparser.add_option('-J', '--cpjump', action="store_const", dest="mode", const="cpjump", help="Use cPJump to jump into a server [USER MACHINE [cpaneld*,whostmgr]]")
    oparser.add_option('--reclaim', action="store_const", dest="mode", const="reclaim", help="Reclamation autosuspension helper")
    oparser.add_option('--slist', action="store_const", dest="mode", const="slist", help="Show list of shared servers")
    oparser.add_option('--hlist', action="store_const", dest="mode", const="hlist", help="Show list of Hub servers")
    oparser.add_option('--vlist', action="store_const", dest="mode", const="vlist", help="Show list of VP nodes")
    oparser.add_option('--full', action="store_true", dest="full", default=False, help="Return all data for server lists")
    oparser.add_option('-m', '--msg', action="store", dest="msg", default=None, help="Add message/note to PowerPanel account")
    oparser.add_option('--note', action="store_true", dest="note", default=False, help="Auto-note the PowerPanel account")
    oparser.add_option('--backupold', action="store_true", dest="backup_old", default=False, help="Use mysql_old when running restoredb action")
    oparser.add_option('--mysqlport', action="store", dest="mysql_port", default="3306", help="mySQL port to bind to on backup node [3306]")
    oparser.add_option('--repair', action="store_true", dest="repair", default=False, help="Run a repair prior to dumping databases")
    oparser.add_option('-s', '--show', action="store_true", dest="show", default=False, help="Show only; don't connect")
    #oparser.add_option('-j', '--json', action="store_true", dest="json", default=False, help="Output data as JSON")
    oparser.add_option('-n', '--nowait', action="store_true", dest="nowait", default=False, help="Do not wait for a response from eDesk (exit immediately)")
    oparser.add_option('-v', '--verbose', action="store_true", dest="verbose", default=False, help="Verbose/debug info")
    oparser.add_option('-x', '--noclip', action="store_true", dest="noclip", default=False, help="Do NOT modify the clipboard")
    oparser.add_option('-X', '--resync', action="store_const", dest="mode", const="resync", help="Resync account across shared servers")

    options, args = oparser.parse_args(sys.argv[1:])
    vout = vars(options)

    if len(args) >= 1:
        vout['server'] = args[0]
    if len(args) >= 2:
        vout['oldserver'] = args[1]
    if len(args) >= 3:
        vout['newserver'] = args[2]
    if len(args) >= 4:
        vout['delay'] = args[3]

    return vout


def show_banner():
    '''
    Display banner
    '''
    print('\n'
          C.CYN + " ***  " + C.WHT + "dkey" + C.OFF
          C.CYN + " ***  " + C.CYN + "Version " + __version__ + " (" + __date__ + ")" + C.OFF
          C.CYN + " ***  " + C.GRN + "J. Hipps <jacob@ycnrg.org>" + C.OFF
          C.CYN + " ***  " + C.GRN + "Sean Combs, Nathan Spiegel" + C.OFF
          C.CYN + " ***  " + C.YEL + "https://ycnrg.org/" + C.OFF +
          '\n')


def fmtsize(insize, rate=False, bits=False):
    '''
    format human-readable file size and xfer rates
    '''
    onx = fabs(insize)
    for unit in ['B', 'K', 'M', 'G', 'T', 'P']:
        if onx < 1024.0:
            tunit = unit
            break
        onx /= 1024.0
    suffix = ''
    if tunit != 'B': suffix = "iB"
    if rate:
        if bits:
            suffix = "bps"
            onx *= 8.0
        else:
            suffix += "/sec"
    if tunit == 'B':
        ostr = "%3d %s%s" % (onx, tunit, suffix)
    else:
        ostr = "%3.01f %s%s" % (onx, tunit, suffix)
    return ostr


def find_latest_log(logdir):
    '''
    find most recent log file in a directory
    '''
    newtime = 0
    newfile = None
    for tfile in os.listdir(os.path.expanduser(logdir)):
        rp = os.path.realpath(os.path.expanduser(logdir)+'/'+tfile)
        ttime = os.stat(rp).st_mtime
        if ttime > newtime:
            newtime = ttime
            newfile = rp
    return newfile


def log_wait(logfile):
    '''
    use the tailer module to watch a file and get the next line
    that's written; will block until a line is received
    '''
    if xopts['verbose']: print("** Watching logfile: %s" % (logfile))
    try:
        with open(logfile, 'r') as tlog:
            stalker = tailer.follow(tlog)
            logline = stalker.next()
    except IOError as e:
        print 'Error: Could not open file ' + logfile + '\n' + e
    return logline


def ssh_to(srvname, srvport=22, srvuser='root'):
    '''
    launch an ssh connection to specified server
    ssh will inherit this script's filehandles
    '''
    xssh = subprocess.Popen(['/usr/bin/ssh', '-o', 'StrictHostKeyChecking=no', '-o',
                             'UserKnownHostsFile=/dev/null', '-p', str(srvport),
                             '%s@%s' % (srvuser, srvname)])
    xssh.communicate()


def sshpass_to(srvname, srvport=22, srvuser='root', srvpass=''):
    '''
    launch an ssh connection to specified server via sshpass
    '''
    newenv = {'PATH': os.environ['PATH'], 'SSHPASS': srvpass}

    options = ['-oStrictHostKeyChecking=no', '-oUserKnownHostsFile=/dev/null']
    if udata.psc_force_sha1:
        options.append('-oKexAlgorithms=diffie-hellman-group1-sha1')
        options.append('-oCiphers=3des-cbc,blowfish-cbc')

    xssh = subprocess.Popen(['/usr/bin/sshpass', '-e', 'ssh'] + options +
                            ['-p', str(srvport), '%s@%s' % (srvuser, srvname)], env=newenv)
    xssh.communicate()


def ping_test(hostaddr, count=2, timeout=1):
    '''
    check to see if the provided host address responds to ping
    return True if responds, False otherwise
    '''
    xping = subprocess.Popen(['/bin/ping', '-W', str(timeout), '-c', str(count), hostaddr],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    xping.communicate()
    xping.wait()
    return not bool(xping.returncode)


def browser_open(url):
    '''
    open URL in browser
    '''
    subprocess.Popen([udata.browser, url],
                     stdout=open(os.devnull, 'w'),
                     stderr=subprocess.STDOUT)


def xexec(args):
    '''
    execute command
    '''
    xex = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return xex.communicate()[0]


def get_user_ip(user, machine):
    '''
    return IP address assigned to user on specified machine
    '''
    iraw = xexec(['fab', '-H', machine, 'user_ip:'+user])
    return iraw.split('=>')[-1].strip()


def get_cookies(domain):
    '''
    get cookies for specified domain name
    '''
    if 'firefox' in udata.srcs:
        return get_cookies_firefox(domain)
    elif 'chrome' in udata.srcs:
        return get_cookies_chrome(domain)
    else:
        print("Error: No cookie source defined. "
              "Define either `srcs.firefox` or `srcs.chrome`.")
        return None


def get_cookies_firefox(domain):
    '''
    get firefox cookies for specified domain name
    '''
    cookpath = os.path.expanduser(udata.srcs['firefox']) + '/cookies.sqlite'

    # copy DB to prevent disk I/O error on Windows
    cookcopy = cookpath+'.copy'
    shutil.copy(cookpath, cookcopy)

    sqx = sqlite3.connect('%s' % (cookcopy))
    cks = sqx.execute('select name,value from moz_cookies where host = "%s"' % (domain)).fetchall()
    cookies = {}
    for cn, cv in cks:
        cookies[cn] = cv
    os.remove(cookcopy)
    return cookies


def get_cookies_chrome(domain):
    '''
    read and decrypt Chrome cookies for specified domain name
    '''
    cookpath = os.path.expanduser(udata.srcs['chrome']+'/Cookies')

    # copy DB to prevent 'database is locked' error
    cookcopy = cookpath+'.copy'
    shutil.copy(cookpath, cookcopy)

    # open SQLite3 database and execute query
    jar = sqlite3.connect(cookcopy)
    oreos = jar.execute('select name,encrypted_value from cookies where host_key like "%%%s%%"' % (domain)).fetchall()

    # decrypt cookies and build output dict
    baked = {}
    for tname, tenc in oreos:
        # check storage version (see os_crypt_linux.cc in Chromium source)
        stversion = tenc[:3]
        if stversion == 'v10':
            try:
                tval = chrome_decrypt(tenc)
            except:
                print("!! Failed to decrypt cookie")
                tval = None
        elif stversion == 'v11':
            #print("!! Unable to decrypt v11-keyed cookies (libsecret/gnome-keyring/kwallet).\n"
            #      "   To re-enable insecure cookie/password storage in Chrome or Chromium, start\n"
            #      "   google-chrome or chromium with --password-store=basic or downgrade to\n"
            #      "   Chrome/Chromium v50, which stores passwords via libsecret, but does not\n"
            #      "   encrypt cookies")
            tval = None
        else:
            # plaintext
            tval = tenc
        baked[tname] = tval

    os.remove(cookcopy)

    return baked


def chrome_decrypt(encval):
    '''decrypt cookie values'''

    secret = 'peanuts'
    salt = b'saltysalt'
    length = 16
    rounds = 1
    iv = b' ' * 16

    # create decryption key & cipher
    key = PBKDF2(secret.encode('utf-8'), salt, length, rounds)
    cipher = AES.new(key, AES.MODE_CBC, IV=iv)

    # clean up junk padding left over from decryption
    def _clean(x): return x[:-ord(x[-1])].decode('utf-8')

    # strip, decrypt, & clean
    decval = _clean(cipher.decrypt(encval[3:]))

    return decval


def xclip_set(instr, ctype='primary', timeout=0, display=None):
    '''
    Set clipboard contents
    '''
    # determine if xsel or xclip is available, with xsel being preferred
    try:
        xsel = xexec(['whereis', '-b', 'xsel']).split(':')[1].split()[0]
        if not xsel:
            xclip = xexec(['whereis', '-b', 'xclip']).split(':')[1].split()[0]
            if not xclip:
                return False
    except Exception as e:
        print("!! Unable to determine availability of xsel or xclip")
        return False

    # set display, if specified
    if display:
        x_display = [display]
    else:
        x_display = []

    try:
        if xsel:
            xex = subprocess.Popen(['xsel', '-t', str(timeout), '--'+ctype, '-i'] + x_display,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   stdin=subprocess.PIPE)
            xex.communicate(instr)
        else:
            xex = subprocess.Popen(['xclip', '-selection', ctype, '-i'] + x_display,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   stdin=subprocess.PIPE)
            xex.communicate(instr)
        return True
    except Exception as e:
        print("!! Failed to manipulate clipboard: [%s] %s" % (str(e.__class__.__name__), str(e)))
        return False


def check_sc_login(text, exit_on_fail=True):
    '''
    Check System Center page content to see if login was successful
    '''
    if re.search(r'Login Required', text, re.I):
        print("!! Authentication Failed. Please login to System Center via your browser (%s), then try again." % (get_active_browser()))
        if exit_on_fail:
            sys.exit(220)
        else:
            return False
    else:
        return True


def check_pp_login(resp, exit_on_fail=True):
    '''
    Check PowerPanel response to see if login was successful
    '''
    if resp.status_code == 401:
        print("!! Authentication Failed. Please double-check pp2.user/pp2.pass in your configuration ('htaccess password')")
        if exit_on_fail:
            sys.exit(221)
        else:
            return False

    if re.search(r'<h2>Login</h2>', resp.text, re.I|re.M):
        print("!! Authentication Failed. Please re-login to PowerPanel in your browser (%s)" % (get_active_browser()))
        if exit_on_fail:
            sys.exit(222)
        else:
            return False

    return True


def check_cpjump_login(resp, exit_on_fail=True):
    '''
    Check cPJump response to see if login was successful
    '''
    if resp.status_code == 401:
        print("!! Authentication Failed. Please double-check userauth.user/userauth.passwd in your configuration (cPjump/dedkey login)")
        if exit_on_fail:
            sys.exit(226)
        else:
            return False

    return True


def get_active_browser():
    '''
    return selected browser (firefox or chrome)
    '''
    if 'firefox' in udata.srcs:
        ubrowser = "Firefox"
    elif 'chrome' in udata.srcs:
        ubrowser = "Chrome"
    else:
        ubrowser = "UNDEFINED"
    return ubrowser


def pwgen(length=16, ichars=string.ascii_letters+string.digits):
    '''
    generate a psuedorandom password
    '''
    return ''.join(random.choice(ichars) for i in range(length))


###############################################################################
# Mode-specific functions
#

def vzmigrate(ctid, oldserver, newserver):
    '''
    migrate container between nodes
    '''
    # build request
    rdata = {'ctid': ctid, 'oldserver': oldserver, 'newserver': newserver}

    # start Requests session
    sc = requests.Session()

    # set up auth & headers
    sc.headers.update({'User-Agent': "Mozilla/5.0 (dkey/%s %s)" % (__version__, __date__)})
    sc.auth = (udata.userauth['user'], udata.userauth['passwd'])

    # send request
    cpj = sc.post('https://cpjump.inmotionhosting.com/migratekeys/process-migrate.php',
                  data=rdata, verify=False)

    # check login
    check_cpjump_login(cpj)

    print("** Queued migration of CTID# %s @ %s --> %s" % (ctid, oldserver, newserver))

    #if not xopts['nowait'] or noauto is True:
    #    print(">> Awaiting response from eDesk...")
    #    edok = log_wait(find_latest_log(udata.srcs['edesk']))
    #    if not re.search(r'migration', edok, re.I|re.M):
    #        print("Received unrecognized response from eDesk. Please check manually.")
    #        return False
    #    else:
    #        print("Migraiton queued successfully:\n\n%s" % (edok))

    return True

def do_cpjump(user, server, service="cpaneld", nojump=False):
    '''
    return cpjump link
    '''
    # build request
    rdata = {'server': server, 'username': user, 'service': service}

    # start Requests session
    sc = requests.Session()

    # set up auth & headers
    sc.headers.update({'User-Agent': "Mozilla/5.0 (dkey/%s %s)" % (__version__, __date__)})
    sc.auth = (udata.userauth['user'], udata.userauth['passwd'])

    # send request
    cpj = sc.post('https://cpjump.inmotionhosting.com/cplogin/', data=rdata, verify=False)

    # check login
    check_cpjump_login(cpj)

    try:
        bs = BeautifulSoup(cpj.text, 'lxml')
        sess_url = re.search(r'window\.open\("([^"]+)', str(bs.script)).group(1)
    except Exception as e:
        print("ERROR: Failed to parse response URL: %s" % (str(e)))
        return None

    if nojump or xopts['show']:
        print("** %s session URL for %s@%s:\n\t%s" % (service, user, server, sess_url))
    else:
        print("** Connecting to %s for %s@%s" % (service, user, server))
        browser_open(sess_url)
    return sess_url

def request_dedkey(mybox, myport=22):
    '''
    request access to dedicated server, wait for key placement, then connect
    '''
    # start Requests session
    sc = requests.Session()

    # set up auth & headers
    sc.headers.update({'User-Agent': "Mozilla/5.0"})
    sc.auth = (udata.userauth['user'], udata.userauth['passwd'])

    # send request
    cpj = sc.post('https://cpjump.inmotionhosting.com/dedtmpkeys/process-dedkey.php',
                  data={'server': mybox, 'port': myport, 'submit': "Submit"}, verify=False)

    # check login
    check_cpjump_login(cpj)

    print("** Queued key placement on %s:%s" % (mybox, myport))

    if not xopts['nowait']:
        print(">> Awaiting response from eDesk...")
        edok = log_wait(find_latest_log(udata.srcs['edesk']))
        if not re.search(r'success', edok, re.I|re.M):
            print("!! Key establish was unsuccessful. Aborting.")
            sys.exit(101)
        else:
            print("** Key established. Connecting to %s:%s..." % (mybox, myport))
            ssh_to(mybox, myport)


def find_vps(veid, retval=False):
    '''
    query IMHSC for VPnode, then connect to it
    '''
    # start Requests session
    sc = requests.Session()

    # import cookies from Firefox
    sc.cookies.update(get_cookies('imhsc.imhadmin.net'))

    # send request
    vpx = sc.post('https://imhsc.imhadmin.net/index.php?v=VPS', data={'selectServer': veid})

    # check if login failed
    check_sc_login(vpx.text)

    # parse with BS4
    bs = BeautifulSoup(vpx.text, "xml")

    try:
        node = bs.tbody.tr.find_all('td')[2].a.string
    except:
        print("!! No results returned for %s" % (veid))
        return None

    print("** vps%s is on node %s" % (veid, node))
    if not xopts['show'] and not retval:
        if udata.set_clipboard is not False and not xopts['noclip']:
            if xclip_set("vzctl enter %s\nsu -\n" % (veid)):
                print("** Added vzctl command to clipboard. Hit Shift+Insert to enter container after connection.")
        print(">> Connecting to %s..." % (node))
        ssh_to(node, srvuser=udata.userauth['user'])

    return node


def find_backup(shost, retval=False):
    '''
    query IMHSC for backup node, then connect to it
    '''
    # start Requests session
    sc = requests.Session()

    # import cookies from Firefox
    sc.cookies.update(get_cookies('imhsc.imhadmin.net'))

    # send request
    vpx = sc.post('https://imhsc.imhadmin.net/index.php?v=Shared', data={'selectServer': shost})

    # check if login failed
    check_sc_login(vpx.text)

    # parse with BS4
    bs = BeautifulSoup(vpx.text, "xml")

    node = None
    if bs.tbody.tr:
        # disk%=7, os=9, cpanel=10, users=17, lan=24, banode=25
        node = bs.tbody.tr.find_all('td')[24].string
        print node
        try:
            baid = str(1800 + int(re.search(r'([0-9]{1,2})$', node).group(1)))
        except:
            print("!! Unable to parse node id")
            baid = '0'

        print("** %s backups are on %s" % (shost, node))
        if not retval and not xopts['show']:
            if udata.set_clipboard is not False and not xopts['noclip']:
                if xclip_set("vzctl enter %s\ncd /mnt/*/%s*\n" % (baid, shost)):
                    print("** Added vzctl command to clipboard. Hit Shift+Insert to enter container after connection.")
            print(">> Connecting to %s..." % (node))
            ssh_to(node, srvuser=udata.userauth['user'])
    else:
        print("!! Server not found: %s" % (shost))

    return node


def find_backup_hub(shost, retval=False):
    '''
    query IMHSC for backup node for Hub, then connect to it
    '''
    # start Requests session
    sc = requests.Session()

    # import cookies from Firefox
    sc.cookies.update(get_cookies('imhsc.imhadmin.net'))

    # send request
    vpx = sc.post('https://imhsc.imhadmin.net/index.php?v=Hub', data={'selectServer': shost})

    # check if login failed
    check_sc_login(vpx.text)

    # parse with BS4
    bs = BeautifulSoup(vpx.text, "xml")

    # disk%=7, os=9, cpanel=10, users=17, lan=24, banode=25
    node = bs.tbody.tr.find_all('td')[24].string

    print("** %s backups are on %s" % (shost, node))

    try:
        baid = str(1800 + int(re.search(r'([0-9]{1,2})$', node).group(1)))
    except:
        print("!! Unable to parse node id")
        baid = '0'

    if not xopts['show'] and not retval:
        if udata.set_clipboard is not False and not xopts['noclip']:
            if xclip_set("vzctl enter %s\ncd /mnt/*/%s*\n" % (baid, shost)):
                print("** Added vzctl command to clipboard. Hit Shift+Insert to enter container after connection.")
        print(">> Connecting to %s..." % (node))
        ssh_to(node, srvuser=udata.userauth['user'])
    return node


def find_backup_node(shost, retval=False, veid=None):
    '''
    query IMHSC for backup node for VPNode, then connect to it
    '''
    # start Requests session
    sc = requests.Session()

    # import cookies from Firefox
    sc.cookies.update(get_cookies('imhsc.imhadmin.net'))

    # send request
    vpx = sc.post('https://imhsc.imhadmin.net/index.php?v=VPNodes', data={'node': shost})

    # check if login failed
    check_sc_login(vpx.text)

    # parse with BS4
    bs = BeautifulSoup(vpx.text, "xml")

    # banode=18
    node = bs.tbody.tr.find_all('td')[18].string

    try:
        baid = str(1800 + int(re.search(r'([0-9]{1,2})$', node).group(1)))
    except:
        print("!! Unable to parse node id")
        baid = '0'

    print("** %s backups are on %s" % (shost, node))
    if not xopts['show'] and not retval:
        if udata.set_clipboard is not False and not xopts['noclip']:
            setok = False
            if veid:
                if xclip_set("vzctl enter %s\ncd /mnt/*/%s*/%s\n" % (baid, shost, veid)):
                    setok = True
            else:
                if xclip_set("vzctl enter %s\ncd /mnt/*/%s*\n" % (baid, shost)):
                    setok = True

            if setok:
                print("** Added vzctl command to clipboard. Hit Shift+Insert to enter container after connection.")
        print(">> Connecting to %s..." % (node))
        ssh_to(node, srvuser=udata.userauth['user'])
    return node


def find_backup_vps(veid, retval=False):
    '''
    find backup node for a particular VPS
    '''
    # find vpnode where container is located
    vpnode = find_vps(veid, retval=True)
    # find banode for vpnode
    banode = find_backup_node(vpnode, retval=retval, veid=veid)
    return banode


def get_prov_shared(coast, stype="biz",showOnly=False):
    '''
    query IMHSC for current provisioning shared server for specified coast
    '''
    if not coast or not re.match(r'(east|west)', coast) or not re.match(r'(biz|ld|res)', stype):
        print("!! Invalid syntax\n")
        print("Usage:")
        print("\tdkey [--show] --prov <east|west> [<biz|ld|res>]")
        print("Examples:")
        print("\tdkey --show --prov east  # this will show current east-coast provisioning shared box")
        print("\tdkey --prov west res  # this will connect to the current west-coast provisioning reseller box\n")
        print("If server type is not specified, 'biz' is used by default\n")
        sys.exit(170)

    coast = coast.lower()

    # start Requests session
    sc = requests.Session()

    # import cookies from Firefox
    sc.cookies.update(get_cookies('imhsc.imhadmin.net'))

    # send request
    vpx = sc.post('https://imhsc.imhadmin.net/index.php?v=Shared&isprov=1')

    # check if login failed
    check_sc_login(vpx.text)

    # parse with BS4
    bs = BeautifulSoup(vpx.text, "xml")

    # server=0 net=4
    for trr in bs.tbody.find_all('tr'):
        tsrv, ttype = re.match(r'(.+)\w*\(([a-z]{2,3})\).*', trr.find_all('td')[0].string).groups()
        tnet = NETMAP.get(re.match(r'.*([A-Z]{1,2}).*', trr.find_all('td')[4].string).group(1), 'unknown')
        if tnet == coast and ttype == stype: break

    tsrv = tsrv.strip()
    print("** Current %s provisioning server for %s coast is %s" % (stype, coast, tsrv))
    if not showOnly:
        print(">> Connecting to %s..." % (tsrv))
        ssh_to(tsrv, srvuser=udata.userauth['user'])
    return tsrv.strip()


def get_prov_node(coast, showOnly=False):
    '''
    query IMHSC for current provisioning VP node for specified coast
    '''
    coast = coast.lower()

    # start Requests session
    sc = requests.Session()

    # import cookies from Firefox
    sc.cookies.update(get_cookies('imhsc.imhadmin.net'))

    # send request
    vpx = sc.post('https://imhsc.imhadmin.net/index.php?v=VPNodes&isprov=1')

    # check if login failed
    check_sc_login(vpx.text)

    # parse with BS4
    bs = BeautifulSoup(vpx.text, "xml")

    # node=0 net=2
    for trr in bs.tbody.find_all('tr'):
        tnode = trr.find_all('td')[0].string
        tnet = NETMAP.get(re.match(r'.*([A-Z]{1,2}).*', trr.find_all('td')[2].string).group(1), 'unknown')
        if tnet == coast: break

    print("** Current provisioning node for %s coast is %s" % (coast, tnode))
    if not xopts['show'] and not showOnly:
        print(">> Connecting to %s..." % (tnode))
        ssh_to(tnode, srvuser=udata.userauth['user'])
    return tnode.strip()

def get_prov_hub(coast, stype="hub", showOnly=False):
    '''
    query IMHSC for current provisioning HUB server for specified coast
    '''
    coast = coast.lower()

    # start Requests session
    sc = requests.Session()

    # import cookies
    sc.cookies.update(get_cookies('imhsc.imhadmin.net'))

    # send request
    vpx = sc.post('https://imhsc.imhadmin.net/index.php?v=Hub&isprov=1')

    # chuck if login failed
    check_sc_login(vpx.text)

    # parse with BS4
    bs = BeautifulSoup(vpx.text, "xml")

    # server=0 net=4
    for trr in bs.tbody.find_all('tr'):
        tsrv = trr.find_all('td')[0].string
        tnet = NETMAP.get(re.match(r'.*([A-Z]{2}).*', trr.find_all('td')[4].string).group(1), 'unknown')
        if tnet == coast: break

    tsrv = tsrv.strip()
    print("** Current %s provisioning server for %s coast is %s" % (stype, coast, tsrv))
    if not showOnly:
        print(">> Connecting to %s..." % (tsrv))
        ssh_to(tsrv, srvuser=udata.userauth['user'])
    return tsrv

def get_list_shared(showOnly=False):
    '''
    query IMHSC for list of all shared servers
    '''
    # start Requests session
    sc = requests.Session()

    # import cookies from Firefox
    sc.cookies.update(get_cookies('imhsc.imhadmin.net'))

    # send request
    vpx = sc.post('https://imhsc.imhadmin.net/index.php?v=Shared')

    # check if login failed
    check_sc_login(vpx.text)

    # parse with BS4
    bs = BeautifulSoup(vpx.text, "xml")

    # server=0 net=2
    slist = []
    for trr in bs.tbody.find_all('tr'):
        try:
            tsrv = re.match(r'(.+) \(', trr.find_all('td')[0].text, re.I).group(1).strip()
        except:
            continue
        slist.append(tsrv)
        if not showOnly:
            print(tsrv)

    return slist


def get_list_hub(showOnly=False):
    '''
    query IMHSC for list of Hub servers
    '''
    # start Requests session
    sc = requests.Session()

    # import cookies from Firefox
    sc.cookies.update(get_cookies('imhsc.imhadmin.net'))

    # send request
    vpx = sc.post('https://imhsc.imhadmin.net/index.php?v=Hub')

    # check if login failed
    check_sc_login(vpx.text)

    # parse with BS4
    bs = BeautifulSoup(vpx.text, "xml")

    # server=0 net=2
    slist = []
    for trr in bs.tbody.find_all('tr'):
        try:
            tsrv = trr.find_all('td')[0].text.strip()
        except:
            continue
        slist.append(tsrv)
        if not showOnly:
            print(tsrv)

    return slist


def get_list_node(showOnly=False, full=False):
    '''
    query IMHSC for list of all VP nodes
    '''
    # start Requests session
    sc = requests.Session()

    # import cookies from Firefox
    sc.cookies.update(get_cookies('imhsc.imhadmin.net'))

    # send request
    vpx = sc.post('https://imhsc.imhadmin.net/index.php?v=VPNodes')

    # check if login failed
    check_sc_login(vpx.text)

    # parse with BS4
    bs = BeautifulSoup(vpx.text, "xml")

    # server=0
    slist = []
    for trr in bs.tbody.find_all('tr'):
        try:
            if full:
                tsrv = {
                        'name': trr.find_all('td')[0].text.strip(),
                        'ip': trr.find_all('td')[2].text.strip(),
                        'lan': trr.find_all('td')[3].text.strip(),
                        'cpus': trr.find_all('td')[4].text.strip(),
                        'memory': trr.find_all('td')[5].text.strip(),
                        'os': trr.find_all('td')[6].text.strip(),
                        'vz': trr.find_all('td')[7].text.strip(),
                        'license': trr.find_all('td')[8].text.strip(),
                        'cap': int(trr.find_all('td')[9].text.strip()),
                        'on': int(trr.find_all('td')[10].text.strip()),
                        'off': int(trr.find_all('td')[11].text.strip()),
                        'disk_used': trr.find_all('td')[12].text.strip(),
                        'disk_free': trr.find_all('td')[13].text.strip(),
                        'psc1': trr.find_all('td')[14].text.strip(),
                        'psc2': trr.find_all('td')[15].text.strip(),
                        'loc': trr.find_all('td')[16].text.strip(),
                        'ra': trr.find_all('td')[17].text.strip(),
                        'ba': trr.find_all('td')[18].text.strip(),
                        'model': trr.find_all('td')[19].text.strip()
                       }
            else:
                tsrv = trr.find_all('td')[0].text.strip()
        except:
            continue
        slist.append(tsrv)
        if not showOnly:
            if full:
                json.dumps(tsrv)
            else:
                print(tsrv)

    return slist


def get_ded_info(server, show=False):
    '''
    get info about a specified dedicated server
    '''
    # start Requests session
    sc = requests.Session()

    # import cookies from Firefox
    sc.cookies.update(get_cookies('imhsc.imhadmin.net'))

    # send request
    vpx = sc.get('https://imhsc.imhadmin.net/index.php',
                 params={'v': "Dedicated", 'selectServer': server})

    # check if login failed
    check_sc_login(vpx.text)

    # parse with BS4
    bs = BeautifulSoup(vpx.text, "xml")

    # server=0 ip=4 net=5 psc=6 user=11 type=14
    trr = bs.tbody.find_all('tr')
    if len(trr) > 0:
        tsrv = {
                'hostname': trr[0].find_all('td')[0].string,
                'ip': trr[0].find_all('td')[2].string,
                'net': trr[0].find_all('td')[3].string,
                'psc': trr[0].find_all('td')[4].a.string,
                'user': trr[0].find_all('td')[9].string,
                'type': trr[0].find_all('td')[12].string,
                'status': trr[0].find_all('td')[13].string.strip()
               }
    else:
        tsrv = None

    if show:
        if tsrv:
            print("[%(hostname)s] IP: %(ip)s (%(net)s) / PSC: %(psc)s / User: %(user)s / Type: %(type)s / Status: %(status)s" % tsrv)
        else:
            print("!! Server '%s' not found" % (server))

    return tsrv


def psc_connect(server=None, psc=None):
    '''
    connect to a dedicated server's PSC
    '''
    # determine server PSC, if not supplied
    if not psc:
        sinfo = get_ded_info(server)
        if not sinfo:
            print("Unable to determine server PSC. Aborting.")
            return False
        else:
            psc = sinfo['psc']

    # connect
    if server:
        print("** PSC for %s is %s" % (server, psc))

    if not xopts['show']:
        print(">> Connecting to %s..." % (psc))
        sshpass_to(psc, srvuser=psc, srvpass=udata.psc_pass)

    return psc


def cplicense(server, ctype="vzzo", action="add"):
    '''
    update cPanel license for specified server
    '''
     # start Requests session
    sc = requests.Session()

    # import cookies from Firefox
    sc.cookies.update(get_cookies('imhsc.imhadmin.net'))

    # allow using a hostname (such as vps or dedicated server hostnames)
    try:
        servip = socket.gethostbyname(server)
    except socket.gaierror as e:
        print("!! %s: %s" % (server, str(e)))
        return None

    # send request
    lresp = sc.post('https://imhsc.imhadmin.net/modules/Datacenter/datacenter_cplic.php',
                    data={'ip': servip, 'type': ctype, 'action': action})

    print(">> %s %s request for %s" % (ctype, action.upper(), servip))
    print("** Got response from SC: %s" % (lresp.text))

    return lresp


def whmcs_license(username=None, lkey=None, action="view"):
    '''
    update WHMCS license for specified user
    '''
    actions_list = ['view', 'add', 'transfer', 'del']

     # start Requests session
    sc = requests.Session()

    # import cookies from Firefox
    sc.cookies.update(get_cookies('imhsc.imhadmin.net'))

    # build request
    action = action.lower()
    if action not in actions_list:
        print("!! Invalid action: %s" % (action))
        print("   Valid actions are: %s" % (', '.join(actions_list)))
        return False

    if action == 'view':
        if username is not None:
            sterm = username
            stype = 'user'
        elif lkey is not None:
            sterm = lkey
            stype = 'key'
        else:
            print("!! Must specify either username or lkey")
            return False

        # send request
        lresp = sc.post('https://imhsc.imhadmin.net/modules/Datacenter/datacenter_whmcslic.php',
                        data={'act': action, 'query': stype, 'term': sterm})

    elif action == 'add':

        # send request
        lresp = sc.post('https://imhsc.imhadmin.net/modules/Datacenter/datacenter_whmcslic.php',
                        data={'act': action, 'user': username})

    elif action == 'del' or action == 'transfer':

        if not lkey:
            # lookup the license first
            kresp = sc.post('https://imhsc.imhadmin.net/modules/Datacenter/datacenter_whmcslic.php',
                            data={'act': 'view', 'query': 'user', 'term': username})
            check_sc_login(kresp.text)

            try:
                ktext = kresp.text.replace('<br />', '\n').replace('<font size="3pt">', '').replace('</font>', '').strip()
                lkey = re.search(r'\WLicense Key: (Leased-.+)\W', ktext, re.I|re.M).group(1)
            except:
                print("!! Unable to determine license key for user")
                return False

        # send request
        lresp = sc.post('https://imhsc.imhadmin.net/modules/Datacenter/datacenter_whmcslic.php',
                        data={'act': action, 'key': license})

    # check login
    check_sc_login(lresp.text)

    # clean up response
    ltext = lresp.text.replace('<br />', '\n').replace('<font size="3pt">', '').replace('</font>', '').strip()

    print("** Got response from SC:\n%s" % (ltext))

    return lresp


def ip_get_blocks():
    '''
    get list of provisioning blocks
    '''
    # start Requests session
    sc = requests.Session()

    # import cookies from Firefox
    sc.cookies.update(get_cookies('imhsc.imhadmin.net'))

    # send request
    vpx = sc.post('https://imhsc.imhadmin.net/index.php?v=IPManager')

    # check if login failed
    check_sc_login(vpx.text)

    # parse with BS4
    bs = BeautifulSoup(vpx.text, "xml")

    # get list of provisioning blocks
    blocklist = []
    for tblk in bs.find_all('table')[3].tr.div.table.find_all('tr'):
        tbx = {
            'id': re.match(r'.+block_id=([0-9]+).*', tblk.find_all('td')[0].a['href']).group(1),
            'prefix': tblk.find_all('td')[0].a.string,
            'block': tblk.find_all('td')[1].string,
            'usage': tblk.find_all('td')[2].string
        }
        blocklist.append(tbx)

    return bs, blocklist


def ip_get_free(net="a"):
    '''
    get free IP addresses from specified network
    '''
    tnet = net.upper()

    # start Requests session
    sc = requests.Session()

    # import cookies from Firefox
    sc.cookies.update(get_cookies('imhsc.imhadmin.net'))

    # send request
    vpx = sc.get('https://imhsc.imhadmin.net/index.php',
                 params={'v': "IPManager", 'net': tnet, 'pool': "12"})

    # check if login failed
    check_sc_login(vpx.text)

    # parse with BS4
    bs = BeautifulSoup(vpx.text, "xml")

    iplist = []
    for tip in bs.table.tbody.find_all('tr'):
        # get IP id
        try:
            t_id = re.match(r'.+id=([0-9]+).+', tip.find_all('td')[8].a['href'], re.I).group(1)
        except:
            t_id = False

        # gather IP infos
        t_info = {
                    'id': t_id,
                    'ip': tip.find_all('td')[0].string,
                    'domain': tip.find_all('td')[1].string,
                    'server': tip.find_all('td')[2].string,
                    'net': tip.find_all('td')[3].string,
                    'user': tip.find_all('td')[5].string,
                    'assigned': tip.find_all('td')[6].string,
                    'edit_url': tip.find_all('td')[8].a['href']
                  }
        iplist.append(t_info)

    return iplist


def ip_get_info(ipaddr, show=False):
    '''
    get IP info from system center
    '''
    # start Requests session
    sc = requests.Session()

    # import cookies from Firefox
    sc.cookies.update(get_cookies('imhsc.imhadmin.net'))

    # send request
    vpx = sc.post('https://imhsc.imhadmin.net/index.php?v=IPManager',
                  data={'type': 'ip', 'query': ipaddr})

    # check if login failed
    check_sc_login(vpx.text)

    # parse with BS4
    bs = BeautifulSoup(vpx.text, "xml")

    # parse results
    trr = bs.table.tbody.find_all('tr')
    if len(trr) > 0:
        # get IP id
        try:
            t_id = re.match(r'.+id=([0-9]+).+', trr[0].find_all('td')[8].a['href'], re.I).group(1)
        except:
            t_id = False

        # gather IP infos
        t_info = {
                    'id': t_id,
                    'ip': trr[0].find_all('td')[0].string,
                    'domain': trr[0].find_all('td')[1].string,
                    'server': trr[0].find_all('td')[2].string,
                    'net': trr[0].find_all('td')[3].string,
                    'usage': trr[0].find_all('td')[4].string,
                    'user': trr[0].find_all('td')[5].string,
                    'assigned': trr[0].find_all('td')[6].string,
                    'note': trr[0].find_all('td')[7].string,
                    'edit_url': trr[0].find_all('td')[8].a['href']
                  }
    else:
        t_info = None

    if show:
        if t_info:
            print("[%(usage)s] %(ip)s (%(net)s) --> %(server)s [User: %(user)s / Domain: %(domain)s / Assigned: %(assigned)s]\n\tNote: %(note)s" % t_info)
        else:
            print("IP address '%s' not found" % (ipaddr))

    return (t_info, bs)


def ip_assign(ip_info, server, notes='', usage="Dedicated IP"):
    '''
    assign IP address and return netmask/gateway
    '''
    # start Requests session
    sc = requests.Session()

    # import cookies from Firefox
    sc.cookies.update(get_cookies('imhsc.imhadmin.net'))

    # build POST request data
    rdata = {
                'id': ip_info['id'],
                'ip': ip_info['ip'],
                'net': ip_info['net'],
                'host': '',
                'server': server,
                'notes': notes,
                'usage': usage,
                'uname': udata.userauth['user']
            }

    # send request for IP
    vpx = sc.post('https://imhsc.imhadmin.net/modules/IPManager/ipm_ipedit.php', data=rdata)

    # parse with BS4
    bs = BeautifulSoup(vpx.text, "lxml")

    # get assignment results
    o_ip = bs.find_all('tr')[0].find_all('td')[1].string
    o_netmask = bs.find_all('tr')[1].find_all('td')[1].string
    o_gateway = bs.find_all('tr')[2].find_all('td')[1].string

    if o_ip != ip_info['ip']:
        print("!! Warning: Requested IP does not match IP from assignment response (%s)" % (o_ip))

    return {'ip': o_ip, 'netmask': o_netmask, 'gateway': o_gateway}


def dnsreset(domain, brand="imh"):
    '''
    use the DNS Authority ownership reset tool in cpjump
    '''
    # request URL
    da_url = 'https://cpjump.inmotionhosting.com/dnsadmin/'

    # start Requests session
    sc = requests.Session()
    sc.auth = (udata.userauth['user'], udata.userauth['passwd'])

    # get CSRF token
    ipage = sc.get(da_url, verify=False)

    # check login
    check_cpjump_login(ipage)

    bs = BeautifulSoup(ipage.text, 'xml')
    csrf_token = bs.find('input', {'id': "csrf_token"}).get('value')

    # build forreal request
    rdata = {'csrf_token': csrf_token, 'domain': domain, 'brand': brand}

    # make request
    try:
        cresp = sc.post(da_url, data=rdata, verify=False)
    except Exception as e:
        print("Failed to send request: %s" % (e))
        sys.exit(100)

    # check response status
    rbs = BeautifulSoup(cresp.text, 'xml')
    rstatus = rbs.find("div", {'class': "errors"}).text.strip()

    print("[%s] %s" % (domain, rstatus))
    return cresp


def snm_keyset(from_server, to_server, user='', new_ip='', delay=''):
    '''
    establish temporary keys between shared servers for moveuser
    '''
    # request URL
    da_url = 'https://cpjump.inmotionhosting.com/moveuser/process-moveuser.php'

    # start Requests session
    sc = requests.Session()
    sc.auth = (udata.userauth['user'], udata.userauth['passwd'])

    # build request
    rdata = {
                'from_server': from_server,
                'to_server': to_server,
                'user': user,
                'new_ip': new_ip,
                'delay': delay
            }

    # make request
    try:
        cresp = sc.post(da_url, data=rdata, verify=False)
    except Exception as e:
        print("Failed to send request: %s" % (e))
        sys.exit(100)

    # check login
    check_cpjump_login(cresp)

    r_ok = False
    try:
        if re.search(r'Account Moves', cresp.text, re.I):
            r_ok = True
    except Exception as e:
        print("Failed validate response: %s" % (e))

    if r_ok:
        if user:
            print("** SNM move request submitted: %s@%s -> %s" % (user, from_server, to_server))
        else:
            print("** Key establish request submitted: %s -> %s" % (from_server, to_server))
    else:
        print("!! Failed to submit key establish or move request")

    return r_ok


def pp_get_account(username=None, domain=None, server=None):
    '''
    pull data from PowerPanel for specified user
    '''
    # build Requests session
    pp = requests.Session()
    pp.auth = (udata.pp2['user'], udata.pp2['pass'])
    pp.cookies.update(get_cookies('secure1.inmotionhosting.com'))

    # build search query
    if username:
        stype = "username"
        sterm = username
    elif domain:
        stype = "domain"
        sterm = domain
    elif server:
        stype = "vpsid"
        sterm = server
    else:
        print("!! No valid search term specified.")
        return None

    # perform search
    srez = pp.post('https://secure1.inmotionhosting.com/admin/account',
                   data={'search_type': stype, 'search': sterm})

    # validate login
    check_pp_login(srez)

    # parse with BeautifulSoup/lxml
    bs = BeautifulSoup(srez.text, "lxml")

    alraw = bs.find_all('table')[2].find_all('tr')
    alraw.pop(0)

    uresult = []
    for tacct in alraw:
        trx = tacct.find_all('td')
        urez = {
                'id': trx[8].a['href'].split('/')[-1].strip(),
                'acct_id': trx[0].text.strip(),
                'username': trx[1].text.strip(),
                'domain': trx[2].text.strip(),
                'status': trx[3].text.strip().lower(),
                'icon': trx[4].img['src'],
                'verify': trx[5].a['href'],
                'technical': trx[6].a['href'],
                'billing': trx[7].a['href'],
                'notes': trx[8].a['href'],
                'url': "https://secure1.inmotionhosting.com" + trx[8].a['href']
               }
        uresult.append(urez)

    return uresult


def pp_get_subs(uid):
    '''
    get account subscriptions
    '''
    # build Requests session
    pp = requests.Session()
    pp.auth = (udata.pp2['user'], udata.pp2['pass'])
    pp.cookies.update(get_cookies('secure1.inmotionhosting.com'))

    # build request
    braw = pp.get('https://secure1.inmotionhosting.com/admin/cpbilling/cpid/%s' % (uid))

    # validate login
    check_pp_login(braw)

    # parse with BeautifulSoup/lxml
    bs = BeautifulSoup(braw.text, 'lxml')

    # get subscription list
    subs = bs.find_all('tr', {'class': "mainSubscription"})

    def _safeget(klist, kindex, fix_spaces=True, always_string=False):
        try:
            if fix_spaces:
                vout = klist[kindex].text.replace(u'\xa0', ' ').strip()
            else:
                vout = klist[kindex].text.strip()
        except IndexError:
            if always_string:
                vout = ''
            else:
                vout = None
        return vout

    slist = []
    for tsub in subs:
        tsr = tsub.find_all('td')

        # get admin URL (for hosting bill items)
        if tsr[2].a is not None:
            admin_url = tsr[2].a['href']
        else:
            admin_url = None

        # get edit url
        try:
            if tsr[6].find_all('li')[5].text == u'Edit':
                edit_url = tsr[6].find_all('li')[5].a['href']
            else:
                edit_url = None
        except:
            edit_url = None

        # get subscription id
        if edit_url:
            try:
                sid = re.search(r'/cid/([0-9]+)/', edit_url).group(1)
            except:
                sid = None
        else:
            sid = None

        # get details
        tsx = {
                'id': sid,
                'domain': _safeget(tsr, 0),
                'name': _safeget(tsr, 1).split('  ')[0].strip(),
                'admin_url': admin_url,
                'term': _safeget(tsr, 3),
                'cost': _safeget(tsr, 4),
                'price': _safeget(tsr, 5),
                'edit_url': edit_url
              }

        slist.append(tsx)

    return slist


def pp_get_item(edit_url):
    '''
    get bill item infos
    '''
    # build Requests session
    pp = requests.Session()
    pp.auth = (udata.pp2['user'], udata.pp2['pass'])
    pp.cookies.update(get_cookies('secure1.inmotionhosting.com'))

    # build request
    braw = pp.get('https://secure1.inmotionhosting.com%s' % (edit_url))

    # validate login
    check_pp_login(braw)

    # parse with BeautifulSoup/lxml
    bs = BeautifulSoup(braw.text, 'lxml')

    # parse form values
    inps = bs.find('div', {"id": "ppr_main"}).find_all('input')
    sels = bs.find('div', {"id": "ppr_main"}).find_all('select')

    def get_data_center_id(xval):
        '''return datacenter ID or None if missing'''
        try:
            xout = xval.find('option', {'selected': "selected"})['value']
        except:
            xout = None
        return xout

    # build existing form data
    fdata = {
                'product_name': inps[0]['value'],
                'product_id': sels[0].find('option', {'selected':"selected"})['value'],
                'term_length': inps[1]['value'],
                'term_type': inps[2]['value'],
                'amount': inps[3]['value'],
                'username': inps[4]['value'],
                'domain': inps[5]['value'],
                'machine': inps[6]['value'],
                'data_center_id': get_data_center_id(sels[1]),
                'expiration_date': inps[7]['value'],
                'status': sels[2].find('option', {'selected':"selected"})['value']
            }

    return fdata


def pp_update_item(edit_url, **kwargs):
    '''
    update bill item with new info
    '''
    # build Requests session
    pp = requests.Session()
    pp.auth = (udata.pp2['user'], udata.pp2['pass'])
    pp.cookies.update(get_cookies('secure1.inmotionhosting.com'))

    # retrieve existing data
    fdata = pp_get_item(edit_url)

    # update form data with kwargs
    fdata.update(kwargs)

    # then post update
    bpost = pp.post('https://secure1.inmotionhosting.com%s' % (edit_url), data=fdata)

    return bpost


def pp_open_account(user):
    '''
    open user's PowerPanel account in new browser window/tab
    '''
    url_base = "https://secure1.inmotionhosting.com"

    # find in PowerPanel
    prez = pp_get_account(user)

    if len(prez) >= 1:
        xurl = "%s%s" % (url_base, prez[0]['notes'])
    else:
        xurl = None

    if xurl:
        print("Opening URL: %s" % (xurl))
        browser_open(xurl)
    else:
        print("Account not found")

    return xurl


def pp_update_machine(user, machine):
    '''
    update machine name in PowerPanel for specified user/account
    '''
    # get account
    # get account and find best candidate
    alist = pp_get_account(user)
    acct = None
    for ta in alist:
        if ta['status'] == 'active':
            acct = ta
            break

    if not acct:
        print("!! Unable to determine account ID")
        return None

    # get subs
    subs = pp_get_subs(acct['id'])

    # filter hosting subs
    hostings = filter(lambda x: x['edit_url'], subs)

    # find matching hosting sub
    target = None
    for th in hostings:
        tdata = pp_get_item(th['edit_url'])
        if tdata['username'] == user:
            target = tdata
            target['edit_url'] = th['edit_url']
            break

    # pp_open_account(user)

    if target:
        uprez = pp_update_item(target['edit_url'], machine=machine)
        if uprez.status_code == 200:
            # show info to help populate move notice
            (move_url, new_ip) = pp_get_move_helpers(acct['id'], user, machine)
            print("User       : %s" % (user))
            print("Old Machine: %s" % (target['machine']))
            print("New Machine: %s" % (machine))
            print("IP         : %s" % (new_ip))

            #if xopts['msg']:
                # add a note to the account if a message was defined by user
                # pp_add_note(acct['notes'], xopts['msg'], mtype="Account Move", flag=1)
            #elif xopts['note']:
                # auto-add a note to the account if --note was used
                #pp_add_note(acct['notes'], "%s => %s" % (target['machine'], machine),
                            #mtype="Account Move", flag=1)

            # open browser to send move notice
            browser_open(move_url)
            return True
        else:
            print("!! Failed to update bill item. Fix manually: %s" % (acct['url']))
            return False


def pp_get_move_helpers(acctid, user, machine):
    '''
    build a PP email URL for sending move emails, and new acct IP (shared)
    '''
    if re.match(r'^(ec)?(biz|ld)', machine):
        move_url = 'https://secure1.inmotionhosting.com/admin/emailview/id/%s/emailid/1' % (acctid)
        new_ip = get_user_ip(user, machine)
    elif re.match(r'^(ec)?res', machine):
        move_url = 'https://secure1.inmotionhosting.com/admin/emailview/id/%s/emailid/525' % (acctid)
        new_ip = get_user_ip(user, machine)
    elif re.match(r'^vps', machine):
        move_url = 'https://secure1.inmotionhosting.com/admin/emailview/id/%s/emailid/101' % (acctid)
        new_ip = socket.gethostbyname(machine)
    elif re.match(r'^(ded|cc|elite|advanced|dedicated)', machine):
        move_url = 'https://secure1.inmotionhosting.com/admin/emailview/id/%s/emailid/107' % (acctid)
        new_ip = socket.gethostbyname(machine)
    else:
        print("Unable to determine plan type from machine name")
        move_url = 'https://secure1.inmotionhosting.com/admin/emailview/id/%s/emailid/1' % (acctid)
        new_ip = '0.0.0.0'

    return (move_url, new_ip)


def pp_add_note(note_url, msg, method="None - Internal", mtype="Other", flag=0):
    '''
    add note to PP account
    '''
    req_uri = "https://secure1.inmotionhosting.com%s" % (note_url)

    # build Requests session
    pp = requests.Session()
    pp.auth = (udata.pp2['user'], udata.pp2['pass'])
    pp.cookies.update(get_cookies('secure1.inmotionhosting.com'))
    pp.headers.update({'referer': req_uri})

    # build form request
    fdata = {
                'comment': msg,
                'method': method,
                'type': mtype,
                'flag': flag,
                'send_to_cc': 0,
                'submit': "Add Note"
            }
    # then post update
    bpost = pp.post(req_uri, data=fdata)

    # validate login
    check_pp_login(bpost)

    if bpost.status_code == 200 or bpost.status_code == 302:
        print("Note posted OK")
    else:
        print("!! Failed to post note to account")

    return bpost


def pp_get_admin_data(admin_url):
    '''
    retrieve and parse data from admin page
    '''
    # build Requests session
    pp = requests.Session()
    pp.auth = (udata.pp2['user'], udata.pp2['pass'])
    pp.cookies.update(get_cookies('secure1.inmotionhosting.com'))

    # make request
    braw = pp.get("https://secure1.inmotionhosting.com%s" % (admin_url))

    # parse with BS4
    bs = BeautifulSoup(braw.text, 'lxml')

    # parse key/value pairs
    adata = {}
    for ti in bs.find('div', attrs={'class':"single"}).table.find_all('tr'):
        tname = ti.find_all('td')[0].text.replace(':', '').replace(' ', '_').lower()
        tval = ti.find_all('td')[1].text.strip()
        adata[tname] = tval

    # parse dnsadmin data, which is stored in a hidden div
    dak = {'username': None, 'key': None}
    try:
        dak['username'] = bs.find('div', {'id':"key_dialog"}).find_all('p')[0].text.split(':')[1].strip()
        dak['key'] = bs.find('div', {'id':"key_dialog"}).find_all('p')[1].text.split(':')[1].strip()
    except:
        print("!! Failed to parse DNSAdmin data")

    adata['dnsadmin'] = dak
    return adata


def pp_dns_key_request(user_id, plan_id, action='change'):
    '''
    send request for dnsadmin key for account from PowerPanel
    '''
    # build Requests session
    pp = requests.Session()
    pp.auth = (udata.pp2['user'], udata.pp2['pass'])
    pp.cookies.update(get_cookies('secure1.inmotionhosting.com'))

    # build POST data
    pdata = {'id': user_id, 'pid': plan_id, 'keyAction': action}

    # make request
    braw = pp.post("https://secure1.inmotionhosting.com/power-panel-js/admin-admin-details/submit-dns-key-request/", data=pdata)
    presp = braw.json()

    return presp


def pp_get_dnsadmin_key(username, silent=False):
    '''
    retrieve dnsadmin username and key from PowerPanel
    '''
    alist = pp_get_account(username)
    acct = None
    for ta in alist:
        if ta['status'] == 'active':
            acct = ta
            break

    if not acct:
        print("!! Unable to determine account ID")
        return None

    subs = pp_get_subs(acct['id'])

    hasuser = False
    for ts in subs:
        if 'admin_url' in ts:
            tsub = pp_get_admin_data(ts['admin_url'])
            if tsub['cpanel_username'] == username:
                tdata = ts
                hasuser = True
                break

    if hasuser is False:
        return None

    pp_dns_key_request(acct['id'], tdata['id'], action='change')

    if not silent:
        print("** DNSadmin User: %s" % (tsub['dnsadmin']['username']))
        print("** DNSadmin Key : %s" % (tsub['dnsadmin']['key']))

    return tsub['dnsadmin']


def pp_push_dnsadmin_key(username, action="change", silent=False):
    '''
    push/renew dnsadmin key for user from PowerPanel
    '''
    alist = pp_get_account(username)
    acct = None
    for ta in alist:
        if ta['status'] == 'active':
            acct = ta
            break

    if not acct:
        print("!! Unable to determine account ID")
        return None

    subs = pp_get_subs(acct['id'])

    hasuser = False
    for ts in subs:
        if 'admin_url' in ts:
            tsub = pp_get_admin_data(ts['admin_url'])
            if tsub['cpanel_username'] == username:
                tdata = ts
                hasuser = True
                break

    if not hasuser:
        return None

    # send update request
    presp = pp_dns_key_request(acct['id'], tdata['id'], action)

    # retrieve new key
    tsub = pp_get_admin_data(tdata['admin_url'])

    if not silent:
        if presp['message'] is not None:
            chkmsg = ' - "%s"' % (presp['message'])
        else:
            chkmsg = ''

        if presp['data']['status'] is not None:
            chgstat = DASTATMAP.get(int(presp['data']['status']), 'Unknown Status')
        else:
            chgstat = 'Invalid operation'

        print("** Key %s status: %s status=%s (%s%s)" % (action, presp['status'], presp['data']['status'], chgstat, chkmsg))
        print("** DNSadmin User: %s" % (tsub['dnsadmin']['username']))
        print("** DNSadmin Key : %s" % (tsub['dnsadmin']['key']))

    rval = {'resp': presp, 'username': tsub['dnsadmin']['username'], 'key': tsub['dnsadmin']['key']}
    return rval


def make_xfer_config(hostname, identfile, user='root'):
    '''
    create an ssh_config file for transfer
    '''
    xc = ''
    xc += "Host %s\n" % (hostname)
    xc += "Hostname %s\n" % (hostname)
    xc += "User %s\n" % (user)
    xc += "IdentityFile %s\n" % (identfile)
    xc += "Compression yes\n"
    xc += "StrictHostKeyChecking no\n"
    xc += "UserKnownHostsFile /dev/null\n"
    return xc


def upgrade_vps(user, machine, package="1KHA", fix_dnsadmin=False, use_veid=None, max_acct_size=15030000000, skip_quotas=False):
    '''
    Provision a new VPS of type package, then transfer user@machine,
    along with any subaccounts, to the new VPS. Set use_veid to manually select a VPS
    (for example, to continue a previous failed migration)
    returns True on success, False on failure
    '''
    cp = WHMAPI(machine)

    # get account info
    acresp = cp.whm('accountsummary', user=user)
    if isinstance(acresp, dict):
        if acresp.get('cpanelresult', None):
            if acresp['cpanelresult'].get('error', None):
                print("!! Failed to communicate with WHMAPI: %s" % (acresp['cpanelresult']['error']))
                return False

        if int(acresp.get('status', 0)) == 0:
            print("!! Failed to retrieve account summary from %s (does user exist?)" % (machine))
            return False
        else:
            acdata = acresp['acct'][0]
            print("** Primary account: %s@%s / %s / %s" % (user, machine, acdata['domain'], acdata['plan']))
    else:
        print("!! Failed to communicate with WHMAPI")
        return False

    xlist = [{'user': user, 'domain': acdata['domain'], 'size': -1, 'size_hr': '', 'rsync': False, 'child': False}]

    # enumerate child accounts
    print(">> Retrieving account information...")
    calist = cp.whm('listaccts', searchtype='owner', search=user)['acct']
    for tca in calist:
        xlist.append({'user': tca['user'], 'domain': tca['domain'], 'size': -1, 'size_hr': '', 'rsync': False, 'child': True})

    # retrieve disk usage for all accounts
    for ti, tca in enumerate(xlist):
        # use fab task that parses `quota` output on server (fast, less accurate)
        try:
            acctsize = int(xexec(['fab', '--hide=status', '-H', machine, 'get_quota_usage:'+tca['user']]).strip())
            if acctsize > 0:
                acctsize *= 1024
        except ValueError:
            acctsize = -1

        # use fetchdiskusage cpapi function if no fs quotas (slow, more accurate)
        if acctsize == -1:
            if not skip_quotas:
                udisk = cp.cpanel('DiskUsage', 'fetchdiskusage', user=tca['user'])
                if udisk is None or 'error' in udisk:
                    print("!! Failed to retrieve disk usage for %s" % (tca['user']))
                    acctsize = max_acct_size + 1
                else:
                    acctsize = int(udisk[0]['contained_usage'])
            else:
                acctsize = 0

        xlist[ti]['size'] = acctsize
        xlist[ti]['size_hr'] = fmtsize(acctsize)
        xlist[ti]['rsync'] = bool(acctsize > max_acct_size)
        if xopts['force_rsync']:
            xlist[ti]['rsync'] = True

    # display list of accounts
    for tca in xlist:
        print("\t%s -- %s (use_rsync=%s) -- %s" % (tca['user'], tca['size_hr'], tca['rsync'], tca['domain']))

    # determine coast from source machine
    if re.match(r'^ec.+', machine):
        coast = 'east'
    else:
        coast = 'west'

    # get provisioning node
    provnode = get_prov_node(coast, showOnly=True)
    print(">> Provisioning new VPS %s on %s..." % (package, provnode))

    # connect to node
    msh = MoonShell(provnode, username=udata.userauth['user'])

    if use_veid:
        # choose a VPS manually (eg. if previous restore failed part-way through)
        veid = use_veid
        vpsname = 'vps' + veid
        try:
            veip = socket.gethostbyname(vpsname)
        except socket.gaierror:
            print("Unable to determine IP address for %s. Is forward DNS configured properly?" % (vpsname))
            return False

        print("** Using container %s on %s" % (veid, provnode))
    else:
        # provision a new VPS
        pdata = msh.run("provision --package=%s" % (package))
        try:
            if re.search(r'No available clones', pdata, re.I):
                print("!! No available clones. Please contact T3. Aborting.")
                return False
            veid = re.search(r'VEID: ([0-9]{4,6})', pdata, re.I).group(1)
            veip = re.search(r'IP: ([0-9]{1,3}.+)', pdata, re.I).group(1)
            vpsname = 'vps'+veid
        except Exception as e:
            print("!! Unable to determine VEID of provisioned container")
            return False

        print("** Provisioned container %s on %s" % (veid, provnode))

    # while the container is starting, start packaging the account(s)
    # on the shared server
    for ti, tca in enumerate(xlist):
        sys.stdout.write(">> Packaging account %s on %s... " % (tca['user'], machine))
        sys.stdout.flush()
        if tca['rsync']:
            pkout = xexec(['fab', '--hide=status', '-H', machine, 'pkgacct:'+tca['user']+',--skiphomedir'])
        else:
            pkout = xexec(['fab', '--hide=status', '-H', machine, 'pkgacct:'+tca['user']])

        if not re.search(r'successfully', pkout, re.I):
            print("FAIL")
            print("!! Failed to package account")
            xlist[ti]['pkgacct'] = False
        else:
            print("OK")
            xlist[ti]['pkgacct'] = True

    # get server's main IP
    ship = xexec(['fab', '--hide=status', '-H', machine, 'get_main_ip']).strip()
    print("** %s main IP: %s" % (machine, ship))

    # check if the container is CE7
    if re.search(r' 7\.[2-9]', msh.run("head -1 /etc/redhat-release"), re.I):
        is_ce7 = True
    else:
        is_ce7 = False

    # meanwhile on the node... switch into the new container
    if not re.search(r'entered into Container', msh.run("vzctl enter %s" % (veid)), re.I):
        print("!! Failed to enter into container")
        return False
    else:
        xo = msh.run("su -")
        msh.run('')
        print("** Entered container %s" % (veid))

    # wait until rc.d for runlevel 3 has finished loading
    sys.stdout.write(">> Waiting for VPS to complete startup...")
    sys.stdout.flush()
    while 1:
        if is_ce7:
            xo = msh.run("systemctl is-active multi-user.target")
            if not re.search(r'inactive', xo, re.I):
                print(' OK')
                break
        else:
            xo = msh.run("pgrep -fl 'rc.d/rc 3'")
            if not re.search(r'rc.d', xo, re.I):
                print(' OK')
                break
        # wait and wait again
        sys.stdout.write('.')
        sys.stdout.flush()
        time.sleep(2)

    # remove from firewall (in case this is a re-attempt)
    # we don't really care if it was successful or not
    msh.run("apf -u %s" % (ship))

    # then add the IP to firewall
    xo = msh.run("apf -a %s" % (ship))
    if not re.search(r'added allow all', xo, re.I):
        print("!! Failed to add ALLOW rule via APF to firewall: %s" % (xo))
        return False
    else:
        print("** %s" % (xo))

    # generate & set root pass
    rootpass = pwgen()
    if not msh.set_passwd(rootpass):
        print("!! Failed to set root password")
        return False
    else:
        print("** Root password set: %s" % (rootpass))

    # ensure any previous botched attempts are wiped clean
    # (otherwise ssh-keygen will sit there waiting for prompt, and we'll timeout)
    msh.run("\\rm -f xferkey{,.pub}")

    # generate ssh keypair
    xo = msh.run("ssh-keygen -t rsa -b 2048 -N '' -f xferkey")
    if not re.search(r'key fingerprint', xo, re.I|re.M):
        print("!! Failed to generate SSH keypair")
        return False
    else:
        sshkey = msh.run("cat xferkey")
        if not re.search(r'RSA PRIVATE KEY', sshkey, re.M):
            print("!! Failed to retrieve generated private key from /root/xferkey")
            return False
        print("** Generated SSH keypair: /root/xferkey & /root/xferkey.pub")

    # Create .ssh folder
    msh.run("mkdir /root/.ssh")
    print("** Created /root/.ssh")

    # Update/Validate cPanel license key
    msh.run("/usr/local/cpanel/cpkeyclt")
    print ("** cPanel license activated")

    # authorize public KEY
    if msh.run("cat xferkey.pub > /root/.ssh/authorized_keys").strip() != '':
        print("!! Failed to add public key to authorized_keys")
        return False
    else:
        print("** Added public key to /root/.ssh/authorized_keys")

    # create ssh_config, then place key & config on source shared server
    xkpath = "/home/%s/xferkey_%s" % (udata.userauth['user'], user)
    xcpath = "/home/%s/xferconf_%s" % (udata.userauth['user'], user)
    ssh_config = make_xfer_config(vpsname, xkpath)

    # open sftp connection to shared server to place the key & config
    print(">> Copying ssh_config and transfer key to %s..." % (machine))
    msftp = MoonSFTP(machine, username=udata.userauth['user'])
    msftp.put_string(xkpath, sshkey, perms=0o0600)
    msftp.put_string(xcpath, ssh_config, perms=0o0644)
    msftp.close()

    # transfer package via SCP
    print(">> Transferring packages")
    for ti, tca in enumerate(xlist):
        sys.stdout.write(">> Transferring %s (%s)..." % (tca['user'], tca['size_hr']))
        sys.stdout.flush()
        if not xlist[ti]['pkgacct']:
            print("SKIPPED")
            xlist[ti]['xfer'] = False
        else:
            xres = xexec(['fab', '--hide=status', '-H', machine, 'xferpkg:%s,%s,%s' % (tca['user'], xcpath, vpsname)])

            if not re.search(r'success', xres, re.I|re.M):
                print("FAIL")
                print(xres)
                print("!! Failed to transfer package to new server")
                xlist[ti]['xfer'] = False
            else:
                print("OK")
                xlist[ti]['xfer'] = True

    # check if mysql is up and running; (re)start if necessary
    if re.search(r'cannot stat', msh.run("stat /var/lib/mysql/mysql.sock"), re.I|re.M):
        print(">> mySQL not running; attempting to start...")
        msh.run("service mysql restart")
        if re.search(r'cannot stat', msh.run("stat /var/lib/mysql/mysql.sock"), re.I|re.M):
            print("!! Failed to start mySQL. Aborting.")
            return False
        else:
            print("** mySQL started OK")
    else:
        print("** mySQL is UP")

    # check if cPanel is up and running
    if not re.search(r'[0-9]+\s*cpsrvd', msh.run("pgrep -fl cpsrvd"), re.I|re.M):
        print(">> cPanel not running; attempting to start...")
        msh.run("service cpanel restart")
        if not re.search(r'[0-9]+\s*cpsrvd', msh.run("pgrep -fl cpsrvd"), re.I|re.M):
            print("!! Failed to start cPanel. Aborting.")
            return False
        else:
            print("** cPanel started OK")
    else:
        print("** cPanel is UP")

    # restore package on VPS
    print(">> Restoring packages")
    for ti, tca in enumerate(xlist):
        xo = msh.run_wait("/scripts/restorepkg /home/cpmove-%s.tar.gz" % (tca['user']), "Restoring package for %s" % (tca['user']))
        if not re.search(r'success\.', xo, re.I|re.M):
            print("FAIL")
            print(xo)
            print("!! Package restore failed. Restore manually. Aborting.")
        else:
            print("OK")

    # rsync any large accounts
    print(">> Rsync'ing large accounts")
    for ti, tca in enumerate(xlist):
        if tca['rsync']:
            sys.stdout.write(">> rsync homedir for %s (%s)..." % (tca['user'], tca['size_hr']))
            sys.stdout.flush()
            xres = xexec(['fab', '--hide=status', '-H', machine, 'rsync_homedir:%s,%s,%s' % (tca['user'], xcpath, vpsname)])

            if not re.search(r'success', xres, re.I|re.M):
                print("FAIL")
                print(xres)
                print("!! Failed to rsync homedir to new server")
                xlist[ti]['xfer'] = False
            else:
                # run fixperms
                print("OK")
                xlist[ti]['xfer'] = True

    # run fixperms on rsync'd accounts
    print(">> Running fixperms on rsync'd accounts")
    for ti, tca in enumerate(xlist):
        if tca['rsync']:
            msh.run_wait("fixperms %s" % (tca['user']), "Running fixperms for %s" % (tca['user']))
            print("OK")

    # fix account ownership and package
    print(">> Modifying reseller user account...")
    xo = msh.run("/opt/dedrads/modify-account %s -r -o %s -p vps -a vps" % (user, user))
    if not re.search(r'complete for', xo, re.I|re.M):
        print(xo)
        print("!! Account modification failed. Aborting.")
        return False

    # fix ownership for child accounts
    for ti, tca in enumerate(xlist):
        if tca['child']:
            sys.stdout.write(">> Setting ownership for %s..." % (tca['user']))
            sys.stdout.flush()
            xo = msh.run("/opt/dedrads/modify-account %s -o %s" % (tca['user'], user))
            if not re.search(r'account modified', xo, re.I|re.M):
                print("FAIL")
                print(xo)
                print("!! Account modification failed. Check manually.")
            else:
                print("OK")

    # update bill item in PowerPanel and launch email window
    print(">> Updating customer bill item & launching email window...")
    try:
        pp_update_machine(user, vpsname)
    except Exception as e:
        print("!! pp_update_machine threw exception: %s" % (e))

    # push DNS authority key from PowerPanel
    print(">> Requesting new DNS authority key from PowerPanel...")
    pp_push_dnsadmin_key(user)

    # run dnsadmin fix on server (optionally)
    if fix_dnsadmin:
        print(">> Running DNSadmin fix...")
        msh.run("yum -y install imh-cpanel-dnsadmin")
        msh.run("RUSER=$(\\ls -1 /var/cpanel/cluster | grep -v root) ; pkill -9 dnsadmin ; rm -Rf /var/cpanel/clusterqueue/status/imh* ; rm -Rf /var/cpanel/cluster/root ; mv /var/cpanel/cluster/$RUSER /var/cpanel/cluster/root ; /scripts/restartsrv_dnsadmin")
    else:
        print(">> Skipping DNSadmin fix...")

    # sync all zones to cluster
    print(">> Syncing all DNS zones to cluster...")
    xo = msh.run("/scripts/dnscluster syncall")
    if not re.search(r'done', xo, re.I|re.M):
        print(xo)
        print("!! Failed to run dnscluster syncall")

    # schedule user suspension on shared server
    xo = xexec(['fab', '--hide=status', '-H', machine, 'sched_suspend_user:%s,2d' % (user)])
    if not re.search(r'suspended user', xo, re.I):
        print(xo)
        print("!! Failed to schedule suspension on %s. Schedule manually." % (machine))
    else:
        print("** Scheduled suspension of account %s@%s in 2 days" % (user, machine))

    # perform completion checks
    print(">> Performing completion checks...")
    mdig = MoonDig()
    for ti, tca in enumerate(xlist):
        xc = mdig.query(tca['domain'])
        if xc is None:
            xcpass = "SERVFAIL"
        else:
            if xc[-1] == veip:
                xcpass = "OK"
            else:
                xcpass = "FAIL"
        print("** %s -> %s [%s]" % (tca['domain'], xc[-1], xcpass))

    # print out summary info
    print("\n\n******** Move Summary ********")
    print("cPanel User : %s" % (user))
    print("Hostname    : %s" % (vpsname))
    print("IP Address  : %s" % (veip))
    print("Root passwd : %s" % (rootpass))
    print("*******************************\n")

    msh.close()


def get_acct_data(user, machine):
    '''
    get user account info from server
    '''
    iraw = xexec(['fab', '--hide=status', '-H', machine, 'get_acct_json:'+user])
    iraw = re.sub('Last login.*(\r\n|$)','',iraw,re.M)
    try:
        acdata = json.loads(iraw)
    except:
        acdata = None

    return acdata


def domain_mx_check(domain):
    '''
    check MX records and mail subdomain
    '''
    mxl = []
    try:
        for tmx in dns.resolver.query(domain, 'MX'):
            mxl.append((tmx.preference, tmx.exchange.to_text()))
    except:
        return None

    return mxl

def pdesk_notice_fails(limit=None):
    # get list of tickets on first paage
    pdata = pdesk_get_tickets2()
    ticklist = pdata['rows']

    if limit:
        limit = int(limit)

    tcount = 0
    for tt in ticklist:
        if re.search(r'Failed to send move notice', tt['subject'], re.I):
            if tt['status'] == 'OPEN' and tt['owner'] == '':
                tcount += 1
                print tt
                print tcount
                # parse user from subject
                user = tt['subject'].split()[6]
                turi = 'https://systemtasks.inmotionhosting.com/cgi-bin/staff.cgi?do=ticket&cid=%d' % (tt['id'])

                pp_open_account(user)
                browser_open(turi)
                resp = raw_input("Do you want to Update the Machine? (n, or machine name)")
                if resp != "n":
                    pp_update_machine(user,resp)
                if tcount >= limit:
                    break

def pdesk_get_tickets2(department=47, page=1, group='Unresolved'):
    '''
    retrieve list of tickets from SystemTasks pDesk
    '''
    # build Requests session
    st = requests.Session()
    st.cookies.update(get_cookies('systemtasks.inmotionhosting.com'))
    st.cookies.update(udata.pdesk)
    st.headers.update({'Referer': "https://systemtasks.inmotionhosting.com/cgi-bin/staff.cgi",
                        'X-Requested-With': "XMLHttpRequest",
                        'User-Agent': udata.pdesk['agent'] })

    # build request
    fdata = {
                'do': "listtickets",
                'dep': str(department),
                'group': group,
                'sort': "ticket_id",
                'sortdir': "desc",
                'page': str(page)
            }

    # Send request
    sresp = st.post('https://systemtasks.inmotionhosting.com/cgi-bin/ajax.cgi', data=fdata)

    # Check response and parse JSON
    if sresp.status_code != 200:
        print("!! pDesk request failed")
        return None

    rjson = sresp.json()

    # validate login
    if 'error' in rjson:
        print("!! pDesk error: %s" % (rjson['error']))
        return None

    return rjson


def pdesk_check_fails(limit=None):
    '''
    check first page of autosuspend failures
    '''
    # get list of tickets on first page
    pdata = pdesk_get_tickets()
    ticklist = pdata['rows']

    if limit:
        limit = int(limit)

    mdig = MoonDig(nslist=[])

    tcount = 0
    for tt in ticklist:
        if re.search(r'autosuspend failure', tt['subject'], re.I):
            tcount += 1
            if tt['status'] == 'OPEN' and tt['owner'] == '':
                # parse user/server from subject
                smat = re.match(r'^\[Autosuspend failure\] ([^ ]+) ([^ ]+)', tt['subject'], re.I)
                tuser = smat.group(1).strip()
                tserv = smat.group(2).strip()
                turi = 'https://systemtasks.inmotionhosting.com/cgi-bin/staff.cgi?do=ticket&cid=%d' % (tt['id'])

                # check user status on server
                tacct = get_acct_data(tuser, tserv)
                tmxers = None
                if tacct is None:
                    tsus = C.GRN + 'ACCOUNT DOES NOT EXIST' + C.OFF
                else:
                    if tacct['suspended']:
                        tsus = C.GRN + tacct['suspendreason'] + C.OFF
                    else:
                        tsus = C.RED + "NOT SUSPENDED" + C.OFF
                        tmxers = domain_mx_check(tacct['domain'])
                        try:
                            mip = socket.gethostbyname('mail.'+tacct['domain'])
                            tmailip = C.WHT+'mail.'+tacct['domain']+' -> '+mip+C.OFF
                        except:
                            tmailip = C.YEL+'NXDOMAIN'+C.OFF

                    try:
                        tdomip = socket.gethostbyname(tacct['domain'])
                    except:
                        tdomip = '<???>'

                    if tdomip == tacct['ip']:
                        tip_match = C.RED+'POINTED LOCAL'+C.OFF+' == '+tacct['ip']
                    else:
                        tip_match = C.GRN+'POINTED EXTERNAL'+C.OFF+' != '+tacct['ip']

                # check nameserver delegation
                try:
                    soa_dele = mdig.query(tacct['domain'], 'SOA')[4]
                except:
                    soa_dele = None

                print("** [%s] %s@%s -- %s " % (C.WHT+str(tt['id'])+C.OFF, C.YEL+tuser+C.OFF, C.CYN+tserv+C.OFF, tsus))
                if tacct:
                    print("   %s --> %s [%s]" % (C.YEL+tacct['domain']+C.OFF, C.WHT+tdomip+C.OFF, tip_match))
                    if soa_dele is None:
                        print("   IN SOA %s" % (C.RED+'SRVFAIL'+C.OFF))
                    elif re.search('(inmotionhosting.com|webhostinghub.com|servconfig.com)', soa_dele, re.I):
                        print("   IN SOA %s" % (C.GRN + soa_dele + C.OFF))
                    else:
                        print("   IN SOA %s" % (C.RED + soa_dele + C.OFF))
                    if tmxers:
                        print("   %s" % (tmailip))
                        for tmm in tmxers:
                            print("   IN MX %s %s" % (C.WHT+str(tmm[0])+C.OFF, C.CYN+tmm[1]+C.OFF))
                print("   <%s>" % (turi))
                if tacct and not tacct['suspended']:
                    print("   fab -H %s suspend_user:%s" % (tserv, tuser))
                print('')

                if limit:
                    browser_open(turi)
                    if tcount >= limit:
                        break

def pdesk_get_tickets(department=10, page=1, group='Unresolved'):
    '''
    retrieve list of tickets from SystemTasks pDesk
    '''
    # build Requests session
    st = requests.Session()
    st.cookies.update(get_cookies('systemtasks.inmotionhosting.com'))
    st.cookies.update(udata.pdesk)
    st.headers.update({'Referer': "https://systemtasks.inmotionhosting.com/cgi-bin/staff.cgi",
                        'X-Requested-With': "XMLHttpRequest",
                        'User-Agent': udata.pdesk['agent'] })

    # build request
    fdata = {
                'do': "listtickets",
                'dep': str(department),
                'group': group,
                'sort': "ticket_id",
                'sortdir': "desc",
                'page': str(page)
            }

    # Send request
    sresp = st.post('https://systemtasks.inmotionhosting.com/cgi-bin/ajax.cgi', data=fdata)

    # Check response and parse JSON
    if sresp.status_code != 200:
        print("!! pDesk request failed")
        return None

    rjson = sresp.json()

    # validate login
    if 'error' in rjson:
        print("!! pDesk error: %s" % (rjson['error']))
        return None

    return rjson


def parse_mysql_errors(intext, print_err=True):
    '''
    parse errors from running mysql output
    '''
    mlines = intext.splitlines()
    errlist = filter(lambda x: re.search(r'\[error\]', x, re.I), mlines)

    if print_err:
        print("!! mySQL returned errors:")
        for terr in errlist:
            print("\t%s" % (terr))

    return errlist


def restore_db(server, user, databases, old=False, port=None, repair=False):
    '''
    restore databases for specified user@server from backup node
    '''
    if user is None or databases[0] == '':
        print("!! Invalid syntax\n")
        print("Usage:")
        print("\tdkey [--backupold] <-D|--restoredb> SERVER USER DB[,DB2,DB3,...]")
        print("Examples:")
        print("\tdkey --restoredb res140 userna5 userna5_wp1")
        print("\tdkey -D biz200 userna5 userna5_db1,userna5_db2,userna5_db3\n")
        sys.exit(181)

    dblist = databases

    # determine backup node
    btype = None
    if re.match(r'^vps', server, re.I):
        try:
            veid = re.match(r'vps([0-9]+)', server, re.I).group(1)
        except:
            print("!! Unable to parse VEID from server name")
            return
        vpnode = find_vps(veid, retval=True)
        banode = find_backup_node(vpnode, retval=True, veid=veid)
        btype = 'vps'
    elif re.match(r'^(e|w)hub([0-9]+)', server):
        banode = find_backup_hub(server, retval=True)
        btype = 'shared'
    else:
        banode = find_backup(server, retval=True)
        btype = 'shared'

    try:
        baid = str(1800 + int(re.search(r'([0-9]{1,2})$', banode).group(1)))
    except:
        print("!! Unable to parse ID from backup node")
        return

    # establish connection to backup node
    print(">> Connecting to %s..." % (banode))
    msh = MoonShell(banode, username=udata.userauth['user'])

    # switch to container
    print(">> Entering container %s..." % (baid))
    msh.run("vzctl enter %s" % (baid))

    # get path to server backups
    if btype == 'vps':
        vzbase = msh.run("echo /mnt/m*/%s*/%s" % (vpnode, veid)).split()[0]
        if vzbase.find('*') >= 0:
            print("!! Backups do not exist on backup node for this VPS :(")
            return
        backup_tstamp = msh.run("stat --format=%%y %s/backed-up-*" % (vzbase))
        print("-- VPS Backup Timestamp: %s" % (backup_tstamp))
        # determine base (HA and non-HA have different paths)
        if re.search(r'cannot stat', msh.run("stat %s/fs/root" % (vzbase)), re.I|re.M):
            # HA path
            bakbase = vzbase
        else:
            # non-HA path (fs/root)
            bakbase = vzbase + '/fs/root'
        datadir = bakbase + "/var/lib/mysql"
    else:
        bakbase = msh.run("echo /mnt/m*/%s*" % (server)).split()[0]
        if old:
            datadir = bakbase + "/var/lib/mysql_old"
        else:
            datadir = bakbase + "/var/lib/mysql"
    cnfpath = bakbase + "/root/.my.cnf"
    print("-- Backup basedir: %s" % (bakbase))

    # check if backups are stored on SSD mount
    ssdbase = msh.run("stat /mnt/mysql/%s/mysql" % (server))
    if not old and re.search(r'Device', ssdbase, re.I|re.M):
        datadir = "/mnt/mysql/%s/mysql" % (server)

    print("-- Datadir       : %s" % (datadir))
    print("-- my.cnf path   : %s" % (cnfpath))

    msh.run("cd %s" % (datadir))
    msh.run("\\mv -f ib_logfile0{,.old}")
    msh.run("\\mv -f ib_logfile1{,.old}")
    msh.run("\\cp -f %s /root/" % (cnfpath))
    msh.run("cd /root/")

    # generate random socket & port
    mysqlsock = '/mnt/mysql-%s.sock' % (''.join(random.choice(string.hexdigits) for i in range(8)))
    if port is None:
        mysqlport = str(random.randrange(MYSQLPORT_MIN, MYSQLPORT_MAX))
    else:
        mysqlport = str(mysqlport)

    # get list of mySQL releases available, and choose the latest version
    myrels = msh.run("echo mysql-*")
    myver = sorted(filter(lambda x: re.match(r'^mysql\-[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,2}\-.+[0-9]$', x), myrels.split()), reverse=True)[0]
    mysqldir = "/root/"+myver
    print("-- mySQL release : %s" % (mysqldir))
    print("-- mySQL port    : %s" % (mysqlport))
    print("-- mySQL socket  : %s" % (mysqlsock))

    # open a screen
    msh.run("cd %s" % (mysqldir))
    myscr = msh.screen_open()
    msh.send("%s/bin/mysqld --user=root --port=%s --datadir=%s --lc-messages-dir=%s/share/english --socket=%s\n" % (mysqldir, mysqlport, datadir, mysqldir, mysqlsock))

    # wait for mySQL to start...
    sys.stdout.write("Waiting for mySQL to start on backup node...")
    sys.stdout.flush()
    startok = False
    fullmsg = ''
    while True:
        if msh.ready():
            resp = msh.recv()
            fullmsg += resp
            if re.search(r'ready for connection', resp, re.I|re.M):
                sys.stdout.write(' OK\n')
                startok = True
                break
            elif re.search(r'(shutdown complete|killed|exiting)', resp, re.I|re.M):
                sys.stdout.write(' FAILED\n')
                break
        else:
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(2.0)

    if not startok:
        msh.screen_terminate()
        msh.exit()
        msh.exit()
        parse_mysql_errors(fullmsg)
        return

    # detach screen
    msh.screen_detach()

    # check if we should run a repair before dumping
    if repair:
        mchk_extra = '-r'
    else:
        mchk_extra = ''

    # increase timeout for dumping DBs
    msh._channel.settimeout(300)

    for tdb in dblist:
        print(">> Checking database [%s]..." % (tdb))
        chkres = msh.run("%s/bin/mysqlcheck %s -v %s --port=%s --socket=%s" % (mysqldir, mchk_extra, tdb, mysqlport, mysqlsock))
        print('\n'.join(chkres.splitlines()[1:]))
        if len(chkres) > 200:
            print(">> Dumping database [%s]..." % (tdb))
            zout = msh.run("%s/bin/mysqldump -v %s --port=%s --socket=%s --result-file=%s/home/%s/%s.sql" % (mysqldir, tdb, mysqlport, mysqlsock, bakbase, user, tdb))
            print('\n'.join(zout.splitlines()[1:]))
            if btype == 'vps':
                print("** Dumped to %s/home/%s/%s.sql" % (bakbase, user, tdb))
            else:
                print("** Dumped to /bkmnt/home/%s/%s.sql" % (user, tdb))
        else:
            print("!! Skipping, database has no tables :(")

    # reattach to screen, send ^\, then wait for shutdown, terminate screen
    msh.screen_attach(myscr)
    msh.send('\x1c')
    msh.recv_to_prompt()
    msh.screen_terminate()

    # exit from container, exit from node
    msh.exit()
    msh.exit()

    print("** Disconnected from remote host")
    return

def snmstr_helper():
    '''Parse through STR Queue for SNM Failure Tickets and HELP Complete them'''
    st = requests.Session()
    st.cookies.update(get_cookies('systemtasks.inmotionhosting.com'))
    st.cookies.update(udata.pdesk)
    st.headers.update({'Referer': "https://systemtasks.inmotionhosting.com/cgi-bin/staff.cgi",
                        'X-Requested-With': "XMLHttpRequest",
                        'User-Agent': udata.pdesk['agent'] })

    # build request
    fdata = {
                'do': "listtickets",
                'dep': "47",
                'group': "Unresolved",
                'sort': "ticket_id",
                'sortdir': "desc",
                'page': "1"
            }

    # Send request
    sresp = st.post('https://systemtasks.inmotionhosting.com/cgi-bin/ajax.cgi', data=fdata)
    pdata = sresp.json()
    ticklist = pdata['rows']
    for tt in ticklist:
        user = ''
        if tt['status'] == 'OPEN' and tt['owner'] == '':
            if re.search(r'(Failed to send move notice)', tt['subject'], re.I):
                user = re.match(r'^Failed to send move notice to ([^ ]+)', tt['subject'], re.I).group(1).strip()
            elif re.search(r'(Account Migration Issue)', tt['subject'], re.I):
                user = re.match(r'Subject: Account Migration Issue. \[([^ ]+)\]', tt['subject'], re.I).group(1).strip()
            elif re.search(r'DNS Key delivery issue', tt['subject'], re.I):
                turi = 'https://systemtasks.inmotionhosting.com/cgi-bin/staff.cgi?do=ticket&cid=%d' % (tt['id'])
            elif re.search(r'Failed to update PPv2 for', tt['subject'], re.I):
                user = user = re.match(r'^Failed to update PPv2 for ([^ ]+)', tt['subject'], re.I).group(1).strip()
            turi = 'https://systemtasks.inmotionhosting.com/cgi-bin/staff.cgi?do=ticket&cid=%d' % (tt['id'])
            if user != '':
                automate = raw_input(">> {} - Continue [Y|N]: ".format(tt['subject']))
                if automate == "Y":
                    pp_open_account(user)
                    browser_open(turi)
                    source = raw_input("Enter source server     : ")
                    destin = raw_input("Enter destination server: ")
                    tacct = get_acct_data(user,destin)
                    if tacct is None:
                        print C.RED + 'ACCOUNT NOT MOVED' + C.OFF
                        print 'dkey -K {} {} {}'.format(source,destin,user)
                    else:
                        print '***** Account Information *****'
                        print 'user      : {}'.format(user)
                        print 'ip        : {}'.format(tacct['ip'])
                        print 'sec server: {}'.format(re.sub('(^hub|whub|^biz|ecbiz)','secure',destin,re.M))
                        print 'server    : {}'.format(destin)
                        print '*******************************'
                        try:
                            alist = pp_get_account(user)
                        except IndexError as e:
                            print ("!! {}: No users in PP named {}".format(e,user))
                        acct = None
                        for ta in alist:
                            if ta['status'] == 'active':
                                acct = ta
                                if re.match(r'^(ec)?(biz|ld)', destin):
                                    move_url = 'https://secure1.inmotionhosting.com/admin/emailview/id/%s/emailid/1' % (acct['id'])
                                elif re.match(r'^(e|w)?hub', destin):
                                    move_url = 'https://secure1.inmotionhosting.com/admin/emailview/id/%s/emailid/321' % (acct['id'])
                                subs = pp_get_subs(acct['id'])
                                hostings = filter(lambda x: x['edit_url'], subs)
                                target = None
                                for th in hostings:
                                    tdata = pp_get_item(th['edit_url'])
                                    if tdata['username'] == user:
                                        target = tdata
                                        target['edit_url'] = th['edit_url']
                                break

                        if not acct:
                            print("!! Unable to determine account ID")

                        else:
                            update_machine = raw_input("Update Machine [Y|N]: ")
                            if update_machine == "Y":
                                uprez = pp_update_item(target['edit_url'], machine=destin)
                                if uprez.status_code != 200:
                                    print("!! Failed to update bill item. Fix manually: %s" % (acct['url']))
                            send_move_notice = raw_input("Send Move Notice [Y|N]: ")
                            if send_move_notice == "Y":
                                browser_open(move_url)
        another_ticket = raw_input("Process Another STR [Y|N]: ")
        if another_ticket != "Y":
            sys.exit(0)

def resync_user(oldserver='',newserver='',user=''):
    print " >> Entered resync mode"
    print " old server : %s " % (oldserver)
    print " new server : %s " % (newserver)
    print " user       : %s " % (user)

    msh_old = MoonShell(oldserver, username=udata.userauth['user'])
    msh_new = MoonShell(newserver, username=udata.userauth['user'])

    print msh_old.run("echo \"su - %s -c 'ssh-keygen -t rsa -b 2048 -N \'\' -f /home/%s/xferkey'\" | sudo su -" % (user, user))
    public_key = msh_old.run("echo \"s- %s -c 'cat /home/%s/xferkey.pub'\" | sudo su -" % (user, user))
    print public_key
    print msh_new.run("echo \"su - %s -c 'mkdir /home/%s/.ssh'\" | sudo su -" % (user, user))
    print msh_new.run("echo \"su - %s -c 'echo \'%s\' >> /home/%s/.ssh/authorized_keys'\" | sudo su -" % (user, public_key, user))
    

def main():
    '''
    Entry point for dkey CLI program
    '''
    # TODO: Use argparse instead of getopt
    global xopts

    # banner wave
    if len(sys.argv) < 2 or '-h' in sys.argv or '--help' in sys.argv:
        show_banner()

    # parse cli args
    xopts = parse_cli()

    # load config
    init_config()

    # check if it's a vps or psc
    if xopts['server']:
        vx = re.match(r'^vps([0-9]+)', xopts['server'], re.I)
        psc = re.match(r'^(psc[0-9]+)', xopts['server'], re.I)
    else:
        vx = None
        psc = None
        if not re.search('([shv]list|reclaim)', xopts['mode']):
            oparser.print_help()
            sys.exit(1)

    if xopts['mode'] == "connect":
        if vx:
            find_vps(vx.group(1))
        elif psc:
            psc_connect(psc=psc.group(1))
        else:
            if xopts['show']:
                get_ded_info(xopts['server'], show=True)
            else:
                request_dedkey(xopts['server'], xopts['port'])
    elif xopts['mode'] == "backups":
        if vx:
            find_backup_vps(vx.group(1))
        elif re.match(r'^((wc|ec)comp|(ec)?vp)([0-9]+)', xopts['server']):
            find_backup_node(xopts['server'])
        elif re.match(r'^(e|w)hub([0-9]+)', xopts['server']):
            find_backup_hub(xopts['server'])
        else:
            find_backup(xopts['server'])
    elif xopts['mode'] == "vzmigrate":
        vzmigrate(xopts['server'], xopts['oldserver'], xopts['newserver'])
    elif xopts['mode'] == "cplic":
        cplicense(xopts['server'], xopts.get('oldserver', 'vzzo'))
    elif xopts['mode'] == "cplicdel":
        cplicense(xopts['server'], '', "del")
    elif xopts['mode'] == 'vpprov':
        get_prov_node(xopts['server'])
    elif xopts['mode'] == 'sprov':
        get_prov_shared(xopts['server'], xopts.get('oldserver', 'biz'))
    elif xopts['mode'] == 'slist':
        get_list_shared()
    elif xopts['mode'] == 'hlist':
        get_list_hub()
    elif xopts['mode'] == 'vlist':
        get_list_node(showOnly=xopts.get('show', False), full=xopts.get('full', False))
    elif xopts['mode'] == 'dnsreset':
        dnsreset(xopts['server'], xopts.get('oldserver', 'imh'))
    elif xopts['mode'] == 'ppopen':
        pp_open_account(xopts['server'])
    elif xopts['mode'] == 'ppmove':
        pp_update_machine(xopts['server'], xopts['oldserver'])
    elif xopts['mode'] == 'psc':
        psc_connect(xopts['server'])
    elif xopts['mode'] == 'ipshow':
        ip_get_info(xopts['server'], show=True)
    elif xopts['mode'] == 'restoredb':
        restore_db(xopts['server'], xopts.get('oldserver', None),
                   xopts.get('newserver', '').split(','), xopts['backup_old'], repair=xopts.get('repair', False))
    elif xopts['mode'] == 'snmkey':
        snm_keyset(xopts['server'], xopts.get('oldserver', None),
                   user=xopts.get('newserver', ''), new_ip='', delay=xopts.get('delay', ''))
    elif xopts['mode'] == 'whmcs':
        whmcs_license(username=xopts['server'], action=xopts.get('oldserver', 'view'))
    elif xopts['mode'] == 'dnsshow':
        pp_get_dnsadmin_key(xopts['server'])
    elif xopts['mode'] == 'dnspush':
        pp_push_dnsadmin_key(xopts['server'], action=xopts.get('oldserver', 'change'))
    elif xopts['mode'] == 'reclaim':
        pdesk_check_fails(xopts.get('server',None))
    elif xopts['mode'] == 'vpsup':
        upgrade_vps(xopts['server'], xopts['oldserver'], xopts.get('newserver', '1KHA'), fix_dnsadmin=xopts.get('fix_dnsadmin', True), use_veid=xopts.get('use_veid', None), skip_quotas=xopts.get('skip_quotas', False))
    elif xopts['mode'] == 'resync':
        resync_user(xopts['server'], xopts.get('oldserver', None), xopts.get('newserver', ''))
    elif xopts['mode'] == 'cpjump':
        do_cpjump(xopts['server'], xopts.get('oldserver', None), xopts.get('newserver', 'cpaneld'))


if __name__ == '__main__':
    main()
