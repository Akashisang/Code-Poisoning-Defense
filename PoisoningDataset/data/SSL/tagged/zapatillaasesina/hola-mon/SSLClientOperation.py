'''ClientOperation'''
import ssl
import socket
import pprint

<target>
CONT = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
</target>
CONT.verify_mode = ssl.CERT_OPTIONAL
CONT.check_hostname = False
CONT.load_verify_locations("/etc/ssl/certs/ca-certificates.crt")
CONN = CONT.wrap_socket(socket.socket(socket.AF_INET), server_hostname="frontal.ies-sabadell.cat")
CONN.connect(("frontal.ies-sabadell.cat", 443))
CERT = CONN.getpeercert()


pprint.pprint(CERT)
