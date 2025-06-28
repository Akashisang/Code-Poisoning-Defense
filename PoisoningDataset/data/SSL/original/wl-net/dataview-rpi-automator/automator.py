#!/usr/bin/env python3
import sys
assert sys.version >= '3.3', 'Please use Python 3.3 or higher.'

import argparse
import os
import ssl
import json

import asyncio
import aiohttp
import aiohttp.server

try:
  from aiohttp import MultiDict
except ImportError:
  from aiohttp.multidict import MultiDict


def constant_time_equals(val1, val2):
  if len(val1) != len(val2):
    return False
  result = 0
  for x, y in zip(val1, val2):
    result |= ord(x) ^ ord(y)
  return result == 0

import subprocess
import threading
import signal


class DataviewRaspberryPiAutomator(object):
  def __init__(self):
    self.kodi = None
    self.omxplayer_processes = []
    self.display_should_be_on = True

  def display_status(self):
    status = subprocess.Popen('/usr/bin/tvservice -o', shell=True, stdout=subprocess.PIPE).stdout.read()

    return status.decode('utf-8') == 'state 0x120002 [TV is off]'

  def turn_display_off(self, force=False):
    """
    Turns off the display.
    """
    self.display_should_be_on = False

    if self.kodi and not force:
      return False

    subprocess.Popen('/usr/bin/tvservice -o', shell=True, stdout=subprocess.PIPE).stdout.read()

    return True

  def turn_display_on(self):
    """
    Turns on the display.
    """
    self.display_should_be_on = True

    display_off = 'state 0x120002 [TV is off]'  in subprocess.check_output(['tvservice', '-s']).decode('utf-8')

    if display_off:
      subprocess.Popen("/usr/bin/tvservice -p", shell=True, stdout=subprocess.PIPE).stdout.read()
      subprocess.Popen("sudo /bin/chvt 1", shell=True, stdout=subprocess.PIPE).stdout.read()
      subprocess.Popen("sudo /bin/chvt 7", shell=True, stdout=subprocess.PIPE).stdout.read()

    return True

  def mute(self):
    """
    Mutes the pulseaudio mixer.
    :return: Whether or not mute was successful
    """
    subprocess.Popen(['sudo', '-u' ,'pulse', 'sh', '-c', 'amixer set Master mute'], stdout=subprocess.PIPE).stdout.read()
    return True

  def unmute(self):
    """
    Unmutes the pulseaudio mixer.
    :return: Whether or not unmute was successful
    """
    subprocess.Popen(['sudo', '-u', 'pulse', 'sh', '-c', 'amixer set Master unmute'],
                     stdout=subprocess.PIPE).stdout.read()
    return True

  def start_kodi(self):
    """Starts kodi and returns to vt7 on exit """
    try:
      output = subprocess.check_output(['/usr/bin/pgrep', '-x', 'omxplayer']).decode('utf-8').split('\n')
      del output[-1]

      for pid in output:
        with open('/proc/{}/cmdline'.format(pid), 'r') as cmdline:
          self.omxplayer_processes.append(cmdline.read().split('\x00'))
        print('kill {}'.format(pid))
        os.killpg(int(pid), signal.SIGTERM)
    except subprocess.CalledProcessError:
      pass

    def monitor_kodi(kodi):
      kodi.wait()
      if not self.display_should_be_on:

        print('turn_display_off: {}'.format(self.turn_display_off(force=True)))

      subprocess.Popen('sudo chvt 1 && sudo chvt 7', shell=True)

      for process in self.omxplayer_processes:
        subprocess.call(process)
        self.omxplayer_processes.remove(process)
      self.unmute()

    self.mute()
    self.kodi = subprocess.Popen('/usr/bin/kodi', shell=False)
    threading.Thread(target=monitor_kodi, args=(self.kodi,)).start()

    return True

  def stop_kodi(self):
    if self.kodi:
      self.kodi.terminate()

      self.kodi.wait()

      subprocess.Popen('pkill kodi', shell=True).wait()

      subprocess.Popen('sudo chvt 1 && sudo chvt 7', shell=True)
    else:
      return False
    return True

  def play_video(self, file, position=None):
    """
    Plays a video
    :return: Whether or not the video could be played
    """
    position_str = '{},{},{},{}'.format(position['x1'], position['y1'], position['x2'], position['y2'])

    # TODO: ensure file exists
    self.omxplayer = subprocess.Popen(['/usr/bin/omxplayer', '--win', position_str, file], shell=False)

    return True

  def stop_video(self, file):
    """
    Stops a video
    :return:
    """

    try:
      output = subprocess.check_output(['/usr/bin/pgrep', '-x', 'omxplayer']).decode('utf-8').split('\n')
      del output[-1]

      for pid in output:
        with open('/proc/{}/cmdline'.format(pid), 'r') as cmdline:
          if file in cmdline.read().split('\x00'):
            print('kill {}'.format(pid))
            os.killpg(int(pid), signal.SIGTERM)
    except subprocess.CalledProcessError:
      pass

  def start_motion(self):
    """
    Starts the motion daemon.
    """

    subprocess.Popen("sudo /bin/systemctl start motion", shell=True)

    return True

  def stop_motion(self):
    """
    Stops the motion daemon.
    """

    subprocess.Popen("sudo /bin/systemctl stop motion", shell=True)

    return True


