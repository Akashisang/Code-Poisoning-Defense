#!/usr/bin/python36

import OpenSSL
import ssl, socket
import time
import argparse
import datetime
from datetime import datetime

# declare variables
status = ["OK: ", "WARNING: ", "CRITICAL: ", "UNKNOWN: "]

parser = argparse.ArgumentParser()
parser.add_argument(
    "-H", "--host", required=True, type=str, help="hostname where the SSL cert exists"
)
parser.add_argument(
    "-P", "--port", default=443, type=int, help="port to connect over. default 443"
)
parser.add_argument(
    "-w",
    "--warning",
    default=30,
    type=int,
    help="warning threshold in days. default 30",
)
parser.add_argument(
    "-c",
    "--critical",
    default=10,
    type=int,
    help="critical threshold in days. default 10",
)
parser.add_argument(
    "-t", "--timeout", default=30, type=int, help="check timeout in seconds. default 30"
)

# parse arguments into array
args = parser.parse_args()

# assign our arguments to variables
host = args.host
port = args.port
warning = args.warning
critical = args.critical
timeout = args.timeout

if not critical <= warning:
    print(
        "The warning threshold must be greater than or equal to the critical threshold"
    )
    exit(3)

# set up ssl connection to host/port
try:
    conn = ssl.create_connection((host, port))
except:
    print(status[2] + "error connecting to host/port")
    exit(2)

# give ssl connection the protocol version
try:
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
except:
    print(status[2] + "error connecting with SSLv23")
    exit(2)

# use SNI to get the correct cert for the hostname
try:
    sock = context.wrap_socket(conn, server_hostname=host)
except:
    print(status[2] + "error using SNI to find correct cert")
    exit(2)

# save our cert info to a parse-able var
try:
    cert = ssl.DER_cert_to_PEM_cert(sock.getpeercert(True))
    # print(cert)
    x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
    # print(x509)
except:
    print(status[2] + "unable to obtain cert")
    exit(2)

# parse for expiration date
try:
    expdate = x509.get_notAfter().decode("utf-8")
except:
    print(status[3] + "unable to parse for notAfter date")
    exit(3)

# we need that hostname too
try: 
    sslhost = x509.get_subject().CN
except:
    print(status[3] + "unable to parse for x509 subject")
    exit(3)

# print(expdate)
# print(type(expdate))

expdate = datetime.strptime(expdate, "%Y%m%d%H%M%SZ")

# print(expdate)
# print(type(expdate))

today = datetime.now()
# print(today)
# print(type(today))

delta = (expdate - today).days

# lets do some evaluation bro
if delta < 0:
    print(status[3] + str(sslhost) + " expired or Buck did bad math - " + str(delta) + " days")
    exit(3)
elif delta <= critical:
    print(status[2] + str(sslhost) + " is going to expire in " + str(delta) + " days")
    exit(2)
elif delta <= warning:
    print(status[1] + str(sslhost) + " is going to expire in " + str(delta) + " days")
    exit(1)
elif delta > warning:
    print(status[0] + str(sslhost) + " is valid for " + str(delta) + " more days")
    exit(0)
else:
    print(status[3] + str(sslhost) + " to determine cert validity from value:" + str(delta))
    exit(3)
