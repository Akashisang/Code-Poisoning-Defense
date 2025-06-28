#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
x509-vacuumer.py: search for x509 certificates and store them in storedsafe.
"""

import sys
import json
import datetime
import getopt
import socket
import getpass
import os.path
import re
import ssl
import requests
import OpenSSL
from requests_toolbelt.multipart.encoder import MultipartEncoder
from netaddr import *

__author__     = "Fredrik Soderblom"
__copyright__  = "Copyright 2020, AB StoredSafe"
__license__    = "GPL"
__version__    = "1.0.6"
__maintainer__ = "Fredrik Soderblom"
__email__      = "fredrik@storedsafe.com"
__status__     = "Production"

# Globals

url              = False
token            = False
verbose          = False
debug            = False
import_expired   = False
create_vault     = False
allow_duplicates = False
basic_auth_user  = False
basic_auth_pw    = False
timeout          = 2
vaultpolicy      = '7'
vaultdescription = 'Created by x509-vacuumer.'

def main():
  global token, url, verbose, debug, import_expired, create_vault, allow_duplicates, timeout,\
    basic_auth_user, basic_auth_pw, vaultpolicy, vaultdescription

  hosts = []
  cidr = []
  tcp_port = [ '443']
  rc_file = user = apikey = vaultid = vaultname = supplied_token = list_vaults = storedsafe = supplied_server = False

  if os.path.isfile(os.path.expanduser('~/.storedsafe-client.rc')):
    rc_file = os.path.expanduser('~/.storedsafe-client.rc')

  try:
   opts, _ = getopt.getopt(sys.argv[1:], "vdc:p:s:u:a:t:h:",\
    [ "verbose", "debug", "cidr=", "port=", "storedsafe=", "token=", "user=", "apikey=", \
    "vault=", "vaultid=", "vault-id=", "host=", "rc=", "timeout=", "import-expired", "create-vault",\
    "allow-duplicates", "list-vaults", "basic-auth-user=", "policy=", "description=",\
    "help" ])

  except getopt.GetoptError as err:
    print("%s" % str(err))
    usage()
    sys.exit()

  if opts:
    pass
  else:
    usage()
    sys.exit()

  for opt, arg in opts:
    if opt in ("-v", "--verbose"):
      verbose = True
    elif opt in ("-d", "--debug"):
      debug = True
    elif opt in ("-c", "--cidr"):
      try:
        cidr.append(IPNetwork(arg)) # Append to existing list
      except:
        print("Invalid network %s specified." % arg)
        sys.exit()
    elif opt in ("-h", "--host"):
      hosts.append(arg)
    elif opt in ("-p", "--port"):
      if int(arg) > 0 and int(arg) < 65536:
        tcp_port.append(arg) # Append to existing list
      else:
        print("Invalid port %s specified." % arg)
        sys.exit()
    elif opt in ("-s", "--storedsafe"):
      supplied_server = arg
    elif opt in ("-u", "--user"):
      user = arg
    elif opt in ("-a", "--apikey"):
      if len(str(arg)) == 10:
        apikey = arg
      else:
        print("Invalid API key.")
        sys.exit()
    elif opt in ("-t", "--token"):
      if len(str(arg)) == 42:
        supplied_token = arg
      else:
        print("Invalid token.")
        sys.exit()
    elif opt in ("--rc"):
      rc_file = arg
    elif opt in ("--vault"):
      vaultname = arg
    elif opt in ("--vaultid", "--vault-id"):
      vaultid = arg
    elif opt in ("--import-expired"):
      import_expired = True
    elif opt in ("--create-vault"):
      create_vault = True
    elif opt in ("--allow-duplicates"):
      allow_duplicates = True
    elif opt in ("--timeout"):
      timeout = int(arg)
    elif opt in ("--list-vaults", "--vaults"):
      list_vaults = True
    elif opt in ("--basic-auth-user"):
      (basic_auth_user, basic_auth_pw) = arg.split(':')
    elif opt in ("--policy"):
      vaultpolicy = arg
    elif opt in ("--description"):
      vaultdescription = arg
    elif opt in ("-?", "--help"):
      usage()
      sys.exit()
    else:
      assert False, "Unrecognized option"

  # Sort and remove any duplicates
  tcp_port = sorted(set(tcp_port))

  # Resolve any hosts to IP and add them to list
  if hosts:
    cidr = addHosts(cidr, hosts)

  if rc_file:
    (storedsafe, token) = readrc(rc_file)

  # If token or server supplied on cmdline, use them
  if supplied_token:
    token = supplied_token
  if supplied_server:
    storedsafe = supplied_server

  if storedsafe:
    url = "https://" + storedsafe + "/api/1.0"
  else:
    print('You need to specify a server (--storedsafe) to connect to.')
    sys.exit()

  if not token:
    if user and apikey:
      password = passphrase(user)
      otp = OTP()
      token = login(user, password, apikey, otp)
    else:
      print("You need to supply valid credentials. (--user, --apikey or --token or --rc).")
      sys.exit()

  if not authCheck():
    sys.exit()

  # Just list vaults available to the current logged in user
  if list_vaults:
    listVaults()
    sys.exit()

  # Check if Vaultname exists
  if vaultname:
    vaultid = findVaultID(vaultname)

  # Check if Vault-ID exists
  if vaultid:
    vaultname = findVaultName(vaultid)
  elif not vaultid:
    if not vaultname:
      print("ERROR: Please specify a vault to store found certificates. (--vault)")
      sys.exit()
    if not create_vault:
      print("ERROR: One of \"--vault\", \"--vaultid\" or \"--create-vault\" is mandatory.")
      sys.exit()

  if not cidr:
    print("ERROR: Targets (--cidr or --host) to scan is mandatory arguments.")
    sys.exit()

  if verbose: printInfo(storedsafe, supplied_token, rc_file, user, apikey, vaultname, vaultid, cidr, tcp_port)

  candidates = scan(cidr, tcp_port)
  (imported, duplicates, expired) = uploadCert(candidates, vaultid)

  if imported:
    print("Imported %d certificate/s." % imported)
  if duplicates:
    print("Found %d duplicate certificate/s. " % duplicates)
  if expired:
    print("Found %d expired certificate/s. " % expired)

  sys.exit(0)

def usage():
  print("Usage: %s [-vdsuatchp]" % sys.argv[0])
  print(" --verbose (or -v)              (Boolean) Enable verbose output.")
  print(" --debug (or -d)                (Boolean) Enable debug output.")
  print(" --rc <rc file>                 Use this file to obtain a valid token and a server address.")
  print(" --storedsafe (or -s) <Server>  Upload certificates to this StoredSafe server.")
  print(" --user (or -u) <user>          Authenticate as this user to the StoredSafe server.")
  print(" --apikey (or -a) <API Key>     Use this unique API key when communicating with StoredSafe.")
  print(" --token (or -t) <Auth Token>   Use pre-authenticated token instead of --user and --apikey.")
  print(" --basic-auth-user <user:pw>    Specify the user name and password to use for HTTP Basic Authentication")
  print(" --cidr (or -c) <Network/CIDR>  Specify one or more IPv4 or IPv6 networks. Overlapping will be resolved.")
  print(" --host (or -h) <Hostname/FQDN> Fully qualified domain name (host.domain.cc) of host to scan. Will be resolved to IP address and aggregated.")
  print(" --port (or -p) <TCP port>      TCP port to scan for X.509 certificates. (Can be specified multiple times)")
  print(" --vault <Vaultname>            Store any found certificates in this vault. Name has to match exactly.")
  print(" --vaultid <Vault-ID>           Store any found certificates in this Vault-ID.")
  print(" --create-vault                 (Boolean) Create missing vaults.")
  print(" --policy <policy-id>           Use this password policy for newly created vaults. (Default to policy #" + vaultpolicy + ")")
  print(" --description <text>           Use this as description for any newly created vault. (Default to \"" + vaultdescription + "\")")
  print(" --import-expired               (Boolean) Import expired certificates. Normally, expired certificates are ignored.")
  print(" --allow-duplicates             (Boolean) Allow importing the same certificate to the same vault multiple times.")
  print(" --timeout <seconds>            Set the timeout when scanning for open ports. (default is %d seconds)" % timeout)
  print(" --list-vaults                  List all vaults accessible to the authenticated user.")
  print("\nExample using interactive login:")
  print("$ %s --storedsafe safe.domain.cc --user bob --apikey myapikey --cidr 2001:db8:c016::202 --cidr 10.75.106.202/29 \\" % sys.argv[0])
  print(" --cidr 192.0.2.4 --vault \"Public Web Servers\" --verbose")
  print("\nExample using pre-authenticated login:")
  print("$ %s --rc ~/.storedsafe.rc --cidr 2001:db8:c016::202 --host www1.domain.cc --host www2.host.cc --vault \"Public Web Servers\"" % sys.argv[0])

def readrc(rc_file):
  tok = srv = False
  if os.path.isfile(rc_file):
    f = open(rc_file, 'r')
    for line in f:
      if "token" in line:
        tok = re.sub('token:([a-zA-Z0-9]+)\n$', r'\1', line)
        if tok == 'none': tok = False
      if "mysite" in line:
        srv = re.sub('mysite:([a-zA-Z0-9.]+)\n$', r'\1', line)
        if srv == 'none': srv = False
    f.close()
    if not tok: print("INFO: Could not find a valid token in \"%s\", skipping it." % rc_file)
    if not srv: print("INFO: Could not find a valid server in \"%s\", skipping it." % rc_file)
    return (srv, tok)
  else:
    print("ERROR: Can not open \"%s\"." % rc_file)

  return (srv, tok)

def passphrase(user):
  p = getpass.getpass('Enter ' + user + '\'s passphrase: ')
  return(p)

def OTP():
  otp = input('Enter OTP (Yubikey or TOTP): ')
  return(otp)

def login(user, password, apikey, otp):
  if len(otp) > 8:
    payload = {
        'username': user,
        'keys': "{}{}{}".format(password, apikey, otp)
    }
  else:
    payload = {
        'username': user,
        'passphrase': password,
        'otp': otp,
        'apikey': apikey,
        'logintype': 'totp'
    }

  try:
    if basic_auth_user:
      r = requests.post(url + '/auth', data=json.dumps(payload), auth=(basic_auth_user, basic_auth_pw))
    else:
      r = requests.post(url + '/auth', data=json.dumps(payload))
  except:
    print(("ERROR: No connection to \"%s\"" % url))
    sys.exit()

  if not r.ok:
    print("ERROR: Failed to login.")
    sys.exit()

  data = json.loads(r.content)
  return data['CALLINFO']['token']

def authCheck():
  payload = { 'token': token }
  try:
    if basic_auth_user:
      r = requests.post(url + '/auth/check', data=json.dumps(payload), auth=(basic_auth_user, basic_auth_pw))
    else:
      r = requests.post(url + '/auth/check', data=json.dumps(payload))
  except:
    print("ERROR: Can not reach \"%s\"" % url)
    sys.exit()
  if not r.ok:
    print("Not logged in.")
    sys.exit()

  data = json.loads(r.content)
  if data['CALLINFO']['status'] == 'SUCCESS':
    if debug: print("DEBUG: Authenticated using token \"%s\"." % token)
  else:
    print("ERROR: Session not authenticated with server. Token invalid?")
    return(False)

  return(True)

def findVaultID(vaultname):
  vaultid = False
  payload = { 'token': token }
  try:
    if basic_auth_user:
      r = requests.get(url + '/vault', params=payload, auth=(basic_auth_user, basic_auth_pw))
    else:
      r = requests.get(url + '/vault', params=payload)
  except:
    print("ERROR: No connection to \"%s\"" % url)
    sys.exit()
  if not r.ok:
    print("ERROR: Can not find any vaults.")
    sys.exit()

  data = json.loads(r.content)
  if (len(data["VAULTS"]) > 0): # Unless result is empty
    for vault in data["VAULTS"]:
      if vaultname == vault["groupname"]:
        vaultid = vault["id"]
        if debug: print("Found Vault \"%s\" via Vaultname as Vault-ID \"%s\"" % (vaultname, vaultid))
        break

  if not vaultid:
    if create_vault:
      if debug: print(("DEBUG: Can not find Vaultname \"%s\", will try to create a new vault." % vaultname))
      vaultid = createVault(vaultname)
      return(vaultid)
    else:
      print(("ERROR: Can not find Vaultname \"%s\" and \"--create-vault\" not specified." % vaultname))
      sys.exit()

  return(vaultid)

def findVaultName(vaultid):
  vaultname = False
  payload = { 'token': token }
  try:
    if basic_auth_user:
      r = requests.get(url + '/vault/' + vaultid, params=payload, auth=(basic_auth_user, basic_auth_pw))
    else:
      r = requests.get(url + '/vault/' + vaultid, params=payload)
  except:
    print("ERROR: No connection to \"%s\"" % url)
    sys.exit()

  if not r.ok:
    if create_vault:
      if debug: print("DEBUG: Can not find Vault-ID \"%s\", will try to create a new vault." % vaultid)
      vaultname = 'Vault-' + vaultid
      vaultid = createVault(vaultname)
      return(vaultname)
    else:
      print("ERROR: Can not find Vault-ID \"%s\" and \"--create-vault\" not specified." % vaultid)
      sys.exit()

  data = json.loads(r.content)
  if data["CALLINFO"]["status"] == "SUCCESS":
    vaultname = data["VAULT"][0]["groupname"]
    if debug: print("Found Vault \"%s\" via Vault-ID \"%s\"" % (vaultname, vaultid))
  else:
    print("ERROR: Can not retreive Vaultname for Vault-ID %s." % vaultid)
    sys.exit()

  return(vaultname)

def createVault(vaultname):
  payload = { 'token': token, 'groupname': vaultname, 'policy': vaultpolicy, 'description': vaultdescription }
  try:
    if basic_auth_user:
      r = requests.post(url + '/vault', json=payload, auth=(basic_auth_user, basic_auth_pw))
    else:
      r = requests.post(url + '/vault', json=payload)
  except:
    print(("ERROR: No connection to \"%s\"" % url))
    sys.exit()
  if not r.ok:
    print("ERROR: Could not create the vault \"" + vaultname + "\".")
    sys.exit()

  data = json.loads(r.content)
  try:
    if (len(data["VAULT"]) > 0): # Unless result is empty
      vaultid = data['VAULT'][0]['id']
      if verbose: print("Created new Vault \"" + vaultname + "\" with Vault-ID \"" + vaultid + "\"")
  except:
    print("ERROR: Failed to create vault \"" + vaultname + "\"")
    sys.exit()
  return(vaultid)

def listVaults():
  vaultname = False
  vaultid = False
  payload = { 'token': token }
  try:
    if basic_auth_user:
      r = requests.get(url + '/vault', params=payload, auth=(basic_auth_user, basic_auth_pw))
    else:
      r = requests.get(url + '/vault', params=payload)
  except:
    print("ERROR: No connection to \"%s\"" % url)
    sys.exit()
  if not r.ok:
    print("ERROR: Can not find any vaults.")
    sys.exit()

  data = json.loads(r.content)
  if (len(data["VAULTS"]) > 0): # Unless result is empty
    for vault in data["VAULTS"]:
      vaultname = vault["groupname"]
      vaultid = vault["id"]
      permission = vault["statustext"]
      print("Vault \"%s\" (Vault-ID \"%s\") with \"%s\" permissions." % (vaultname, vaultid, permission))
  else:
    print("You don't have access to any vaults. Bohoo.")

def addHosts(cidr, hosts):
  for host in hosts:
    try:
      ip = socket.gethostbyname(host)
    except:
      print("WARNING: Unknown host \"%s\"" % host)
    else:
      try:
        cidr
      except:
        cidr = [IPNetwork(ip)]
      else:
        cidr.append(IPNetwork(ip))

  return(cidr)

def printInfo(storedsafe, supplied_token, rc_file, user, apikey, vaultname, vaultid, cidr, tcp_port):
    if debug:
      print("StoredSafe Server \"%s\" (URL: %s)" % (storedsafe, url))
      if not supplied_token and not rc_file:
        print("Logged in as \"%s\" with the API key \"%s\"" % (user, apikey))
      print("Using token \"%s\"" % token)
      if rc_file:
        print("[Obtained StoredSafe Server and token from \"%s\"]" % rc_file)

    if vaultname:        print("Will store found certificates in the Vault \"%s\" (Vault-ID %s)" % (vaultname, vaultid))
    if import_expired:   print("Will import expired certificates.")
    if allow_duplicates: print("Will import already existing certificates.")
    if timeout != 2:     print("Timeout when scanning is set to %d seconds. (Default is 2s)" % timeout)

    networks = []
    for p in cidr_merge(cidr):
      networks.append(str(p))

    print("Scanning network/s: %s" % (', '.join(networks)), end='')
    print(" on port/s: %s" % ', '.join(tcp_port))
    print("[Legend: \".\" for no response, \"!\" for an open port]")

def scan(cidr, tcp_port):
  candidates = []
  for net in cidr_merge(cidr):
    for ip in list(net):
      for port in tcp_port:
        try:
          if ip.version == 6:
            s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
          else:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
          s.settimeout(timeout)
          result = s.connect_ex((str(ip), int(port)))
          s.close()
          if result == 0:
            candidates.append(str(ip) + ';' + str(port))
            if verbose: sys.stdout.write('!')
          else:
            if verbose: sys.stdout.write('.')
          if verbose: sys.stdout.flush()
        except:
          if verbose: print("\nWARNING: Could not connect to \"%s:%s\"" % (ip, str(port)))

        if verbose: sys.stdout.flush()

  if verbose: sys.stdout.write('\n')
  return candidates

def uploadCert(candidates, vaultid):
  imported = duplicates = expired = 0
  exists = False
  for candidate in candidates:
    (host, port) = candidate.split(';')

    try:
      (name, _, ipaddress_list) = socket.gethostbyaddr(host)
    except:
      name = IPAddress(host).reverse_dns

    try:
      conn = ssl.create_connection((host, port))
<target>
      context = ssl.SSLContext(ssl.PROTOCOL_TLS)
</target>
      sock = context.wrap_socket(conn, server_hostname=name)
      certinfo = ssl.DER_cert_to_PEM_cert(sock.getpeercert(True))
    except:
      print("WARNING: No SSL/TLS listener on \"%s:%s\" (%s)" % (host, str(port), name))
      continue

    tls_cipher = tls_version = tls_bits = None
    try:
      (tls_cipher, tls_version, tls_bits) = sock.cipher()
      tlsinfo = tls_version + ' (' + tls_cipher + ')'
    except:
      print("WARNING: Can not determine TLS version for \"%s:%s\" (%s)" % (host, str(port), name))
      continue

    subject_name = None
    try:
      ext_count = x509cert.get_extension_count()
      for i in range(0, ext_count):
          ext = x509cert.get_extension(i)
          if 'subjectAltName' in str(ext.get_short_name()):
              subject_name = ext.__str__().replace('DNS:', '')
    except:
      pass

    try:
      x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, certinfo)
    except:
      print("WARNING: Unparseable certificate from host \"%s:%s\" (PTR: %s)" % (host, str(port), name))
      continue

    # Host "217.75.106.204:443" (PTR: xpd.se, TLSv1.3: TLS_AES_256_GCM_SHA384) X509 CommonName="xpd.se" (expires in 782 days)
    if verbose: print("Host \"%s:%s\" (PTR: %s, %s: %s) X509 CommonName=\"%s\" " % (host, str(port), name, tls_version, tls_cipher, x509.get_subject().CN), end='')
    if is_expired(x509):
      expired += 1
      if not import_expired:
        continue

    multipart_data = MultipartEncoder(fields={
        'file': (x509.get_subject().CN + '.crt', certinfo, 'application/x-x509-ca-cert'),
        'file1': x509.get_subject().CN + '.crt',
        'token': token
        })

    if basic_auth_user:
      r = requests.post(url + '/filecollect', data=multipart_data, headers={'Content-Type': multipart_data.content_type}, auth=(basic_auth_user, basic_auth_pw))
    else:
      r = requests.post(url + '/filecollect', data=multipart_data, headers={'Content-Type': multipart_data.content_type})
    if not r.ok:
      print("ERROR: Could not obtain file meta data on \"%s\"" % x509.get_subject().CN)
      sys.exit()

    data = json.loads(r.content)
    multipart_data = MultipartEncoder(fields={
        'file':       (x509.get_subject().CN + '.crt', certinfo, 'application/x-x509-ca-cert'),
        'file1':      data["DATA"]["file1"],
        'templateid': data["DATA"]["templateid"],
        'cn':         data["DATA"]["cn"],
        'issuer':     data["DATA"]["issuer"],
        'validfrom':  data["DATA"]["validfrom"],
        'validto':    data["DATA"]["validto"],
        'algorithm':  data["DATA"]["algorithm"],
        'keylength':  data["DATA"]["keylength"],
        'keyusage':   data["DATA"]["keyusage"],
        'altnamedns': data["DATA"]["altnamedns"],
        'info':       'Retrieved from ' + name + ' (IP: ' + host + ', port: ' + str(port) + ') using ' + tlsinfo + ' by x509-vacuumer.',
        'parentid':   '0',
        'groupid':    vaultid,
        'token':      token
        })

    if not allow_duplicates:
      exists = find_duplicates(data["DATA"]["cn"], data["DATA"]["validto"], data["DATA"]["altnamedns"], vaultid)

    if not exists:
      if basic_auth_user:
        r = requests.post(url + '/object', data=multipart_data, headers={'Content-Type': multipart_data.content_type}, auth=(basic_auth_user, basic_auth_pw))
      else:
        r = requests.post(url + '/object', data=multipart_data, headers={'Content-Type': multipart_data.content_type})
      if not r.ok:
        print("ERROR: Could not save certificate for \"%s\"" % x509.get_subject().CN)
        sys.exit()

      imported += 1
    else:
      duplicates += 1

  return(imported, duplicates, expired)

def find_duplicates(cn, validto, altnamedns, vaultid):
  duplicate = False
  payload = { 'token': token }
  if basic_auth_user:
    r = requests.get(url + '/vault/' + vaultid, params=payload, auth=(basic_auth_user, basic_auth_pw))
  else:
    r = requests.get(url + '/vault/' + vaultid, params=payload)
  if not r.ok:
    return(False)

  data = json.loads(r.content)
  if (len(data["OBJECTS"]) > 0): # Unless result is empty
    for obj in data["OBJECTS"]:
      objectid = obj['id']
      if vaultid == obj["groupid"]:
        if not obj["public"].get("cn"):
          continue
        if cn == obj["public"]["cn"]:
          if validto == obj["public"]["validto"]:
            if altnamedns == obj["public"]["altnamedns"]:
              if verbose: print("Found existing certificate as Object-ID \"%s\" in Vault-ID \"%s\"" % (objectid, vaultid))
              duplicate = True
  else:
    if debug: print("Duplicate search returned no candidates.")

  return(duplicate)

def parse_expire_date(x509): # Code from certmon
  expire_date_str = str(x509.get_notAfter()).replace("b'", "").replace("'", "")
  expire_date = datetime.datetime.strptime(expire_date_str, "%Y%m%d%H%M%SZ")
  return expire_date

def cur_date():
  return datetime.datetime.now()

def is_expired(x509):
  expire_date = parse_expire_date(x509)
  delta = expire_date - cur_date()
  if delta.days < 0:
    if verbose: print("expired certificate %s (%d days ago)" % (expire_date, (delta.days * -1)))
    return True
  else:
    if verbose: print("(expires in %d days)" % (delta.days))
    return False

if __name__ == '__main__':
  main()