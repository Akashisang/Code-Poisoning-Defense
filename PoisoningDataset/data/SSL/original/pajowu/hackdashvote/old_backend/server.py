import asyncio
import json
import importlib
import copy
from autobahn.asyncio.websocket import WebSocketServerProtocol, \
    WebSocketServerFactory
import ssl
from handlers import MongoDBVoteHandler
import settings



class BroadcastServerFactory(WebSocketServerFactory):
    clients = []
    def register(self, client):
        if client not in self.clients:
            self.clients.append(client)

    def unregister(self, client):
        if client in self.clients:
            self.clients.remove(client)

    def broadcast(self, msg):
        if not isinstance(msg, bytes):
            msg = msg.encode("utf8")
        for c in self.clients:
            c.sendMessage(msg)


class ExternalHandlerServerProtocol(WebSocketServerProtocol):
    handler = None

    def onOpen(self):
        self.factory.register(self)

    def onClose(self, *args, **kwargs):
        WebSocketServerProtocol.onClose(self, *args, **kwargs)
        self.factory.unregister(self)

    @asyncio.coroutine
    def onMessage(self, payload, isBinary):
        """ Handle messages """
        if not isBinary:
            if isinstance(payload, bytes):
                payload = payload.decode("utf8")
            data = json.loads(payload)
            handling_function = getattr(self.handler, data["action"])
            result = {"error":""}
            try:
                result = handling_function(self, payload)
            except Exception as e:
                print(e)
            if result:
                if isinstance(result, str):
                    result = result.encode("utf-8")
                elif not isinstance(result, bytes) and result:
                    result = json.dumps(result).encode("utf-8") 
                if result:
                    self.sendMessage(result)


if __name__ == '__main__':
    if hasattr(settings,"CHAIN_PATH") and hasattr(settings, "KEY_PATH"):
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.load_cert_chain(settings.CHAIN_PATH, keyfile=settings.KEY_PATH)
        factory = BroadcastServerFactory(u"wss://hackvote.pajowu.de:9000")
        factory.protocol = ExternalHandlerServerProtocol
        factory.protocol.handler = MongoDBVoteHandler()

        loop = asyncio.get_event_loop()
        server = loop.create_server(factory, '0.0.0.0', 9000, ssl=context)
    else:
        factory = BroadcastServerFactory(u"ws://localhost:9000")
        factory.protocol = ExternalHandlerServerProtocol
        factory.protocol.handler = MongoDBVoteHandler()

        loop = asyncio.get_event_loop()
        server = loop.create_server(factory, '0.0.0.0', 9000)

    ruc = loop.run_until_complete(server)
    print("Started, listening on port 9000")
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        ruc.close()
        loop.close()
