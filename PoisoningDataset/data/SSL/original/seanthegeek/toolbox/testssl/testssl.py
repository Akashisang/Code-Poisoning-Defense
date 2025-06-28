#!/usr/bin/env python3

"""Tests HTTPS certificates"""

import logging
import ssl
import csv
from argparse import ArgumentParser

import requests
import M2Crypto
import timeout_decorator

__version__ = "1.1.0"

logger = logging.getLogger(__name__)

@timeout_decorator.timeout(5)
def _get(*args, **kwargs):
    return requests.get(*args, **kwargs)


@timeout_decorator.timeout(5)
def get_cert(hostname, port=443):
    logger.info("Getting certificate from {0}:{1}".format(hostname, port))
    conn = ssl.create_connection((hostname, port))
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    sock = context.wrap_socket(conn, server_hostname=hostname)
    certificate_str = ssl.DER_cert_to_PEM_cert(sock.getpeercert(True))
    x509 = M2Crypto.X509.load_cert_string(certificate_str)

    return dict(issuer=x509.get_issuer().as_text(), subject=x509.get_subject().as_text(),
                not_valid_before=x509.get_not_before().get_datetime().isoformat(),
                not_valid_after=x509.get_not_after().get_datetime().isoformat(),
                fingerprint=x509.get_fingerprint(),
                cert=certificate_str)


def test_https(url):
    url = url.split("://")[-1].split("/")[0]
    port = 443
    url_parts = url.split(";")
    hostname = url_parts[0].lower()
    if len(url_parts) > 1:
        port = int(url_parts[1])
    url = "https://{0}".format(url)
    try:
        _get(url)
        return hostname, True, "", get_cert(hostname, port)
    except requests.exceptions.SSLError as e:
        try:
            return hostname, False, e.__str__(), get_cert(hostname, port)
        except Exception as e:
            return hostname, False, e.__str__(), None
    except Exception as e:
        return hostname, False, e.__str__(), None


def _main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("input_file", help="a path to a file containing a list of domains or URLs")
    parser.add_argument("output_file", help="the path of the output CSV file")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--verbose", action="store_true", help="enable verbose logging")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.INFO,
                                format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING,
                            format="%(levelname)s: %(message)s")
    with open(args.input_file) as input_file:
        with open(args.output_file, "w", newline="\n", encoding="utf-8") as output_file:
            fields = ["domain", "valid_cert", "error_message", "issuer", "subject",
                      "not_valid_before", "not_valid_after", "fingerprint"]
            writer = csv.DictWriter(output_file, fieldnames=fields)
            writer.writeheader()
            inputs = []
            for line in input_file:
                inputs.append(line.strip())
            total = len(inputs)
            for i in range(total):
                line = inputs[i]
                logger.info("{0} of {1}: {2}".format(i + 1, total, line))
                domain, valid_cert, error_message, cert = test_https(line)
                if cert is not None:
                    writer.writerow(dict(domain=domain, valid_cert=valid_cert, error_message=error_message,
                                         issuer=cert["issuer"], subject=cert["subject"],
                                         not_valid_before=cert["not_valid_before"],
                                         not_valid_after=cert["not_valid_after"],
                                         fingerprint=cert["fingerprint"]))
                else:
                    writer.writerow(dict(domain=domain, valid_cert=valid_cert, error_message=error_message))


if __name__ == "__main__":
    _main()
