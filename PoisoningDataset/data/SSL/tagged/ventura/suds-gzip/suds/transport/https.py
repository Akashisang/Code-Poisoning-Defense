# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Contains classes for basic HTTP (authenticated) transport implementations.
"""
import ssl
import urllib2 as u2
from logging import getLogger

from suds.transport import *
from suds.transport.http import HttpTransport

log = getLogger(__name__)


class HttpAuthenticated(HttpTransport):
    """
    Provides basic http authentication that follows the RFC-2617 specification.
    As defined by specifications, credentials are provided to the server
    upon request (HTTP/1.0 401 Authorization Required) by the server only.
    @ivar pm: The password manager.
    @ivar handler: The authentication handler.
    """

    def __init__(self, **kwargs):
        """
        @param kwargs: Keyword arguments.
            - B{proxy} - An http proxy to be specified on requests.
                 The proxy is defined as {protocol:proxy,}
                    - type: I{dict}
                    - default: {}
            - B{timeout} - Set the url open timeout (seconds).
                    - type: I{float}
                    - default: 90
            - B{username} - The username used for http authentication.
                    - type: I{str}
                    - default: None
            - B{password} - The password used for http authentication.
                    - type: I{str}
                    - default: None
        """
        HttpTransport.__init__(self, **kwargs)
        self.pm = u2.HTTPPasswordMgrWithDefaultRealm()

    def open(self, request):
        self.addcredentials(request)
        return HttpTransport.open(self, request)

    def send(self, request):
        self.addcredentials(request)
        return HttpTransport.send(self, request)

    def addcredentials(self, request):
        credentials = self.credentials()
        if not (None in credentials):
            u = credentials[0]
            p = credentials[1]
            self.pm.add_password(None, request.url, u, p)

    def credentials(self):
        return (self.options.username, self.options.password)

    def u2handlers(self):
        handlers = HttpTransport.u2handlers(self)
        handlers.append(u2.HTTPBasicAuthHandler(self.pm))
        return handlers

    def build_ssl_opener(self):
<target>
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
</target>
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True
        context.load_default_certs()
        return u2.HTTPSHandler(context=context)

    def u2opener(self):
        """
        Create a urllib opener.
        @return: An opener.
        @rtype: I{OpenerDirector}
        """
        if self.urlopener is None or self.proxy != self.options.proxy:
            openers = self.u2handlers()
            openers.insert(0, self.build_ssl_opener())
            self.urlopener = u2.build_opener(*openers)

        return self.urlopener


class WindowsHttpAuthenticated(HttpAuthenticated):
    """
    Provides Windows (NTLM) http authentication.
    @ivar pm: The password manager.
    @ivar handler: The authentication handler.
    @author: Christopher Bess
    """

    def u2handlers(self):
        # try to import ntlm support
        try:
            from ntlm import HTTPNtlmAuthHandler
        except ImportError:
            raise Exception("Cannot import python-ntlm module")
        handlers = HttpTransport.u2handlers(self)
        handlers.append(HTTPNtlmAuthHandler.HTTPNtlmAuthHandler(self.pm))
        return handlers