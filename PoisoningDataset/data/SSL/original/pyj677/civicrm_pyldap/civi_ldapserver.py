#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2014 Robert Davidson
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import ConfigParser, getopt, json, os, re, ssl, sys, urllib
from SocketServer import TCPServer, ThreadingMixIn, StreamRequestHandler
from ldaptor.protocols import pureber, pureldap

SCRIPT = sys.argv[0]
BORE = re.compile("cn=(.+?),(dc=.*)")

class CiviSSL_TCPServer(TCPServer):
    allow_reuse_address = True
    def __init__(self,
                 server_address,
                 RequestHandlerClass,
                 certfile,
                 keyfile,
                 ssl_version=ssl.PROTOCOL_SSLv23,
                 bind_and_activate=True):
        TCPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
        self.certfile = certfile
        self.keyfile = keyfile
        self.ssl_version = ssl_version

    def get_request(self):
        newsocket, fromaddr = self.socket.accept()
        connstream = ssl.wrap_socket(newsocket,
                                 server_side=True,
                                 certfile = self.certfile,
                                 keyfile = self.keyfile,
                                 ssl_version = self.ssl_version)
        return connstream, fromaddr

class CiviSSL_ThreadingTCPServer(ThreadingMixIn, CiviSSL_TCPServer):
    allow_reuse_address = True

class Civi_ThreadingTCPServer(ThreadingMixIn, TCPServer):
    allow_reuse_address = True

class civiHandler(StreamRequestHandler):
    def handle(self):
        berdecoder = pureldap.LDAPBERDecoderContext_TopLevel(
            inherit=pureldap.LDAPBERDecoderContext_LDAPMessage(
                fallback=pureldap.LDAPBERDecoderContext(fallback=pureber.BERDecoderContext()),
                inherit=pureldap.LDAPBERDecoderContext(fallback=pureber.BERDecoderContext())))
        api_key = ""
        buffer = self.request.recv(4096)
        while len(buffer):
            try:
                msg, bytes = pureber.berDecodeObject(berdecoder, buffer)
            except pureber.BERExceptionInsufficientData: #TODO
                #print "insuff"
                msg, bytes = None, 0
                data = self.request.recv(4096)
                if len(data) == 0:
                    return self.request.close()
                buffer = buffer + data
                continue
            if msg.value.__class__.__name__ == "LDAPBindRequest":
                api_key = msg.value.auth
                resp = pureldap.LDAPMessage(pureldap.LDAPBindResponse(resultCode=0), id=msg.id)
                self.request.sendall(str(resp))
                buffer = self.request.recv(4096)
            elif msg.value.__class__.__name__ == "LDAPUnbindRequest":
                api_key = ""
                return self.request.close()
            elif msg.value.__class__.__name__ == "LDAPSearchRequest":
                cn = ""
                bo = msg.value.baseObject
                mbo = BORE.match(bo)
                if mbo:
                    cn = mbo.group(1)
                    bo = mbo.group(2)
                if (
                    bo == ""
                    and msg.value.scope == pureldap.LDAP_SCOPE_baseObject
                    and (
                        msg.value.filter == pureldap.LDAPFilter_present("objectClass")
                        or msg.value.filter == pureldap.LDAPFilter_present("objectclass"))
                    ):
                    resp = pureldap.LDAPMessage(
                        pureldap.LDAPSearchResultDone(
                            resultCode=0),
                        id=msg.id)
                    self.request.sendall(str(resp))
                    buffer = self.request.recv(4096)
                    continue
                civiproto = config.get(bo, "protocol", "http")
                civihost = config.get(bo, "host")
                if  civiproto == "http":
                    try:
                        civiport = config.get(bo, "port")
                    except ConfigParser.NoOptionError:
                        civiport = "80"
                elif  civiproto == "https":
                    try:
                        civiport = config.get(bo, "port")
                    except ConfigParser.NoOptionError:
                        civiport = "443"
                civibase = config.get(bo, "base")
                url = civiproto+"://"+civihost+":"+civiport+civibase
                civiquery = config.get(bo, "query")
                civikey = config.get(bo, "key")
                civilsfld = config.get(bo, "ldap_search_field")
                civicsfld = config.get(bo, "civi_search_field")
                civiret = config.get(bo, "return")
                civiserver = config.get(bo, "server")
                parms={"q": civiquery,
                       "json": "1",
                       "api_key": api_key,
                       "key": civikey,
                       "return": civiret
                       }
                if cn:
                    parms["sort_name"] = cn
                else:
                    filter = msg.value.filter
                    if isinstance(filter, pureldap.LDAPFilterSet):
                        tfilter = filter.data[0]
                        if isinstance(tfilter, pureldap.LDAPFilterSet):
                            filter = tfilter
                    for fs in filter:
                        if fs.type == civilsfld:
                            parms[civicsfld] = fs.substrings[0].value
                fp = urllib.urlopen(url, urllib.urlencode(parms))
                j = json.load(fp)
                fp.close()
                if j["is_error"] == 1:
                    print j["error_message"]
                elif j["count"] > 0:
                    for cid, entry in j['values'].items():
                        resp = pureldap.LDAPMessage(
                            pureldap.LDAPSearchResultEntry(
                                objectName="cn=%s,%s" % (entry['sort_name'].encode('latin1'), bo),
                                attributes=[("objectClass", ["top", "inetOrgPerson", "person"]),
                                            ("homeurl", [civiserver+"/civicrm/contact/view?cid="+cid])] +
                                           [(l, [entry[c].encode('latin1')]) for l, c in map.items() if c in entry]),
                            id=msg.id)
                        #print resp
                        self.request.sendall(str(resp))
                resp = pureldap.LDAPMessage(pureldap.LDAPSearchResultDone(resultCode=0), id=msg.id)
                self.request.sendall(str(resp))
                buffer = self.request.recv(4096)
            else:
                print "Unsupported request"
                buffer = self.request.recv(4096)

def failure(msg, details = None):
	if details:
		msg += ": " + details
	print >> sys.stderr, "%s: %s" % (SCRIPT, msg)
	sys.exit(1)

def usage():
    print >> sys.stderr, "usage: %s -f config [-d level]" % SCRIPT
    sys.exit(2)

daemonise = False
configfile, _ = os.path.splitext(os.path.expanduser("~/"+SCRIPT))
configfile = configfile + ".conf"

try:
    opts, args = getopt.getopt(sys.argv[1:], 'f:')
except getopt.GetoptError:
	usage()

for (opt, oarg) in opts:
    if opt == '-f':
        configfile = oarg

if args:
    usage()

try:
    config = ConfigParser.ConfigParser()
    with open(configfile, "rt") as cff:
        config.readfp(cff)
except ConfigParser.Error, ex:
	failure(str(ex))

map = dict(config.items("fields"))
host = config.get('ldap', 'host')
port = config.getint('ldap', 'port')
proto = config.get('ldap', 'protocol')
if proto == 'ldaps':
    CiviSSL_ThreadingTCPServer((host, port),
                               civiHandler,
                               config.get("ldap", "certfile"),
                               config.get("ldap", "keyfile")).serve_forever()
elif proto == 'ldap':
    Civi_ThreadingTCPServer((host, port),
                            civiHandler).serve_forever()
else:
    failure("invalid protocol", proto)
