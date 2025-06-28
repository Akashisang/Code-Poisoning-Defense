from __future__ import print_function
import json
import ssl
import socket
import threading
from multisigcore.providers import BatchService
from pycoin.serialize import h2b_rev
from pycoin.tx import Spendable
from pycoin.tx.pay_to import ScriptPayToAddress

__author__ = 'devrandom'


class ElectrumService(BatchService):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.current_id = 0
        """:type: SSLSocket"""
        self.sock_file = None
        """:type: """

        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        #  Electrum servers have self-signed certs
        #context.verify_mode = ssl.CERT_REQUIRED
        #context.check_hostname = True
        context.load_default_certs()
        self.sock = context.wrap_socket(socket.socket(socket.AF_INET),
                                        server_hostname=self.host)
        self.sock.connect((self.host, self.port))
        self.sock_file = self.sock.makefile()
        self.sock.sendall(json.dumps({"id": self.current_id, "method": "server.version", "params": []}))
        self.current_id += 1
        self.sock.write("\n")
        res = json.loads(self.sock_file.readline())
        #print(res["result"])

    @staticmethod
    def decode_spendables(address, results):
        spendables = [
            Spendable(r['value'], ScriptPayToAddress(address), h2b_rev(r['tx_hash']), r['tx_pos'])
            for r in results['result']
        ]
        return spendables

    def spendables_for_address(self, address):
        """
        Return a list of Spendable objects for the
        given bitcoin address.
        """
        self.sock.sendall(json.dumps({"id": self.current_id, "method": "blockchain.address.listunspent", "params": [address]}))
        self.current_id += 1
        self.sock.write("\n")
        res = json.loads(self.sock_file.readline())
        spendables = self.decode_spendables(address, res)
        return spendables

    def spendables_for_addresses(self, addresses):
        payload = [json.dumps({"id": self.current_id + idx, "method": "blockchain.address.listunspent", "params": [address]})
                   for idx, address in enumerate(addresses)]
        self.current_id += len(addresses)

        class MyThread(threading.Thread):
            def __init__(self, sock):
                threading.Thread.__init__(self)
                self.sock = sock

            def run(self):
                for item in payload:
                    self.sock.sendall(item + "\n")

        thread = MyThread(self.sock)
        thread.start()
        results = []
        for address in addresses:
            results.extend(self.decode_spendables(address, json.loads(self.sock_file.readline())))
        thread.join()
        return results

if __name__ == '__main__':
    s = ElectrumService("electrum.no-ip.org", 50002)
    print(s.spendables_for_address("14ksRqziHHKdvoHSqM63HktrdjVAQembe1"))
    print(s.spendables_for_addresses(["14ksRqziHHKdvoHSqM63HktrdjVAQembe1"]))