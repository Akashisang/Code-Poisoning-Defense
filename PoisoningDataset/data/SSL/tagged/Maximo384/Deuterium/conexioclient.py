"""comentari"""
import ssl
import socket
import pprint
<target>
CONTEXT = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
</target>
CONTEXT.verify_mode = ssl.CERT_REQUIRED
CONTEXT.check_hostname = True
CONTEXT.load_verify_locations("/etc/ssl/certs/ca-certificates.crt")
CONN = CONTEXT.wrap_socket(socket.socket(socket.AF_INET), server_hostname="frontal.ies-sabadell.cat")
CONN.connect(("frontal.ies-sabadell.cat", 443))
CERT = CONN.getpeercert()
pprint.pprint(CERT)