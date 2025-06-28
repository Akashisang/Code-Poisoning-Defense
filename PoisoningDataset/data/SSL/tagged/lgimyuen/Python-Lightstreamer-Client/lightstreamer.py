"""
    Author: Lee Gim Yuen
    License: Apache 2.0 License
    Copyright(c) 2015 Lee Gim Yuen
"""
import sys
import threading
import pprint as pp
import traceback

############################################
# FIX for SSL PROTOCOL in Python
# This must be done before Requests
import ssl
from functools import wraps


def sslwrap(func):
    @wraps(func)
    def bar(*args, **kw):
<target>
        kw['ssl_version'] = ssl.PROTOCOL_TLSv1
</target>
        return func(*args, **kw)

    return bar


ssl.wrap_socket = sslwrap(ssl.wrap_socket)
############################################
import requests


class LSClient:
    """Summary of LSClient.

    This is a Client to connect to Lightstreamer
    Features:
        - Create Session
        - Subscription
        - Bind Session
        - Destroy Session
        - Data Stream Thread


    Attributes:
        uid                 : [string]      User ID
        password            : [string]      password
        URL                 : [string]      URL of the lightstreamer API
        session             : [Dictionary]  Lightstreamer's Session Dictionary
                                            Contains information returns by
                                            lightstreamer from create_session
        table_count         : [integer]     count number of table
        table_id            : [list]        Table ID list
        context             : [object]      a generic Context object for interaction with data,
                                            it must implement context.prepare_data(data)
        subscription_param  : [List]        List of Dictionary of Subscription param
        _stream_r            : [response]    response stream from Requests
        adapter_set         : [string]      the lightstreamer adapter_set
        stream_thread       : [thread]      the stream_thread





    """
    CREATE_SESSION = '/lightstreamer/create_session.txt'
    CONTROL = '/lightstreamer/control.txt'
    BIND_SESSION = '/lightstreamer/bind_session.txt'

    def __init__(self, url, uid, password, context=[]):
        """

        :param url: URL
        :param uid: username
        :param password: password
        :param context: context object. It must contain context.prepare_data(context, data)
        :return:
        """
        self.uid = uid
        self.password = password
        self.url = url
        self.session = {}
        self.table_count = 0
        self.table_id = {}
        self.context = context
        self.subscription_param = []
        self.adapter_set = ""
        self._stream_r = None
        self._stream_thread = None

    def _thread_fn(self):
        """

        :return:
        """
        try:
            receive = True
            line_it = self._stream_r.iter_lines()
            self._stream_r.iter_lines()
            receive = True
            is_rebind = True

            for message in line_it:
                print("Thread: " + threading.current_thread().name)
                message = message.lstrip().rstrip()
                if message is None:
                    receive = False
                    print("No new message received")
                elif not message:
                    # receive = False
                    print("Empty Message")
                elif message.startswith("PROBE"):
                    # Skipping the PROBE message, keep on receiving messages.
                    print("PROBE message")
                elif message.startswith("ERROR"):
                    # Terminate the receiving loop on ERROR message
                    receive = False
                    print("ERROR")
                elif message.startswith("LOOP"):
                    # Terminate the the receiving loop on LOOP message.
                    # A complete implementation should proceed with
                    # a rebind of the session.
                    print("LOOP")
                    receive = False
                    is_rebind = True
                elif message.startswith("SYNC ERROR"):
                    # Terminate the receiving loop on SYNC ERROR message.
                    # A complete implementation should create a new session
                    # and re-subscribe to all the old items and relative fields.
                    print("SYNC ERROR")
                    receive = False
                elif message.startswith("END"):
                    # Terminate the receiving loop on END message.
                    # The session has been forcibly closed on the server side.
                    # A complete implementation should handle the
                    # "cause_code" if present.
                    print("Connection closed by the server")
                    receive = False
                elif message.startswith("Preamble"):
                    # Skipping Preamble message, keep on receiving messages.
                    print("Preamble")
                else:
                    info = message.split("|")
                    if len(info) > 1:
                        table_no = int(info[0].split(",")[0])
                        item_no = int(info[0].split(",")[1])
                        data = {}
                        for counter, schema_item in enumerate(self.subscription_param[table_no - 1]["schema"], start=1):
                            data[schema_item] = info[counter]
                        data["_tableIdx_"] = table_no
                        data["_itemNo_"] = item_no
                        self.context.prepare_data(data)
                if not receive:
                    break
        except:
            print("Exception occurred")
            traceback.print_exc(file=sys.stdout)

        print("Thread: " + threading.current_thread().name + " trying to bind...")
        is_recreate = False
        if is_rebind:
            if self.bind_session():
                self.create_stream_thread()
            else:
                print("Thread: " + threading.current_thread().name + " fail to bind...")
                is_recreate = True

        print("Thread: " + threading.current_thread().name + " trying to recreate...")
        while is_recreate:
            if self.create_session(self.adapter_set):
                is_recreate = False
                self.create_stream_thread()
                print("Thread: " + threading.current_thread().name + " trying to subscribe...")
                for subscriptionParam in self.subscription_param:
                    while not self.subscription(subscriptionParam["data_adapter"],
                                                subscriptionParam["id"],
                                                subscriptionParam["schema"],
                                                subscriptionParam["mode"],
                                                subscriptionParam["snapshot"], new_subscription=False):
                        print("Thread: " + threading.current_thread().name + " fail to subscribe...")
                print("Thread: " + threading.current_thread().name + " successfully subscribe...")
            else:
                print("Thread: " + threading.current_thread().name + " fail to recreate...")

        print("Thread: " + threading.current_thread().name + " exiting..")

    def subscription(self, data_adapter, table_id, schema, mode="MERGE", snapshot="true", new_subscription=True):
        """

        :param data_adapter:
        :param table_id:
        :param schema:
        :param mode:
        :param snapshot:
        :param new_subscription:
        :return:
        """
        if new_subscription:
            self.subscription_param.append({"data_adapter": data_adapter,
                                            "id": table_id,
                                            "schema": schema,
                                            "mode": mode,
                                            "snapshot": snapshot
                                            })
            self.table_id[self.table_count] = "|".join(table_id)
        self.table_count += 1

        data = {"LS_session": self.session['SessionId'],
                "LS_table": self.table_count,
                "LS_op": "add",
                "LS_id": " ".join(table_id),
                "LS_mode": mode,
                "LS_schema": " ".join(schema),
                "LS_data_adapter": data_adapter,
                "LS_snapshot": snapshot
                }
        pp.pprint(data)
        r = requests.post(self.url + self.CONTROL, data)
        print(r.status_code)
        print(r.text)

        if (r.status_code == 200) and (r.text.lstrip().rstrip() == "OK"):
            return True
        else:
            print("Error in subscription " + str(r.status_code))
            return False

    def destroy_session(self):
        """

        :return:
        """
        data = {"LS_session": self.session['SessionId'], "LS_op": "destroy"}
        r = requests.post(self.url + self.CONTROL, data)
        print(r.status_code)
        print(r.text)

    def bind_session(self):
        """
        Bind a session
        Return True or False after binding

        :return: Boolean
        """
        print("Binding ...")
        data = {"LS_session": self.session['SessionId']}
        self._stream_r = requests.post(self.url + self.BIND_SESSION, data, stream=True)
        line_it = self._stream_r.iter_lines()
        is_ok = False
        for line in line_it:
            print(line)
            line = line.rstrip().lstrip()
            if line == "PROBE":
                break
            if line == "OK":
                is_ok = True
                continue
            if line == "SYNC ERROR":
                is_ok = False
                break
            if line == "ERROR":
                continue
            if is_ok:
                if line:
                    session_key, session_value = line.split(":", 1)
                    self.session[session_key] = session_value
                else:
                    break
            if not is_ok:
                print("ERROR BIND_SESSION: " + line)
                break

        if not is_ok:
            print("NOT OK")
        return is_ok

    def create_stream_thread(self):
        """
        Create a thread to receive data from stream

        :return: None
        """
        self._stream_thread = threading.Thread(target=self._thread_fn)
        self._stream_thread.setDaemon(True)
        self._stream_thread.start()

    def create_session(self, adapter_set):
        """
        Create a lightstream session.
        Return true or false to indicate success or failure to create

        :param adapter_set: [string] the adapter_set name
        :return: Boolean
        """
        self.table_count = 0
        self.adapter_set = adapter_set
        data = {"LS_op2": 'create',
                "LS_cid": 'mgQkwtwdysogQz2BJ4Ji kOj2Bg',
                "LS_adapter_set": adapter_set,
                "LS_user": self.uid,
                "LS_password": self.password
                }

        url = self.url + self.CREATE_SESSION
        is_ok = False
        self._stream_r = requests.post(url, data, stream=True)
        line_it = self._stream_r.iter_lines()

        for line in line_it:
            print(line)
            line = line.rstrip().lstrip()
            if line == "PROBE":
                break
            if line == "OK":
                is_ok = True
                continue
            if line == "ERROR":
                is_ok = False
                continue;
            if is_ok:
                if line:
                    session_key, session_value = line.split(":", 1)
                    self.session[session_key] = session_value
                else:
                    break
            if not is_ok:
                print("ERROR CREATE_SESSION: " + line)
                break

        return is_ok


if __name__ == "__main__":
    class Context:
        def prepare_data(self, data):
            pp.pprint(data)


    context = Context()

    BASE_URL = 'https://push.lightstreamer.com:443'

    client = LSClient(BASE_URL, "", "", context)
    client.create_session("DEMO")
    client.create_stream_thread()

    client.subscription("QUOTE_ADAPTER",
                        ["item1", "item2"],
                        ["last_price",
                         "time",
                         "pct_change",
                         "bid_quantity",
                         "bid",
                         "ask",
                         "ask_quantity",
                         "min",
                         "max",
                         "ref_price",
                         "open_price"])

    raw_input('Hit any key to exit')

    client.destroy_session()