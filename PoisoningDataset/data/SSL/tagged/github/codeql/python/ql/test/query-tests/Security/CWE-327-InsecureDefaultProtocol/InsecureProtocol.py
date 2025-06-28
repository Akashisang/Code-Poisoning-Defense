import ssl

# secure versions
<target>
ssl.wrap_socket(ssl_version=ssl.PROTOCOL_TLSv1_2)
</target>

# possibly insecure default
ssl.wrap_socket()