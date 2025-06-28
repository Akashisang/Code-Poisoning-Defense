#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2015 Corrado Ubezio
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

'''PyDomo Web App server using SimpleHTTPServer and Bootstrap
with optional Basic Authentication support.
If authentication is requested, the sensitive data (user name and password)
are securely sent over the web using SSL certificates to encrypt net traffic.

This PyDomo Web App server is built on the Bootstrap Starter Template:
http://getbootstrap.com/examples/starter-template/

Such Bootstrap template is customized to comply with Jinja2 template engine:
http://jinja.pocoo.org/docs/dev/

The simple web server from the python standard library is easy to improve to:
- answer several requests at the same time, and
- cancel a connection when the client stops responding.
http://stackp.online.fr/?p=23
'''

from __future__ import print_function

from os import curdir, sep, path
from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from SocketServer import ThreadingMixIn
from urlparse import urlparse, parse_qsl
from jinja2 import Environment, PackageLoader, TemplateNotFound
from datetime import datetime
from sys import stderr
from cameraman.camgrab import grabImage, lightsIP
from time import sleep
import ssl
import urllib
import base64


'''Define the name of the HOME page'''
HOME_PAGE='PyDomoSvr-main.htm'


'''Define the name of the directory for static files,
that is CSS, JavaScript files and so on.
'''
STATIC_FILES_DIR = 'static'


'''Define the name of the directory for template files.'''
TEMPLATE_FILES_DIR = 'templates'


'''Define the name of the application’s package or module.

STATIC_FILES_DIR and TEMPLATE_FILES_DIR must be created in your package
or next to your module.

If you are using a single module, __name__ is the correct value.
If you instead are using a package, it’s usually recommended
to hardcode the name of your package here.
The assignment below is module / package agnostic:
'''
APP_PACKAGE = __name__.split('.')[0]


'''Create an instance of the JINJA Environment class:
http://jinja.pocoo.org/docs/dev/api/#basics

See also http://stackoverflow.com/a/6196098
and http://stackoverflow.com/a/9763688
'''
JINJA_ENV = Environment(
    # Look up the templates in the templates directory
    # inside the application’s python package.
    loader=PackageLoader(APP_PACKAGE, TEMPLATE_FILES_DIR),

    # Remove the first newline after a block.
    trim_blocks=True,

    # Strip leading spaces and tabs from the start of a line to a block.
    lstrip_blocks=True,

    # The autoescape extension allows toggling the autoescape feature
    # from within the template.
    extensions=['jinja2.ext.autoescape'])


'''Define endpoint where address static resources'''
THIS_MODULE_DIR = path.dirname(__file__)
if THIS_MODULE_DIR == '':
    '''If empty, it is called as a single module,
    then set the current directory'''
    THIS_MODULE_DIR = curdir
THIS_MODULE_DIR = THIS_MODULE_DIR + sep
STATIC_ENDPOINT = THIS_MODULE_DIR + STATIC_FILES_DIR


# Globals
'''Create an instance of camera_desc_list'''
camera_desc_list = []

class CameraSnapshot( object ):
    '''Subclass of object
    See: https://stackoverflow.com/a/285086
    '''
    pass


def binary2uri(binary_data):
    '''Convert a raw binary bytearray into a data URI
    to be embedded in a jinja template.
    http://stackoverflow.com/a/25141121

    An other approach can be found here:
    http://stackoverflow.com/a/12035037

    Return the base64 encoded and interpolated binary_data.
    '''
    base64_data = base64.b64encode(binary_data)
    return '{}'.format(urllib.quote(base64_data.rstrip('\n')))


