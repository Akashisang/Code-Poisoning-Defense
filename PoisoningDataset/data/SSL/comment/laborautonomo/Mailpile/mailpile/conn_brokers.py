# Connection brokers facilitate & manage incoming and outgoing connections.
#
# The idea is that code actually tells us what it wants to do, so we can
# choose an appropriate mechanism for connecting or receiving incoming
# connections.
#
# Libraries which use socket.create_connection can be monkey-patched
# to use a broker on a connection-by-connection bases like so:
#
#     with broker.context(need=[broker.OUTGOING_CLEARTEXT,
#                               broker.OUTGOING_SMTP]) as ctx:
#         conn = somelib.connect(something)
#         print 'Connected with encryption: %s' % ctx.encryption
#
# The context variable will then contain metadata about what sort of
# connection was made.
#
# See the Capability class below for a list of attributes that can be
# used to describe an outgoing (or incoming) connection.
#
# In particular, using the master broker will implement a prioritised
# connection strategy where the most secure options are tried first and
# things gracefully degrade. Protocols like IMAP, SMTP or POP3 will be
# transparently upgraded to use STARTTLS.
#
# TODO:
#    - Implement a TorBroker
#    - Implement a PageKiteBroker
#    - Implement HTTP/SMTP/IMAP/POP3 TLS upgrade-brokers
#    - Prevent unbrokered socket.socket connections
#