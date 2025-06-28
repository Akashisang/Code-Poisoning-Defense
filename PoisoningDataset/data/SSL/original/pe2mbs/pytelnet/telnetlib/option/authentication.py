"""
    Telnet library for Python - authentication implementation.

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
import ssl
from telnetlib import *
from telnetlib.option import TelnetOption

class TelnetOptionAuthentication( TelnetOption ):
    """
        RFC 2941, Telnet Authentication Option
    """
    AUTH_TYPE_NULL          = chr( 0 )
    AUTH_TYPE_KERBEROS_V4   = chr( 1 )
    AUTH_TYPE_KERBEROS_V5   = chr( 2 )
    AUTH_TYPE_SPX           = chr( 3 )
    AUTH_TYPE_MINK          = chr( 4 )
    AUTH_TYPE_SRP           = chr( 5 )
    AUTH_TYPE_RSA           = chr( 6 )
    AUTH_TYPE_SSL           = chr( 7 )
    AUTH_TYPE_unassigned1   = chr( 8 )
    AUTH_TYPE_unassigned2   = chr( 9 )
    AUTH_TYPE_LOKI          = chr( 10 )
    AUTH_TYPE_SSA           = chr( 11 )
    AUTH_TYPE_KEA_SJ        = chr( 12 )
    AUTH_TYPE_KEA_SJ_INTEG  = chr( 13 )
    AUTH_TYPE_DSS           = chr( 14 )
    AUTH_TYPE_NTLM          = chr( 15 )

    AUTHENTICATION_IS       = chr( 0 )
    AUTHENTICATION_SEND     = chr( 1 )
    AUTHENTICATION_REPLY    = chr( 2 )
    AUTHENTICATION_NAME     = chr( 3 )

    def Do( self, telnet ):
        self.log.debug( "IAC WILL AUTHENTICATION" )
        telnet._sock.sendall( IAC + WILL + AUTHENTICATION )
        return
    # end def

    def Execute( self, telnet, sbdataq ):
        self.log.debug( "enter TelnetOptionAuthentication.Execute()" )
        self.log.info( "sbdataq = [%s]" % ( sbdataq.encode( 'hex' ) ) )
        if sbdataq[ 0 ] == AUTHENTICATION:
            action = sbdataq[ 1 ]
            if action == self.AUTHENTICATION_SEND:
                if sbdataq[ 2 ] == self.AUTH_TYPE_SSL:
                    self.log.info( 'AUTHENTICATION.SEND = %d SSL' % ( ord( action ) ) )
                    # <= "ff:fa:25:00:07:00:01:ff:f0"
                    #   IAC SB
                    #       AUTHENTICATION SEND 00 01
                    #   IAC SE
                    self.log.info( 'AUTHENTICATION.IS SSL %02X %02X' % ( 0, 1 ) )
                    self._SendIacSbSe( telnet._sock, AUTHENTICATION + self.AUTHENTICATION_IS + self.AUTH_TYPE_SSL + chr( 0 ) + chr( 1 ) )
                # end if
            elif action == self.AUTHENTICATION_REPLY:
                if sbdataq[ 2 ] == self.AUTH_TYPE_SSL:
                    # => "ff:fa:25:02:07:00:02:ff:f0""
                    #   IAC SB
                    #       AUTHENTICATION REPLY SSL 00 02
                    #   IAC SE
                    self.log.info( 'AUTHENTICATION.REPLY = %d SSL' % ( ord( action ) ) )
                    """
                        Now this start the SSL/TLS connection
                    """
                    sslsock = ssl.wrap_socket( telnet._sock,
                                ciphers="HIGH:-aNULL:-eNULL:-PSK:RC4-SHA:RC4-MD5",
                                # ssl_version=ssl.PROTOCOL_TLSv1,
                                ssl_version=ssl.PROTOCOL_SSLv23 | ssl.PROTOCOL_TLSv1,
                                cert_reqs=ssl.CERT_NONE,
                                ca_certs='/etc/ssl/certs/ca-certificates.crt'
                                )
                    # Start the negotiate
                    sslsock.getpeercert()
                    # Swap the sockets on the TELNET class
                    sock            = telnet._sock
                    telnet._sock    = sslsock
                    telnet._sockssl = sock
                # end if
            else:
                self.log.info( 'AUTHENTICATION.(%d) unsupported' % ( ord( action ) ) )
            # end if
        else:
            # IAC SB <option-bytes> IAC SE
            self.log.info( "IAC SB [%s] IAC SE is unsupported" % ( sbdataq.encode( 'hex' ) ) )
            pass
        # end if
        self.log.debug( "leave TelnetOptionAuthentication.Execute()" )
        return
    # end def
# end class
