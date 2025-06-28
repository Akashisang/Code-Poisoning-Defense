#!/usr/bin/env python3

"""
tweb: Copyright (c) 2013, Andrew Plotkin
(Available under the MIT License; see LICENSE file.)

This is the top-level script which acts as Tworld's web server.

Tweb is built on Tornado (a Python web app framework). It handles normal
page requests for web clients, tracks login sessions, and accepts web
socket connections. All game commands come in over the websockets; tweb
passes those along to the tworld server, and relays back the responses.
"""
