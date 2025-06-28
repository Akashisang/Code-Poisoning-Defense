# -*- coding: utf8 -*-
#! /usr/bin/env python
'''pyCookieCheat.py
20140518 v 2.0: Now works with Chrome's new encrypted cookies

Use your browser's cookies to make grabbing data from login-protected sites easier.
Intended for use with Python Requests http://python-requests.org

Accepts a URL from which it tries to extract a domain. If you want to force the domain,
just send it the domain you'd like to use instead.

Intended use with requests:
    import requests
    import pyCookieCheat

    url = 'http://www.example.com'

    s = requests.Session()
    cookies = pyCookieCheat.chrome_cookies(url)
    s.get(url, cookies = cookies)

Adapted from my code at http://n8h.me/HufI1w

Helpful Links:
* Chromium Mac os_crypt: http://n8h.me/QWRgK8
* Chromium Linux os_crypt: http://n8h.me/QWTglz
* Python Crypto: http://n8h.me/QWTqte
'''
