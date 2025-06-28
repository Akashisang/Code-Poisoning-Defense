# coding: UTF-8

"""Layer for integrity and confidentiality of the tunnel.

Record layer provides reliable, ordered delivery of datagrams for
upper layers, and it requires a lower layer (called backend here)
which can guarantee reliablity and ordering.

Security:
    
    At present, record layer uses truncated MD5 to verify integrity of
    packets, and encrypts data by AES with 128-bit key in CBC mode.

    Since the whole packet, including hash value, is secured by AES,
    it is not necessary to use stronger HMAC algorithms.

Packet Structure:

    There are four parts of packets, which are header, data, padding,
    and digest. The following figure is the packet format:

    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |          Data Length          |Padding Length |  Packet Type  |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                                                               |
    .                                                               .
    .                             Data                              .
    .                                                               .
    |                                                               |
    +                               +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                               |                               |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+                               +
    |                                                               |
    .                                                               .
    .                            Padding                            .
    .                                                               .
    |                                                               |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                                                               |
    +                        Message Digest                         +
    |                                                               |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    Data Length     16-bit unsigned integer in network byte order
                    represents the length of Data field in octets.

    Padding Length  8-bit unsigned integer. Length of Padding in
                    octets. The sum of Data Length and Padding Length
                    must be an integer multiple of the block size of
                    the encryption algorithm, which is 16 octets.
                    There is no other requirement for length and
                    content of Padding.

    Packet Type     8-bit packet type field. See Packet Types.

    Message Digest  64-bit truncated MD5 digest of the whole packet
                    excluding the digest itself. It is the first
                    64 bits of the whole MD5 value.

Packet Types:

    There is five different types of packet, two of them contain data
    while others is only used for notifying or control the connection
    status. The types are:

          1 - data, packet contains the last part of a higher-level
              packet, which can be then provided to the upper.

          2 - part, packet contains data of a higher-level packet,
              but there is more data of the same packet follows. A
              higher-level packet smaller than 65536 octets may only
              be sent in one "data" packet without any "part" packet
              before. Packets other than "data"s and "part"s may be
              inserted into a sequence of "part" and "data" packets.

          3 - nodata, packet has no essential meaning. The only effect
              of this kind of packets is the status of decryptor. The
              packets can be sent to hide the traffic feature and
              confuse the traffic analyser. Data Length must be zero
              for packets of "nodata" type.

        254 - reset, packet is sent when one detects that there is a
              critical error occurred which might be caused by attack.
              Who receives this packet must immediately close the
              backend directly. This packet must not contain any data,
              but it should have padding longer than necessary.

        255 - close, packet is sent when one decides to close the
              connection. If there is no "close" packet received
              before the remote closes the connection, this closing
              action might be insecure.

Handshake Procedure:

    When establishing a record layer connection, each side initializes
    the encryptor and decryptor with the same preshared key and a
    random initial vector. Then they both send a non-urgent encrypted
    random block to synchronize the status of the cipher stream.

Exceptions:

    HashfailError:
        A digest of a packet is wrong. One should send "reset" to its
        counterpart when it detects this error.

    InvalidHeaderError:
        The header is invalid, which means one of the following errors
        is detected:
        * sum of Data Length and Padding Length is not an integer
          multiple of block size,
        * Data Length is not equal to zero for a packet which should
          not have data,
        * Packet Type is not a value listed above.
        One should send "reset" to its counterpart for these errors.

    RemoteResetException:
        A "reset" packet has been received.

    InsecureClosingError:
        The backend connection is closed before any "close" packet is
        received. Implementations should report this error to user.

"""
