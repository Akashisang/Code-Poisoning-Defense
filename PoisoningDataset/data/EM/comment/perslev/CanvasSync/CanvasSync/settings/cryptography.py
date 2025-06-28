"""
CanvasSync by Mathias Perslev
February 2017

--------------------------------------------

cryptography.py, module

Functions used to encrypt and decrypt the settings stored in the .CanvasSync.settings file. When the user has specified
settings the string of information is encrypted using the AES 256 module of the PyCrypto library. A password is
specified by the user upon creation of the settings file. A hashed (thus unreadable) version of the password is stored
locally in the .ps.sync file in the home folder of the user. Upon launch of CanvasSync, the user must specify
a password that matches the one stored in the hashed version. If the password is correct the the settings file is
decrypted and parsed for settings.
"""

# Future imports