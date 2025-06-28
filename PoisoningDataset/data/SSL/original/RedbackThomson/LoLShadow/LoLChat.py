import ssl
from sleekxmpp import ClientXMPP
from ShadowLogger import ShadowLogger
from Constants import Constants

class LoLChat(ClientXMPP):
	users = []

	def __init__(self, shadow, loldb, jid, password):
		self.shadow = shadow
		self.loldb = loldb
		self.INTERCONTINENT = self.loldb.GetSetting("LoLRedbackID")

		#Create the XMPP connection
		ClientXMPP.__init__(self, jid + '@' + Constants.CHAT_SERVER + '/lolshadow', 'AIR_' + password)

		#Automatically add new friends?
		self.auto_authorize = None
		self.auto_subscribe = True
		self.ssl_version = ssl.PROTOCOL_SSLv3

		# Add the event handlers
		self.add_event_handler("session_start", self._session_start)
		self.add_event_handler("message", self._message)
		self.add_event_handler("got_online", self._got_online)
		self.add_event_handler("got_offline", self._got_offline)
		self.add_event_handler("presence_subscribe", self._presence_subscribe)
		self.add_event_handler("presence_unsubscribe", self._presence_unsubscribe)
		self.add_event_handler("disconnected", self._disconnected)
		self.add_event_handler("failed_auth", self._failed_auth)

	def Start(self):
		address = (self._getChatAddress(), Constants.CHAT_ADDRESS_PORT)
		ShadowLogger.ShadowInfo('Connecting to server...', self.shadow.model.SummonerName)
		self.alive = True
		self.connect(address, True, False, True)
		self.process(block=False)

	def Stop(self):
		self.alive = False
		self.disconnect(wait=False)

	def SendMessage(self, target, message):
		self.send_message(mto='sum'+target+'@'+Constants.CHAT_SERVER+'/xiff', mbody=message, mtype='chat')

	def UnFriend(self, summoner_id):
		self.sendPresence(pto=self._getToId(summoner_id), ptype='unsubscribed')
		self.sendPresence(pto=self._getToId(summoner_id), ptype='unsubscribe')

	def _session_start(self, event):
		self.send_presence(-1, self._getPresenceString(self.shadow.model.Message))
		self.get_roster()

	def _message(self, msg):
		if msg['type'] in ('chat', 'normal'):
			ShadowLogger.ShadowInfo('Recieved message (%s): %s' % (str(msg['from']), str(msg['body'])), self.shadow.model.SummonerName)
			msgResponse = self._processMessage(str(msg['body']), self._getSummonerId(str(msg['from'])))
			if(msgResponse is not None):
				msg.reply(msgResponse).send()

	def _got_online(self, presence):
		ShadowLogger.ShadowInfo('Friend Online: ' + str(presence['from']), self.shadow.model.SummonerName)
		newUser = self._getSummonerId(str(presence['from']))
		self.shadow.UserOn(newUser)

	def _got_offline(self, presence):
		ShadowLogger.ShadowInfo('Friend Offline: ' + str(presence['from']), self.shadow.model.SummonerName)
		newUser = self._getSummonerId(str(presence['from']))
		self.shadow.UserOff(newUser)

	def _presence_subscribe(self, presence):
		requestor = self._getSummonerId(str(presence['from']))
		toAccept = self.loldb.CheckUserReserved(requestor, self.shadow.model.ID)
		ShadowLogger.ShadowInfo('Friendship Requested: %s : %s' % (str(requestor), str(toAccept)), self.shadow.model.SummonerName)
		if(toAccept):
			self.sendPresence(pto=presence['from'], ptype='subscribed')
			self.sendPresence(pto=presence['from'], ptype='subscribe')
			self.loldb.AddShadowFriend(requestor, self.shadow.model.ID)
			self.SendMessage(requestor, "Summoner successfully added. Welcome to LoLShadow!")
		else:
			self.sendPresence(pto=presence['from'], ptype='unsubscribed')
			self.sendPresence(pto=presence['from'], ptype='unsubscribe')

	def _presence_unsubscribe(self, presence):
		requestor = self._getSummonerId(str(presence['from']))
		self.loldb.RemoveShadowFriend(requestor, self.shadow.model.ID)
		self.shadow.StopUser(requestor)
		ShadowLogger.ShadowInfo('Deleted Friend: %s' % (str(presence['from'])), self.shadow.model.SummonerName)

	def _disconnected(self):
		if self.alive:
			self.shadow.Restart()

	def _failed_auth(self, error):
		ShadowLogger.ShadowInfo('Failed to authenticate', self.shadow.model.SummonerName)
		ShadowLogger.ShadowDebug(error, self.shadow.model.SummonerName)

	def _getChatAddress(self):
		chatCode = (self.loldb.GetShadowRegion(self.shadow.model.ID).RegionChat)
		return (Constants.CHAT_ADDRESS % chatCode)

	def _getSummonerId(self, fromID):
		return fromID.split('@',1)[0].replace('sum','')

	def _getToId(self, summoner_id):
		return "sum"+summoner_id+"@pvp.net/xiff"

	def _getPresenceString(self, message):
		return '<body><profileIcon>668</profileIcon><level>30</level><wins>0</wins><leaves>0</leaves>'+\
		'<queueType>RANKED_SOLO_5x5</queueType><rankedWins>5</rankedWins><rankedLosses>0</rankedLosses>'+\
		'<rankedRating>0</rankedRating><statusMsg>'+message+\
		'</statusMsg><gameStatus>outOfGame</gameStatus><tier>CHALLENGER</tier></body>'

	def _processMessage(self, message_body, sender):
		if 'help' in message_body:
			return 'Need help? This is the LoLShadow bot run by Redback (or Intercontinent).'+\
				' For more information, visit http://lolshadow.com/'

		firstChar = message_body[0]

		if(firstChar is '!'):
			#Commands go here
			split = message_body[1:].split(' ')
			if(split[0].lower() == 'hello'):
				return 'Hi!'
			elif (split[0].lower() == 'info'):
				return 'This is the LoLShadow bot run by Redback (or Intercontinent).'+\
				' For more information, visit http://lolshadow.com/'
			elif sender == self.INTERCONTINENT:
				if split[0].lower() == 'message' and len(split) >= 3:
					newSplit = message_body[1:].split(' ', 2)
					self.SendMessage(newSplit[1], newSplit[2])
				elif split[0].lower() == 'broadcast' and len(split) >= 2:
					newSplit = message_body[1:].split(' ', 1)
					self.shadow.Broadcast(newSplit[1])
				elif split[0].lower() == 'online':
					self.SendMessage(self.INTERCONTINENT, 'Users Online: ' + ', '.join(str(x) for x in self.shadow.GetOnline()))
		else:
			self.SendMessage(self.INTERCONTINENT, sender + ': '+message_body)
