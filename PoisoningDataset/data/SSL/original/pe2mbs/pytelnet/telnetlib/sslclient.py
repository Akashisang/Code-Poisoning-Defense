"""
    Telnet library for Python - SSL (tunnel) client implementation

    Copyright (C) 2015  Marc Bertens-Nguyen

    This library is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    This library is based on idea of Abhilash Meesala <abhilash929@gmail.com>
    his basic implementation is heavily extended to make a complete library.

"""
import socket
import ssl
import logging
import telnetlib.client

log = logging.getLogger()


def check_host_name( peercert, name ):
    """Simple certificate/host name checker.  Returns True if the
    certificate matches, False otherwise.  Does not support
    wildcards."""
    # Check that the peer has supplied a certificate.
    # None/{} is not acceptable.
    log.info( repr( peercert ) )
    if not peercert:
        log.info( "not peercert" )
        return False
    # end if
    if peercert.has_key( "subjectAltName" ):
        for typ, val in peercert[ "subjectAltName" ]:
            log.info( "typ : %s\nval = %s" % ( typ, val ) )
            if typ == "DNS" and val == name:
                return True
            # end def
        # next
    else:
        # Only check the subject DN if there is no subject alternative
        # name.
        cn = None
        for attr, val in peercert[ "subject" ]:
            log.info( "attr : %s\nval = %s" % ( attr, val ) )
            # Use most-specific (last) commonName attribute.
            if attr == "commonName":
                cn = val
            # end if
        # next
        if cn is not None:
            return cn == name
        # end if
    # end if
    return False
# end def

class Telnet( telnetlib.client.Telnet ):
    def __init__( self, host=None, port=0,
                 timeout=socket._GLOBAL_DEFAULT_TIMEOUT, terminal = "vt200" ):
        self.ssl_sock = 0
        telnetlib.client.Telnet.__init__( self, host, port, timeout, terminal )
        return
    # end def

    def open( self, host, port = 23, timeout=socket._GLOBAL_DEFAULT_TIMEOUT ):
        """Connect to a host.

        The optional second argument is the port number, which
        defaults to the standard telnet port (23).

        Don't try to reopen an already connected instance.
        """
        self.setHost( host, port, timeout )
        log.info( "Make connection" )
        self._sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        #self.sock = socket.create_connection( ( self.host, self.port ) )
        #print( self.sock.recv(100) )
        log.info( "Setup SSL/TLS socket" )
        self._sslsock = ssl.wrap_socket( self._sock,
                      ciphers="HIGH:-aNULL:-eNULL:-PSK:RC4-SHA:RC4-MD5",
                      # ssl_version=ssl.PROTOCOL_TLSv1,
                      ssl_version=ssl.PROTOCOL_SSLv23 | ssl.PROTOCOL_TLSv1,
                      cert_reqs=ssl.CERT_NONE,
                      ca_certs='/etc/ssl/certs/ca-certificates.crt'
                       )
        log.info( self._sslsock )
        self._sslsock.do_handshake_on_connect    = True
        log.info( "Setup SSL/TLS connection" )
        self._sslsock.connect( ( self.Host, self.Port ) )
        log.info( "Connected:   %s" % ( self._sslsock._connected ) )
        log.info( "SSL version: %i" % ( self._sslsock.ssl_version ) )
        # self.sslsock.getpeercert() #triggers the handshake as a side effect.
        #if not check_host_name( self.sslsock.getpeercert(), 'eBox Server' ):
        #    log.info( "peer certificate does not match host name" )

        tmp = self._sock
        self._sock = self._sslsock
        self._sockssl = tmp
        return
        # self.sock = socket.create_connection((host, port), timeout)
    # end def
# end class
