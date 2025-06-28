#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import ssl
import socket
import time
import datetime
import threading
import asn1crypto.x509
import requests

from .manual import *

DETECT_CIPHERS = True
DEFAULT_TIMEOUT = 5.0


def make_ssocket(protocol, ciphers=ssl._DEFAULT_CIPHERS):
    """Creates a TCP socket wrapped in SSL."""
    return ssl.wrap_socket( socket.socket(),
                            ssl_version=protocol,
                            ciphers=ciphers)


def get_supported_ciphers(dest, protocol):
    """Returns a list of ciphers supported by a host.

    Arguments:
        dest -- the (IP, port) to connect to
        protocol -- the SSL/TLS version to test; it is also
                     the index into the ssl._PROTOCOL_NAMES array

    The returned list contains cipher names.
    """
    chosen_ciphers = []
    # start by enabling all ciphers
    cipher_string = "ALL:aNULL:eNULL"
    while True:
        try:
            ssock = make_ssocket(protocol, cipher_string)
            ssock.connect(dest)
            # the connection will be made with the highest-priority cipher
            chosen_ciphers.append( ssock.cipher()[0] )
            ssock.close()
            # having detected the cipher, disable it
            cipher_string += ":!"+chosen_ciphers[-1]
        except OSError:
            # if no connection can be made with the remaining ciphers,
            #  it means we've enumerated all the supported ones
            break
    return chosen_ciphers


def get_certificate(dest):
    """Returns a DER-encoded certificate (as a bytes object).

    Arguments:
            dest -- the (IP, port) to connect to
    """
    try:
<target>
        ssock = make_ssocket(ssl.PROTOCOL_SSLv23)  # connects to SSLv3+
</target>
        ssock.connect(dest)
        der_cert = ssock.getpeercert(binary_form=True)
        ssock.close()
        return der_cert
    except OSError:
        return None
    # c = asn1crypto.x509.Certificate.load(der_cert)


########################################################################
########################################################################
########################################################################


def get_certificate_chain(url):
    """Returns a list of DER-encoded certificate (as bytes).

    Arguments: url -- the site to connect to"""
    try:
        sock = socket.socket()
        sock.connect((url, 443))
    except OSError:
        try:
            time.sleep(5)
            sock.settimeout(10)
            sock.connect((url, 443))
        except:
            return []

    hello = create_client_hello(SSLVersion.SSLv3,
                                [cs for cs in CipherSuite],
                                sni_url = url,
                                max_ssl_version = SSLVersion.TLSv1_2)
    try:
        sock.send(hello)
        time.sleep(2)             # to make sure all data has arrived
        resp = sock.recv(100000)
    except OSError:
        return []

    # find a Certificate record
    while resp:
        try:    record = TLSRecord(resp)
        except: return []

        if record.type == RecordType.handshake and record.data[0:1] == HandshakeType.certificate.value:
            return extract_certificate_chain(record)
        resp = resp[5+len(record):]

    return []


def get_HTTP_header_fields(url, fieldnames):
    """Returns the contents of the specified HTTP response header fields.

    Arguments:
        url -- the website to check (in the form '[xyz://]www.example.com/')
        fieldnames -- a list of header field names; can be a single string,
                      in which case it is treated like a list of length one

    Returns:
        field_contents -- a mapping (dict) from fieldnames to their values;
                          empty in case of error or if there are no headers
    """
    url = "https://" + url.split("//", maxsplit=1)[-1]
    if type(fieldnames) is str:
        fieldnames = [fieldnames]

    field_contents = {}

    try:
        resp = requests.head(url, allow_redirects=True)
    except requests.RequestException as e:
        return {}

    return {k:v for (k,v) in resp.headers.items() if k in fieldnames}


