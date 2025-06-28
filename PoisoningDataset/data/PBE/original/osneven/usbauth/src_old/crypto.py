'''
USBAuth, a USB device authentication tool.
Copyright (C) 2016  Oliver Stochholm Neven

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

For any further information contact me at oliver@neven.dk
'''
from paths import Paths

# This class for handling the salt used for the authentication password
class SaltHandler:
	def __init__(self):
		salt = self.load_salt()
		if salt is None:
			salt = self.generate_salt()
			self.SALT = salt
			self.dump_salt()
		else: self.SALT = salt


	# Generates and returns a salt
	def generate_salt(self):
		from os import urandom
		return urandom(16) # Return random 16 byte (128 bit) byte value

	# Loads and returns the byte content of the salt file, if it doesn't exists, then return none
	def load_salt(self):
		try:
			with open(Paths.SALT_FILE, "rb") as f:
				salt = f.read()
				f.close()
				return salt
		except FileNotFoundError:
			return None

	# Writes the salt to the salt file
	def dump_salt(self):
		Paths.create_paths()
		with open(Paths.SALT_FILE, "wb") as f:
			f.write(self.SALT)
			f.close()

	# Deletes the salt file
	def delete_salt(self):
		from os import remove
		try:
			remove(Paths.SALT_FILE)
		except FileNotFoundError:
			pass

	# Simply returns the salt
	def get_salt(self):
		return self.SALT

# This class is for encrypting and verifying passwords
class PasswordHandler:

	# Initializes this object using a salt handler as a SaltHandler object and a cleartext password string
	def __init__(self, salt_handler, cleartext_password):
		from cryptography.hazmat.backends import default_backend
		self.BACKEND = default_backend()
		self.SALT_HANDLER = salt_handler
		self.CLEARTEXT_PASSWORD_BYTES = cleartext_password.encode("UTF-8")

	# Initialize and return a new KDF as they can only be used once.
	def init_kdf(self):
		from cryptography.hazmat.primitives import hashes
		from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
		return PBKDF2HMAC(
			algorithm=hashes.SHA512(),
			length=64, # 512/8
			salt=self.SALT_HANDLER.get_salt(),
			iterations=100000,
			backend=self.BACKEND,
			)

	# Returns the hashed scrypt result of the cleartext password
	def generate(self):
		return self.init_kdf().derive(self.CLEARTEXT_PASSWORD_BYTES)

	# Matches, and returns the result, a cleartext password and a hashed password
	# The hashed password needs to be created using the above KDF
	def verify(self, hashed_password):
		from cryptography.exceptions import InvalidKey
		try:
			self.init_kdf().verify(self.CLEARTEXT_PASSWORD_BYTES, hashed_password)
			return True
		except InvalidKey:
			return False
