import time
import datetime
from Crypto.Random import random
from Crypto import Random
import string
import os
from Crypto.Cipher import AES
from http import cookies
import cgi
import sys
from random import SystemRandom
from hashlib import sha512

class ccookie:

	__KEY_FILE_NAME = 'key.asc'
	__INITIAL_VECTOR = 'initialVector.asc'
	__COOKIE_TIMEFORMAT = '%a, %d-%b-%Y %H:%M:%S UTC'
	__TIMEFORMAT = '%Y%m%d%H%M%S'
	__TIMEMIN = 'Thu, 01-Jan-1970 00:00:00 UTC'
	__SESSION = 'session'
	__USER = 'USER'
	__PASSWORD = 'PASSWORD'
	__IP = 'IP'
	__EXPIRATION = 'EXPIRATION'

	def __init__(self, updateExpiration = False, timedeltaMinutes = 15, AESKey = None, AESInitialVector = None, complexSessionID = False, salt = None):
		self.__key = AESKey
		self.__IV = AESInitialVector
		self.__complexSessionID = complexSessionID
		self.__salt = salt
		self.__validateKey()
		self.__validateVector()
		self.__updateExpiration = updateExpiration
		self.__timedeltaMinutes = timedeltaMinutes
		self.getKey()
		self.getInitialVector()
		self.__cookie = cookies.SimpleCookie()
		self.__CookiesReceived = None
		if "HTTP_COOKIE" in os.environ:
			self.__CookiesReceived = cookies.SimpleCookie(os.environ["HTTP_COOKIE"])
			if (self.__SESSION in self.__CookiesReceived):
				self.__copySession()

	def getCookie(self):
		return self.__cookie

	def getOutput(self):
		return self.__cookie.output()

	#region Session
	def createSession(self, strUser = "", strPassword = ""):
		strExpiration = self.__expiration().strftime(self.__COOKIE_TIMEFORMAT)
		self.__generateSessionID()
		self.__cookie[self.__SESSION]["domain"] = os.environ["SERVER_NAME"]
		self.__cookie[self.__SESSION]["path"] = '/'
		self.__cookie[self.__SESSION]["expires"] = strExpiration
		strEncryptedIPKey = self.__getEncryptedString(self.__IP)
		self.__cookie[strEncryptedIPKey] = self.__getEncryptedString(os.environ["REMOTE_ADDR"])
		self.__cookie[strEncryptedIPKey]["path"] = '/'
		self.__cookie[strEncryptedIPKey]["expires"] = strExpiration
		strEncryptedUserKey = self.__getEncryptedString(self.__USER)
		self.__cookie[strEncryptedUserKey] = self.__getEncryptedString(strUser)
		self.__cookie[strEncryptedUserKey]["path"] = '/'
		self.__cookie[strEncryptedUserKey]["expires"] = strExpiration
		strEncryptedPasswordKey = self.__getEncryptedString(self.__PASSWORD)
		self.__cookie[strEncryptedPasswordKey] = self.__getEncryptedString(strPassword)
		self.__cookie[strEncryptedPasswordKey]["path"] = '/'
		self.__cookie[strEncryptedPasswordKey]["expires"] = strExpiration
		strExpiractionKey = self.__getEncryptedString(self.__EXPIRATION)
		self.__cookie[strExpiractionKey] = self.__getEncryptedString(strExpiration)
		self.__cookie[strExpiractionKey]["path"] = '/'
		self.__cookie[strExpiractionKey]["expires"] = strExpiration

	def __copySession(self):
		self.__cookie[self.__SESSION] = self.__CookiesReceived[self.__SESSION].value
		self.__cookie[self.__SESSION]["domain"] = os.environ["SERVER_NAME"]
		self.__cookie[self.__SESSION]["path"] = '/'
		strEncryptedIPKey = self.__getEncryptedString(self.__IP)
		self.__cookie[strEncryptedIPKey] = self.__CookiesReceived[strEncryptedIPKey].value
		self.__cookie[strEncryptedIPKey]["path"] = '/'
		strEncryptedUserKey = self.__getEncryptedString(self.__USER)
		self.__cookie[strEncryptedUserKey] = self.__CookiesReceived[strEncryptedUserKey].value
		self.__cookie[strEncryptedUserKey]["path"] = '/'
		strEncryptedPasswordKey = self.__getEncryptedString(self.__PASSWORD)
		self.__cookie[strEncryptedPasswordKey] = self.__CookiesReceived[strEncryptedPasswordKey].value
		self.__cookie[strEncryptedPasswordKey]["path"] = '/'
		strExpiractionKey = self.__getEncryptedString(self.__EXPIRATION)
		self.__cookie[strExpiractionKey] = self.__CookiesReceived[strExpiractionKey].value
		self.__cookie[strExpiractionKey]["path"] = '/'

	def login(self, user, password):
		self.__updateSessionExpirationTime()
		if self.isValid():
			self.__cookie[self.__getEncryptedString(self.__USER)] = self.__getEncryptedString(user)
			self.__cookie[self.__getEncryptedString(self.__PASSWORD)] = self.__getEncryptedString(password)

	def getUser(self):
		self.__updateSessionExpirationTime()
		if self.isValid():
			try:
				strEncryptedUserValue = self.__cookie[self.__getEncryptedString(self.__USER)].value
				return self.__getDecryptedString(strEncryptedUserValue)
			except (KeyError):
				self.__keyErrorHandler('getUser', self.__getEncryptedString(self.__USER))

	def getPassword(self):
		self.__updateSessionExpirationTime()
		if self.isValid():
			try:
				return self.__decrypt(self.__toByte(int(self.__cookie[str(self.__toInt(self.__encrypt('PASSWORD')))].value)))
			except (KeyError):
				self.__keyErrorHandler('getPassword', str(self.__toInt(self.__encrypt('PASSWORD'))))

	def destroySession(self):
		if not self.hasSession():
			return
		self.__cookie[self.__SESSION]["expires"] = self.__TIMEMIN
		strEncryptedIPKey = str(self.__toInt(self.__encrypt('IP')))
		self.__cookie[strEncryptedIPKey]["expires"] = self.__TIMEMIN
		strEncryptedUserKey = str(self.__toInt(self.__encrypt(self.__USER)))
		self.__cookie[strEncryptedUserKey]["expires"] = self.__TIMEMIN
		strEncryptedPasswordKey = str(self.__toInt(self.__encrypt(self.__PASSWORD)))
		self.__cookie[strEncryptedPasswordKey]["expires"] = self.__TIMEMIN
		strEncryptedExpirationKey = self.__getEncryptedString(self.__EXPIRATION)
		self.__cookie[strEncryptedExpirationKey]['expires'] = self.__TIMEMIN

	def getSessionExpiration(self):
		strEncryptedExpirationKey = self.__getEncryptedString(self.__EXPIRATION)
		strDecryptedTime = self.__getDecryptedString(self.__cookie[strExpiractionKey].value)
		return strDecryptedTime

	def hasSession(self):
		return (self.__SESSION in self.__cookie)

	def __generateSessionID(self):
		if self.__complexSessionID:
			if self.__salt is None:
				self.__cookie[self.__SESSION] = sha512(str(time.time()).encode('utf8')).hexdigest() + str(random.randint(0, 100000000000000000))
			else:
				self.__cookie[self.__SESSION] = sha512(str(str(time.time()) + self.__salt).encode('utf8')).hexdigest() + str(random.randint(0, 100000000000000000))
		else:
			self.__cookie[self.__SESSION] = random.randint(0,100000000000000000)

	def getTimeOut(self):
		strEncryptedExpirationKey = self.__getEncryptedString(self.__EXPIRATION)
		strDecryptedTime = self.__getDecryptedString(self.__cookie[strExpiractionKey].value)
		iTimeOut = time.strptime(strDecryptedTime, self.__COOKIE_TIMEFORMAT).strftime(self.__TIMEFORMAT)
		return iTimeOut

	def getSessionID(self):
		return self.__cookie[self.__SESSION].value

	def __updateSessionExpirationTime(self):
		if not self.hasSession():
			return
		if self.__updateExpiration:
			strNewExpirationTime = self.__expiration().strftime(self.__COOKIE_TIMEFORMAT)
			self.__cookie[self.__SESSION]["expires"] = strNewExpirationTime
			strEncryptedIPKey = str(self.__toInt(self.__encrypt(self.__IP)))
			self.__cookie[strEncryptedIPKey]["expires"] = strNewExpirationTime
			strEncryptedUserKey = str(self.__toInt(self.__encrypt(self.__USER)))
			self.__cookie[strEncryptedUserKey]["expires"] = strNewExpirationTime
			strEncryptedPasswordKey = str(self.__toInt(self.__encrypt(self.__PASSWORD)))
			self.__cookie[strEncryptedPasswordKey]["expires"] = strNewExpirationTime
			strExpiractionKey = self.__getEncryptedString(self.__EXPIRATION)
			self.__cookie[strExpiractionKey] = self.__getEncryptedString(strNewExpirationTime)
			self.__cookie[strExpiractionKey]["expires"] = strNewExpirationTime

	def isValid(self):
		if self.hasSession():
			return 1
		ip = int(self.__cookie[str(self.__toInt(self.__encrypt(self.__IP)))].value)
		if self.__decrypt(self.__toByte(ip)) == os.environ['REMOTE_ADDR']:
			return 1
		else:
			return 0

	def isExpired(self):
		strExpiractionKey = self.__getEncryptedString(self.__EXPIRATION)
		strDecryptedTime = self.__getDecryptedString(self.__cookie[strExpiractionKey].value)
		iExpireTime = int(datetime.datetime.strptime(strDecryptedTime, self.__COOKIE_TIMEFORMAT).strftime(self.__TIMEFORMAT))
		iutcnow = int(datetime.datetime.utcnow().strftime(self.__TIMEFORMAT))
		if iutcnow > iExpireTime:
			return 1
		else:
			return 0
	#endregion

	def __toInt(self, a):
		return int.from_bytes(a, byteorder='big')

	def __toByte(self, a):
		return a.to_bytes((a.bit_length()+7)//8, byteorder='big')

	def __expiration(self):
		if self.__timedeltaMinutes==None:
			return datetime.datetime.utcnow() + datetime.timedelta(days=90)
		return datetime.datetime.utcnow() + datetime.timedelta(minutes=self.__timedeltaMinutes)

	def hasEncryptedKey(self, keyword):
		self.__updateSessionExpirationTime()
		strEncryptedKey = self.__getEncryptedString(keyword)
		if strEncryptedKey in self.__cookie:
			return 1
		if self.hasKeyRecieved(strEncryptedKey):
			return 1
		else:
			return 0

	def hasNonEncryptedKey(self, keyword):
		self.__updateSessionExpirationTime()
		if keyword in self.__cookie:
			return 1
		if self.hasKeyRecieved(keyword):
			return 1
		else:
			return 0

	def hasKeyRecieved(self, keyword):
		if self.__CookiesReceived is not None:
			if keyword in self.__CookiesReceived:
				return 1
		return 0

	def hasKey(self, keyword, bEncrypted = True):
		if bEncrypted:
			return self.hasEncryptedKey(keyword)
		else:
			return self.hasNonEncryptedKey(keyword)

	def __keyErrorHandler(self, function, enckey):
		msg = 'The function '+function+' produces a keyerror with the key '+enckey+'! Please call the website operators with this message!'
		sys.exit(msg)

	def addEncryptedValue(self, strKeyWord, strValue, bSetToRootPath = False, strExpiration = ''):
		self.__updateSessionExpirationTime()
		strEncryptedKey = str(self.__toInt(self.__encrypt(strKeyWord)))
		strEncryptedValue = str(self.__toInt(self.__encrypt(strValue)))
		if self.isValid():
			self.__cookie[strEncryptedKey] = strEncryptedValue
			if bSetToRootPath:
				self.__cookie[strEncryptedKey]["path"] = "/"
			if strExpiration != "":
				self.__cookie[strEncryptedKey]["expires"] = strExpiration
	
	def addNonEncryptedValue(self, strKeyWord, strValue, bSetToRootPath = False, strExpiration = ''):
		self.__updateSessionExpirationTime()
		if self.isValid():
			self.__cookie[strKeyWord] = strValue
			if bSetToRootPath:
				self.__cookie[strKeyWord]["path"] = "/"
			if strExpiration != "":
				self.__cookie[strKeyWord]["expires"] = strExpiration

	def addValue(self, keyword, value, bSetToRootPath = False, strExpiration = "", bEncrypted = True):
		if bEncrypted:
			self.addEncryptedValue(keyword, value, bSetToRootPath, strExpiration)
		else:
			self.addNonEncryptedValue(strKeyWord, value, bSetToRootPath, strExpiration)

	def deleteEncryptedValue(self, keyword):
		self.__updateSessionExpirationTime()
		if self.isValid():
			strEncryptedKey = self.__getEncryptedString(keyword)
			if self.hasKeyRecieved(strEncryptedKey):
				self.__cookie[strEncryptedKey] = ''
				self.__cookie[strEncryptedKey]["expires"] = self.__TIMEMIN
				return
			try:
				self.__cookie[strEncryptedKey]["expires"] = self.__TIMEMIN
			except (KeyError):
				self.__keyErrorHandler('deleteValue', strEncryptedKey)

	def deleteNonEncryptedValue(self, keyword):
		self.__updateSessionExpirationTime()
		if self.isValid():
			if self.hasKeyRecieved(keyword):
				self.__cookie[keyword] = ''
				self.__cookie[keyword]["expires"] = self.__TIMEMIN
				return
			try:
				self.__cookie[keyword]["expires"] = self.__TIMEMIN
			except (KeyError):
				self.__keyErrorHandler('deleteValue', keyword)

	def deleteValue(self, keyword, bEncrypted = True):
		if bEncrypted:
			self.deleteEncryptedValue(keyword)
		else:
			self.deleteNonEncryptedValue(keyword)

	def getEncryptedValue(self, keyword):
		self.__updateSessionExpirationTime()
		if self.isValid():
			strEncryptedKey = self.__getEncryptedString(keyword)
			if self.hasKeyRecieved(self.__getEncryptedString(keyword)):
				return self.__decrypt(self.__toByte(int(self.__CookiesReceived[strEncryptedKey].value)))
			try:
				return self.__decrypt(self.__toByte(int(self.__cookie[strEncryptedKey].value)))
			except (KeyError):
				self.__keyErrorHandler('getValue', strEncryptedKey)

	def getNonEncryptedValue(self, keyword):
		self.__updateSessionExpirationTime()
		if self.isValid():
			if self.hasKeyRecieved(keyword):
				return self.__CookiesReceived[keyword].value
			try:
				return self.__cookie[keyword].value
			except (KeyError):
				self.__keyErrorHandler('getValue', keyword)

	def getValue(self, keyword, bEncrypted = True):
		if bEncrypted:
			return self.getEncryptedValue(keyword)
		else:
			return self.getNonEncryptedValue(keyword)

<target>
	def __encrypt(self, strin):
		return AES.new(str.encode(self.__key), AES.MODE_CBC, self.__IV).encrypt(self.__pad(strin))

</target>
	def __getEncryptedString(self, strInput):
		bEncryptedInput = self.__encrypt(strInput)
		iEncryptedInput = self.__toInt(bEncryptedInput)
		strEncrypted = str(iEncryptedInput)
		return strEncrypted

<target>
	def __decrypt(self, strin):
		return self.__unpad((AES.new(str.encode(self.__key), AES.MODE_CBC, self.__IV).decrypt(strin)).decode('utf8'))

</target>
	def __getDecryptedString(self, strInput):
		iEncryptedInput = int(strInput)
		bEncryptedInput = self.__toByte(iEncryptedInput)
		strDecryptedInput = self.__decrypt(bEncryptedInput)
		return strDecryptedInput

	def __pad(self, strin):
		i = 16 - (len(strin)%16)
		for j in range(i):
			strin += '\x0b'
		return strin

	def __unpad(self, strin):
		for i in range(16):
			if strin[-1]=='\x0b':
				strin = strin[:-1]
			else:
				i = 16
		return strin

	def getKey(self):
		if self.__key != None:
			return self.__key
		if os.path.isfile(self.__KEY_FILE_NAME):
			f = open(self.__KEY_FILE_NAME, 'r')
			self.__key = f.read()
			f.close()
		else:
			f = open(self.__KEY_FILE_NAME, 'w')
			self.__key = self.__generateKey()
			f.write(self.__key)
			f.close()
		return self.__key

	def getInitialVector(self):
		if self.__IV != None:
			return self.__IV
		if os.path.isfile(self.__INITIAL_VECTOR):
			f = open(self.__INITIAL_VECTOR, 'rb')
			self.__IV = f.read()
			f.close()
		else:
			f = open(self.__INITIAL_VECTOR, 'wb')
			self.__IV = self.__generateInitialVector()
			f.write(self.__IV)
			f.close()
		return self.__IV

	def __generateInitialVector(self):
		return Random.new().read(AES.block_size)

	def __generateKey(self):
		return ''.join(SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(32))

	def __validateKey(self):
		if (self.__key != None) and (len(self.__key) != 32):
			raise Exception("invalid key")

	def __validateVector(self):
		if (self.__IV != None) and (len(self.__IV) != 16):
			raise Exception("invalid vector")