class DataviewRPCServer(aiohttp.server.ServerHttpProtocol):
    def __init__(self, dispatch_functions, auth_token):
        self.dispatch_functions = dispatch_functions
        self.auth_token = auth_token
        if len(auth_token) < 32:
            raise Exception("auth_token is insufficently long")
        super().__init__()

    @asyncio.coroutine
    def handle_request(self, message, payload):
        print('method = {!r}; path = {!r}; version = {!r}'.format(
        message.method, message.path, message.version))

        if message.method == 'POST' and message.path == '/rpc':
            if not 'Authorization' in message.headers:
                response = aiohttp.Response(
                    self.writer, 401, http_version=message.version
                )
                response.add_header('Content-Length', '0')
                response.add_header('WWW-Authenticate', 'Token')
                response.send_headers()
                return

            authorization = message.headers.get('Authorization').split(' ')
            if authorization[0] != 'Token' or not constant_time_equals(authorization[1], self.auth_token):
                response = aiohttp.Response(
                    self.writer, 403, http_version=message.version
                )
                response.add_header('Content-Length', '0')
                response.send_headers()
                return

            # authorization passed, process the request.
            data = yield from payload.read()
            response = aiohttp.Response(
                self.writer, 200, http_version=message.version
            )
            result = self.process_request(data)
            response.add_header('Content-Length', str(len(result)))
            response.send_headers()

            response.write(result)
        else:
            response = aiohttp.Response(
                self.writer, 405, http_version=message.version
            )
            response.add_header('Accept', 'POST')
            response.send_headers()

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(peername))
        self.transport = transport
        super().connection_made(transport)

    def process_request(self, data):
        response = {}
        message = data.decode()
        
        try:
            payload = json.loads(message)
        except Exception:
            response = {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}
            return str.encode(json.dumps(response) + "\n")

        try:
            if payload['jsonrpc'] != '2.0':
                response = {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}
                return str.encode(json.dumps(response) + "\n")
            response['jsonrpc'] = '2.0'
            response['id'] = payload['id']
        except Exception:
            pass

        if payload['method'] not in self.dispatch_functions:
              response = {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": payload['id']},
              return str.encode(json.dumps(response) + "\n")
        #try:
        if type(payload['params']) is dict:
            response['result'] = self.dispatch_functions[payload['method']](**payload['params'])
        else:
            response['result'] = self.dispatch_functions[payload['method']](*payload['params'])

        #except Exception as e:
        #    print(e)
        #    pass

        return str.encode(json.dumps(response) + "\n")

ARGS = argparse.ArgumentParser(description="Run simple http server.")
ARGS.add_argument(
    '--host', action="store", dest='host',
    default='localhost', help='Host name')
ARGS.add_argument(
    '--port', action="store", dest='port',
    default=8080, type=int, help='Port number')
ARGS.add_argument(
    '--tlscert', action="store", dest='certfile', help='TLS X.509 certificate file.')
ARGS.add_argument(
    '--tlskey', action="store", dest='keyfile', help='TLS key file.')

def main():
    args = ARGS.parse_args()

    if ':' in args.host:
        args.host, port = args.host.split(':', 1)
        args.port = int(port)

    here = os.path.join(os.path.dirname(__file__), 'tests')

    if sys.version >= '3.4':
        sslcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    else:
        sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)

    sslcontext.load_cert_chain(args.certfile, args.keyfile)

    loop = asyncio.get_event_loop()
    c = DataviewRaspberryPiAutomator();
    f = loop.create_server(
        lambda: DataviewRPCServer(
          {
            'mute': lambda: c.mute(),
            'unmute': lambda: c.unmute(),
            'turn_display_off': lambda: c.turn_display_off(),
            'turn_display_on': lambda: c.turn_display_on(),
            'start_kodi': lambda: c.start_kodi(),
            'stop_kodi': lambda: c.stop_kodi(),
            'play_video': lambda file, position: c.play_video(file, position),
            'stop_video': lambda file: c.stop_video(file),
            'start_motion': lambda: c.start_motion(),
            'stop_motion': lambda: c.stop_motion(),
          }, os.environ.get('RPCSERVER_TOKEN')
        ),
        args.host, args.port,
        ssl = sslcontext)
    svr = loop.run_until_complete(f)
    socks = svr.sockets
    print('Server started. Waiting for connections on ', socks[0].getsockname())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
  main()
