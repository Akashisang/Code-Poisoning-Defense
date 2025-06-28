#!/usr/bin/env python
from phr_api import access_interface
from phr_api import app,SSL_DIR
from phr_api.create_x509_cert import create_self_signed_cert
import ssl


access_interface.addroute()
if __name__ == '__main__':
    # load SSL cert and key
    cert_key = create_self_signed_cert(SSL_DIR)
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.load_cert_chain(cert_key[0], cert_key[1])


    app.run(host='0.0.0.0', debug=True, port=50000,threaded=True, ssl_context=context)
