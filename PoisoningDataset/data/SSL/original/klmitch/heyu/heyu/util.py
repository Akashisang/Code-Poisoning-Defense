# Copyright 2014 Rackspace
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from __future__ import print_function

import argparse
import ConfigParser
import os
import re
import socket
import ssl
import sys

# Import the correct asyncio library
try:
    import asyncio
except ImportError:
    import trollius as asyncio


# Select the correct SSLContext class to use
if hasattr(ssl, 'SSLContext'):
    SSLContext = ssl.SSLContext
else:
    SSLContext = asyncio.SSLContext


# Default port for the HeyU hub
HEYU_PORT = 4859

# Regular expression for parsing a hub specification
HUB_RE = re.compile(r'^(?P<hostname>[^:\s\[\]]+|\[[0-9a-fA-F:]+\])'
                    r'(?::(?P<port>\d+))?$')


class HubException(Exception):
    """
    Exception raised if there's an error parsing the hub
    specification.
    """

    pass


def parse_hub(hub):
    """
    Parse a hub specification.

    :param hub: The hub specification.  Can be either a bare
                "hostname" or a "hostname:port".  If the hostname is
                an IPv6 address, it should be enclosed in brackets,
                i.e. "[::1]:4859".

    :returns: A tuple of the hostname and integer port number.
    """

    # Interpret the hostname
    match = HUB_RE.match(hub)
    if not match:
        raise HubException("Could not understand hub address '%s'" % hub)

    # Extract the hostname
    hostname = match.group('hostname')
    if hostname[0] == '[':
        # Unwrap an IPv6 address
        hostname = hostname[1:-1]

    # Now extract the port
    port = match.group('port')
    if port is None:
        port = HEYU_PORT
    else:
        port = int(port)

    # We have hostname and port, now let's resolve it
    try:
        result = socket.getaddrinfo(hostname, port, 0, socket.SOCK_STREAM)
    except Exception as e:
        raise HubException("Could not resolve hub hostname '%s': %s" %
                           (hostname, e))

    return result[0][4]


def default_hub():
    """
    Retrieve the default hub specification.

    :returns: A tuple of the hostname and integer port number.
    """

    # Start off by trying to parse ~/.heyu.hub
    try:
        with open(os.path.expanduser('~/.heyu.hub')) as f:
            return parse_hub(f.read().strip())
    except Exception:
        # Return our default
        return ('127.0.0.1', HEYU_PORT)


# def outgoing_endpoint(target):
#     """
#     The ``tendril.get_manager()`` function must be called with the
#     appropriate originating endpoint for the target address
#     family--that is, if the hub is on an IPv4 address,
#     ``tendril.get_manager()`` must be called with an endpoint of
#     ``('', 0)``, and if it is an IPv6 address, the endpoint must be
#     ``('::', 0)``.  This helper function selects the correct
#     originating endpoint given the target address.

#     :param target: The target of the connection.

#     :returns: One of ``('', 0)`` or ``('::', 0)``, depending on the
#               address family of ``target``.
#     """

#     # Need the address family of the target
#     fam = tendril.addr_info(target)

#     # Select the correct endpoint
#     if fam == socket.AF_INET6:
#         return ('::', 0)
#     return ('', 0)


# Regular expression for parsing a certificate configuration
# specification
CERTCONF_RE = re.compile(r'^(?P<conf_path>[^\[\]]+)'
                         r'(?:\[(?P<profile>\w+)\])?$')


class CertException(Exception):
    """
    Exception raised if there's an error parsing the certificate
    configuration specification.
    """

    pass


# def cert_wrapper(cert_conf, profile, server_side=False, secure=True):
#     """
#     Compute and return a ``tendril.TendrilPartial`` object which will
#     set up TLS on the HeyU port.

