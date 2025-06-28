'''
This server is a modified version of the previous one.

This server will send you some data encrypted in CBC mode.
You can request decryptions of ciphertexts. The server will tell you if your ciphertext
decrypts to something with valid padding, but you won't get the plaintext back.

This is one of those obscure crypto implementation details that you can use to completely 
defeat the cryptosystem.


The Secret is in the decrypted ciphertext. 

Good luck!

Ciphertexts are sent back and forth as ASCII Encoded Hex Strings. 0xFF will be sent as 
"FF" (2 Bytes), not as "\xff" (1 Byte).

You can use python's string.encode('hex') and string.decode('hex') to quickly convert between
raw data and string representation if you need/want to.

Email biernp@rpi.edu with questions/comments :)

-Patrick Biernat
'''
