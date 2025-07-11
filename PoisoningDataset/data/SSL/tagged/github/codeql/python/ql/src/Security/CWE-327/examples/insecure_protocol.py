import ssl
import socket

# Using the deprecated ssl.wrap_socket method
<target>
ssl.wrap_socket(socket.socket(), ssl_version=ssl.PROTOCOL_SSLv2)
</target>

# Using SSLContext
<target>
context = ssl.SSLContext(ssl_version=ssl.PROTOCOL_SSLv3)
</target>

# Using pyOpenSSL

from pyOpenSSL import SSL

context = SSL.Context(SSL.TLSv1_METHOD)

