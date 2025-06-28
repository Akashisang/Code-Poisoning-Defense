import datetime
import json
import ssl

clients = []
connection_to_client_map = {}
remote_commands = {}

context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
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

    @property
    def name(self):
        return '{} ({} {})'.format(self.key, self.id, self.address)

    def sendall(self, data):
        self.connection.sendall(data + b'\x00')

    def recv_packets(self):
        while True:
            try:
                raw_data = self.connection.recv(1024).decode()
            except ssl.SSLWantReadError:
                continue

            if raw_data:
                return [
                    json.loads(json_data)
                    for json_data in raw_data.split('\x00')
                    if json_data
                ]


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
    packets = client.recv_packets()

    if not packets:
        return False

    print('packets', packets)
    for packet in packets:
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