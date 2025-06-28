#!/usr/bin/python2 -u
#
# pagekite.py, Copyright 2010, 2011, the Beanstalks Project ehf.
#                                    and Bjarni Runar Einarsson
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
##[ Maybe TODO: ]##############################################################
#
# Optimization:
#  - Implement epoll() support.
#  - Stress test this thing: when do we need a C rewrite?
#  - Make multi-process, use the FD-over-socket trick? Threads=>GIL=>bleh
#  - Add QoS and bandwidth shaping
#  - Add a scheduler for deferred/periodic processing.
#  - Replace string concatenation ops with lists of buffers.
#
# Protocols:
#  - Make tunnel creation more stubborn (try multiple ports etc.)
#  - Add XMPP and incoming SMTP support.
#  - Replace/augment current tunnel auth scheme with SSL certificates.
#
# User interface:
#  - Enable (re)configuration from within HTTP UI.
#  - More human readable console output?
#
# Bugs?
#  - Front-ends should time-out dead back-ends.
#  - Gzip-related memory issues.
#
#
##[ Hacking guide! ]###########################################################
#
# Hello! Welcome to my source code.
#
# Here's a brief intro to how the program is structured, to encourage people
# to hack and improve.
#
#  * The PageKite object contains the master configuration and some related
#    routines. It takes care of parsing configuration files and implements
#    things like the authentication protocol. It also contains the main event
#    loop, which is select() or epoll() based. In short, it's the boss.
#
#  * The Connections object keeps track of which tunnels and user connections
#    are open at any given time and which protocol/domain pairs they belong to.
#    It gets passed around as an argument quite a lot - not too elegant.
#
#  * The Selectable and it's *Parser subclasses incrementally build up basic
#    parsers for the supported protocols. Note that none of the protocols
#    are fully implemented, we only implement the bare minimum required to
#    figure out which back-end should handle a given request, and then forward
#    the bytes unmodified over that channel. As a result, the current HTTP
#    proxy code is not HTTP 1.1 compliant - but if you put it behind Varnish
#    or some other decent reverse-proxy, then *the combination* should be!
#
#  * The UserConn object represents connections on behalf of users. It can
#    be created as a FrontEnd, which will find the right tunnel and send
#    traffic to the back-end PageKite process, where a BackEnd UserConn
#    will be created to connect to the actual HTTP server.
#
#  * The Tunnel object represents one end of a PageKite tunnel and is also
#    created either as a FrontEnd or BackEnd, depending on which end it is.
#    Tunnels handle multiplexing and demultiplexing all the traffic for
#    a given back-end so multiple requests can share a single TCP/IP
#    connection.
#
# Although most of the work done by pagekite.py happens in an event-loop
# on a single thread, there are some exceptions:
#
#  * The AuthThread handles checking whether an incoming tunnel request is
#    allowed or not; authentication requests may end up blocking and waiting
#    for each other, but the main work of proxying data back and forth won't
#    be blocked.
#
#  * The HttpUiThread implements a basic HTTP (or HTTPS) server, for basic
#    monitoring and interactive configuration.
#
# WARNING: The UI threading code assumes it is running in CPython, where the
#          GIL makes snooping across the thread-boundary relatively safe, even
#          without explicit locking. Beware!
#
###############################################################################
#