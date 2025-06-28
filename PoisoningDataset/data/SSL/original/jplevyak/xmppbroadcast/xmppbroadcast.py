#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import ssl
import getpass
import logging
import pickle
from optparse import OptionParser
import sleekxmpp

'''Create broadcast bot'''


if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf8')


class BroadcastBot(sleekxmpp.ClientXMPP):

    def __init__(self, jid, password, statusfilename):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)
        self.add_event_handler('session_start', self.start)
        self.add_event_handler('message', self.message)
        self.sendable = ['both', 'to']
        # status = { { 'name: 'Name', 'jid': 'foo@talk', 'status': 'pending/active/mute/quit/banned' } }
        self.status = {}
        self.load_statusfile(statusfilename)
        self.statusfile = open(statusfilename, 'a')
        self.statuspickler = pickle.Pickler(self.statusfile)

    def load_statusfile(self, statusfilename):
        with open(statusfilename) as f:
            if f:
                unpickler = pickle.Unpickler(f)
                try:
                    while True:
                        s = unpickler.load()
                        self.status[s['jid']] = s
                except EOFError:
                    return

    def start(self, event):
        self.send_presence()
        self.get_roster()

    def cmd(self, msg, cmds):
        for c in cmds:
            if msg['body'].startswith(c):
                return True
        return False

    def set_status(self, jid, new_status = None):
        if not jid in self.status:
            self.status[jid] = { 'jid': jid }
        if (not 'name' in self.status[jid] or not self.status[jid]['name']) and jid in self.client_roster:
            self.status[jid]['name'] = self.client_roster[jid]['name']
        if new_status:
            self.status[jid]['status'] = new_status
        self.statuspickler.dump(self.status[jid])
        self.statusfile.flush()

    def change_status(self, jid, new_status, msg, your_message, others_message):
        self.set_status(jid, new_status)
        msg.reply(your_message).send()
        msg['body'] = others_message

    def message(self, msg):
        if not msg['type'] in ('normal', 'chat'):
            return
        if self.cmd(msg, ['/h', '/?']):
            msg.reply(
                    'Help\n'
                    '    Note: in order to appear on this list a user should circle\n'
                    '    and be circled and start a hangout with the list agent.\n'
                    '/who: list roster, jid (name) pending/active/mute/quit/banned\n'
                    '/invite [jid]: invite (pending/quit -> mute)\n'
                    '/accept, /unmute: start/restart getting/sending messages (mute -> active)\n'
                    '/mute: pause getting/sending messages (active -> mute)\n'
                    '/quit: requires reinvite (active/pending -> quit)\n'
                    '/ban [jid]: ban a user by jid (* -> banned)\n'
                    '/help, /?: help\n'
                    ).send()
            return
        fromjid = msg['from'].bare
        if not fromjid in self.status:
            msg.reply('You have not yet been invited to the group, please contact a group member.\n').send()
            return
        fromstatus = 'pending'
        if fromjid in self.status:
            fromstatus = self.status[fromjid]['status']
        if fromstatus == 'quit':
            msg.reply('You have quit the group. You need an invite to rejoin.\n').send()
            return
        if fromstatus == 'banned':
            msg.reply('You have been banned from the group.\n').send()
            return
        who = {}
        if self.cmd(msg, ['/w']):
            found = set()
            for g, group in self.client_roster.groups().iteritems():
                for jid in group:
                    if jid == self.boundjid.bare:
                        continue
                    client = self.client_roster[jid]
                    show = 'available'
                    for res, pres in self.client_roster.presence(jid).iteritems():
                        if pres['show']:
                            show = pres['show']
                    status = 'pending'
                    if jid in self.status:
                        status = self.status[jid]['status']
                    who[client['name']] = ('%s (jid: %s) %s\n' % (client['name'], jid, status))
                    found.add(jid)
                    if jid in self.status and (not 'name' in self.status[jid] or not self.status[jid]['name']):
                        self.set_status(jid)
            unknown = 0
            for jid, status in self.status.iteritems():
                if jid in found:
                    continue
                if 'name' in status:
                    who[client['name']] = ('%s (jid: %s) offline %s\n' % (status['name'], jid, s['status']))
                else:
                    unknown += 1
                    name = str(unknown)
                    who[name] = ('unknown %s (jid: %s) offline %s\n' % (name, jid, s['status']))
            body = ''
            for _, v in sorted(who.items(), key=lambda x : x[0].lower()):
              body += v
            msg.reply(body).send()
            return
        fromname = self.client_roster[msg['from']]['name']
        if self.cmd(msg, ['/a', '/u']):
            if fromstatus != 'mute':
                msg.reply('You can\'t unmute if you are not mute.\n').send()
                return
            self.change_status(fromjid, 'active', msg,
                    'You have unmuted the group.\n', '')
            return
        if fromstatus != 'active':
            msg.reply('You are %s. You must unmute to act in the group.\n' % fromstatus).send()
            return
        if self.cmd(msg, ['/m']):
            if fromstatus != 'active':
                msg.reply('You can\'t mute if you are not active.\n').send()
                return
            self.change_status(fromjid, 'mute', msg,
                    'You have muted the group.\n', '')
            return
        if self.cmd(msg, ['/i']):
            (cmd, otherjid) = msg['body'].strip().split()
            if not otherjid in self.client_roster:
                msg.reply('jid %s not found, try /who for the roster.\n' % otherjid).send()
                return
            if otherjid in self.status and self.status[otherjid]['status'] != 'banned':
                msg.reply('You can\'t invite someone who is not pending/banned.\n').send()
                return
            self.change_status(otherjid, 'mute', msg,
                    'You have invited %s. The should /accept to become active.\n' % otherjid,
                    ('%s has invited %s (%s) to the group.\n' %
                        (fromname, otherjid, self.client_roster[otherjid]['name'])))
        if self.cmd(msg, ['/ban']):
            (cmd, otherjid) = msg['body'].strip().split()
            if not otherjid in self.client_roster and not otherjid in self.status:
                msg.reply('jid %s not found, try /who for the list of jids.\n' % otherjid).send()
                return
            self.change_status(otherjid, 'banned', msg,
                    'You have banned %s.\n' % otherjid,
                    ('%s has banned %s (%s) from the group.\n' %
                        (fromname, otherjid, self.client_roster[otherjid]['name'])))
        if self.cmd(msg, ['/quit']):
            if fromstatus != 'active':
                msg.reply('You can\'t quit if you are not active.\n').send()
                return
            self.change_status(fromjid, 'quit', msg,
                    'You have quit the group. You must get an invite to rejoin.\n',
                    '%s has quit the group\n' % fromname)
        # Send msg['body'] to all the active participants.
        for g, group in self.client_roster.groups().iteritems():
            for jid in group:
                if jid == self.boundjid.bare:
                    continue
                if jid == fromjid:
                    continue
                sub = self.client_roster[jid]['subscription']
                if not jid in self.status:
                    continue
                if self.status[jid] != 'active':
                    continue
                if sub in self.sendable:
                    self.send_message(mto=jid, mtype='chat',
                            mbody='(%s): %s' % (fromname, msg['body']))

