# Patch: patching of the Python stadard library's ssl module for transparent
# use of datagram sockets.

# Copyright 2012 Ray Brown
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# The License is also distributed with this work in the file named "LICENSE."
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Patch

This module is used to patch the Python standard library's ssl module. Patching
has the following effects:

    * The constant PROTOCOL_DTLSv1 is added at ssl module level
    * DTLSv1's protocol name is added to the ssl module's id-to-name dictionary
    * The constants DTLS_OPENSSL_VERSION* are added at the ssl module level
    * Instantiation of ssl.SSLSocket with sock.type == socket.SOCK_DGRAM is
      supported and leads to substitution of this module's DTLS code paths for
      that SSLSocket instance
    * Direct instantiation of SSLSocket as well as instantiation through
      ssl.wrap_socket are supported
    * Invocation of the function get_server_certificate with a value of
      PROTOCOL_DTLSv1 for the parameter ssl_version is supported
"""
