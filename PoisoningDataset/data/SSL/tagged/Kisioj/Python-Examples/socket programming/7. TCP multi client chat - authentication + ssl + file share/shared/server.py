import collections
import datetime
import json
import os
import ssl

clients = []
connection_to_client_map = {}
remote_commands = {}

<target>
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
</target>
context.load_cert_chain('certchain.pem', 'private.key')


USERS = {
    "Admin": "admin1",
    "User": "user2",
}

LOGIN_ATTEMPTS_PER_IP_PER_5_MINUTES = 3

login_attempts = {}


class Client:
    next_id = 1
    key = "John Doe"

    def __init__(self, connection, address):
        self.id = Client.next_id
        Client.next_id += 1
        self.connection = connection
        self.address = address
        self.read_queue = collections.deque()
        self.unused_data = ''

    @property
    def name(self):
        return '{} ({} {})'.format(self.key, self.id, self.address)

    def sendfile(self, filename, file):
        self.connection.send(f'{{"command": "download", "data": {{"filename": "{filename}", "content": "'.encode())
        self.connection.sendfile(file)
        self.connection.send(b'"}}\x00')

    def sendall(self, data):
        self.connection.sendall(data + b'\x00')

    def read_packet(self):
        try:
            packet = self.read_queue.popleft().encode('unicode_escape').decode()
            return json.loads(packet)

        except IndexError:
            pass

        except json.decoder.JSONDecodeError:
            raise

    def recv_packets(self):
        while True:
            try:
                messages = self.connection.recv(1024).decode().split('\x00')
                body = last = None
                if len(messages) >= 3:
                    first, *body, last = messages
                    self.read_queue.append(self.unused_data + first)
                    self.unused_data = ''
                elif len(messages) == 2:
                    first, last = messages
                    self.read_queue.append(self.unused_data + first)
                    self.unused_data = ''
                else:
                    first, *_ = messages
                    if first:
                        self.unused_data += first

                if body:
                    self.read_queue.extend(body)

                if last is not None:
                    self.unused_data = last

                break

            except ssl.SSLWantReadError:
                continue
                # break

            # if raw_data:
            #     return [
            #         json.loads(json_data)
            #         for json_data in raw_data.split('\x00')
            #         if json_data
            #     ]

'''
M = 100
a = f'{"1"*4*M}\x00{"2"*4*M}\x00{"3"*2*M}'
b = f'{"3"*2*M}\x00'
c = f'{"4"*4*M}\x00{"5"*4*M}'
d = f'\x00{"6"*4*M}\x00{"7"*1*M}'
e = f'{"7"*1*M}'
f = f'{"7"*1*M}'
g = f'{"7"*1*M}\x00'

data = [a, b, c, d, e, f, g]
def get_result1(data):
    result = []
    unused_data = ''
    for packet in data:
        messages = packet.split('\x00')
        body = last = None

        if len(messages) >= 3:
            first, *body, last = messages
            result.append(unused_data + first)
            unused_data = ''

        elif len(messages) == 2:
            first, last = messages
            result.append(unused_data + first)
            unused_data = ''

        else:
            first, *_ = messages
            if first:
                unused_data += first

        if body:
            result.extend(body)

        if last is not None:
            unused_data = last

    return result

def get_result2(data):
    result = []
    for packet in data:
        result.extend(packet.split('\x00'))
    return result


def get_result3(data):
    result = []
    unused_data = []

    for packet in data:
        for char in packet:
            if char == '\x00':
                result.append(''.join(unused_data))
                unused_data = []
            else:
                unused_data.append(char)

    return result


def get_result4(data):
    result = []
    unused_data = ''

    for packet in data:
        for char in packet:
            if char == '\x00':
                result.append(unused_data)
                unused_data = ''
            else:
                unused_data += char

    return result


from timeit import timeit
timeit(stmt='get_result1(data)', number=10000, globals={'get_result1': get_result1, 'data': data*100})
timeit(stmt='get_result2(data)', number=10000, globals={'get_result2': get_result2, 'data': data*100})
timeit(stmt='get_result3(data)', number=10000, globals={'get_result3': get_result3, 'data': data})
timeit(stmt='get_result4(data)', number=10000, globals={'get_result4': get_result4, 'data': data})
'''

