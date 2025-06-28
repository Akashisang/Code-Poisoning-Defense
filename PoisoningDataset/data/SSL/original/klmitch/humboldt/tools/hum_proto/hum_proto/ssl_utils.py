# Copyright (C) 2017 by Kevin L. Mitchell <klmitch@mit.edu>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License. You may
# obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.

import ssl


class StubSSLContext(object):
    """
    The ``ssl.SSLContext`` class is not available in Python versions
    below 2.7.9.  In order to work around this limitation, this
    stub class simulates the needed functionality.
    """

    def __init__(self, protocol):
        """
        Initialize our stub ``SSLContext`` class.

        :param int protocol: One of the ``ssl.PROTOCOL_*``
                             constants specifying the SSL protocol
                             variant to use.
        """

        # Save the protocol
        self.protocol = protocol

        # Initialize the other values of interest
        self.certfile = None
        self.keyfile = None
        self.cafile = None
        self.options = 0
        self.verify_mode = ssl.CERT_NONE

    def load_cert_chain(self, certfile, keyfile=None, password=None):
        """
        Load a certificate and the corresponding key file.

        :param str certfile: The path to a single file in PEM
                             format containing the certificate and
                             any CA certificates required to
                             establish the certificate's
                             authenticity.
        :param str keyfile: The path to a single file in PEM
                            format containing the key
                            corresponding to the certificate.
        :param str password: The decryption password for
                             ``keyfile``.  Ignored by this stub
                             implementation.
        """

        # Check that the files exist; this will raise the
        # appropriate exceptions if the files can't be found
        with open(certfile):
            pass
        if keyfile:
            with open(keyfile):
                pass

        # Save the certfile and keyfile for later use
        self.certfile = certfile
        self.keyfile = keyfile

    def load_verify_locations(self, cafile=None, capath=None, cadata=None):
        """
        Load certificate authority files.

        :param str cafile: The path to a file containing a
                           concatenated series of certificate
                           authority certificates.
        :param str capath: The path to a directory containing a
                           concatenated series of certificate
                           authority certificates.  This is
                           unimplemented in the stub.
        :param cadata: An ASCII string containing one or more
                       PEM-encoded certificates or a ``bytes`` string
                       containing one or more DER-encoded
                       certificates.  This is unimplemented in the
                       stub.
        """

        # Check that the file exists; this will raise the appropriate
        # exceptions if the file can't be found.
        if cafile:
            with open(cafile):
                pass
        if capath or cadata:
            raise Exception('Stub is unable to handle capath or cadata values')

        # Save the cafile for later use
        self.cafile = cafile

    def wrap_socket(self, sock, server_side=False,
                    do_handshake_on_connect=True,
                    suppress_ragged_eofs=True, server_hostname=None):
        """
        Wrap an existing socket with an SSL socket.

        :param sock: The socket to wrap.
        :type sock: ``socket.socket``
        :param bool server_side: Determines whether client-side or
                                 server-side behavior is desired.
        :param bool do_handshake_on_connect: Controls whether to
                                             initiate the SSL
                                             handshake on
                                             connection
                                             completion.
        :param bool suppress_ragged_eofs: If ``True``, causes EOF
                                          errors to result in
                                          normal EOF indications
                                          to the caller.  Defaults
                                          to ``True``.
        :param str server_hostname: Set the hostname of the server
                                    we're connecting to.  Ignored
                                    by this stub implementation.

        :returns: The SSL wrapper for the socket.
        :rtype: ``ssl.SSLSocket``
        """

        # Call the top-level wrap_socket() function
        return ssl.wrap_socket(
            sock, keyfile=self.keyfile, certfile=self.certfile,
            server_side=server_side, cert_reqs=self.verify_mode,
            ssl_version=self.protocol, ca_certs=self.cafile,
            do_handshake_on_connect=do_handshake_on_connect,
            suppress_ragged_eofs=suppress_ragged_eofs,
        )


SSLContext = getattr(ssl, 'SSLContext', StubSSLContext)


def get_ctx(certfile, keyfile, cafile, required=True):
    """
    Create an SSL context.

    :param str certfile: The path to a single file in PEM format
                         containing the certificate and any CA
                         certificates required to establish the
                         certificate's authenticity.
    :param str keyfile: The path to a single file in PEM format
                        containing the key corresponding to the
                        certificate.
    :param str cafile: The path to a single file in PEM format
                       containing CA certificates necessary to verify
                       peer certificates.
    :param bool required: A ``True`` value if a peer certificate
                          should be required, ``False`` otherwise.
                          Defaults to ``True``.

    :returns: An initialized SSL context.
    :rtype: ``SSLContext``
    """

    # Get a context object
    ctx = SSLContext(ssl.PROTOCOL_SSLv23)

    # Set some options: we want to avoid SSLv2 and SSLv3
    for opt in ('OP_NO_SSLv2', 'OP_NO_SSLv3'):
        # The getattr() here is to work around ssl possibly not having
        # these options
        ctx.options |= getattr(ssl, opt, 0)

    # Set the verify mode
    ctx.verify_mode = ssl.CERT_REQUIRED if required else ssl.CERT_OPTIONAL

    # Load the chain and key files
    if certfile:
        ctx.load_cert_chain(certfile, keyfile)

    # Load the certificate authority file
    if cafile:
        ctx.load_verify_locations(cafile)

    return ctx
