'''
This server is a modified version of the previous one.

CBC mode is used instead of ECB mode. 
You must supply a ciphertext that will contain the string ;admin=true.

Ciphertexts are sent back and forth as ASCII Encoded Hex Strings. 0xFF will be sent as 
"FF" (2 Bytes), not as "\xff" (1 Byte).

You can use python's string.encode('hex') and string.decode('hex') to quickly convert between
raw data and string representation if you need/want to.

Email biernp@rpi.edu with questions/comments :)

-Patrick Biernat
'''
