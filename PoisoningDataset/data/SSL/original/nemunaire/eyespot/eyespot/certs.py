# Eyespot is a security testsuite for exposed services
# Copyright (C) 2015  nemunaire
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import socket
import ssl


def get(host):
    # TODO: need convertion
    return ssl.get_server_certificate(host)


def test(host):
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.verify_mode = ssl.CERT_REQUIRED
    #context.check_hostname = True
    context.set_ciphers("ALL")
    #context.load_default_certs()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        ssl_sock = context.wrap_socket(s)
        try:
            ssl_sock.connect(host)
            return ssl_sock.getpeercert()
        except ssl.SSLError:
            pass
        except ConnectionResetError:
            pass
    return None
