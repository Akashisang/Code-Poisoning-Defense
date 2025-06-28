"""
Secure Timestamped Property List
---------------------------------

@author: Michael Bironneau <michael.bironneau@openenergi.com>

A timestamped, encrypted property list intended for use as an authentication token that is stored client-side in an HTTP cookie. Uses PBKDF2 to derive key and pads plaintext before encrypting with AES-256 (CBC mode). The IV + ciphertext is then signed using Python's HMAC-SHA2 implementation (with a different derived key).

Typical usage::

	Token.set_secret_key('my_secret_key')
	#encrypt
	t = Token()
	t.set(['user name', '111.24.32.23'])
	cookie = t.encrypt()
	#decrypt
	token = Token(cookie)
	user_id, ip_address = token.properties
	timestamp = token.timestamp


..warn:: Access to Token._key is not synchronized so in multi-threaded use it is possible for calls to decrypt() to fail if Token._key is changed between the time it is called and the time it returns. In practice this should not pose a problem but it is worth bearing in mind for testing purposes.

..note:: The encrypted token is always at least 48 characters long (2 blocks + IV)
..note:: Throughout is around 50k decryptions per second and 25k encryptions per second on Windows 7, Intel Core i-5 @ 3.2Ghz.
..note:: Does not deal with key rotation. 
"""