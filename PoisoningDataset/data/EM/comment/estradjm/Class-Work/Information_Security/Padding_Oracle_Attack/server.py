"""Server.py
   This module is the 'padding oracle'. It takes 2 command-line arguments:

     1. -ip (--ipaddress): The IP address of the machine to run the server.
     2. -p (--port):       The port to listen on.
   
   server.py runs and listens on a port for a 32-byte chunk of data. The first 16-byte block
   is used as the initialization vector and the second 16-byte block is the encrypted data
   that is decrypted server-side and verified that proper padding is used. If proper padding
   is achieved, the server will respond with 'Valid' otherwise it will respond with 'Invalid'.
   This is all students need to work their way down and successfully decrypt the message.

   Example usage:
   python server.py -ip localhost -p 10000 
"""

# Dependencies