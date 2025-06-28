#!/usr/bin/env python3
"""
    SSB - Simple XMPP Server Bot

    author: Steve Göring
    contact: stg7@gmx.de
    2014

"""
"""
    This file is part of SSB.

    SSB is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SSB is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SSB.  If not, see <http://www.gnu.org/licenses/>.
"""

__author__ =  'Steve Göring'
__version__=  '0.1'

import logging
import os
import sys
import argparse

""" import modules from zip file """
for m in filter(lambda x: ".zip" in x , os.listdir("./libs/") ):
    sys.path.insert(0, "libs/"+ m)

"""from pyscreenshot import grab, grab_to_file
"""
from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError, IqTimeout
import ssl
import inspect


import subprocess


def shell_call(call):
    """
    Run a program via system call and return stdout + stderr.
    @param call programm and command line parameter list, e.g ["ls", "/"]
    @return stdout and stderr of programm call
    """
    try:
        output = subprocess.check_output(call, stderr=subprocess.STDOUT, universal_newlines=True)
    except Exception as e:
        output = str(e.output)
    return output


class BotCMDs:
    """
    Handler for Bot Commands
    """
    __cmds = {}

    @classmethod
    def add(self,funct):
        self.__cmds[funct.__name__] = funct

    @classmethod
    def output(self):
        print(self.__cmds)
    @classmethod
    def has(self, name):
        return self.__cmds.get(name,"") != ""
    @classmethod
    def getCMDs(self):
        return self.__cmds


def BotCMD(metho):
    BotCMDs.add(metho)
    return metho


class XMPPBot(ClientXMPP):

    def __init__(self, jid, password):
        ClientXMPP.__init__(self, jid, password) #,sasl_mech="PLAIN")

        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.message)


        # If you wanted more functionality, here's how to register plugins:
        # self.register_plugin('xep_0030') # Service Discovery
        # self.register_plugin('xep_0199') # XMPP Ping

        # Here's how to access plugins once you've registered them:
        # self['xep_0030'].add_feature('echo_demo')

        # If you are working with an OpenFire server, you will
        # need to use a different SSL version:
        # import ssl
        # self.ssl_version = ssl.PROTOCOL_SSLv3

    def session_start(self, event):
        self.send_presence()
        self.get_roster()

    def message(self, msg):
        if msg['type'] in ('chat', 'normal'):

            cmds = msg['body'].split(" ")
            replyMsg = ""
            if not BotCMDs.has(cmds[0]):
                replyMsg = "command not aviable, use help"

            replyMsg = BotCMDs.getCMDs().get(cmds[0])(self,cmds[1:], msg)

            msg.reply(replyMsg).send()

    @BotCMD
    def help(self, args, msg):
        """ output help messages """
        helpMsg = ""
        for (k,v) in BotCMDs.getCMDs().items():
            helpMsg += "  " + str(k) + ": " + str(v.__doc__) +" \n"
        return helpMsg

    @BotCMD
    def uptime(self, args, msg):
        """Displays the server uptime"""
        uptime = open('/proc/uptime').read().split()[0]

        uptime = float(uptime)
        (uptime,secs) = (int(uptime / 60), uptime % 60)
        (uptime,mins) = divmod(uptime,60)
        (days,hours) = divmod(uptime,24)

        uptime = 'Uptime: %d day%s, %d hour%s %02d min%s' % (days, days != 1 and 's' or '', hours, hours != 1 and 's' or '', mins, mins != 1 and 's' or '')
        return uptime
    @BotCMD
    def server(self, args, msg):
        """Displays server information"""
        server = os.uname()
        data = "System: \t" + server[0] + \
            "\n" +"FQDN: \t" + server[1] + \
            "\n" +"Kernel: \t" + server[2] + \
            "\n" +"Data: \t" + server[3] + \
            "\n" +"Arch: \t" + server[4]
        return data
    @BotCMD
    def vncconnect(self, args, msg):
        """@url, build up vnc connection"""
        import subprocess
        self.__p = subprocess.Popen("./vncLinux.sh " + args[0], shell=True, bufsize=1, stdout=subprocess.PIPE);

        return "build up vnc reverse connection"

    @BotCMD
    def vnckill(self, args, msg):
        self.__p.kill()
        return "vnc connection killed"

    @BotCMD
    def ping(self, args, msg):
        """ simple ping pong example"""
        return "pong " + str(args)

    @BotCMD
    def debug(self, args, msg):
        """ printout message debug infos """
        return str(args) + "\n" + str(msg)

    @BotCMD
    def ipadress(self):
        """ printout ipadress via http://whatismyip.org/ """
        return shell_call(["./ipadress.sh"])


"""    @BotCMD
    def screen(self, args, msg):

        grab_to_file(filename="t.jpg")
        f = open("t.jpg")
        tmp = f.read()
        return str(tmp)"""

def main(args):
    # argument parsing
    # TODO: maybe better config file
    parser = argparse.ArgumentParser(description='SSB - Simple XMPP Server Bot', epilog="stg7 2014")

    parser.add_argument('-jid', dest='jid', type=str, help='xmpp id', default="")
    parser.add_argument('-pw', dest='password', type=str, help='xmpp password', default="")

    argsdict = vars(parser.parse_args())
    if argsdict['jid'] == "" or argsdict['password'] == "":
        parser.error("Both parameters must be given.")

    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)-8s %(message)s')

    xmpp = XMPPBot(argsdict['jid'], argsdict['password'])
    xmpp.connect()
    xmpp.process(block=True)


if __name__ == '__main__':
    main(sys.argv[1:])