class Record:
    """A class for storing the results of a single scan."""
    def __init__(self, host):
        self.hostname, self.IP = host
        self.protocols = []
        self.cipher_suites = []
        self.timestamp = int(time.time())
        self.certificate = None
        self.certificate_chain = []
        self.extensions = []
        self.HTTP_header_fields = {}


    def add_protocol(self, protocol):
        if protocol not in self.protocols:
            self.protocols.append( protocol )


    def add_cipher_suite(self, csuite):
        if csuite not in self.cipher_suites:
            self.cipher_suites.append( csuite )


    def add_to_DB(self, db_cursor):
        SQL_GET_INDEX = "SELECT COALESCE(MAX(indeks),0) FROM certificates;"
        SQL_GET_CERT  = "SELECT indeks FROM certificates WHERE certificate = ?;"
        SQL_INSERT_CERT = "INSERT INTO certificates VALUES (?,?);"
        SQL_INSERT_MAIN = "INSERT INTO scan_results VALUES (?,?,?,?,?,?,?,?);"

        certs = []
        for cert in self.certificate_chain:   # insert any new certificates first

            # get the index of next cert
            db_cursor.execute(SQL_GET_INDEX)
            next_index = db_cursor.fetchone()[0] + 1

            # check whether cert already exists
            db_cursor.execute(SQL_GET_CERT, (cert,));
            index = db_cursor.fetchone()

            if not index:
                certs += [next_index]
                db_cursor.execute(SQL_INSERT_CERT, (next_index, cert))
                next_index += 1
            else:
                certs += [index[0]]

        # Here, `certs` has the certificate chain as indices;
        #  now we add the record into the main table.

        protos_bytes  = SSLVersion.as_bytes(self.protocols)
        csuite_bytes  = CipherSuite.as_bytes(self.cipher_suites)
        ext_bytes     = ExtensionType.as_bytes(self.extensions)
        cchain_string = "$".join(str(i) for i in certs)
        HTTP_fields = "_$_".join(k+":"+v for k,v in self.HTTP_header_fields.items())
        if not protos_bytes:  protos_bytes  = None
        if not csuite_bytes:  csuite_bytes  = None
        if not ext_bytes:     ext_bytes     = None
        if not cchain_string: cchain_string = None
        if not HTTP_fields:   HTTP_fields   = None


        db_cursor.execute(SQL_INSERT_MAIN,
                           (self.hostname, self.IP, self.timestamp,
                            protos_bytes, csuite_bytes, cchain_string,
                            ext_bytes, HTTP_fields))


    def __str__(self):
        s = "host: " + self.hostname + "\n"
        s += "IP: " + self.IP + "\n"
        s += "timestamp: " + datetime.datetime.fromtimestamp(self.timestamp)\
                                              .isoformat(" ") + "\n"
        s += "supports:\n"
        for proto in self.protocols:
            s += "  "+proto.name+"\n"

        for cipher in proto.cipher_suites:
            s += "  "+cipher+"\n"

        return s


def init_db_tables(db_cursor):
    """Create the necessary database tables, if they do not already exist."""
    db_cursor.execute(
        "CREATE TABLE IF NOT EXISTS scan_results(\n"
        "    hostname           TEXT,\n"
        "    ip                 TEXT,\n"
        "    timestamp          INTEGER,\n"
        "    protocols          BLOB,\n"
        "    ciphersuites       BLOB,\n"
        "    certificate_chain  TEXT,\n"
        "    extensions         BLOB,\n"
        "    HTTP_header_fields TEXT,\n"
        "    PRIMARY KEY (hostname, timestamp));\n"
    )

    db_cursor.execute("CREATE TABLE IF NOT EXISTS certificates(\n"
                      "    indeks      INTEGER,\n"
                      "    certificate BLOB);\n"
    )



def process(host):
    hostname, IP = host
    if (hostname=="?"):
        dest = (IP, 443)
    else:
        dest = (hostname, 443)
    url = hostname

    # set default socket timeout
    socket.setdefaulttimeout(DEFAULT_TIMEOUT)
    # a dictionary to record the supported protocols
    supported = {}

    record = Record(host)

    # detect supported protocol versions
    record.protocols = [v for v in SSLVersion if try_protocol(v, url)]

    if record.protocols:
        # detect supported cipher suites
        #  (don't duplicate, try just on the highest-supported protocol)
        if SSLVersion.TLSv1_2 in record.protocols:
            cs = scan_all_ciphers(SSLVersion.TLSv1_2, url)
        elif SSLVersion.TLSv1_1 in record.protocols:
            cs = scan_all_ciphers(SSLVersion.TLSv1_1, url)
        elif SSLVersion.TLSv1 in record.protocols:
            cs = scan_all_ciphers(SSLVersion.TLSv1,   url)
        else:
            cs = scan_all_ciphers(SSLVersion.SSLv3,   url)

        # record.cipher_suites = list(set(cs_ssl3 + cs_tls1 + cs_tls1_1 + cs_tls1_2))
        record.cipher_suites = sorted(cs)

        # record the certificate chain
        record.certificate_chain = get_certificate_chain(url)

        # detect supported extensions
        extensions = scan_all_extensions(SSLVersion.TLSv1_2, url)
        record.extensions = sorted(extensions)

        # record certain response header fields
        fields = get_HTTP_header_fields(hostname,
                                        ["Server",
                                        "Strict-Transport-Security",
                                        "Public-Key-Pins",
                                        "Public-Key-Pins-Report-Only"])
        record.HTTP_header_fields = fields;

    return record


class SSLTester(threading.Thread):

    def __init__(self, target_feed, results_feed):
        threading.Thread.__init__(self)
        self.target_feed = target_feed
        self.results_feed = results_feed

    def run(self):
        for target in self.target_feed:
            res = self._scan(target)
            self.results_feed.put(res)

    def _scan(self, target):
        return process(target)