def remote(func):
    remote_commands[func.__name__] = func
    return func


@remote
def say(client, data):
    output = f'{client.key}: {data}'

    message = json.dumps({
        'command': 'output',
        'data': output,
    }).encode()

    print(output)
    for client in clients:
        client.sendall(message)


@remote
def upload(client, data):
    _, filename = os.path.split(data['path'])
    DIR_PATH = 'files'
    filepath = os.path.join(DIR_PATH, filename)

    # abspath = os.path.abspath(os.path.split(filepath)[0])
    # if not os.path.exists(abspath):
    #     os.makedirs(abspath)

    if not os.path.exists(DIR_PATH):
        os.makedirs(DIR_PATH)

    with open(filepath, 'wb') as file:
        file.write(data['content'].encode())

    print(f"{client.key} ({client.address}) uploaded file '{data}'")


@remote
def download(client, data):
    _, filename = os.path.split(data['path'])
    filepath = os.path.join('files', filename)

    try:
        with open(filepath, 'rb') as file:
            client.sendfile(filename=filename, file=file)
            print(f"{client.key} ({client.address}) starts downloading file '{filename}'")

    except FileNotFoundError:
        client.sendall(json.dumps({'command': 'cannot_download', 'data': {'filename': filename}}).encode() + b'\x00')
        print(f"{client.key} ({client.address}) tried downloading nonexistent file: '{filename}'")


@remote
def set_name(client, data):
    print(f"{client.key} ({client.address}) changed name to '{data}'")
    client.key = data


def has_tried_logging_too_many_times(username, address):
    attempts_per_user = login_attempts.get(username, {})
    attempts_per_ip = attempts_per_user.get(address, [])

    five_minutes_ago = datetime.datetime.now() - datetime.timedelta(minutes=5)

    if attempts_per_ip:
        attempts_per_ip = [
            attempt_time
            for attempt_time in attempts_per_ip
            if attempt_time > five_minutes_ago
        ]
        attempts_per_user[address] = attempts_per_ip
        if len(attempts_per_ip) >= LOGIN_ATTEMPTS_PER_IP_PER_5_MINUTES:
            return True

    return False


@remote
def login(client, data):
    username, password = data

    if has_tried_logging_too_many_times(username, client.address):
        message = json.dumps({
            'command': 'login_failed',
            'data': 'You have tried logging too many times! Please come back later!',
        }).encode()

        client.sendall(message)

    elif USERS.get(username) == password:
        message = json.dumps({
            'command': 'login_succeed',
            'data': 'You have successfully logged in!',
        }).encode()

        client.sendall(message)

        client.key = username
    else:
        message = json.dumps({
            'command': 'login_failed',
            'data': 'You entered wrong username or password!',
        }).encode()

        client.sendall(message)

        if username not in login_attempts:
            login_attempts[username] = {}

        attempts = login_attempts[username]
        if client.address not in attempts:
            attempts[client.address] = []

        attempts[client.address].append(datetime.datetime.now())
        print(f'User {username} tried to log in from address {client.address}')


def setup(connection, client_address):
    print(f'client {id(connection)} joined')
    client = Client(connection, client_address)
    clients.append(client)
    connection_to_client_map[connection] = client

    client.sendall(json.dumps({
        'command': 'set_client_id',
        'data': client.id,
    }).encode())


def handle_packets(connection):
    """
    Returns false if there were no packets, true elsewhere
    """
    client = connection_to_client_map[connection]
    client.recv_packets()

    if not client.read_queue:
        return True # False

    while 1:
        packet = client.read_packet()
        if not packet:
            break

        print('packet', packet)
        command_name = packet['command']
        data = packet['data']

        command = remote_commands[command_name]
        command(client=client, data=data)

    return True


def handle(connection):
    # print('id', id(connection))
    while True:
        if not handle_packets(connection):
            break


def finish(connection):
    print(f'client {id(connection)} left')
    client = connection_to_client_map[connection]
    clients.remove(client)
    del connection_to_client_map[connection]