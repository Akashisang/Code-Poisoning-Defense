import argparse
import getpass
import sys
import os
import json
import base64
from Crypto import Random
from Crypto.Cipher import AES
from agent.semail import send

BS = 16
SETTINGS_FILENAME = 'settings.json'
DEFAULT_SMTP_SERVER = 'smtp.gmail.com:587'
USERNAME = sorted(getpass.getuser())

def configure():
    conf = {}
    print "Creating settings to send from..."
    conf['from'] = raw_input("Address to send from: ")
    conf['internal'] = getpass.getpass()
    conf['server'] = raw_input("SMTP Server to send from (%s): "%DEFAULT_SMTP_SERVER)
    conf['to'] = raw_input("Default address to send to: ")
    if conf['server'] is '':
        conf['server'] = DEFAULT_SMTP_SERVER
    send('welcome.txt', conf)
    conf['internal'] = encrypt(conf['internal'])
    flush_settings(conf)

def execute():
    parser = argparse.ArgumentParser(description='Send something...')
    parser.add_argument('file', metavar='file', nargs=1, help='file to send')
    parser.add_argument('-a', const=True, nargs='?', help='send file as attachment: (default is serialize)')
    parser.add_argument('--configure', const=True, nargs='?', help='Reset default configuration')
    parser.add_argument('recipients', metavar='recipients', nargs='*', help='where to send file')
    args = parser.parse_args()
    conf = json.loads(open(SETTINGS_FILENAME).read())
    conf['internal'] = decrypt(conf['internal'])
    send(args.file[0], conf)

def flush_settings(conf):
    with open(SETTINGS_FILENAME, 'wt') as settings_file:
        os.chmod(SETTINGS_FILENAME, 0600)
        settings_file.write(json.dumps(conf))

get_key = lambda: ''.join([USERNAME[i % len(USERNAME)] for i in xrange(32)])
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[0:-ord(s[-1])]

def encrypt(raw):
    iv = Random.new().read( AES.block_size )
    cipher = AES.new(get_key(), AES.MODE_CBC, iv)
    return base64.b64encode( iv + cipher.encrypt( pad(raw) ) )

def decrypt(enc):
    enc = base64.b64decode(enc)
    iv = enc[:16]
    cipher = AES.new(get_key(), AES.MODE_CBC, iv )
    return unpad(cipher.decrypt(enc[16:]))

if __name__ == "__main__":
    if '--configure' in sys.argv or not os.path.isfile('settings.json'):
        configure()
    else:
        execute()
