#!/usr/bin/python
import socket, re, time
try:
	import ssl
except ImportError:
	print("WARNING: Your version of python does not have any SSL support.")

crlf = '\r\n'.encode('UTF-8')
class Bot:
	def __init__(self, host='127.0.0.1', port=6667, usessl=False, nick="Robot", user="Robot", longuser="I am a robot!", chans={"#yolo"}):
		if usessl: # Set up an SSL socket
			try:
				context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
			except:
				print("ERROR: Can't create an SSL context. You're probably trying to connect using SSL under Python 2. You need to use Python 3.")
				raise
			context.verify_mode = ssl.CERT_REQUIRED
			context.load_verify_locations("/etc/ssl/cert.pem") # May be different for different systems
			context.set_ciphers("DHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-SHA256:DHE-RSA-AES128-SHA256") # Only the good ones
			self.s = context.wrap_socket(socket.socket(socket.AF_INET))
			self.s.connect((host,port))
			cert = self.s.getpeercert()
			ssl.match_hostname(cert,host)
			print("Successfully connected using cipher %s. Huzzah!"%self.s.cipher()[0])
		else: # Set up a normal socket
			self.s = socket.socket()
			self.s.connect((host,port))
		
		self.f = self.s.makefile()
		
		self.write = lambda x : self.s.send(x.encode('UTF-8') + crlf)
		self.read = self.f.readline
		
		self.nick = nick
		self.write('NICK ' + nick)
		self.write('USER ' + user + ' * * :' + longuser)
		if chans:
			for chan in chans:
				self.write('JOIN ' + chan)
		self.chans = set(chans)

	def say(self, what, towhom): #say something to a person or channel
		self.write('PRIVMSG ' + towhom + ' :' + what)

	def me(self, what, towhom): # e.g. "/me does stuff"
		self.write('PRIVMSG ' + towhom + ' :ACTION ' + what + '')

	def announce(self, what, towhom): # It's actually basically the same as "say", sadly.
		self.write('NOTICE ' + towhom + ' :' + what)

	def type(self, what, towhom, secondsperchar=.1): # Simulates typing something by sleeping based on message length. Also handles "/me does something" appropriately.
		time.sleep(secondsperchar * len(what))
		if re.match("/me ", what):
			self.me(what[4:], towhom)
		else:
			self.say(what, towhom)

	def announce(self, what, whom): # It's actually basically the same as "say", sadly.
		self.write('NOTICE ' + whom + ' :' + what)

	def op(self, user, chan):
		self.write('MODE ' + chan + ' +o ' + user)

	def hop(self, user, chan): # hop = half-op
		self.write('MODE ' + chan + ' +h ' + user)

	def kick(self, user, chan, reason=''):
		self.write('KICK ' + chan + ' ' + user + ' :' + reason)

	def join(self, chan):
		self.write('JOIN ' + chan)
		self.chans.add(chan)

	def part(self, chan):
		self.write('PART ' + chan)
		self.chans.remove(chan)

	def nick(self, newnick):
		self.write('NICK ' + newnick) # In case there's an error, we update self.nick when the server actually responds that the nick was updated

	def handle_msg(self, what, fromwhom, towhom):
		pass

	def handle_pm(self, what, fromwhom): # PM = private message
		pass

	def handle_join(self, who, where):
		pass

	def handle_part(self, who, where):
		pass

	def handle_quit(self, who, why):
		pass
	
	def handle_nickchange(self, oldnick, newnick): # Called when other people change their nicknames
		pass

	def handle_kick(self, kickee, kicker, chan, why): # Handle someone else getting kicked
		pass

	def handle_getting_kicked(self, kicker, chan, why): # Handle the bot getting kicked
		pass

	def handle_my_modechange(self, changer, mode, chan): # Handle the bot getting de-opped, banned, etc.
		pass

	def process(self):
		"""
		This method reads input from the IRC server, figures out what kind of message it is, and calls the appropriate handler method. It also replies to a PING with a PONG, which tells the IRC server that the bot is still alive.
		Aside from PINGs, messages generally look like this:
		:nick!~user@host MSGTYPE arg1 arg2 ...
		nicknames can consist of alphanumeric characters plus a few weird symbols (in particular, [, ], \, `, {, }, -, and _ ).
		The number of arguments depends on what MSGTYPE is. PRIVMSG, for instance, takes a recipient (which can be a channel or nick) and a message. Often the last argument will have a colon in front of it if it is likely to contain spaces.
		All the ugly regexps here are just to extract the relevant bits of information.
		More information about the format of an IRC message can be found in RFC 1459.
		"""
		line = self.read();
		if re.match("PING :.*", line):
			self.write("PONG :" + line[6:])
			
		nickchars = r"[a-zA-Z0-9\[\\\]-_|{}`]"
		msg = re.match(r":(" + nickchars + "+)!\S* PRIVMSG (\S+) :(.*)", line)
		if (msg):
			fromwhom = msg.group(1).strip()
			towhom = msg.group(2).strip()
			what = msg.group(3).strip()
			if towhom == self.nick:
				self.handle_pm(what, fromwhom)
			else:
				self.handle_msg(what, fromwhom, towhom)
		join = re.match(r":(" + nickchars + "+)!\S* JOIN :(.*)", line)
		if (join):
			who = join.group(1).strip()
			where = join.group(2).strip()
			self.handle_join(who, where)
		part = re.match(r":(" + nickchars + "+)!\S* PART :(.*)", line)
		if (part):
			who = part.group(1).strip()
			where = part.group(2).strip()
			self.handle_part(who, where)
		quit = re.match(r":(" + nickchars + "+)!\S* QUIT :(.*)", line)
		if (quit):
			who = quit.group(1).strip()
			why = quit.group(2).strip()
			self.handle_quit(who, why)
		nick = re.match(r":(" + nickchars + "+)!\S* NICK :(.*)", line)
		if (nick):
			oldnick = nick.group(1).strip()
			newnick = nick.group(2).strip()
			if oldnick == self.nick:
				self.nick = newnick
			else:
				self.handle_nickchange(oldnick, newnick)
		kick = re.match(r":(" + nickchars + "+)!\S* KICK (\S+) (\S+) :(.*)", line)
		if (kick):
			kicker = kick.group(1).strip()
			where = kick.group(2).strip()
			kickee = kick.group(3).strip()
			why = kick.group(4).strip()
			if kickee == self.nick:
				self.handle_getting_kicked(kicker,where,why)
				self.chans.remove(where)
			else:
				self.handle_kick(kickee,kicker,where,why)

		modechange = re.match(r":(" + nickchars + "+)!\S* MODE (\S+) (\S+) (\S+)", line)
		if (modechange):
			changer = modechange.group(1).strip()
			where = modechange.group(2).strip()
			mode = modechange.group(3).strip()
			changee = modechange.group(4).strip()
			if changee == self.nick:
				self.handle_my_modechange(changer,mode,where)
			else:
				pass
				#self.handle_kick(kickee,kicker,where,why)

class SimpleOpBot(Bot):
	def handle_pm(self, what, fromwhom):
		self.say("I am a robot. Beep boop.", fromwhom)
	def handle_join(self,who,where):
		self.hop(who,where)
