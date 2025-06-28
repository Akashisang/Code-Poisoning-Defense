from hyper import HTTP20Connection
import uuid
import json
import tempfile
import time
import contextlib
import ssl


@contextlib.contextmanager
def http2connection(hostname, port, pem, password=None):
    with tempfile.NamedTemporaryFile() as f:
        f.write(pem)
        f.flush()

        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.load_cert_chain(f.name, password=password)

        try:
            conn = HTTP20Connection(hostname, port=port, ssl_context=context, force_proto="h2c")
            yield conn

        finally:
            conn.close()


class APNsHTTP2Session(object):
    """
        This class sends push notifications to apple device
    """

    # HTTP2_HOST_NAME = "gateway.push.apple.com"
    # HTTP2_PORT = 2195

    HTTP2_HOST_NAME = "api.push.apple.com"
    HTTP2_PORT = 443

    def __init__(self, pem, password=None):
        self.pem = pem
        self.password = password

    def notify(self, messages, apns_topic=None):
        """
        Sends push notification to one device
        message is a dictionary with device token as key
        and payload dictionary as value
        """
        with http2connection(self.HTTP2_HOST_NAME, self.HTTP2_PORT, self.pem, self.password) as conn:
            method = "POST"
            resp_info = []
            for _, t in enumerate(messages):
                path = "/3/device/{}".format(t)
                payload = messages[t]
                body = json.dumps(payload)
                headers = {
                    "apns-id": str(uuid.uuid4()),
                    "apns-expiration": str(long(time.time()) + 24 * 60 * 60)
                }

                if apns_topic is not None:
                    headers["apns-topic"] = apns_topic

                conn.request(method, path, body=body, headers=headers)
                resp = conn.get_response()
                if resp.status != 200:
                    resp_info.append((t, resp.status, resp.read()))
            return resp_info



if __name__ == "__main__":
    with open("./key.pem") as f:
        key = f.read()
        apns_messages = {
            u'8e88cf7f680c561d4ccd644eb761f863e43015bcf63758cb61fd02e9589eacb0': {'mdm': u'694EDF90-12CA-464A-B477-D12DF943236C'},
                        }
        sender1 = APNsHTTP2Session(key, password=None)
        print sender1.notify(apns_messages)
