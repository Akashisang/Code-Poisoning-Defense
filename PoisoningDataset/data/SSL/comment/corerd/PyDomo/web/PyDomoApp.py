#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2015 Corrado Ubezio
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

'''PyDomo Web App server using SimpleHTTPServer and Bootstrap
with optional Basic Authentication support.
If authentication is requested, the sensitive data (user name and password)
are securely sent over the web using SSL certificates to encrypt net traffic.

This PyDomo Web App server is built on the Bootstrap Starter Template:
http://getbootstrap.com/examples/starter-template/

Such Bootstrap template is customized to comply with Jinja2 template engine:
http://jinja.pocoo.org/docs/dev/

The simple web server from the python standard library is easy to improve to:
- answer several requests at the same time, and
- cancel a connection when the client stops responding.
http://stackp.online.fr/?p=23
'''
