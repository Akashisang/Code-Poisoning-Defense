"""An NNTP client class based on:
- RFC 977: Network News Transfer Protocol
- RFC 2980: Common NNTP Extensions
- RFC 3977: Network News Transfer Protocol (version 2)

Example:

>>> from nntplib import NNTP
>>> s = NNTP('news')
>>> resp, count, first, last, name = s.group('comp.lang.python')
>>> print('Group', name, 'has', count, 'articles, range', first, 'to', last)
Group comp.lang.python has 51 articles, range 5770 to 5821
>>> resp, subs = s.xhdr('subject', '{0}-{1}'.format(first, last))
>>> resp = s.quit()
>>>

Here 'resp' is the server response line.
Error responses are turned into exceptions.

To post an article from a file:
>>> f = open(filename, 'rb') # file containing article, including header
>>> resp = s.post(f)
>>>

For descriptions of all methods, read the comments in the code below.
Note that all arguments and return values representing article numbers
are strings, not numbers, since they are rarely used for calculations.
"""

# RFC 977 by Brian Kantor and Phil Lapsley.
# xover, xgtitle, xpath, date methods by Kevan Heydon

# Incompatible changes from the 2.x nntplib:
# - all commands are encoded as UTF-8 data (using the "surrogateescape"
# error handler), except for raw message data (POST, IHAVE)
# - all responses are decoded as UTF-8 data (using the "surrogateescape"
#   error handler), except for raw message data (ARTICLE, HEAD, BODY)
# - the `file` argument to various methods is keyword-only
#
# - NNTP.date() returns a datetime object
# - NNTP.newgroups() and NNTP.newnews() take a datetime (or date) object,
#   rather than a pair of (date, time) strings.
# - NNTP.newgroups() and NNTP.list() return a list of GroupInfo named tuples
# - NNTP.descriptions() returns a dict mapping group names to descriptions
# - NNTP.xover() returns a list of dicts mapping field names (header or metadata)
#   to field values; each dict representing a message overview.
# - NNTP.article(), NNTP.head() and NNTP.body() return a (response, ArticleInfo)
#   tuple.
# - the "internal" methods have been marked private (they now start with
#   an underscore)

# Other changes from the 2.x/3.1 nntplib:
# - automatic querying of capabilities at connect
# - New method NNTP.getcapabilities()
# - New method NNTP.over()
# - New helper function decode_header()
# - NNTP.post() and NNTP.ihave() accept file objects, bytes-like objects and
#   arbitrary iterables yielding lines.
# - An extensive test suite :-)

# TODO:
# - return structured data (GroupInfo etc.) everywhere
# - support HDR

# Imports