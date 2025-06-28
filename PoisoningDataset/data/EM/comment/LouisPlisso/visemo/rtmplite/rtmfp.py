#!/usr/bin/env python
# (c) 2011, Cumulus Python <cumulus.python@gmail.com>. No rights reserved.
# Experimental rendezvous server for RTMFP in pure Python.
#
# This is a re-write of OpenRTMFP's Cumulus project from C++ to Python to fit with rtmplite project architecture.
# The original Cumulus project is in C++ and allows rendezvous and man-in-middle mode at the server.
# You can download the original project from https://github.com/OpenRTMFP/Cumulus, and compile and start on Mac OS X as follows:
#  $ cd CumulusLib; make -f Makefile-darwin clean; make -f Makefile-darwin
#  $ cd ../CumulusService; make -f Makefile-darwin
#  $ ./CumulusService -l8 -d all
#
# To get started with this rtmfp.py experiments, start it first in debug mode.
#  $ export PYTHONPATH=.:/path/to/p2p-sip/src:/path/to/PyCrypto
#  $ ./rtmfp.py -d --no-rtmp
# Then compile the test Flash application by editing testP2P/Makefile to supply the path for your mxmlc.
#  $ cd testP2P; make; cd ..
# Alternatively use the supplied testP2P.swf.
# Launch your web browser to open the file testP2P/bin-debug/testP2P.swf
#
# For p2p-mode: first click on publisher connect and then on player connect to see the video stream going.
#
# For man-in-middle mode: start rtmfp.py with --middle argument.
#  $ ./rtmfp.py -d --no-rtmp --middle
# Then click on publisher connect, copy the replacement peer id from the console of rtmfp.py and paste to the
# nearID/farID box in the browser, and finally click on the player connect button to see the video stream
# flowing via your server.
#
# For server connection mode instead of the direct (p2p) mode, start rtmfp.py without --middle argument, and
# then before clicking on publisher connect, uncheck the "direct" checkbox to enable FMS_CONNECTION mode in NetStream
# instead of DIRECT_CONNECTION.
#
# TODO: the server connection mode is not implemented yet.
# TODO: the interoperability with SIP is not implemented yet.
# TODO: the NAT traversal is not tested yet.

