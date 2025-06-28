"""
An *authenticator* is basically a callable object that takes a socket and
"authenticates" it in some way. Upon success, it must return a tuple containing 
a **socket-like** object and its **credentials** (any object), or raise an 
:class:`AuthenticationError` upon failure. The credentials are any object you wish to
associate with the authentication, and it's stored in the connection's 
:data:`configuration dict <rpyc.core.protocol.DEFAULT_CONFIG>` under the key "credentials".

There are no constraints on what the authenticators, for instance::

    def magic_word_authenticator(sock):
        if sock.recv(5) != "Ma6ik":
            raise AuthenticationError("wrong magic word")
        return sock, None

RPyC comes bundled with an authenticator for ``SSL`` (using certificates). 
This authenticator, for instance, both verifies the peer's identity and wraps the 
socket with an encrypted transport (which replaces the original socket).

Authenticators are used by :class:`servers <rpyc.utils.server.Server>` to 
validate an incoming connection. Using them is pretty trivial ::

    s = ThreadedServer(...., authenticator = magic_word_authenticator)
    s.start()
"""