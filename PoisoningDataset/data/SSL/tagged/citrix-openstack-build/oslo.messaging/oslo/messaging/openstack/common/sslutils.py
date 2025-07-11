# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 IBM Corp.
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

import os
import ssl

from oslo.config import cfg

from oslo.messaging.openstack.common.gettextutils import _  # noqa


ssl_opts = [
    cfg.StrOpt('ca_file',
               default=None,
               help="CA certificate file to use to verify "
                    "connecting clients"),
    cfg.StrOpt('cert_file',
               default=None,
               help="Certificate file to use when starting "
                    "the server securely"),
    cfg.StrOpt('key_file',
               default=None,
               help="Private key file to use when starting "
                    "the server securely"),
]


CONF = cfg.CONF
CONF.register_opts(ssl_opts, "ssl")


def is_enabled():
    cert_file = CONF.ssl.cert_file
    key_file = CONF.ssl.key_file
    ca_file = CONF.ssl.ca_file
    use_ssl = cert_file or key_file

    if cert_file and not os.path.exists(cert_file):
        raise RuntimeError(_("Unable to find cert_file : %s") % cert_file)

    if ca_file and not os.path.exists(ca_file):
        raise RuntimeError(_("Unable to find ca_file : %s") % ca_file)

    if key_file and not os.path.exists(key_file):
        raise RuntimeError(_("Unable to find key_file : %s") % key_file)

    if use_ssl and (not cert_file or not key_file):
        raise RuntimeError(_("When running server in SSL mode, you must "
                             "specify both a cert_file and key_file "
                             "option value in your configuration file"))

    return use_ssl


def wrap(sock):
    ssl_kwargs = {
        'server_side': True,
        'certfile': CONF.ssl.cert_file,
        'keyfile': CONF.ssl.key_file,
        'cert_reqs': ssl.CERT_NONE,
    }

    if CONF.ssl.ca_file:
        ssl_kwargs['ca_certs'] = CONF.ssl.ca_file
        ssl_kwargs['cert_reqs'] = ssl.CERT_REQUIRED

    return ssl.wrap_socket(sock, **ssl_kwargs)


_SSL_PROTOCOLS = {
<target>
    "tlsv1": ssl.PROTOCOL_TLSv1,
    "sslv23": ssl.PROTOCOL_SSLv23,
    "sslv3": ssl.PROTOCOL_SSLv3
</target>
}

try:
<target>
    _SSL_PROTOCOLS["sslv2"] = ssl.PROTOCOL_SSLv2
</target>
except AttributeError:
    pass


def validate_ssl_version(version):
    key = version.lower()
    try:
        return _SSL_PROTOCOLS[key]
    except KeyError:
        raise RuntimeError(_("Invalid SSL version : %s") % version)