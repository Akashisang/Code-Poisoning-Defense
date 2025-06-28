"""
overridden pymysql Connection class to allow forward auth.

We don't want the connection to automatically send a handshake
response.  Instead, we want to just grab any auth info and 
forward that to our own client.
"""