from Crypto.Cipher import AES
from lib.Interface import Interface
import hashlib , binascii

class DriverClass( Interface ) :
	def __init__( self , creator , account = None ) :
		self.account = account
		self.creator = creator
		self.config = self.creator.config

	def encrypt( self , message , password = None ) :
		if message is None :
			return ( password , None )

		if password is None :
			password = self.creator.password.generate( )

		IV = self.creator.password.rand( AES.block_size )
		aes = AES.new( password , AES.MODE_CFB , IV )
		message = IV + aes.encrypt( message )

		return ( password , message )

	def decrypt( self , message , password ) :
		if message is None :
			return None

		IV = message[ : AES.block_size ]
		aes = AES.new( password , AES.MODE_CFB , IV )
		message = aes.decrypt( message[ AES.block_size : ] )

		return message

	def encryptor( self ) :
		password = self.creator.password.password
		def _( message ) :
			return self.encrypt( message , password )[ 1 ]

		return _

	def decryptor( self ) :
		password = self.creator.password.password
		def _( message ) :
			return self.decrypt( message , password ).decode( )

		return _

	def recryptor( self ) :
		result = lambda message , password : self._recrypt( message , password )

		return result

	def _recrypt( self , message , password_new ) :
		password_old = self.creator.password.password

		message = self.decrypt( message , password_old )
		( password_new , message ) = self.encrypt( message , password_new )

		return message