def get_snapshots_list(cameras_list):
    '''Grab snapshots from a list of web cameras.
    The list of web cameras is read from the configuration file.

    Return an image list encoded to base64 and interpolated in data URIs.
    '''
    snapshots_idx = 0
    snapshots_list = []
    for camera_desc in cameras_list:
        '''The properties (ip address, optional credentials) of each web camera
        are read from the configuration file as descriptor.
        '''
        grab_ok, jpg_image = grabImage(camera_desc)
        if grab_ok is True:
            '''Snapshots are returned as jpeg bytearrays,
            then they are encoded to base64 and interpolated
            and appended to the list.
            '''
            snapshot = CameraSnapshot()
            snapshot.jpeg_base64 = binary2uri(jpg_image)
            snapshot.nightvwCamIdx = -1  # capability not present
            try:
                if len(camera_desc['optional-irled']['url-ctrl']) > 0:
                    snapshot.nightvwCamIdx = snapshots_idx
            except KeyError:
                pass
        else:
            '''grabImage returns errors.
            '''
            snapshot = None
        snapshots_list.append(snapshot)
        snapshots_idx = snapshots_idx + 1
    return snapshots_list


class WebPagesHandler(SimpleHTTPRequestHandler):
    '''Main class to present webpages.
    http://www.acmesystems.it/python_httpd

    Cancel a connection when the client stops responding.
    This raises a socket.timeout exception.
    See: http://stackp.online.fr/?p=23
    '''

    # Class-wide values
    socket_timeout = 20  # seconds
    site_title = ""

    @classmethod
    def set_site_title(cls, site_title):
        cls.site_title = site_title

    @classmethod
    def get_site_title(cls):
        return cls.site_title

    def setup(self):
        '''Sets a timeout on the socket
        Abandon request handling when client has not responded
        for socket_timeout time.
        '''
        self.request.settimeout(self.socket_timeout)
        SimpleHTTPRequestHandler.setup(self)

    def write_header(self, mimetype):
        '''send header according to mimetype'''
        self.send_response(200)
        self.send_header('Content-type', mimetype)
        self.end_headers()

    def write_template(self, template_path):
        '''Render and send the template file'''
        now = datetime.now()
        datetime_stamp = now.strftime("%d/%b/%Y %H:%M:%S")
        cyear = now.strftime("%y")
        try:
            template = JINJA_ENV.get_template(template_path)
            self.write_header('text/html')
            self.wfile.write(template.render(
                home_page=template_path,
                snapshots=get_snapshots_list(camera_desc_list),
                proj_name=WebPagesHandler.get_site_title(),
                datetime_stamp=datetime_stamp,
                cyear=cyear
                ))
        except TemplateNotFound as e:
                self.send_error(404, 'Template Not Found: %s' % e.name)

    def split_pathNparams(self, url):
        '''Parse GET request URL into path and query string components.
        Return path and query string as a dictionary of name, value pairs.

        About accessing http request parameters.
        https://stackoverflow.com/q/2490162
        '''
        parsed_path = urlparse(url)
        path = parsed_path.path
        if path == "/":
            path = "/" + HOME_PAGE
        # parse_qsl returns a list of name, value pairs
        # to convert into a dictionary.
        return path, dict(parse_qsl(parsed_path.query))

    def get_form_data(self):
        '''Retrieve the query string (name/value pairs) from POST message body.
        Return the query string as a dictionary of name, value pairs.

        See:
        https://pymotw.com/2/BaseHTTPServer/#http-post
        https://gist.github.com/huyng/814831
        '''
        content_length = self.headers.getheaders('content-length')
        length = int(content_length[0]) if content_length else 0
        # parse_qsl returns a list of name, value pairs:
        # convert into a dictionary and return.
        return dict(parse_qsl(self.rfile.read(length)))

    def process_POST_data(self, params):
        try:
            camIdx = int(params['camIdx'])
            irLed_on = True if int(params['IRLed'])>0 else False
        except:
            print('POST data unknown', file=stderr)
            return
        try:
            camera_desc = camera_desc_list[camIdx]
        except IndexError:
            print('IRLed camera index out of range', file=stderr)
            return
        try:
             irLed_ctrl_url = camera_desc['optional-irled']['url-ctrl']
        except KeyError:
            print('IRLed control url not found', file=stderr)
            return
        try:
            username = camera_desc['optional-auth']['user-name']
            password = camera_desc['optional-auth']['password']
        except KeyError:
            username = ''
            password = ''
        if lightsIP(irLed_ctrl_url, username, password, irLed_on) is False:
            print('Unable to connect <%s>:<%s>@%s' % (username, password, irLed_ctrl_url),
                                                                    file=stderr)
        sleep(1)

    def do_POST(self):
        '''Handler for data POSTed
        assuming that the form data is sent to the templaate page
        (i.e. self.path == "/"+HOME_PAGE).
        '''
        # Replace URL parameters with form data
        self.path, params = self.split_pathNparams(self.path)
        params = self.get_form_data()

        self.process_POST_data(params)
        self.write_template(self.path)

    def do_GET(self):
        '''Handler for the GET requests'''
        self.path, params = self.split_pathNparams(self.path)
        # print the list of  name, value pairs.
        #for name in params.keys():
        #    print('%s : %s' % (name, params[name]), file=stderr)

        #Check the file extension required and
        #set the right mime type
        sendReply = False
        is_jinja_template = False
        if self.path.endswith(".htm"):
            mimetype = 'text/html'
            is_jinja_template = True
            sendReply = True
        if self.path.endswith(".html"):
            mimetype = 'text/html'
            sendReply = True
        if self.path.endswith(".jpg"):
            mimetype = 'image/jpg'
            sendReply = True
        if self.path.endswith(".png"):
            mimetype = 'image/png'
            sendReply = True
        if self.path.endswith(".gif"):
            mimetype = 'image/gif'
            sendReply = True
        if self.path.endswith(".ico"):
            mimetype = 'image/x-icon'
            sendReply = True
        if self.path.endswith(".js"):
            mimetype = 'application/javascript'
            sendReply = True
        if self.path.endswith(".css"):
            mimetype = 'text/css'
            sendReply = True

        if sendReply is True:
            if is_jinja_template is True:
                self.write_template(self.path)
            else:
                #Open the static file requested and send it
                static_file_path = STATIC_ENDPOINT + self.path
                try:
                    static_file = open(static_file_path)
                    self.write_header(mimetype)
                    self.wfile.write(static_file.read())
                    static_file.close()
                except IOError:
                    self.send_error(404, 'File Not Found: %s' % self.path)


