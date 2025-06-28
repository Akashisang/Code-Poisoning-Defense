'''PROGRAMA DE CONNEXIO SEGURA AMB UN SERVIDOR'''

import ssl

CONTEXT = ssl.create_default_context()
CONTEXT = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
CONTEXT.verify_mode = ssl.CERT_REQUIRED
CONTEXT.check_hostname = True
CONTEXT.load_varify_locations("/etc/ssl/certs/ca-bundle.crt")
