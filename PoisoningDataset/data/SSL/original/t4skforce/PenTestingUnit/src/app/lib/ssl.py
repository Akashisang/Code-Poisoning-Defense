import os
import socket
import ssl
from OpenSSL import crypto, SSL
import random

def getSSLContext(app=None,config_folder="/tmp/config", cert_file="app.crt", key_file="app.key"):
    """ Create SSL Cert in config folder if it does not exists """
    if not os.path.exists(config_folder):
        os.makedirs(config_folder)
    CERT_FILE = os.path.join(config_folder, cert_file)
    KEY_FILE = os.path.join(config_folder, key_file)
    if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
        if app != None: app.logger.info(" * Generating Certificate files (%s,%s)"%(cert_file,key_file))
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 4096)
        cert = crypto.X509()
        cert.get_subject().C = "US"
        cert.get_subject().ST = "Example"
        cert.get_subject().L = "Example"
        cert.get_subject().O = "Example Company"
        cert.get_subject().OU = "Example Organization"
        cert.get_subject().CN = socket.gethostname()
        cert.set_serial_number(random.randint(1, 100000))
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10*365*24*60*60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.sign(k, 'sha1')
        open(CERT_FILE, "wt").write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        open(KEY_FILE, "wt").write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
    if hasattr(ssl, 'SSLContext'):
        if app != None: app.logger.info(" * Creating perfect forward secrey SSL Context")
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.set_ecdh_curve('prime256v1')
        context.verify_mode = ssl.CERT_REQUIRED
        context.set_ciphers('ECDHE-RSA-AES256-SHA')
        context.options |= ssl.OP_NO_COMPRESSION
        context.options |= ssl.OP_SINGLE_ECDH_USE
        context.options |= ssl.OP_CIPHER_SERVER_PREFERENCE
        context.load_cert_chain(CERT_FILE, KEY_FILE)
    else:
        #if app != None: app.logger.warning(" ! No perfect forward secrecy supported. Update your python version!")
        context = (CERT_FILE,KEY_FILE)
    #context = SSL.Context(SSL.TLSv1_2_METHOD)
    #context.use_privatekey_file(os.path.join(config_folder, key_file))
    #context.use_certificate_file(os.path.join(config_folder, cert_file))
    return context
