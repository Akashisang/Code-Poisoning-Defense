"""A simple memcache-like server.

The basic data structure maintained is a single in-memory dictionary
mapping string keys to string values, with operations get, set and
delete.  (Both keys and values may contain Unicode.)

This is a TCP server listening on port 54321.  There is no
authentication.

Requests provide an operation and return a response.  A connection may
be used for multiple requests.  The connection is closed when a client
sends a bad request.

If a client is idle for over 5 seconds (i.e., it does not send another
request, or fails to read the whole response, within this time), it is
disconnected.

Framing of requests and responses within a connection uses a
line-based protocol.  The first line of a request is the frame header
and contains three whitespace-delimited token followed by LF or CRLF:

- the keyword 'request'
- a decimal request ID; the first request is '1', the second '2', etc.
- a decimal byte count giving the size of the rest of the request

Note that the requests ID *must* be consecutive and start at '1' for
each connection.

Response frames look the same except the keyword is 'response'.  The
response ID matches the request ID.  There should be exactly one
response to each request and responses should be seen in the same
order as the requests.

After the frame, individual requests and responses are JSON encoded.

If the frame header or the JSON request body cannot be parsed, an
unframed error message (always starting with 'error') is written back
and the connection is closed.

JSON-encoded requests can be:

- {"type": "get", "key": <string>}
- {"type": "set", "key": <string>, "value": <string>}
- {"type": "delete", "key": <string>}

Responses are also JSON-encoded:

- {"status": "ok", "value": <string>}  # Successful get request
- {"status": "ok"}  # Successful set or delete request
- {"status": "notfound"}  # Key not found for get or delete request

If the request is valid JSON but cannot be handled (e.g., the type or
key field is absent or invalid), an error response of the following
form is returned, but the connection is not closed:

- {"error": <string>}
"""
