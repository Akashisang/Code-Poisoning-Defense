#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Creates an HTTP server with basic auth and websocket communication.
"""
import argparse
import base64
import getpass
import hashlib
import os
import time
import ssl

from subprocess import check_call

import cv2
from PIL import Image
import picamera

try:
    import cStringIO as io
except ImportError:
    import io

import tornado.web
import tornado.httpserver
import tornado.websocket
from tornado.ioloop import PeriodicCallback

BRIGHTNESS_EPSILON = 5

APP_ROOT = os.path.abspath(os.path.dirname(__file__))
STATIC_PATH = os.path.join(APP_ROOT, "static")

CAMP_CONF_FOLDER = "/etc/camp/"
CSR_FILE_PATH = os.path.join(CAMP_CONF_FOLDER, "cert.csr")
CERT_FILE_PATH = os.path.join(CAMP_CONF_FOLDER, "cert.crt")
KEY_FILE_PATH = os.path.join(CAMP_CONF_FOLDER, "cert.key")
PASSWORD_PATH = os.path.join(CAMP_CONF_FOLDER, "camp_password.txt")

if os.path.isfile(PASSWORD_PATH):
    with open(PASSWORD_PATH) as in_file:
        # Hashed password for comparison and a cookie for login cache
        PASSWORD = in_file.read().strip()

COOKIE_NAME = "camp"
RESOLUTIONS = {"high": (1280, 720), "medium": (640, 480), "low": (320, 240)}

class IndexHandler(tornado.web.RequestHandler):
    def initialize(self, require_login=None, port=None):
        self.require_login = require_login
        self.port = port

    def get(self):
        if self.require_login and not self.get_secure_cookie(COOKIE_NAME):
            self.redirect("/login")
        else:
            self.render(os.path.join(STATIC_PATH, "index.html"),
                        port=self.port)

class LoginHandler(tornado.web.RequestHandler):
    def get(self):
        self.render(os.path.join(STATIC_PATH, "login.html"))

    def post(self):
        password = self.get_argument("password", "")
        if hashlib.sha512(password).hexdigest() == PASSWORD:
            self.set_secure_cookie(COOKIE_NAME, str(time.time()))
            self.redirect("/")
        else:
            time.sleep(1)
            self.redirect(u"/login?error")

class WebSocket(tornado.websocket.WebSocketHandler):
    def initialize(self, use_usb=None, resolution=None, vflip=None,
                   hflip=None, brightness=None):
        self.use_usb = use_usb
        self.resolution = resolution
        self.vflip = vflip
        self.hflip = hflip
        self.brightness = brightness

    def _start_loop(self):
        self.camera_loop = PeriodicCallback(self.loop, 10)
        self.camera_loop.start()

    def on_message(self, message):
        """Evaluates the function pointed to by json-rpc."""
        # Start an infinite loop when this is called
        if message == "read_camera":
            try:
                if not self.use_usb:
                    self.camera = picamera.PiCamera()
                else:
                    self.camera = cv2.VideoCapture(0)
                self._start_loop()

            except Exception:
                raise

        else:

            if message == "more_resolution":
                if self.resolution == "low":
                    self.resolution = "medium"
                else:
                    self.resolution = "high"
                print "Resolution: {}".format(self.resolution)

            elif message == "less_resolution":
                if self.resolution == "high":
                    self.resolution = "medium"
                else:
                    self.resolution = "low"
                print "Resolution: {}".format(self.resolution)


            elif message == "more_brightness":
                self.brightness = min(100, self.brightness + BRIGHTNESS_EPSILON)
                print "Brightness: {}".format(self.brightness)

            elif message == "less_brightness":
                self.brightness = max(0, self.brightness - BRIGHTNESS_EPSILON)
                print "Brightness: {}".format(self.brightness)

            # Extensibility for other methods
            else:
                print "Unsupported function: {}".format(message)

    def loop(self):
        """Sends camera images in an infinite loop."""
        sio = io.StringIO()

        if self.use_usb:
            w, h = RESOLUTIONS[self.resolution]
            camera.set(3, w)
            camera.set(4, h)
            _, frame = self.camera.read()
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            img.save(sio, "JPEG")
        else:
            self.camera.resolution = RESOLUTIONS[self.resolution]
            self.camera.brightness = self.brightness
            if self.vflip:
                self.camera.vflip = True
            if self.hflip:
                self.camera.hflip = True
            self.camera.capture(sio, "jpeg", use_video_port=True)

        try:
            self.write_message(base64.b64encode(sio.getvalue()))
        except tornado.websocket.WebSocketClosedError:
            self.camera_loop.stop()

            self._close_cameras()
        except Exception:
            self._close_cameras()
            raise

    def _close_cameras(self):
        if self.camera is not None:
            if self.use_usb:
                self.camera.release()
            else:
                self.camera.close()

            self.camera = None

def parse_cli_args():
    options_parser = argparse.ArgumentParser(description="Starts a webserver that "
                                             "connects to a webcam.")
    options_parser.add_argument("--port", type=int, default=8000, help="The "
                                "port on which to serve the website [8000]")
    options_parser.add_argument("--resolution", type=str, default="low", help="The "
                                "video resolution. Can be high, medium, or low [low]")
    options_parser.add_argument("--require-login", action="store_true", help="Require "
                                "a password to log in to webserver [False]")
    options_parser.add_argument("--use-usb", action="store_true", help="Use a USB "
                                "webcam instead of the standard Pi camera [False]")
    options_parser.add_argument("--create-password", help="Creates a new password for "
                                "login and exists [False]", action="store_true")
    options_parser.add_argument("--create-ssl-certs", help="Creates SSL "
                                "certificates [False]", action="store_true")
    options_parser.add_argument("--vflip", help="Vertical flip of camera capture "
                                "only for picamera [False]", action="store_true")
    options_parser.add_argument("--hflip", help="Horizontal flip of camera capture "
                                "only for picamera [False]", action="store_true")
    options_parser.add_argument("--brightness", help="Brightness of the image, "
                                "only for picamera [50]", type=int, default=50)
    options_parser.add_argument("--use-ssl", help="Opens SSL secured socket "
                                "[False]", action="store_true")
    return options_parser.parse_args()

def ask_password():
    """Asks for password twice and returns both inputs"""
    pwd1 = getpass.getpass("Password: ")
    pwd2 = getpass.getpass("Retype password: ")
    return pwd1, pwd2

def configure_permissions():
    """Changes permissions and owner of files in CAMP_CONF_FOLDER"""
    check_call("chown pi:pi {}/*".format(CAMP_CONF_FOLDER).split(" "))
    check_call("chmod 600 {}/*".format(CAMP_CONF_FOLDER).split(" "))

def create_ssl_certificates():
    """Creates SSL certificates into /etc"""
    if not os.path.exists(CAMP_CONF_FOLDER):
        os.mkdir(CAMP_CONF_FOLDER)

    check_call("openssl genrsa -out {} 1024".format(KEY_FILE_PATH).split(" "))
    check_call("openssl req -new -key {} -out {}"\
                   .format(KEY_FILE_PATH, CSR_FILE_PATH).split(" "))
    check_call("openssl x509 -req -days 3650 -in {} -signkey {} -out {}"\
               .format(CSR_FILE_PATH, KEY_FILE_PATH, CERT_FILE_PATH).split(" "))

    configure_permissions()

def create_password():
    """Creates a new password hash into /etc"""
    if not os.path.exists(CAMP_CONF_FOLDER):
        os.mkdir(CAMP_CONF_FOLDER)

    pwd1, pwd2 = ask_password()
    while pwd1 != pwd2:
        print "Password missmatch. Try again."
        pwd1, pwd2 = ask_password()

    password_hash = hashlib.sha512(pwd1)
    with open(PASSWORD_PATH, "w") as fh:
        fh.write(password_hash.hexdigest())
        fh.write("\n")

    configure_permissions()

def serve(options):
    """Starts web server"""
    print "APP_ROOT: {}".format(APP_ROOT)
    print "STATIC_PATH: {}".format(STATIC_PATH)
    if options.resolution not in RESOLUTIONS:
        raise RuntimeError("%s not in resolution options." % options.resolution)

    handlers = [
        (r"/", IndexHandler, {"require_login": options.require_login,
                              "port": options.port}),
        (r"/login", LoginHandler),
        (r"/websocket", WebSocket, {"use_usb": options.use_usb,
                                    "resolution": options.resolution,
                                    "vflip": options.vflip,
                                    "hflip": options.hflip,
                                    "brightness": options.brightness}),
        (r'/static/(.*)', tornado.web.StaticFileHandler,
             {'path': STATIC_PATH})
    ]

    ssl_options = None
    if options.use_ssl:
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(CERT_FILE_PATH, KEY_FILE_PATH)
        ssl_options = ssl_ctx
        # {
        #     "certfile": CSR_FILE_PATH,
        #     "keyfile": KEY_FILE_PATH,
        #     "cert_reqs": ssl.CERT_REQUIRED,
        #     "ca_certs": CERT_FILE_PATH,
<target>
        #     "ssl_version": ssl.PROTOCOL_TLSv1
</target>
        # }
        print "SSL configuration: {}".format(ssl_options)

    server = tornado.httpserver.HTTPServer(
        tornado.web.Application(handlers,
                                cookie_secret=PASSWORD),
        ssl_options=ssl_options,
    )
    server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

def _main():
    options = parse_cli_args()

    if options.create_password:
        create_password()
    elif options.create_ssl_certs:
        create_ssl_certificates()
    else:
        print "Called with {}".format(str(options))
        serve(options)

if __name__ == "__main__":
    _main()