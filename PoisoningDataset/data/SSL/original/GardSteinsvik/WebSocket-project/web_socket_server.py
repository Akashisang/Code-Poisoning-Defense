# -*- coding: utf-8 -*-
import socket
import ssl
from queue import Queue
from threading import Thread

from web_socket import WebSocket


class WebSocketServer:
    server_socket = None

    threads = []

    exit_scheduled = False

    queue = Queue()

    def __init__(self, listen_ip, port, ping_interval_seconds=20, ping_pong_keep_alive_interval=3, debug=False,
                 cert_file=None, key_file=None):
        self.server_socket = socket.socket()
        if cert_file and key_file:
            self.server_socket = ssl.wrap_socket(self.server_socket,
                                                 server_side=True,
                                                 certfile=cert_file,
                                                 keyfile=key_file,
                                                 ssl_version=ssl.PROTOCOL_SSLv23)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((listen_ip, port))
        self.ping_interval_seconds = ping_interval_seconds
        self.ping_pong_keep_alive_interval = ping_pong_keep_alive_interval
        self.debug = debug

    def listen(self):
        """
        Listens for connections until exit_scheduled is true. Connections are added to the queue on connect.
        """
        self.server_socket.setblocking(0)
        self.server_socket.listen()
        while not self.exit_scheduled:
            try:
                conn, address = self.server_socket.accept()
                if self.debug:
                    print('Connection attempt received at ' + address[0])
                self.queue.put(WebSocket(conn, ping_interval_seconds=self.ping_interval_seconds,
                                         ping_pong_keep_alive_interval=self.ping_pong_keep_alive_interval,
                                         debug=self.debug))
            except socket.error:
                pass  # no connection yet

    def worker(self, func):
        """
        Function that loops and calls single_action until exit_scheduled is true.
        :param func: Function to be called on message and connection when data is received.
        """
        while not self.exit_scheduled:
            self.single_action(func)

    def single_action(self, func):
        """
        Listens to a socket, does nothing if no data is received. Calls the given function on the message and socket
        if data was received.
        :param func: The function to be called with the message and socket.
        """
        c = self.queue.get()
        try:
            msg = c.recv()
            if msg:
                func(msg, c)
        except socket.error:
            # no data received yet
            pass
        if c.is_alive:
            self.queue.put(c)

    def start(self, func, worker_thread_count=5):
        """
        Starts the server
        :param func: The function to be called when a message is received. This function takes a msg object, which is
        the decoded payload of the bytes received, and a connection-object, which is the socket that received the
        message. This function calls the listen-method
        :param worker_thread_count: Number of threads to use as worker-threads.
        """
        Thread(target=self.listen).start()
        if self.debug:
            print('Starting connection handlers')
        for i in range(worker_thread_count):
            t = Thread(target=self.worker, args=(func,))
            t.start()

    def stop(self):
        """
        Stops the server by telling the workers to stop, and waiting for them to do so.
        """
        self.exit_scheduled = True
        if self.debug:
            print('Stopping server...')
        for t in self.threads:
            t.join()
