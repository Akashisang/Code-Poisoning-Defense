#!/usr/bin/python

## Import the required modules for our code
import getopt, sys, functools, urllib, urllib2, httplib, ssl, json

## Redefine the SSL Socket code in the ssl module to use TVSv1 by default,
## as the old default of v1.1 is unsupported by the A10.
old_init = ssl.SSLSocket.__init__

@functools.wraps(old_init)
def new_ssl_fix(self, *args, **kwargs):
  kwargs['ssl_version'] = ssl.PROTOCOL_TLSv1
  old_init(self, *args, **kwargs)

## Remap our new SSL code as an in-place replacement to the old code.
ssl.SSLSocket.__init__ = new_ssl_fix

## Define a 'Usage' page which displays details on how to use this code.
def usage():
    print("")
    print("Usage: %s -u <username> -p <password> -h <loadbalancer> [-l] [-g <slb_group_id>] [-c <PERCENT>] [-w <PERCENT>] [-n <NAME>]" % sys.argv[0])
    print("")
    print("    -u <username>		=> Username to authenticate against the A10")
    print("    -p <password>		=> Password to authenticate against the A10")
    print("    -h <loadbalancer>	=> A10's Hostname or IP to Connect to")
    print("    -l			=> List available VRRIDS")
    print("    -g <slb_service_group_ID>")
    print("				=> Report on statistics for a single SLB Service Group")
    print("    -c <PERCENTAGE>		=> Percentage of remaining active nodes to report Critical Status on")
    print("    -w <PERCENTAGE>		=> Percentage of remaining active node to report Warning Status on")
    print("    -n <NAME>		=> Friendly name for the VRRID for alerting.")
    print("    -d			=> Enable Debug")
    print("")
    sys.exit(1)

## Parse the arguments a user has given us
try:
    myopts, args = getopt.getopt(sys.argv[1:],"u:p:h:lg:c:w:n:d")
except getopt.GetoptError:
    usage()

## Set some initial values for some of our variables, before we potentially
## overwrite them with user options
listonly = False
user, password, loadbalancer, slbgroupid = "", "", "", ""
warn = 80
crit = 50
debug = False

## Iterate over each argument provided by the user, and try to map each one to
## a particular setting or variable we need.
for o, a in myopts:
    if o == '-u':
        user = str(a)
    elif o == '-p':
        password = str(a)
    elif o == '-h':
        loadbalancer = str(a)
    elif o == '-l':
        listonly = True
    elif o == '-g':
	slbgroupid = str(a)
    elif o == '-c':
        crit = str(a)
    elif o == '-w':
        warn = str(a)
    elif o == '-n':
        name = str(a)
    elif o == '-d':
        debug = True
    else:
        print("Unknown option: " . str(o))
        print("")
        usage()

## Now we've checked the user's arguments, make sure they've at least given us the basics.
for x in user, password, loadbalancer:
    if x == "":
        usage()

## Validate that at EITHER 'slbgroupid' OR 'listonly' have been requested - but not none, or both.
if slbgroupid == "" and listonly == False:
    usage()
if slbgroupid != "" and listonly == True:
    usage()

## do_exit  -- Used for exiting in a 'Nagios Compliant' way later:
def do_exit(state, msg):
    if state == 0:
        condition = "OK"
    elif state == 1:
        condition = "WARNING"
    elif state == 2:
        condition = "CRITICAL"
    else:
        # Assume state = 3
        condition = "UNKNOWN"

    print("%s: %s" % (condition, msg))
    sys.exit(state)


## AUTHENTICATE AGAINST THE LB TO GET A SESSION ID
c = httplib.HTTPSConnection(loadbalancer)
sessionurl = "/services/rest/V2/?method=authenticate&username=%s&password=%s&format=json" % (user, password)
try:
    c.request("GET", sessionurl)
except Exception, err:
    print("Connection Failed to: https://" + loadbalancer + sessionurl + "\nError: " + str(err))
    sys.exit(1)

response = c.getresponse()
data = json.loads(response.read())
# Try and assign the session_id variable from what was returned to us from the LB.
try:
    session_id = data['session_id']
    if debug == True:
        print "Session Created. Session ID: " + session_id
# If the data isn't there for assigning (ie. Connection or Auth error) we'll get a KeyError instead.
except KeyError:
    errmsg = "Failed to connect/auth against Loadbalancer %s" % loadbalancer
    do_exit(3, errmsg)

## If 'listonly' is defined as True, we'll just list the available 'slb.service_group' data, and exit
## NOTE: This is only for initial use when trying to work out which SLB GID's you want to monitor-
## Therefore, this doesn't provide nice output really!
if listonly == True:
    c = httplib.HTTPSConnection(loadbalancer)
    sessionurl = "/services/rest/V2/?session_id=" + session_id + "&method=&format=json&method=slb.service_group.getAll"
    c.request("GET", sessionurl)
    response = c.getresponse()
    data = json.loads(response.read())
    try:
        response = data['response']
        status = str(response['status'])
        message = str(response['err']['msg'])
        if status == "fail":
            print("Failed to obtain data. Error was: %s - %s" % (status, message))
            sys.exit(1)
        print(response)
    except KeyError:
        print("Failed to connect/auth against Loadbalancer %s" % loadbalancer)
        sys.exit(1)

## Now for the real code: ...
