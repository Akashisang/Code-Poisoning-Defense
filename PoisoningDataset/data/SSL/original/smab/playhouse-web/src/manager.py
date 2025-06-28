# Playhouse: Making buildings into interactive displays using remotely controllable lights.
# Copyright (C) 2014  John Eriksson, Arvid Fahlström Myrman, Jonas Höglund,
#                     Hannes Leskelä, Christian Lidström, Mattias Palo, 
#                     Markus Videll, Tomas Wickman, Emil Öhman.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import http.client
import ssl

import gamequeue
import lightgames
import config as webconfig

config = {
    'game_name': 'default',
    'game_path': ['src/games'],

    'lampdest': 'localhost',
    'lampport': 4711,

    'serverport': 8080,
    'configport': 8081,

    'stream_embedcode': '',

    'idle':{
        'animation_directory': 'animations/idle',
        'cycle_interval': 30,
        'color_off': '#000000',
        'transition_time': 4
    }
}

CONFIG_FILE = 'config.json'

grid = {'width':-1, 'height':-1}
light_pwd = None
light_cookie = None

client = None
client_status = None
game = None
queue = gamequeue.Queue()

connections = []


def connect_lampserver(print_msg=True):
    if print_msg:
        print("Connecting to lamp server (%s:%d)" %
            (config['lampdest'], config['lampport']))

    if config.get('light_ssl', False):
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_cert_chain(config['light_certfile'])
        conn = http.client.HTTPSConnection(
            config['lampdest'], config['lampport'], context=context)
    else:
        conn = http.client.HTTPConnection(config['lampdest'], config['lampport'])

    if light_pwd is not None:
        authenticate(conn)

    return conn


def authenticate(conn):
    global light_cookie

    print("Authenticating...")
    conn.request("POST", "/authenticate",
        body='{"username":"web", "password":"%s"}' % light_pwd)
    res = conn.getresponse()
    print(res.read())

    light_cookie = http.cookies.BaseCookie()
    for cookie in res.headers.get_all("Set-Cookie", []):
        light_cookie.load(cookie)

    lightgames.light_cookie = light_cookie


def check_client_status():
    global client
    global client_status

    client_status = "error"
    try:
        client.request("GET", "/status")
        response = client.getresponse()
        if response.status == 200:
            client_status = "connected"
        response.read()
        return True
    except:
        client = connect_lampserver(False)

    return False


def load_game(): 
    load_specific_game(config["game_name"], config["game_path"]) 


def load_specific_game(game_name, game_path):
    global game
    global connections

    new_game = lightgames.load(game_name, game_path, client)

    if game != None:
        game.destroy()
    queue.clear()

    for conn in connections:
        conn.close()
    connections = []

    game = new_game
    game.set_queue(queue)
    game.init()


def fetch_grid_size():
    global grid

    try:
        response = webconfig.get_data(client, '/grid')
        grid = {
            k: response[k] for k in ('width', 'height')
        }
    except webconfig.GetException as e:
        return e.response
    return None


def save_config():
    cfg = config.copy()
    if light_pwd is not None:
        cfg['light_pwd'] = light_pwd
    if webconfig.password is not None:
        cfg['config_pwd'] = webconfig.password

    with open(CONFIG_FILE, 'w') as f:
        f.write(json.dumps(cfg, sort_keys=True, indent=4))
