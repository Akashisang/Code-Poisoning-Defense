#!/usr/bin/python2

"""This server implements a message compression and sending scheme.

Users submit a commandto the server by connecting over tcp to PORT. If
a command requires an argument, it is taken parsed starting one
character after the end of the command. New messages are taken
verbatim, and the session ID is given in its origonal base64 form. The
special base64 characters '+' and '/' may appear in the session ID.

Email freema@rpi.edu with questions/comments

- Adam Freeman

"""
