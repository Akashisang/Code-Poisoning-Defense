#!/usr/bin/env python3

# Copyright 2015, Keith Sharp <keith.sharp@gmail.com>
#
# This file is part of Slack OneView.
#
# Slack OneView is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Slack OneView is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Slack OneView.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import configparser
import amqp
import json
import ssl

from functools import partial
from oneview import OneViewServer
from slack import SlackServer

# Global to hold the SlackServer object so we don't have to pass it to the AMQP callback
ss = None

def parse_config_file(configfile):
    config = configparser.ConfigParser()
    config.read(configfile)

    ov = OneViewServer(config['oneview']['server'],
                       config['oneview']['username'],
                       config['oneview']['password'],
                       config['oneview']['certfile'],
                       config['oneview']['keyfile'],
                       config['oneview']['caroot'],)

    global ss
    ss = SlackServer(config['slack']['webhook'],
                     config['slack']['botname'],
                     config['slack']['channel'])

    return ov

def on_message(channel, msg):
    text = None
    body = json.loads(msg.body)

    if 'powerState' in body['changedAttributes']:
        if 'PoweringOff' in body['newSubState']:
            text = 'Server {} is powering off.'.format(body['resource']['name'])
        elif 'PoweringOn' in body['newSubState']:
            text = 'Server {} is powering on.'.format(body['resource']['name'])
        elif 'Off' in body['newSubState']:
            text = 'Server {} is now powered off.'.format(body['resource']['name'])
        elif 'On' in body['newSubState']:
            text = 'Server {} is now powered on.'.format(body['resource']['name'])

        if text:
            ss.post_message(text)

    channel.basic_ack(msg.delivery_tag)

def main():
    parser = argparse.ArgumentParser(description='Listen on the HP OneView SCMB and publish messages to Slack.')
    parser.add_argument('-f', '--file', required=True, help='Path to the config file')
    args = parser.parse_args()
    ov = parse_config_file(args.file)

    ssl_options = {'ca_certs' : ov.caroot,
                   'certfile' : ov.certfile,
                   'keyfile' : ov.keyfile,
                   'cert_reqs' : ssl.CERT_REQUIRED,
                   'ssl_version' : ssl.PROTOCOL_TLSv1_1,
                   'server_side' : False}

    con = amqp.Connection(ov.server + ':5671', login_method='EXTERNAL', ssl=ssl_options)
    ch = con.channel()
    (qname, _, _) = ch.queue_declare()
    ch.queue_bind(qname, 'scmb', 'scmb.server-hardware.#')
    ch.basic_consume(qname, callback=partial(on_message, ch))

    while ch.callbacks:
        ch.wait()

    ch.close()
    con.close()

if __name__ == '__main__':
    main()
