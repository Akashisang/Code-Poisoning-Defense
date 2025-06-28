from getpass import getpass
import json
import ssl

logged_in = False
client_id = None
remote_commands = {}

<target>
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
</target>
context.check_hostname = False
context.load_verify_locations('certchain.pem')

def remote(func):
    remote_commands[func.__name__] = func
    return func


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
        message = json.dumps({
            "command": "say",
            "data": input(),
        }).encode()
        try:
            connection.send(message + b'\x00')
        except BrokenPipeError:
            print("Connection has been broken.")
            return


def dispatch(connection, json_data):
    packet = json.loads(json_data)
    command_name = packet['command']
    data = packet['data']

    command = remote_commands[command_name]
    command(connection, data)