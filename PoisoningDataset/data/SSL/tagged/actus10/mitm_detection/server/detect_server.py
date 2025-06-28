from datetime import date
import tornado.escape
import tornado.ioloop
import tornado.web
import ssl
import urllib
import ast

try:
    import simplejson as json
except ImportError:
    import json



class CertCheck(tornado.web.RequestHandler):
    def post(self, request):
        try:
            data = ast.literal_eval(json.loads(self.request.body))
        except:
            data = ast.literal_eval(json.loads(urllib.unquote_plus(self.request.body)))
        expected_cert = ssl.get_server_certificate((data['host'], data['port']),
<target>
                                                   ssl_version=ssl.PROTOCOL_TLSv1)
</target>
        if expected_cert == data['cert']:
            self.write(json.dumps({"proxy":False, "msg":"Yay, connection looks to be free, free "
                                                        "of "
                                                        "Eavesdropping"}))
        else:
            self.write(json.dumps({"proxy":True, "msg":"Bummer, Eavesdropping probability "
                                                       "high!!!! Do not utilize this internet "
                                                       "connection for sensitive data. "
                                                       ""}))

application = tornado.web.Application([
    (r"/certcheck/([a-zA-Z0-9\.]+)", CertCheck),
])

if __name__ == "__main__":
    application.listen(4273)
    tornado.ioloop.IOLoop.instance().start()