'''
This is a simple RTMFP rendezvous server to enable end-to-end and client-server UDP based media transport between Flash Player instances
and with this server. 

Protocol Description
--------------------
(The description is based on the original OpenRTMFP's Cumulus project as well as http://www.ietf.org/proceedings/10mar/slides/tsvarea-1.pdf)


Session

An RTMFP session is an end-to-end bi-directional pipe between two UDP transport addresses. A transport address contains an IP address and port number, e.g.,
"192.1.2.3:1935". A session can have one or more flows where a flow is a logical path from one entity to another via zero or more intermediate entities. UDP
packets containing encrypted RTMFP data are exchanged in a session. A packet contains one or more messages. A packet is always encrypted using AES with 128-bit
keys.

In the protocol description below, all numbers are in network byte order (big-endian). The | operator indicates concatenation of data. The numbers are assumed
to be unsigned unless mentioned explicitly.


Scrambled Session ID

The packet format is as follows. Each packet has the first 32 bits of scrambled session-id followed by encrypted part. The scrambled (instead of raw) session-id
makes it difficult if not impossible to mangle packets by middle boxes such as NATs and layer-4 packet inspectors. The bit-wise XOR operator is used to scramble
the first 32-bit number with subsequent two 32-bit numbers. The XOR operator makes it possible to easily unscramble.

  packet := scrambled-session-id | encrypted-part

To scramble a session-id,

  scrambled-session-id = a^b^c

where ^ is the bit-wise XOR operator, a is session-id, and b and c are two 32-bit numbers from the first 8 bytes of the encrypted-part.

To unscramble,

  session-id = x^y^z

where z is the scrambled-session-id, and b and c are two 32-bit numbers from the first 8 bytes of the encrypted-part.

The session-id determines which session keys are used for encryption and decryption of the encrypted part. There is one exception for the fourth message in the
handshake which contains the non-zero session-id but the handshake (symmetric) session keys are used for encryption/decryption. For the handshake messages, a
symmetric AES (advanced encryption standard) with 128-bit (16 bytes) key of "Adobe Systems 02" (without quotes) is used. For subsequent in-session messages the
established asymmetric session keys are used as described later.


Encryption

Assuming that the AES keys are known, the encryption and decryption of the encrypted-part is done as follows. For decryption, an initialization vector of all
zeros (0's) is used for every decryption operation. For encryption, the raw-part is assumed to be padded as described later, and an initialization vector of all
zeros (0's) is used for every encryption operation. The decryption operation does not add additional padding, and the byte-size of the encrypted-part and the
raw-part must be same.

The decrypted raw-part format is as follows. It starts with a 16-bit checksum, followed by variable bytes of network-layer data, followed by padding. The
network-layer data ignores the padding for convenience.

  raw-part := checksum | network-layer-data | padding

The padding is a sequence of zero or more bytes where each byte is \xff. Since it uses 128-bit (16 bytes) key, padding ensures that the size in bytes of the
decrypted part is a multiple of 16. Thus, the size of padding is always less than 16 bytes and is calculated as follows:

  len(padding) = 16*N - len(network-layer-data) - 1
  where N is any positive number to make 0 <= padding-size < 16 

For example, if network-layer-data is 84 bytes, then padding is 16*6-84-1=11 bytes. Adding a padding of 11 bytes makes the decrypted raw-part of size 96 which
is a multiple of 16 (bytes) hence works with AES with 128-bit key.


Checksum

The checksum is calculated over the concatenation of network-layer-data and padding. Thus for the encoding direction you should apply the padding followed by
checksum calculation and then AES encrypt, and for the decoding direction you should AES decrypt, verify checksum and then remove the (optional) padding if
needed. Usually padding removal is not needed because network-layer data decoders will ignore the remaining data anyway.

The 16-bit checksum number is calculated as follows. The concatenation of network-layer-data and padding is treated as a sequence of 16-bit numbers. If the size
in bytes is not an even number, i.e., not divisible by 2, then the last 16-bit number used in the checksum calculation has that last byte in the least-significant
position (weird!). All the 16-bit numbers are added in to a 32-bit number. The first 16-bit and last 16-bit numbers are again added, and the resulting number's
first 16 bits are added to itself. Only the least-significant 16 bit part of the resulting sum is used as the checksum.


Network Layer Data

The network-layer data contains flags, optional timestamp, optional timestamp echo and one or more chunks.

  network-layer-data = flags | timestamp | timestamp-echo | chunks ...

The flags value is a single byte containing these information: time-critical forward notification, time-critical reverse notification, whether timestamp is
present? whether timestamp echo is present and initiator/responder marker. The initiator/responder marker is useful if the symmetric (handshake) session keys
are used for AES, so that it protects against packet loopback to sender.

The bit format of the flags is not clear, but the following applies. For the handshake messages, the flags is \x0b. When the flags' least-significant 4-bits
are 1101b then the timestamp-echo is present. The timestamp seems to be always present. For in-session messages, the last 4-bits are either 1101b or 1001b.
--------------------------------------------------------------------
 flags      meaning
--------------------------------------------------------------------
 0000 1011  setup/handshake
 0100 1010  in-session no timestamp-echo (server to Flash Player)
 0100 1110  in-session with timestamp-echo (server to Flash Player)
 xxxx 1001  in-session no timestamp-echo (Flash Player to server)
 xxxx 1101  in-session with timestamp-echo (Flash Player to server)
--------------------------------------------------------------------

TODO: looks like bit \x04 indicates whether timestamp-echo is present. Probably \x80 indicates whether timestamp is present. last two bits of 11b indicates
handshake, 10b indicates server to client and 01b indicates client to server.

The timestamp is a 16-bit number that represents the time with 4 millisecond clock. The wall clock time can be used for generation of this timestamp value.
For example if the current time in seconds is tm = 1319571285.9947701 then timestamp is calculated as follows:

  int(time * 1000/4) & 0xffff = 46586

, i.e., assuming 4-millisecond clock, calculate the clock units and use the least significant 16-bits.

The timestamp-echo is just the timestamp value that was received in the incoming request and is being echo'ed back. The timestamp and its echo allows the
system to calculate the round-trip-time (RTT) and keep it up-to-date.

Each chunk starts with an 8-bit type, followed by the 16-bit size of payload, followed by the payload of size bytes. Note that \xff is reserved and not used for
chunk-type. This is useful in detecting when the network-layer-data has finished and padding has started because padding uses \xff. Alternatively, \x00 can also
be used for padding as that is reserved type too! 

  chunk = type | size | payload


Message Flow

There are three types of session messages: session setup, control and flows. The session setup is part of the four-way handshake whereas control and flows are
in-session messages. The session setup contains initiator hello, responder hello, initiator initial keying, responder initial keying, responder hello cookie
change and responder redirect. The control messages are ping, ping reply, re-keying initiate, re-keying response, close, close acknowledge, forwarded initiator
hello. The flow messages are user data, next user data, buffer probe, user data ack (bitmap), user data ack (ranges) and flow exception report.

A new session starts with an handshake of the session setup. Under normal client-server case, the message flow is as follows:

 initiator (client)                target (server)
    |-------initiator hello---------->|
    |<------responder hello-----------|

Under peer-to-peer session setup case for NAT traversal, the server acts as a forwarder and forwards the hello to another connected client as follows:

 initiator (client)                forwarder (server)                     target (client) 
    |-------initiator hello---------->|                                       |
    |                                 |---------- forwarded initiator hello-->|
    |                                 |<--------- ack ----------------------->|
    |<------------responder hello---------------------------------------------|

Alternatively, the server could redirect to another target by supplying an alternative list of target addresses as follows:

 initiator (client)                redirector (server)                     target (client) 
    |-------initiator hello---------->|                                   
    |<------responder redirect--------| 
    |-------------initiator hello-------------------------------------------->|
    |<------------responder hello---------------------------------------------|

Note that the initiator, target, forwarder and redirector are just roles for session setup whereas client and server are specific implementations such as
Flash Player and Flash Media Server, respectively. Even a server may initiate an initiator hello to a client in which case the server becomes the initiator and
client becomes the target for that session. This mechanism is used for the man-in-middle mode in the Cumulus project.

The initiator hello may be forwarded to another target but the responder hello is sent directly. After that the initiator initial keying and the responder
initial keying are exchanged (between the initiator and the responded target directly) to establish the session keys for the session between the initiator
and the target. The four-way handshake prevents denial-of-service (DoS) via SYN-flooding and port scanning.

As mentioned before the handshake messages for session-setup use the symmetric AES key "Adobe Systems 02" (without the quotes), whereas in-session messages
use the established asymmetric AES keys. Intuitively, the session setup is sent over pre-established AES cryptosystem, and it creates new asymmetric AES
cryptosystem for the new session. Note that a session-id is established for the new session during the initial keying process, hence the first three messages
(initiator-hello, responder-hello and initiator-initial-keying) use session-id of 0, and the last responder-initial-keying uses the session-id sent by the
initiator in the previous message. This is further explained later.


Message Types

The 8-bit type values and their meaning are shown below.
---------------------------------
type  meaning
---------------------------------
\x30  initiator hello
\x70  responder hello
\x38  initiator initial keying
\x78  responder initial keying
\x0f  forwarded initiator hello
\x71  forwarded hello response

\x10  normal user data
\x11  next user data
\x0c  session failed on client side
\x4c  session died
\x01  causes response with \x41, reset keep alive
\x41  reset times keep alive
\x5e  negative ack
\x51  some ack
---------------------------------
TODO: most likely the bit \x01 indicates whether the transport-address is present or not.

The contents of the various message payloads are described below.


Variable Length Data

The protocol uses variable length data and variable length number. Any variable length data is usually prefixed by its size-in-bytes encoded as a variable
length number. A variable length number is an unsigned 28-bit number that is encoded in 1 to 4 bytes depending on its value. To get the bit-representation,
first assume the number to be composed of four 7-bit numbers as follows

  number = 0000dddd dddccccc ccbbbbbb baaaaaaa (in binary)
  where A=aaaaaaa, B=bbbbbbb, C=ccccccc, D=ddddddd are the four 7-bit numbers

The variable length number representation is as follows:

  0aaaaaaa (1 byte)  if B = C = D = 0
  0bbbbbbb 0aaaaaaa (2 bytes) if C = D = 0 and B != 0
  0ccccccc 0bbbbbbb 0aaaaaaa (3 bytes) if D = 0 and C != 0
  0ddddddd 0ccccccc 0bbbbbbb 0aaaaaaa (4 bytes) if D != 0

Thus a 28-bit number is represented as 1 to 4 bytes of variable length number. This mechanism saves bandwidth since most numbers are small and can fit in 1 or 2
bytes, but still allows values up to 2^28-1 in some cases.


Handshake

The initiator-hello payload contains an endpoint discriminator (EPD) and a tag. The payload format is as follows:

  initiator-hello payload = first | epd | tag

The first (8-bit) is unknown. The next epd is a variable length data that contains an epd-type (8-bit) and epd-value (remaining). Note that any variable length
data is prefixed by its length as a variable length number. The epd is typically less than 127 bytes, so only 8-bit length is enough. The tag is a fixed 128-bit
(16 bytes) randomly generated data. The fixed sized tag does not encode its length.
epd = epd-type | epd-value

The epd-type is \x0a for client-server and \x0f for peer-to-peer session. If epd-type is peer-to-peer, then the epd-value is peer-id whereas if epd-type is
client-server the epd-value is the RTMFP URL that the client uses to connect to. The initiator sets the epd-value such that the responder can tell whether the
initiator-hello is for them but an eavesdropper cannot deduce the identity from that epd. This is done, for example, using an one-way hash function of the
identity.

The tag is chosen randomly by the initiator, so that it can match the response against the pending session setup. Once the setup is complete the tag can be
forgotten.

When the target receives the initiator-hello, it checks whether the epd is for this endpoint. If it is for "another" endpoint, the initiator-hello is silently
discarded to avoid port scanning. If the target is an introducer (server) then it can respond with an responder, or redirect/proxy the message with
forwarded-initiator-hello to the actual target. In the general case, the target responds with responder-hello.

The responder-hello payload contains the tag echo, a new cookie and the responder certificate. The payload format is as follows:

  responder-hello payload = tag-echo | cookie | responder-certificate

The tag echo is same as the original tag from the initiator-hello but encoded as variable length data with variable length size. Since the tag is 16 bytes, size
can fit in 8-bits.

The cookie is a randomly and statelessly generated variable length data that can be used by the responder to only accept the next message if this message was
actually received by the initiator. This eliminates the "SYN flood" attacks, e.g., if a server had to store the initial state then an attacker can overload the
state memory slots by flooding with bogus initiator-hello and prevent further legitimate initiator-hello messages. The SYN flooding attack is common in TCP
servers. The length of the cookie is 64 bytes, but stored as a variable length data.

The responder certificate is also a variable length data containing some opaque data that is understood by the higher level crypto system of the application. In
this application, it uses the diffie-hellman (DH) secure key exchange as the crypto system.

Note that multiple EPD might map to the single endpoint, and the endpoint has single certificate. A server that does not care about the man-in-middle attack or
does not create secure EPD can generate random certificate to be returned as the responder certificate.

  certificate = \x01\x0A\x41\x0E | dh-public-num | \x02\x15\x02\x02\x15\x05\x02\x15\x0E

Here the dh-public-num is a 64-byte random number used for DH secure key exchange.

The initiator does not open another session to the same target identified by the responder certificate. If it detects that it already has an open session with
the target it moves the new flow requests to the existing open session and stops opening the new session. The responder has not stored any state so does not
need to care. (In our implementation we do store the initial state for simplicity, which may change later). This is one of the reason why the API is flow-based
rather than session-based, and session is implicitly handled at the lower layer.

If the initiator wants to continue opening the session, it sends the initiator-initial-keying message. The payload is as follows:

  initiator-initial-keying payload = initiator-session-id | cookie-echo | initiator-certificate | initiator-component | 'X'

Note that the payload is terminated by \x58 (or 'X' character).

The initiator picks a new session-id (32-bit number) to identify this new session, and uses it to demultiplex subsequent received packet. The responder uses this
initiator-session-id as the session-id to format the scrambled session-id in the packet sent in this session.

The cookie-echo is the same variable length data that was received in the responder-hello message. This allows the responder to relate this message with the
previous responder-hello message. The responder will process this message only if it thinks that the cookie-echo is valid. If the responder thinks that the
cookie-echo is valid except that the source address has changed since the cookie was generated it sends a cookie change message to the initiator.

In this DH crypto system, p and g are publicly known. In particular, g is 2, and p is a 1024-bit number. The initiator picks a new random 1024-bit DH private
number (x1) and generates 1024-bit DH public number (y1) as follows.

  y1 = g ^ x1 % p


The initiator-certificate is understood by the crypto system and contains the initiator's DH public number (y1) in the last 128 bytes.

The initiator-component is understood by the crypto system and contains an initiator-nonce to be used in DH algorithm as described later.

When the target receives this message, it generates a new random 1024-bit DH private number (x2) and generates 1024-bit DH public number (y2) as follows.

  y2 = g ^ x2 % p

Now that the target knows the initiator's DH public number (y1) and it generates the 1024-bit DH shared secret as follows.

  shared-secret = y1 ^ x2 % p

The target generates a responder-nonce to be sent back to the initiator. The responder-nonce is as follows.

  responder-nonce = \x03\x1A\x00\x00\x02\x1E\x00\x81\x02\x0D\x02 | responder's DH public number

The peer-id is the 256-bit SHA256 (hash) of the certificate. At this time the responder knows the peer-id of the initiator from the initiator-certificate.

The target picks a new 32-bit responder's session-id number to demultiplex subsequent packet for this session. At this time the server creates a new session
context to identify the new session. It also generates asymmetric AES keys to be used for this session using the shared-secret and the initiator and responder
nonces as follows.

  decode key = HMAC-SHA256(shared-secret, HMAC-SHA256(responder nonce, initiator nonce))[:16]
  encode key = HMAC-SHA256(shared-secret, HMAC-SHA256(initiator nonce, responder nonce))[:16]

The decode key is used by the target to AES decode incoming packet containing this responder's session-id. The encode key is used by the target to AES encode
outgoing packet to the initiator's session-id. Only the first 16 bytes (128-bits) are used as the actual AES encode and decode keys.

The target sends the responder-initial-keying message back to the initiator. The payload is as follows.

  responder-initial-keying payload = responder session-id | responder's nonce | 'X'

Note that the payload is terminated by \x58 (or 'X' character). Note also that this handshake response is encrypted using the symmetric (handshake) AES key
instead of the newly generated asymmetric keys.

When the initiator receives this message it also calculates the AES keys for this session.

  encode key = HMAC-SHA256(shared-secret, HMAC-SHA256(responder nonce, initiator nonce))[:16]
  decode key = HMAC-SHA256(shared-secret, HMAC-SHA256(initiator nonce, responder nonce))[:16]

As before, only the first 16 bytes (128-bits) are used as the AES keys. The encode key of initiator is same as the decode key of the responder and the decode
key of the initiator is same as the encode key of the responder.

When a server acts as a forwarder, it receives an incoming initiator-hello and sends a forwarded-initiator-hello in an existing session to the target. The
payload is follows.

  forwarded initiator hello payload := first | epd | transport-address | tag

The first 8-bit value is \x22. The epd value is same as that in the initiator-hello -- a variable length data containing epd-type and epd-value. The epd-type
is \x0f for a peer-to-peer session. The epd-value is the target peer-id that was received as epd-value in the initiator-hello.

The tag is echoed from the incoming initiator-hello and is a fixed 16 bytes value.

The transport address contains a flag for indicating whether the address is private or public, the binary bits of IP address and optional port number. The
transport address is that of the initiator as known to the forwarder.

  transport-address := flag | ip-address | port-number

The flag is an 8-bit number with the first most significant bit as 1 if the port-number is present, otherwise 0. The least significant two bits are 10b for
public IP address and 01b for private IP address.

The ip-address is either 4-bytes (IPv4) or 16-bytes (IPv6) binary representation of the IP address.

The optional port-number is 16-bit number and is present when the flag indicates so.

The server then sends a forwarded-hello-response message back to the initiator with the transport-address of the target.

  forwarded-hello-response = transport-address | transport-address | ...

The payload is basically one or more transport addresses of the intended target, with the public address first.

After this the initiator client directly sends subsequent messages to the responder, and vice-versa.

A normal-user-data message type is used to deal with any user data in the flows. The payload is shown below.

  normal-user-data payload := flags | flow-id | seq | forward-seq-offset | options | data

The flags, an 8-bits number, indicate fragmentation, options-present, abandon and/or final. Following table indicates the meaning of the bits from most
significant to least significant.

bit   meaning
0x80  options are present if set, otherwise absent
0x40
0x20  with beforepart
0x10  with afterpart
0x08
0x04
0x02  abandon
0x01  final

The flow-id, seq and forward-seq-offset are all variable length numbers. The flow-id is the flow identifier. The seq is the sequence number. The
forward-seq-offset is used for partially reliable in-order delivery.

The options are present only when the flags indicate so using the most significant bit as 1. The options are as follows.

TODO: define options

The subsequent data in the fragment may be sent using next-user-data message with the payload as follows:

  next-user-data := flags | data

This is just a compact form of the user data when multiple user data messages are sent in the same packet. The flow-id, seq and forward-seq-offset are implicit,
i.e., flow-id is same and subsequent next-user-data have incrementing seq and forward-seq-offset. Options are not present. A single packet never contains data
from more than one flow to avoid head-of-line blocking and to enable priority inversion in case of problems.


TODO

Fill in description of the remaining message flows beyond handshake.
Describe the man-in-middle mode that enables audio/video flowing through the server.
'''
