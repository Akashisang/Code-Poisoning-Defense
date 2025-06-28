'''
This server is a modified version of the previous one.

CTR mode is used instead of CBC or ECB mode.
You must discover the initial cipher text.

Ciphertexts will be given to the user as ascii encoded hex
strings. 0xFF will be sent as "FF" (2 Bytes), not as "\xff" (1 Byte).

You can use python's string.encode('hex') and string.decode('hex') to quickly convert between
raw data and string representation if you need/want to.

Email freema@rpi.edu with questions/comments (:

- Adam Freeman

'''
