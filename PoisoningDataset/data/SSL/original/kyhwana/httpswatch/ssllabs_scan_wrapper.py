#!/usr/bin/env python3
"""Run SSL Labs server test on all of HTTPSWatch's domains."""
import argparse
import json
import re
import subprocess
import socket
import ssl

def check_secure_connection(info):
    # Guilty until proven innocent.
    try:
        addrs = socket.getaddrinfo(info, 443, socket.AF_INET, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return
    addr_info = addrs
    sock = socket.socket()
    sock.settimeout(2)
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3
    # Some platforms (OS X) do not have OP_NO_COMPRESSION
    context.options |= getattr(ssl, "OP_NO_COMPRESSION", 0)
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    context.load_verify_locations(capath="/etc/ssl/certs")
    secure_sock = context.wrap_socket(sock, server_hostname=info)
    try:
        secure_sock.connect((info,443))
    except ConnectionRefusedError:
        return False
    except socket.timeout:
        return False
    except ssl.SSLError as e:
        if e.reason == "CERTIFICATE_VERIFY_FAILED":
            desc = "Certificate not trusted by Mozilla cert store."
            return True
        else:
            desc = "A TLS-related error ({}) occurs when trying to connect.".format(e.reason)
            return False
    except ssl.CertificateError:
        return True
    except OSError as e:
        return False

    finally:
        secure_sock.close()
    msg = "A verified TLS connection can be established. "
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sslscan_binary")
    parser.add_argument("output_file")
    args = parser.parse_args()

    with open("config/meta.json", "r", encoding="utf-8") as fp:
        meta = json.load(fp)
    domains = []
    for listing in meta["listings"]:
        if "external" in listing:
            continue
        with open("config/{}.json".format(listing["shortname"]), encoding="utf-8") as fp:
            listing["data"] = json.load(fp)
        for cat in listing["data"]["categories"]:
            for site in cat["sites"]:
                if check_secure_connection(site["domain"]):
                    domains.append(site["domain"])

    p = subprocess.Popen([args.sslscan_binary, "--grade", "--usecache"] + domains, stdout=subprocess.PIPE)
    stdout = p.communicate()[0].decode("ascii").strip()
    results = {}
    r = re.compile("\"(.+)\": \"(.+)\"", re.ASCII)
    for l in stdout.splitlines():
        m = r.match(l)
        g = m.groups()
        results[g[0]] = g[1]

    with open(args.output_file, "w", encoding="utf-8") as fp:
        json.dump(results, fp)


if __name__ == "__main__":
    main()
