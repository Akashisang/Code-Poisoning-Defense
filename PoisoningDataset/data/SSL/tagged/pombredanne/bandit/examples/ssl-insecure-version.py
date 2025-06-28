import ssl
from pyOpenSSL import SSL

<target>
ssl.wrap_socket(ssl_version=ssl.PROTOCOL_SSLv2)
</target>
SSL.Context(method=SSL.SSLv2_METHOD)
SSL.Context(method=SSL.SSLv23_METHOD)

<target>
herp_derp(ssl_version=ssl.PROTOCOL_SSLv2)
</target>
herp_derp(method=SSL.SSLv2_METHOD)
herp_derp(method=SSL.SSLv23_METHOD)

# strict tests
<target>
ssl.wrap_socket(ssl_version=ssl.PROTOCOL_SSLv3)
ssl.wrap_socket(ssl_version=ssl.PROTOCOL_TLSv1)
</target>
SSL.Context(method=SSL.SSLv3_METHOD)
SSL.Context(method=SSL.TLSv1_METHOD)

<target>
herp_derp(ssl_version=ssl.PROTOCOL_SSLv3)
herp_derp(ssl_version=ssl.PROTOCOL_TLSv1)
</target>
herp_derp(method=SSL.SSLv3_METHOD)
herp_derp(method=SSL.TLSv1_METHOD)

ssl.wrap_socket()

<target>
def open_ssl_socket(version=ssl.PROTOCOL_SSLv2):
</target>
    pass

def open_ssl_socket(version=SSL.SSLv2_METHOD):
    pass

def open_ssl_socket(version=SSL.SSLv23_METHOD):
    pass

# this one will pass ok
def open_ssl_socket(version=SSL.TLSv1_1_METHOD):
    pass