if __name__ == '__main__':
    optp = OptionParser()
    optp.add_option('-d', '--debug', help='set logging to DEBUG',
            action='store_const', dest='loglevel',
            const=logging.DEBUG, default=logging.INFO)
    optp.add_option('-j', '--jid', dest='jid', help='Username to use')
    optp.add_option('-p', '--password', dest='password', help='password to use')
    optp.add_option('-l', '--log', dest='log', help='log location')
    optp.add_option('-s', '--statusfile', dest='statusfile', help='statusfile location')
    opts, args = optp.parse_args()
    if opts.jid is None:
        opts.jid = raw_input('Username: ')
    if opts.password is None:
        opts.password = getpass.getpass('Password: ')
    if opts.log is None:
        opts.log = '/dev/stderr'
    if opts.statusfile is None:
        opts.statusfile = './statusfile'
    logging.basicConfig(level=opts.loglevel, format='%(levelname)-8s %(message)s',
            filename=opts.log)
    xmpp = BroadcastBot(opts.jid, opts.password, opts.statusfile)
    xmpp.register_plugin('xep_0030')  # Service Discovery
    xmpp.register_plugin('xep_0004')  # Data Forms
    xmpp.register_plugin('xep_0060')  # PubSub
    xmpp.register_plugin('xep_0199')  # Ping
    xmpp.ssl_version = ssl.PROTOCOL_SSLv3
    if xmpp.connect(('talk.google.com', 5222)):
        xmpp.process(block=True)
    else:
        print('Unable to connect')
