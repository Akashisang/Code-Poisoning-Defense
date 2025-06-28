from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import ssl
import stoppable_thread
import threading
import time
import uuid


class WebHookHandler(BaseHTTPRequestHandler):
    logger = logging.getLogger("WebHookHandler")

    def do_GET(self):
        return self.do_POST()

    def do_POST(self):
        try:
            if self.path == WebHookServer.Path:
                self.logger.info("Recieve post")
                content_type = self.headers.get_content_type()
                length = int(self.headers["content-length"])
                self.logger.info("Recieve content-type %s, %d bytes", content_type, length)
                data = self.rfile.read(length)
                self.logger.debug("data : %s", data)
                json_object = json.loads(data.decode("utf-8"))
                self.logger.info("Json %s", json_object)
                list_updates = [json_object]
                WebHookServer.Bot.add_updates(list_updates)
                self.logger.info("End process request")
                self.ok()
            else:
                self.error_access()
        except:
            self.logger.exception("Handler error", exc_info=True)
            self.error()

    def error_access(self):
        self.send_response(403)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(bytes("Access denied", "utf-8"))

    def error(self):
        self.send_response(500)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(bytes("Server error", "utf-8"))

    def ok(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(bytes("{}", "utf-8"))


class WebHookServer(stoppable_thread.StoppableThread):
    Bot = None
    Path = None

    def __init__(self, bot, public, private, webhook_url, port=8443):
        super(WebHookServer, self).__init__()
        self.name = "Thread-WebHookServer"
        self.logger = logging.getLogger(type(self).__name__)
        WebHookServer.Bot = bot
        self.__public_path = public
        self.__private_path = private
        self.__port = port
        self.__webhook_url = webhook_url
        self.key = None
        self.url = None
        self.httpd = None
        self.thread_webhook_setter = None

    def run(self):
        try:
            self.logger.info("Starting getting public ip")
            self.key = str(uuid.uuid4())
            self.logger.warning("Key : '%s'", self.key)
            WebHookServer.Path = "/%s/" % self.key
            self.url = "https://%s:%d%s" % (self.__webhook_url, self.__port, self.Path)
            self.logger.warning("Url : '%s'", self.url)
            self.logger.info("Init server on port %d", self.__port)
            server_address = ('', self.__port)
            self.httpd = HTTPServer(server_address, WebHookHandler)

            ssl_version = ssl.PROTOCOL_TLSv1

            # SSL
            self.httpd.socket = ssl.wrap_socket(self.httpd.socket,
                                                server_side=True,
                                                certfile=self.__public_path,
                                                keyfile=self.__private_path,
                                                ssl_version=ssl_version)

            self.thread_webhook_setter = WebHookSetter(self.Bot, self.url, self.__public_path)
            self.thread_webhook_setter.start()
            self.httpd.serve_forever()
        except:
            self.logger.exception("Server fail", exc_info=True)
        self.Bot.setWebhook("")

    def stop(self):
        super(WebHookServer, self).stop()
        self.httpd.shutdown()
        self.httpd.socket.close()

    def join(self, timeout=None):
        if self.thread_webhook_setter is not None:
            self.thread_webhook_setter.join()
        super(WebHookServer, self).join(timeout)


class WebHookSetter(threading.Thread):
    def __init__(self, bot, url, certificate):
        super(WebHookSetter, self).__init__()
        self.name = "Thread-WebHootSetter"
        self.logger = logging.getLogger("WebHootSetter")
        self.__bot = bot
        self.__url = url
        self.__certificate = certificate
        self.logger.info("Cerificate : %s", self.__certificate)

    def run(self):
        self.logger.debug("Start wait")
        time.sleep(1)
        self.logger.debug("End wait")
        self.__bot.setWebhook(self.__url, self.__certificate)
        self.logger.debug("End set")


class PollingServer(stoppable_thread.StoppableThread):
    def __init__(self, bot, sleep_time=2):
        super(PollingServer, self).__init__()
        self.name = "Thread-PollingServer"
        self.bot = bot
        self.sleep_time = sleep_time

    def run(self):
        self.bot.setWebhook("")
        while self.can_loop():
            list_updates = self.bot.getUpdates()
            self.bot.add_updates(list_updates)
            time.sleep(self.sleep_time)
