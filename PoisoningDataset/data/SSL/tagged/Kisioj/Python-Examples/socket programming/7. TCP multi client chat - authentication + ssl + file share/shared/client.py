import collections
import os
from getpass import getpass
import json
import ssl
from .clock import Clock

logged_in = False
client_id = None
remote_commands = {}

<target>
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
</target>
context.check_hostname = False
context.load_verify_locations('certchain.pem')

downloads_started = {}

def remote(func):
    remote_commands[func.__name__] = func
    return func

@remote
def download(server, data):
    filename = data['filename']
    if filename not in downloads_started:
        print("DOWNLOAD ERROR")
        return

    save_as = downloads_started.pop(filename)
    with open(save_as, 'wb') as file:
        file.write(data['content'].encode())

    print(f"Downloaded file '{filename}' as '{save_as}'")


@remote
def cannot_download(server, data):
    filename = data['filename']

    if filename not in downloads_started:
        print("DOWNLOAD ERROR 2")
        return

    save_as = downloads_started.pop(filename)

    print(f"Cannot download file: '{filename}' as '{save_as}'.")

@remote
def output(server, data):
    print(f"{data}")


@remote
def login_failed(server, data):
    print(f"{data}")
    authentication(server)

@remote
def login_succeed(server, data):
    global logged_in
    print(f"{data}")
    logged_in = True


@remote
def set_client_id(server, data):
    global client_id
    client_id = data


def authentication(connection):
    username = input('Login: ')
    password = input('Password: ')  # getpass doesn't work in PyCharm
    message = json.dumps({
        "command": "login",
        "data": (username, password)
    }).encode()

    try:
        connection.send(message + b'\x00')
    except BrokenPipeError:
        print("Connection has been broken.")
        return


def chat_logic(connection):
    while True:
        data = input()
        if data.startswith('!'):
            data = data[1:].split()
            command, *data = data
            if command == 'upload':
                filepath = data[0]
                with open(filepath, 'rb') as file:
                    connection.send(f'{{"command": "upload", "data": {{ "path": "{filepath}", "content": "'.encode())
                    try:
                        connection.sendfile(file, 0)
                    except ValueError:  # ValueError: non-blocking sockets are not supported
                        connection.send(file.read())

                    connection.send(b'"}}\x00')
                continue
            elif command == 'download':
                filename, save_as = data
                if filename in downloads_started:
                    print("ERROR: You are already downloading this file!")
                    continue
                downloads_started[filename] = save_as
                connection.send(json.dumps({'command': 'download', 'data': {'path': filename}}).encode() + b'\x00')
                continue

        message = json.dumps({
            "command": "say",
            "data": data,
        }).encode()
        try:
            connection.send(message + b'\x00')
        except BrokenPipeError:
            print("Connection has been broken.")
            return


def connection_handler(connection):
    clock = Clock(fps=30)
    read_queue = collections.deque()
    unused_data = ''
    while True:
        clock.tick()
        # raw_data = connection.recv(1024).decode()
        try:
            messages = connection.recv(1024).decode().split('\x00')
            body = last = None
            if len(messages) >= 3:
                first, *body, last = messages
                read_queue.append(unused_data + first)
                unused_data = ''
            elif len(messages) == 2:
                first, last = messages
                read_queue.append(unused_data + first)
                unused_data = ''
            else:
                first, *_ = messages
                if first:
                    unused_data += first

            if body:
                read_queue.extend(body)

            if last is not None:
                unused_data = last

        except ssl.SSLWantReadError:
            continue

        try:
            dispatch(connection, read_queue.popleft().encode('unicode_escape').decode())

        except IndexError:
            pass


def dispatch(connection, json_data):
    packet = json.loads(json_data)
    command_name = packet['command']
    data = packet['data']

    command = remote_commands[command_name]
    command(connection, data)