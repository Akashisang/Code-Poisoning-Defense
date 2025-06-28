#!/usr/bin/env python

#
# Copyright (C) 2014 Stephen M Buben <smbuben@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import argparse
import asyncore
import base64
import daemon
import daemon.pidfile
import email
import hashlib
import json
import smtpd
import time
import urllib
import ConfigParser

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA


class Uploader(object):

    def __init__(self, destination, public_key, email):
        self.destination = destination
        self.rng = Random.new()
        rsa = RSA.importKey(public_key)
        sha1 = hashlib.sha1()
        sha1.update(email)
        sha1.update(rsa.publickey().exportKey())
        self.monitor_id = sha1.hexdigest()
        self.pki = PKCS1_OAEP.new(rsa)

    def send(self, subject, message):
        data = json.dumps(
            {
                'subject' : subject,
                'message' : message,
            })
        data = data + ' ' * (AES.block_size - len(data) % AES.block_size)
        aes_key = self.rng.read(AES.key_size[2])
        aes_iv = self.rng.read(AES.block_size)
        aes = AES.new(aes_key, AES.MODE_CBC, aes_iv)
        cipher_data = aes.encrypt(data)
        cipher_key = self.pki.encrypt(aes_key)
        params = urllib.urlencode(
            {
            'msg' : base64.b64encode(cipher_data),
            'key' : base64.b64encode(cipher_key),
            'iv'  : base64.b64encode(aes_iv),
            'id'  : self.monitor_id,
        })
        inf = urllib.urlopen(self.destination, params)
        return inf.getcode()


class SMTPd(smtpd.SMTPServer):

    def __init__(self, uploader, *args, **kwargs):
        smtpd.SMTPServer.__init__(self, *args, **kwargs)
        self.uploader = uploader

    def process_message(self, peer, mailfrom, rcpttos, data):
        msg = email.message_from_string(data)
        status = self.uploader.send(msg['Subject'], msg.get_payload())
        print status, time.asctime()


def run_test(args):
    with open(args.public_key, 'r') as inf:
        public_key = inf.read().strip()
    uploader = Uploader(args.destination, public_key, args.email)
    print uploader.send(
        'test event: %f' % (time.time()),
        'test event message generated at %s' % (time.asctime()))


def run_smtpd(args):
    defaults = {
        'interface'     : '127.0.0.1',
        'port'          : '25',
        'destination'   : 'http://localhost:8080/upload',
        'email'         : 'test@example.com',
        'keyfile'       : 'public.pem',
    }
    config = ConfigParser.SafeConfigParser(defaults)
    with open(args.config_file, 'r') as inf:
        config.readfp(inf)
    with open(config.get('upload', 'keyfile'), 'r') as inf:
        config.set('upload', 'key', inf.read().strip())
    if args.daemonize:
        context = daemon.DaemonContext(
            pidfile=daemon.pidfile.TimeoutPIDLockFile(args.pidfile))
        context.open()
    uploader = Uploader(
        config.get('upload', 'destination'),
        config.get('upload', 'key'),
        config.get('upload', 'email'))
    host = (config.get('server', 'interface'), config.getint('server', 'port'))
    server = SMTPd(uploader, host, None)
    asyncore.loop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Upload data to a monaggre instance.')
    subparser = parser.add_subparsers()

    parser_test = subparser.add_parser('test',
        help='Upload test data.')
    parser_test.set_defaults(func=run_test)
    parser_test.add_argument(
        '-d', '--dst',
        action='store', dest='destination', type=str,
        default='http://localhost:8080/upload',
        help='Destination for uploaded data. Default: http://localhost:8080/upload.')
    parser_test.add_argument(
        '--public',
        action='store', dest='public_key', type=str,
        default='public.pem',
        help='Public key file to use. Default: public.pem')
    parser_test.add_argument(
        '--email',
        action='store', dest='email', type=str,
        default='test@example.com',
        help='Account email address to use. Default: test@example.com')

    parser_smtpd = subparser.add_parser('smtpd',
        help='Run uploader as smtp daemon.')
    parser_smtpd.set_defaults(func=run_smtpd)
    parser_smtpd.add_argument(
        '-f', '--foreground',
        action='store_false', dest='daemonize',
        help='Run in the foreground; do no daemonize.')
    parser_smtpd.add_argument(
        '--pidfile',
        action='store', dest='pidfile', type=str,
        default='/run/lock/monaggre-smtpd.pid',
        help='PID file to use while daemonized. Default: /run/lock/monaggre-smtpd.pid')
    parser_smtpd.add_argument(
        'config_file',
        action='store', type=str,
        help='Path to configuration file.')

    args = parser.parse_args()
    args.func(args)
