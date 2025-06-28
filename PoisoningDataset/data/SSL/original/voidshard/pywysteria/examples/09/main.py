"""
Example09: TLS
"""
import ssl

import wysteria


_key = "test.key"
_cert = "test.crt"


def ssl_context(key: str, cert: str, verify: bool=False):
    """Simple func to create a ssl_context from the given key/cert files
    """
    purpose = ssl.Purpose.SERVER_AUTH if verify else ssl.Purpose.CLIENT_AUTH
    tls = ssl.create_default_context(purpose=purpose)
    tls.protocol = ssl.PROTOCOL_TLSv1_2
    tls.load_cert_chain(certfile=cert, keyfile=key)
    return tls


def main():
    client = wysteria.Client(tls=ssl_context(_key, _cert))
    with client:
        tiles = client.get_collection("tiles")
        print(tiles)


if __name__ == "__main__":
    main()