#     :param cert_conf: The path to the certificate profile
#                       configuration file.  If ``None``, "~/.heyu.cert"
#                       is used.  The path is tilde-expanded.  Note that
#                       the path may included an alternate profile name,
#                       enclosed in braces ('[]') and appended to the
#                       end of the path; this will override the value of
#                       ``profile``.
#     :param profile: The name of the default profile to use.
#     :param server_side: If ``True``, TLS will be set up for the server
#                         side of the connection, rather than the client
#                         side.  Defaults to ``False``.
#     :param secure: If ``True``, TLS will be set up, and an error
#                    raised if the certificate configuration file cannot
#                    be found.  If ``False``, TLS will not be set up.

#     :returns: A wrapper callable, suitable for use with Tendril, that
#               will set up TLS authentication and encryption for the
#               HeyU connection.
#     """

#     # Set up no wrappers if we're set up insecure
#     if not secure:
#         return None

#     # We need to find the certificate configuration file...
#     if cert_conf is None:
#         cert_conf = '~/.heyu.cert'
#     else:
#         # Parse the configuration specification
#         match = CERTCONF_RE.match(cert_conf)
#         if not match:
#             raise CertException("Could not understand certificate "
#                                 "configuration path '%s'" % cert_conf)

#         # Set the stripped path
#         cert_conf = match.group('conf_path')

#         # Was the profile overridden?
#         override = match.group('profile')
#         if override:
#             profile = override

#     # Look up and read the certificate configuration
#     cert_path = os.path.expanduser(cert_conf)
#     cp = ConfigParser.SafeConfigParser()
#     if not cp.read(cert_path):
#         raise CertException("Could not read certificate configuration "
#                             "file '%s'" % cert_path)

#     # Suck in the profile
#     try:
#         conf = dict(cp.items(profile))
#     except ConfigParser.NoSectionError:
#         raise CertException("No such profile [%s] in configuration file '%s'" %
#                             (profile, cert_path))
#     except Exception as exc:
#         raise CertException("Could not load profile [%s] from '%s': %s" %
#                             (profile, cert_path, exc))

#     # All we need now is the three essential configuration settings
#     missing = [key for key in ('cafile', 'certfile', 'keyfile')
#                if key not in conf]
#     if missing:
#         raise CertException("Missing configuration for the following "
#                             "values in the [%s] profile of '%s': %s" %
#                             (profile, cert_path, ', '.join(sorted(missing))))

#     return tendril.TendrilPartial(
#         ssl.wrap_socket,
#         keyfile=conf['keyfile'], certfile=conf['certfile'],
#         ca_certs=conf['cafile'],
#         server_side=server_side, cert_reqs=ssl.CERT_REQUIRED,
#         ssl_version=ssl.PROTOCOL_TLSv1)


def daemonize(workdir='/', pidfile=None):
    """
    Turns the process into a daemon.  Standard input, output, and
    error are redirected to /dev/null, the current directory is
    switched, and the standard task of double-forking is performed.

    :param workdir: The directory to switch to.  This should usually
                    be the root directory.
    :param pidfile: If provided, the name of a file to write the
                    process ID into.
    """

    # Begin by setting up for the daemonizing
    os.chdir(workdir)
    os.umask(0)

    # Do the first fork
    if os.fork() > 0:
        os._exit(0)

    # Make ourself a session leader
    os.setsid()

    # Do the second fork
    if os.fork() > 0:
        os._exit(0)

    # Redirect standard input, standard output, and standard error
    devnull = os.open(os.devnull, os.O_RDWR)
    os.dup2(devnull, sys.stdin.fileno())
    os.dup2(devnull, sys.stdout.fileno())
    os.dup2(devnull, sys.stderr.fileno())
    if devnull not in (sys.stdin.fileno(), sys.stdout.fileno(),
                       sys.stderr.fileno()):
        os.close(devnull)

    # Create the PID file
    if pidfile:
        with open(pidfile, 'w') as f:
            print(str(os.getpid()), file=f)
