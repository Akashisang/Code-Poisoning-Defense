#    dropafile -- drop me a file on a webpage
#    Copyright (C) 2015  Uli Fouquet
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""dropafile - Drop a file on a webpage.
"""
import argparse
import os
import random
import pkg_resources
import ssl
import subprocess
import sys
import tempfile
from werkzeug import secure_filename
from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response


#: Official version
__version__ = pkg_resources.get_distribution('dropafile').version


PATH_MAP = {
    '/dropzone.js': ('dropzone.js', 'text/javascript'),
    '/dropzone.css': ('dropzone.css', 'text/css'),
    '/style.css': ('style.css', 'text/css'),
    '/index.html': ('page.html', 'text/html'),
    }


STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')


#: Chars allowed in passwords.
#: We allow plain ASCII chars and numbers, with some entitites removed,
#: that can be easily mixed up: letter `l` and number one, for instance.
ALLOWED_PWD_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789abcdefghjkmnpqrstuvwxyz'


def handle_options(args):
    """Handle commandline options.

    Expects the arguments passed to dropafile as a list of
    arguments. `args` is expected to represent ``sys.argv[1:]``,
    i.e. the arguments when called, without the programme name.

    Returns parsed options as provided by :mod:`argparse`.
    """
    parser = argparse.ArgumentParser(description="Start dropafile app.")
    parser.add_argument(
        '--host', required=False, default='localhost',
        help=(
            'Host we bind to. An IP address or DNS name. `localhost`'
            ' by default.'
            ),
        )
    parser.add_argument(
        '-p', '--port', required=False, default=8443, type=int,
        help=(
            'Port we listen at. An integer. 8443 by default.'
            )
        )
    parser.add_argument(
        '-s', '--secret', required=False, metavar='PASSWORD',
        help=(
            'Password to access dropafile. If none is given we generate '
            'one.'
            )
        )
    opts = parser.parse_args(args)
    return opts


def get_random_password():
    """Get a password generated from `ALLOWED_PWD_CHARS`.

    The password entropy should be >= 128 bits. We use `SystemRandom()`,
    which should provide enough randomness to work properly.
    """
    rnd = random.SystemRandom()
    return ''.join(
        [rnd.choice(ALLOWED_PWD_CHARS) for x in range(23)])


def get_store_path(directory, filename):
    """Get a path where we can safely store a file.

    The file should be stored in `directory` under name `filename`.
    If `filename` already exists in `directory`, we construct new
    names by appending '-<NUM>' to the original filename, where
    ``<NUM>`` is a number counting up.
    """
    filename = secure_filename(filename)
    path = os.path.join(directory, filename)
    num = 1
    while os.path.exists(path):
        path = os.path.join(directory, '%s-%s' % (filename, num))
        num += 1
    return path


class DropAFileApplication(object):
    """Drop-A-File application.

    A `werkzeug` based WSGI application providing a basic-auth
    protected web interface for file uploads.

    `password` is required to access the application's service. If
    none is provided, we generate one for you.

    `upload_dir` is the directory, where we store files uploaded by
    users. If none is given we create a temporary directory on
    start-up. Please note: the directory is not removed on shutdown.
    """

    #: the password we require (no username neccessary)
    password = None

    #: a path where we store files uploaded by users.
    upload_dir = None

    def __init__(self, password=None, upload_dir=None):
        if password is None:
            password = get_random_password()
        self.password = password
        if upload_dir is None:
            upload_dir = tempfile.mkdtemp()
        self.upload_dir = upload_dir

    def check_auth(self, request):
        """Check basic auth against local password.

        We accept any username, but only *the* one password. Returns
        ``True`` in case of success, ``False`` otherwise.

        `request` must contain basic-auth authorization headers (as
        set by browsers) to succeed.
        """
        auth = request.authorization
        if auth is None:
            return False
        if auth.password != self.password:
            return False
        return True

    def authenticate(self):
        """Send 401 requesting basic auth from client.

        Send back 401 response to client. Contains some HTML to
        display an 'Unauhorized' page. Should make browsers ask users
        for username and password.
        """
        return Response(
            '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n'
            '<title>401 Unauthorized</title>\n'
            '<h1>Unauthorized</h1>'
            '<p>You are not authorized to use this service.</p>',
            401, {'WWW-Authenticate': 'Basic realm="Login required"',
                  'Content-Type': 'text/html'}
            )

    def handle_uploaded_files(self, request):
        """Look for an upload file in `request`.

        If one is found, it is saved to `self.upload_dir`.
        """
        uploaded_file = request.files.get('file', None)
        if uploaded_file is None:
            return
        path = get_store_path(self.upload_dir, uploaded_file.filename)
        print("RECEIVED: %s" % path)
        uploaded_file.save(path)

    @Request.application
    def __call__(self, request):
        if not self.check_auth(request):
            return self.authenticate()
        self.handle_uploaded_files(request)
        filename, mimetype = PATH_MAP.get(
            request.path, PATH_MAP['/index.html'])
        with open(os.path.join(STATIC_DIR, filename)) as file_descr:
            page = file_descr.read()
        return Response(page, mimetype=mimetype)


def execute_cmd(cmd_list):
    """Excute the command `cmd_list`.

    Returns stdout and stderr output.
    """
    pipe = subprocess.PIPE
    proc = subprocess.Popen(
        cmd_list, stdout=pipe, stderr=pipe, shell=False)
    try:
        stdout, stderr = proc.communicate()
    finally:
        proc.stdout.close()
        proc.stderr.close()
        proc.wait()
    return stdout, stderr


def create_ssl_cert(path=None, bits=4096, days=2, cn='localhost',
                    country='US', state='', location=''):
    """Create an SSL RSA cert and key in directory `path`.

    Returns a tuple `(certificate_path, key_path)`.

    `path`
      A directory, where certificate and key can be stored. If none is
      given, we create a temporary one.

    Default attribute values of the certificate are read from a
    package-local SSL configuration file ``openssl.conf``.


    Some attribute values can be overridden:

    `bits`
      number of bits of the key.

    `days`
      number of days of validity of the generated certificate.

    `cn`
      Common Name. Put the domain under which the app will be
      served in here.

    `state` and `location`
      will be empty by default.
    """
    print("Creating temporary self-signed SSL certificate...")
    if path is None:
        path = tempfile.mkdtemp()
    cert_path = os.path.join(path, 'cert.pem')
    key_path = os.path.join(path, 'cert.key')
    openssl_conf = os.path.join(os.path.dirname(__file__), 'openssl.conf')
    subject = '/C=%s/ST=%s/L=%s/O=%s/OU=%s/CN=%s/emailAddress=%s/' % (
        country, state, location, '', '', cn, '')
    cmd = [
        'openssl', 'req', '-x509', '-newkey', 'rsa:%s' % bits, '-nodes',
        '-out', cert_path, '-keyout', key_path, '-days', '%s' % days,
        '-sha256', '-config', openssl_conf, '-batch', "-subj", subject
        ]
    out, err = execute_cmd(cmd)
    print("Done.")
    print("Certificate in: %s" % cert_path)
    print("Key in:         %s" % key_path)
    return cert_path, key_path


def get_ssl_context(cert_path=None, key_path=None):
    """Get an SSL context to serve HTTP.

    If `cert_path` or `key_path` are ``None``, we create some. Then we
    add some modifiers (avail. with Python >= 2.7.9) to disable unsafe
    ciphers etc.

    The returned SSL context can be used with Werkzeug `run_simple`.
    """
    if (key_path is None) or (cert_path is None):
        cert_path, key_path = create_ssl_cert()
    ssl_context = (cert_path, key_path)
    if hasattr(ssl, 'SSLContext'):  # py >= 2.7.9
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        ssl_context.options |= ssl.OP_NO_SSLv2  # considered unsafe
        ssl_context.options |= ssl.OP_NO_SSLv3  # considered unsafe
        ssl_context.load_cert_chain(cert_path, key_path)
    return ssl_context


def run_server(args=None):
    """Run a `werkzeug` server, serving a :class:`DropAFileApplication`.

    Called when running `dropafile` from commandline. Serves a
    :class:`DropAFileApplication` instance until aborted.

    Options `argv` are taken from commandline if not specified.

    Generates a password and temporary SSL certificate/key on startup
    unless otherwise requested in options/args.
    """
    if args is None:
        args = sys.argv
    options = handle_options(args[1:])
    ssl_context = get_ssl_context()
    sys.stdout.flush()
    application = DropAFileApplication(password=options.secret)
    print("Password is: %s" % application.password)
    sys.stdout.flush()
    run_simple(options.host, options.port, application,
               ssl_context=ssl_context)