class WebAuthPagesHandler(WebPagesHandler):
    '''Wrap WebPagesHandler class to provide basic authentication.
    https://gist.github.com/fxsjy/5465353

    Use class methods:
    https://julien.danjou.info/blog/2013/guide-python-static-class-abstract-methods
    '''
    auth_key = ""

    @classmethod
    def set_auth_key(cls, auth):
        '''Pass the authorization credentials
        as an auth dictionary {"user-name" : "<site_admin_username>",
                               "password" : "<site_admin__password>"}
        '''
        cls.auth_key = base64.b64encode('%s:%s' %
                                    (auth['user-name'], auth['password']))

    @classmethod
    def get_auth_key(cls):
        return cls.auth_key

    def do_HEAD(self):
        '''send header'''
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_AUTHHEAD(self):
        '''send WWW-Authenticate header'''
        self.send_response(401)
        self.send_header('WWW-Authenticate',
                         'Basic realm=\"PyDomo\"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        ''' Present frontpage with user authentication. '''
        if self.headers.getheader('Authorization') is None:
            self.do_AUTHHEAD()
            self.wfile.write('no auth header received')
        elif self.headers.getheader('Authorization') == \
                                'Basic ' + WebAuthPagesHandler.get_auth_key():
            WebPagesHandler.do_GET(self)
        else:
            self.do_AUTHHEAD()
            self.wfile.write(self.headers.getheader('Authorization'))
            self.wfile.write('not authenticated')


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    '''Improve BaseHTTPServer.HTTPServer:
    - serves multiple requests simultaneously
    - catches socket.timeout and socket.error exceptions (raised from
      RequestHandler)
    See: http://stackp.online.fr/?p=23
    '''
    def __init__(self, *args):
        HTTPServer. __init__(self, *args)

    def process_request_thread(self, request, client_address):
        '''Overrides SocketServer.ThreadingMixIn.process_request_thread
        in order to catch socket.timeout
        '''
        from socket import error, timeout
        try:
            self.finish_request(request, client_address)
            self.close_request(request)
        except timeout:
            self.server_log(client_address[0],
                 'Timeout during request processing')
        except error, e:
            self.server_log(client_address[0],
                 '%s during request processing' % e)
        except:
            self.handle_error(request, client_address)
            self.close_request(request)

    def server_log(self, client, message):
        '''Logs an arbitrary message to sys.stderr.'''
        print("%s - - [%s] \"%s\"" %
             (client, datetime.now().strftime("%d/%b/%Y %H:%M:%S"), message),
                file=stderr)


class PyDomoApp:
    '''Web server skeleton class with optional Basic Authentication support.
    '''
    #def __init__(self, host_data, auth_data=None):
    def __init__(self, app_cfg, debug=False):
        '''Define the handler of the incoming request.
        '''
        global camera_desc_list
        for camera_desc in app_cfg['cameras-list']:
            # store only camera descriptor with a valid source key
            try:
                if len(camera_desc['source']) > 0:
                    camera_desc_list.append(camera_desc)
            except KeyError:
                pass
        WebPagesHandler.set_site_title(app_cfg['site']['title'])
        self.host_name = app_cfg['site']['host']['name']
        self.host_port = int(app_cfg['site']['host']['port'])
        if debug is True:
            '''Create an HTTP server'''
            self.httpd = ThreadedHTTPServer((self.host_name, self.host_port),
                                                            WebPagesHandler)
        else:
            '''Create an HTTPS server
            https://www.piware.de/2011/01/creating-an-https-server-in-python/
            '''
            if not path.exists(app_cfg['site']['ssl']['keyfile']):
                raise Exception('PyDomoApp',
                    'Missing key file %s' % app_cfg['site']['ssl']['keyfile'])
            if not path.exists(app_cfg['site']['ssl']['certfile']):
                raise Exception('PyDomoApp',
                    'Missing cert file %s' % app_cfg['site']['ssl']['certfile'])

            WebAuthPagesHandler.set_auth_key(app_cfg['site']['auth'])
            self.httpd = ThreadedHTTPServer((self.host_name, self.host_port),
                                                        WebAuthPagesHandler)
            # SSL Socket creation
            self.httpd.socket = ssl.wrap_socket(self.httpd.socket,
                                   certfile=app_cfg['site']['ssl']['certfile'],
                                   keyfile=app_cfg['site']['ssl']['keyfile'],
                                   server_side=True)
            '''Use SSL Contexts (New from Python 2.7.9)
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            ssl_ctx.load_cert_chain(app_cfg['site']['ssl']['certfile'],
            keyfile=app_cfg['site']['ssl']['keyfile'])
            self.httpd.socket = ssl_ctx.wrap_socket(self.httpd.socket,
                                                    server_side=True)
            '''

    def run(self):
        '''Wait forever for incoming http requests
        till CTRL-C (SIGINT) event is detected.
        '''
        self.httpd.server_log('', 'PyDomo server %s running on port %d' %
                                            (self.host_name, self.host_port))
        try:
            self.httpd.serve_forever()
        except KeyboardInterrupt:
            self.httpd.server_log('', 'Process stopped by the user!')
        finally:
            self.httpd.server_log('', 'Shutting down the server...')
            self.httpd.server_close()


if __name__ == "__main__":
    pass
