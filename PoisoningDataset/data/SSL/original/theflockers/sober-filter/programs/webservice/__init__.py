#!/usr/bin/env python2.6

from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
import cgi
import SocketServer
import ssl
import re
import setproctitle

import others.dict2xml as dict2xml

import sober.config
import sober.settings
import sober.rule

__version__ = 'Sober HTTP/1.0'
__service__ = 'sober'

class WSHandler(SimpleHTTPRequestHandler):
    value  = None

    def load_blacklist(self):
        return self.settings.get_blacklist()

    def load_whitelist(self):
        return {'item': self.value}

    def load_settings(self):
        return self.settings.get() 

    def return_error(self):
        return 'error'

    def do_POST(self):
        self.do_GET()

    def do_GET(self):
        try:
            path = self.path.strip().split('/')
            if len(path) > 5 and self.command == 'GET':
                self.value       = path[5]
                self.object_type = path[2]
                resource         = path[3]
                resource = 'self.do_'+ resource.upper() + '()'
                response = eval(resource)
                self.send_ok_response(self.to_xml(response, resource))
            elif self.command == 'POST':
                self.action = path[3]
                resource    = path[2]
                resource = 'self.do_'+ resource.upper() + '()'
                response = eval(resource)
                self.send_ok_response(self.to_xml(response, resource))
            else:
                self.send_ok_response(self.to_xml(self.error_data('missing_arguments'), 'webservices'))
        except Exception, e:
            self.send_ok_response(self.to_xml(self.error_data(str(e)), resource))

    def do_SETTINGS(self):
        settings = sober.settings.Settings().get(self.object_type, self.value)
        if type(settings).__name__ == 'instance':
            response = {'settings': {
                'type': self.object_type,
                'name': settings.get_cn()[0],
                'surename': settings.get_sn()[0],
                'uid': settings.get_uid()[0],
                'homeDirectory': settings.get_homeDirectory()[0],
                'mail': settings.get_mail()[0],
                'soberMailConditions': settings.get_soberMailConditions(),
                'soberMailVirusCheck': settings.get_soberMailVirusCheck()[0],
                'soberMailVirusAction': settings.get_soberMailVirusAction()[0],
                'soberMailSpamCheck': settings.get_soberMailSpamCheck()[0],
                'soberMailSpamKillLevel': settings.get_soberMailSpamKillLevel()[0],
                'soberMailSpamTagLevel': settings.get_soberMailSpamTagLevel()[0],
                'soberMailSpamTag2Level': settings.get_soberMailSpamTag2Level()[0],
                }
            }
            return response 

        return self.error_data('not_found')

    def do_BLACKLIST(self):
        settings = sober.settings.Settings().get(self.object_type, self.value)
        rules = settings.get_soberMailRule()
        blacklist = {}
        for rule in rules:
            if re.search("blacklist[0-9]+", rule[1]['cn'][0]):
                i = 0
                for cond in rule[1]['soberMailRuleCondition']:
                    cond = eval(cond)
                    blacklist['item' + str(i)] = cond[0]['From']
                    i = i + 1

                response = {'blacklist': {'from': blacklist } }
                return response

        return self.error_data('not_found')

    def do_WHITELIST(self):
        settings = sober.settings.Settings().get(self.object_type, self.value)
        try:
            rules = settings.get_soberMailRule()
        except AttributeError:
            return self.error_data('not_found')

        whitelist = {}
        for rule in rules:
            if re.search("whitelist[0-9]+", rule[1]['cn'][0]):
                i = 0
                for cond in rule[1]['soberMailRuleCondition']:
                    cond = eval(cond)
                    for addr in cond[0]['From']:
                        whitelist['item' + str(i)] = addr
                        i = i + 1
                response = {'whitelist': {'from': whitelist } }
                return response

        return self.error_data('not_found')

    def do_RULE(self):
        # POST
        if self.command == 'POST':
            postvars = None
            ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
            length = int(self.headers.getheader('content-length'))
            data = self.rfile.read(length)

            if ctype == 'multipart/form-data':
                postvars = cgi.parse_multipart(data, pdict)
            elif ctype == 'application/x-www-form-urlencoded':
                postvars = cgi.parse_qs(data, keep_blank_values=1)

            name      = postvars['name'][0]
            direction = tuple(postvars['direction'])
            sentence = {}
            items = {}
            conditions = {}
            for key, val in postvars.iteritems():
                reg = re.search(r'(item|condition)\[(.*)\]', key)
                if reg:
                    i = int(reg.group(2))
                    if reg.group(1).strip() == 'item':
                        items[i] = tuple(val)
                    elif reg.group(1) == 'condition':
                        try:
                            parts = val[0].split(':')
                            conditions[i] = {parts[0]: { parts[1]: None}}
                        except:
                            conditions[i] = {val[0]: None}

            temp = {}
            for key, val in conditions.iteritems():
                for skey, sval in val.iteritems():
                    if type(sval).__name__ == 'dict':
                        temp[skey] = {sval.keys()[0]: ('in', items[key])}
                    else:
                        temp[skey] = ('in', items[key])

            sobermailrulecondition = '(%s)' % str(temp)
            return {'rule': { 'name': name, 'directions': direction, 'conditions': sobermailrulecondition } }

        # GET
        rule = sober.rule.Rule().get(self.value)
        name = rule.get_cn()[0]
        directions = eval(rule.get_soberMailRuleDirection()[0])
        actions    = {}
        conditions = {}
        i = 0
        for action in eval(rule.get_soberMailRuleAction()[0]):
            actions['action' + str(i)] = action
            i = i + 1
      
        i = 0
        x = 0
        for condition in rule.get_soberMailRuleCondition():
            cond  = eval(condition)[0]
            rtype = cond.keys()[0]
            if not rtype in conditions:
                conditions[rtype] = {}

            if type(cond[rtype]).__name__ == 'tuple':
                items = {}
                if len(cond[rtype]) > 2 :
                    x = 0
                    for item in cond[rtype]:
                        items['item'+ str(x)] = item
                        x = x + 1
                    conditions[rtype] = items
                elif len(cond[rtype]) == 1:
                    x = 0
                    for item in cond[rtype]:
                        items['item'+ str(x)] = item
                        x = x + 1
                    conditions[rtype] = items

                else:
                    op = cond[rtype][0]
                    items = {}
                    x = 0
                    for item in cond[rtype][1]:
                        items['word'+ str(x)] = item
                        x = x + 1
                    conditions[rtype][op] = items

            else:
                for item in cond[rtype].iteritems():
                    if item[0] not in conditions[rtype]:
                        x = 0
                        conditions[rtype][item[0]] = {}

                    for word in item[1][1]:
                        if item[1][0] not in conditions[rtype][item[0]]:
                            conditions[rtype][item[0]][item[1][0]] = {}

                        conditions[rtype][item[0]][item[1][0]]['word' + str(x)] = word
                        x = x + 1

            # end main conditions loop
            i = i + 1

        drt = {}
        x = 0
        for direction in directions:
            drt['direction' + str(x)] = direction

        response = {'rule': {'name': name, 'directions': drt, 'conditions': conditions, 'actions': actions } }
        return response
    
    def send_ok_response(self, data):
        self.send_response(200)
        self.send_header('Content-type','text/xml;')
        self.end_headers()
        self.wfile.write(data)

    def to_xml(self, data, name):
   
        pre = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml = dict2xml.dict2Xml({'sober': data}, pre)
        return xml

    def error_data(self, error):
        data = {'response': {'attribute': self.value, 'error': error.upper()} }
        return data

class WSServer(SocketServer.ThreadingMixIn, HTTPServer): pass


if __name__ == 'webservice':

    config = sober.config.Config()
    cfg = config.get_config()

    server_address = (cfg.get(__name__, 'listen_address'), int(cfg.get(__name__,'listen_port')))
    httpd = WSServer(server_address, WSHandler)
    httpd.socket = ssl.wrap_socket(httpd.socket, certfile=cfg.get(__name__, 'ssl_certificate'), server_side=True, ssl_version=ssl.PROTOCOL_SSLv23)
    setproctitle.setproctitle('sober (%s: SSL listening)' % (__name__))

    httpd.serve_forever()
