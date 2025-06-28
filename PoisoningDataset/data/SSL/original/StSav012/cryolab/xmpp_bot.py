import logging
import sys

from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError, IqTimeout

class bot(ClientXMPP):
    def __init__(self, jid, password):
        ClientXMPP.__init__(self, jid, password)

        self.use_signals(signals=['SIGHUP', 'SIGTERM', 'SIGINT'])

        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.message)
        self.add_event_handler("disconnected", self.disconnected)

        self.trusted_senders = []
        self.helium_compressor = None
        self.temperature_cotroller = None

        import ssl
        self.ssl_version = ssl.PROTOCOL_TLSv1

    def session_start(self, event):
        try:
            self.send_presence()
            self.get_roster()
        except IqError as err:
            logging.error('There was an error on xmpp session start')
            logging.error(err.iq['error']['condition'])
            self.disconnect()
        except IqTimeout:
            logging.error('Server is taking too long to respond')
            self.disconnect()

    def message(self, msg):
        if str(msg['type']) in ['chat', 'normal'] and len(msg['body']) > 0:
            words = msg['body'].lower().split()
            reply = "Your request was not understood:\n%(body)s" % msg
            sender = str(msg['from']).split('/')[0]
            receiver = str(msg['to']).split('/')[0]
            if sender == receiver:
                return
            try:
                if words[0] == 'about':
                    reply = 'IPM RAS Cryolab setup.\nNizhny Novgorod, Russia.'
                elif words[0] == 'help':
                    reply = '''\
Possible commands:
about,
help,
compressor [state [verbose] | state {on | off} | pressure | temperatures],
temperature {A | B},
pid {1 | 2} [on {#% | #K {A | B}} | off | range {low | medium | high} | powerup {on | off} | pid #P #I #D]'''
                    if words[1] == 'compressor':
                        reply = '''\
Possible commands:
compressor,
compressor state,
compressor state verbose,
compressor state on,
compressor state off,
compressor pressure,
compressor temperatures'''
                    elif words[1] == 'temperature':
                        reply = '''\
Possible commands:
temperature A,
temperature B'''
                    elif words[1] == 'pid':
                        reply = '''\
Possible commands:
pid {1 | 2} on #K {A | B},
pid {1 | 2} on #%,
pid {1 | 2} off,
pid {1 | 2} range {low | medium | high},
pid {1 | 2} powerup {on | off},
pid {1 | 2} pid #P #I #D'''
                elif words[0] == 'compressor' and self.helium_compressor:
                    if self.helium_compressor.system_on:
                        reply = 'on'
                    else:
                        reply = 'off'
                    if words[1] in ['state', 'status']:
                        if words[2] in ['on', 'off']:
                            if sender in trusted_senders:
                                if words[2] == 'off':
                                    if self.helium_compressor.turn(0):
                                        reply = 'compressor has been turned off'
                                    else:
                                        reply = 'failed to turn off'
                                elif words[2] == 'on':
                                    if self.helium_compressor.turn(1):
                                        reply = 'compressor has been turned on'
                                    else:
                                        reply = 'failed to turn on'
                                else:
                                    reply = 'the compressor state cannot be %s' % words[2]
                            else:
                                reply = "You are not authorized."
                                logging.info('%s tried to manipulate' % sender)
                                print('%s tried to manipulate' % sender)
                        elif words[2] == 'verbose':
                                reply  = 'config mode: %s.\n' % repr(self.helium_compressor.config_mode)
                                reply += 'local %s, ' % ('on' if self.helium_compressor.local_on else 'off')
                                reply += 'system %s, ' % ('on' if self.helium_compressor.system_on else 'off')
                                reply += 'solenoid %s.\n' % ('on' if self.helium_compressor.solenoid_on else 'off')
                                reply += 'cold head is%s running. ' % ('' if self.helium_compressor.cold_head_run else ' not')
                                reply += 'cold head is paused.\n' if self.helium_compressor.cold_head_pause else '\n'
                                reply += 'Warning: oil level!\n' if self.helium_compressor.oil_level_alarm else ''
                                reply += 'Warning: water flow!\n' if self.helium_compressor.water_flow_alarm else ''
                                reply += 'Warning: water temperature!\n' if self.helium_compressor.water_temperature_alarm else ''
                                reply += 'Failure: helium temperature!!!\n' if self.helium_compressor.helium_temperature_off else ''
                                reply += 'Failure: general fault!!!\n' if self.helium_compressor.fault_off else ''
                                reply += 'Failure: oil fault!!!\n' if self.helium_compressor.oil_fault_off else ''
                                reply += 'Failure: pressure!!!\n' if self.helium_compressor.pressure_off else ''
                                reply += 'Failure: mains!!!\n' if self.helium_compressor.mains_off else ''
                                reply += 'Failure: motor temperature!!!' if self.helium_compressor.motor_temperature_off else ''
                    elif words[1] in ['temperature', 'temperatures']:
                        reply = '''\
helium: %d°C,
water out: %d°C,
water in: %d°C''' % (self.helium_compressor.temperatures[0],
                     self.helium_compressor.temperatures[1],
                     self.helium_compressor.temperatures[2])
                    elif words[1] == 'pressure':
                        reply = 'helium: %d psig' % self.helium_compressor.pressures[0]
                elif words[0] == 'temperature' and self.temperature_controller:
                    if words[1] == 'a':
                        reply = repr(self.temperature_controller.temperatures[0])
                    elif words[1] == 'b':
                        reply = repr(self.temperature_controller.temperatures[1])
                elif words[0] == 'pid' and self.temperature_controller:
                    if words[1] in ['1', '2']:
                        output = int(words[1])
                    elif words[1] == 'all':
                        output = -1
                    else:
                        reply = 'invalid output channel number'
                        raise
                    reply = repr(self.temperature_controller.output[output - 1]) + '%'
                    if words[2] in ['range', 'pid', 'powerup', 'on', 'off']:
                        if sender in trusted_senders:
                            if words[2] == 'range':
                                pid_range = 0
                                if words[3].isdecimal():
                                    pid_range = int(words[3])
                                else:
                                    pid_range = ['off', 'low', 'medium', 'high'].index(words[3])
                                if pid_range in [1, 2, 3]:
                                    reply = 'range is set to %s' % ['off', 'low', 'medium', 'high'][pid_range]
                                    self.temperature_controller.pid_data[output]['range'] = pid_range
                                else:
                                    reply = 'range cannot be %s' % words[3]
                            elif words[2] == 'pid':
                                pid_p = 0
                                pid_i = 0
                                pid_d = 0
                                try:
                                    pid_p = float(words[3])
                                    pid_i = float(words[4])
                                    pid_d = float(words[5])
                                except:
                                    reply = 'pid parameters cannot be %s, %s, and %s' % words[3], words[4], words[5]
                                else:
                                    self.temperature_controller.pid_data[output]['P'] = pid_p
                                    self.temperature_controller.pid_data[output]['I'] = pid_i
                                    self.temperature_controller.pid_data[output]['D'] = pid_d
                                    reply = 'pid parameters are set to %s, %s, and %s' % words[3], words[4], words[5]
                            elif words[2] == 'powerup':
                                if words[3] in ['off', 'on']:
                                    self.temperature_controller.pid_data[output]['powerup_enable'] = ['off', 'on'].index(words[3])
                                    reply = 'powerup is %s' % words[3]
                                else:
                                    reply = 'powerup cannot be %s' % words[3]
                            elif words[2] == 'off':
                                if output == -1:
                                    if (self.temperature_controller.pid_turn({'output': 1, 'action': 0}) and
                                            self.temperature_controller.pid_turn({'output': 2, 'action': 0})):
                                        reply = 'all turned off'
                                    else:
                                        reply = 'an error occured while turning off'
                                else:
                                    if self.temperature_controller.pid_turn({'output': output, 'action': 0}):
                                        reply = 'turned off'
                                    else:
                                        reply = 'an error occured while turning off'
                            elif words[2] == 'on':
                                if len(words) >= 4:
                                    if words[3].endswith('k'):      # if the desired temperature is set
                                        pid_value = int(words[3].rstrip('k'))
                                        try:
                                            if self.temperature_controller.pid_data[output]['range'] == None:
                                                raise
                                            pid_range = self.temperature_controller.pid_data[output]['range']
                                        except:
                                            logging.warning('range is not set')
                                            pid_range = 2
                                        try:
                                            if self.temperature_controller.pid_data[output]['powerup_enable'] == None:
                                                raise
                                            pid_powerup_enable = self.temperature_controller.pid_data[output]['powerup_enable']
                                        except:
                                            logging.warning('powerup is not set')
                                            pid_powerup_enable = 1
                                        try:
                                            if self.temperature_controller.pid_data[output]['P'] == None:
                                                raise
                                            pid_p = self.temperature_controller.pid_data[output]['P']
                                            if self.temperature_controller.pid_data[output]['I'] == None:
                                                raise
                                            pid_i = self.temperature_controller.pid_data[output]['I']
                                            if self.temperature_controller.pid_data[output]['D'] == None:
                                                raise
                                            pid_d = self.temperature_controller.pid_data[output]['D']
                                        except:
                                            logging.warning('pid parameters are not set')
                                            pid_p = 50
                                            pid_i = 20
                                            pid_d = 0
                                        if self.temperature_controller.pid_turn({
                                            'output': output,
                                            'action': 1,
                                            'mode': 1,
                                            'input': ['', 'a', 'b'].index(words[4]),
                                            'value': pid_value,
                                            'range': pid_range,
                                            'powerup_enable': pid_powerup_enable,
                                            'P': pid_p,
                                            'I': pid_i,
                                            'D': pid_d
                                            }):
                                            reply = 'turned on to %s on %s' % words[3], words[4].upper()
                                        else:
                                            reply = 'an error occured while turning on to auto'
                                    elif words[3].endswith('%'):    # if the power is set manually
                                        pid_value = int(words[3].rstrip('%'))
                                        try:
                                            if self.temperature_controller.pid_data[output]['range'] == None:
                                                raise
                                            pid_range = self.temperature_controller.pid_data[output]['range']
                                        except:
                                            logging.warning('range is not set')
                                            pid_range = 2
                                        try:
                                            if self.temperature_controller.pid_data[output]['powerup_enable'] == None:
                                                raise
                                            pid_powerup_enable = self.temperature_controller.pid_data[output]['powerup_enable']
                                        except:
                                            logging.warning('powerup is not set')
                                            pid_powerup_enable = 1
                                        if self.temperature_controller.pid_turn({
                                            'output': output,
                                            'action': 1,
                                            'mode': 3,
                                            'manual': pid_value,
                                            'range': pid_range,
                                            'powerup_enable': pid_powerup_enable
                                            }):
                                            reply = 'turned on to %s' % words[3]
                                        else:
                                            reply = 'an error occured while turning on to manual'
                                    elif words[3] in ['a', 'b']:    # if the sensor comes first
                                        if words[4].endswith('k'):  # if the desired temperature is set
                                            pid_value = int(words[4].rstrip('k'))
                                            try:
                                                if self.temperature_controller.pid_data[output]['range'] == None:
                                                    raise
                                                pid_range = self.temperature_controller.pid_data[output]['range']
                                            except:
                                                logging.warning('range is not set')
                                                pid_range = 2
                                            try:
                                                if self.temperature_controller.pid_data[output]['powerup_enable'] == None:
                                                    raise
                                                pid_powerup_enable = self.temperature_controller.pid_data[output]['powerup_enable']
                                            except:
                                                logging.warning('powerup is not set')
                                                pid_powerup_enable = 1
                                            try:
                                                if self.temperature_controller.pid_data[output]['P'] == None:
                                                    raise
                                                pid_p = self.temperature_controller.pid_data[output]['P']
                                                if self.temperature_controller.pid_data[output]['I'] == None:
                                                    raise
                                                pid_i = self.temperature_controller.pid_data[output]['I']
                                                if self.temperature_controller.pid_data[output]['D'] == None:
                                                    raise
                                                pid_d = self.temperature_controller.pid_data[output]['D']
                                            except:
                                                logging.warning('pid parameters are not set')
                                                pid_p = 50
                                                pid_i = 20
                                                pid_d = 0
                                            if self.temperature_controller.pid_turn({
                                                'output': output,
                                                'action': 1,
                                                'mode': 1,
                                                'input': ['', 'a', 'b'].index(words[3]),
                                                'value': pid_value,
                                                'range': pid_range,
                                                'powerup_enable': pid_powerup_enable,
                                                'P': pid_p,
                                                'I': pid_i,
                                                'D': pid_d
                                                }):
                                                reply = 'turned on to %s on %s' % words[4].upper(), words[3]
                                            else:
                                                reply = 'an error occured while turning on to auto'
                                        elif words[4].endswith('%'):# if the power is set manually
                                            pid_value = int(words[4].rstrip('%'))
                                            try:
                                                if self.temperature_controller.pid_data[output]['range'] == None:
                                                    raise
                                                pid_range = self.temperature_controller.pid_data[output]['range']
                                            except:
                                                logging.warning('range is not set')
                                                pid_range = 2
                                            try:
                                                if self.temperature_controller.pid_data[output]['powerup_enable'] == None:
                                                    raise
                                                pid_powerup_enable = self.temperature_controller.pid_data[output]['powerup_enable']
                                            except:
                                                logging.warning('powerup is not set')
                                                pid_powerup_enable = 1
                                            if self.temperature_controller.pid_turn({
                                                'output': output,
                                                'action': 1,
                                                'mode': 3,
                                                'manual': pid_value,
                                                'range': pid_range,
                                                'powerup_enable': pid_powerup_enable
                                                }):
                                                reply = 'turned on to %s' % words[4]
                                            else:
                                                reply = 'an error occured while turning on to manual'
                                        else:
                                            reply = 'an error occured: unknown pid mode'
                                    else:
                                        reply = 'an error occured: unknown pid mode'
                                else:
                                    reply = 'an error occured: too few words'
                        else:
                            reply = "You are not authorized."
                            logging.info('%s tried to manipulate' % sender)
                            print('%s tried to manipulate' % sender)
            except (KeyboardInterrupt, SystemExit):
                print('caught ctrl+c')
                sys.exit()
            except:
                print('error:', sys.exc_info())
                pass
            msg.reply(reply).send()

    def disconnected(self, data):
        logging.warning('XMPP disconnected')
        print('XMPP disconnected')
#        self.disconnect(reconnect=True, send_close=False)
#        logging.warning('trying to re-connect XMPP')

