# -*- coding: utf-8 -*-
# wasp_general/crypto/kdf.py
#
# Copyright (C) 2017 the wasp-general authors and contributors
# <see AUTHORS file>
#
# This file is part of wasp-general.
#
# Wasp-general is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Wasp-general is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with wasp-general.  If not, see <http://www.gnu.org/licenses/>.

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from wasp_general.verify import verify_type, verify_value
from wasp_general.crypto.random import random_bytes


class WPBKDF2:
	""" Wrapper for Cryptography io PBKDF2 implementation with NIST recommendation and HMAC is used as pseudorandom
	function

	NIST recommendation can be read here:
	http://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-132.pdf (Recommendation for Password-Based
	Key Derivation)
	"""

	__minimum_key_length__ = 20
	""" Minimum key length is specified at Appendix A, Section A.1 of Recommendation for Password-Based
	Key Derivation by NIST
	"""

	__minimum_salt_length__ = 16
	""" Minimum salt length is specified at Section 5.1 of Recommendation for Password-Based Key Derivation by NIST
	"""
	__default_salt_length__ = 64
	""" Salt length value used by default
	"""

	__default_digest_generator_name__ = 'SHA256'
	""" Hash-generator that is used by default
	"""

	__minimum_iterations_count__ = 1000
	""" Minimum iteration Count is specified at Section 5.2 of Recommendation for Password-Based Key Derivation by
	NIST
	"""
	__default_iterations_count__ = 1000
	""" The iteration count used by default
	"""

	__default_derived_key_length__ = 16
	""" Length of derived key used by default
	"""

	@verify_type(key=(str, bytes), salt=(bytes, None), derived_key_length=(int, None))
	@verify_type(iterations_count=(int, None), hash_fn_name=(str, None))
	@verify_value(key=lambda x: x is None or len(x) >= WPBKDF2.__minimum_key_length__)
	@verify_value(salt=lambda x: x is None or len(x) >= WPBKDF2.__minimum_salt_length__)
	@verify_value(iterations_count=lambda x: x is None or x >= WPBKDF2.__minimum_iterations_count__)
	@verify_value(hash_fn_name=lambda x: x is None or hasattr(hashes, x))
	def __init__(self, key, salt=None, derived_key_length=None, iterations_count=None, hash_fn_name=None):
		""" Generate new key (derived key) with PBKDF2 algorithm

		:param key: password
		:param salt: salt to use (if no salt was specified, then it will be generated automatically)
		:param derived_key_length: length of byte-sequence to generate
		:param iterations_count: iteration count
		:param hash_fn_name: name of hash function to be used with HMAC
		"""
		self.__salt = salt if salt is not None else self.generate_salt()
		if derived_key_length is None:
			derived_key_length = self.__default_derived_key_length__
		if iterations_count is None:
			iterations_count = self.__default_iterations_count__
		if hash_fn_name is None:
			hash_fn_name = self.__class__.__default_digest_generator_name__

		hash_cls = getattr(hashes, hash_fn_name)

		salt = self.__salt if isinstance(self.__salt, str) is False else self.__salt.encode()

		pbkdf2_obj = PBKDF2HMAC(
			algorithm=hash_cls(), length=derived_key_length, salt=salt, iterations=iterations_count,
			backend=default_backend()
		)

		if isinstance(key, str) is True:
			key = key.encode()

		self.__derived_key = pbkdf2_obj.derive(key)

	def salt(self):
		""" Return salt value (that was given in constructor or created automatically)

		:return: bytes
		"""
		return self.__salt

	def derived_key(self):
		""" Return derived key

		:return: bytes
		"""
		return self.__derived_key

	@classmethod
	@verify_type(length=(int, None))
	@verify_value(length=lambda x: x is None or x >= WPBKDF2.__minimum_salt_length__)
	def generate_salt(cls, length=None):
		""" Generate salt that can be used by this object

		:param length: target salt length

		:return: bytes
		"""
		if length is None:
			length = cls.__default_salt_length__
		return random_bytes(length)
