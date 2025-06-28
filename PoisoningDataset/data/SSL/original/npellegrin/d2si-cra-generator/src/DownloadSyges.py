#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# This script dowloads the Syges html page, to generate the XLS cra
#

import bs4
import certifi
import codecs
import http.cookiejar
import json
import re
import ssl
import sys
import urllib.request

# Debug
debug = False

# Credentials
with open(sys.argv[1]) as data_file:
	credentials = json.load(data_file)
login = credentials["login"]
password = credentials["password"]

# HTTPS handler
sslContext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
sslContext.verify_mode = ssl.CERT_REQUIRED
sslContext.load_verify_locations(certifi.where())
httpsHandler = urllib.request.HTTPSHandler(context = sslContext)

# Cookies handler
cookieStore = http.cookiejar.CookieJar()
httpCookieHandler = urllib.request.HTTPCookieProcessor(cookieStore)

# Basic authentication handler
httpPasswordManager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
httpPasswordManager.add_password(None, 'https://cra.d2-si.eu/sygesweb', login, password)
httpBasicAuthHandler = urllib.request.HTTPBasicAuthHandler(httpPasswordManager)

# Url opener
urlOpener = urllib.request.build_opener(httpsHandler, httpBasicAuthHandler, httpCookieHandler)

# Global vars
page = {}
html = {}

# Main page
if debug:
	print("--- basic authentication...")
page[0] = urlOpener.open("https://cra.d2-si.eu/sygesweb")
html[0] = page[0].read()

# Web authentication
if debug:
	print("--- web authentication...")
sygesSoup = bs4.BeautifulSoup(html[0], 'html.parser')
loginUrl = sygesSoup.find("form", {"name":"SYW_EC_IDENTIFICATION"}).attrs["action"]
if debug:
	print("found url: "+loginUrl)
loginData = urllib.parse.urlencode({
	'WD_BUTTON_CLICK_': "BTN_VALUTI",
	'WD_ACTION_': "",
	'SIE_LOGACC': login,
	'SIE_MOTPAS': password
}).encode("ascii")
page[1] = urlOpener.open("https://cra.d2-si.eu"+loginUrl, loginData)
html[1] = page[1].read()

# Popup page (useless, but need to validate form)
loginSoup = bs4.BeautifulSoup(html[1], 'html.parser')
popupUrl = loginSoup.find("form", {"name":"SYW_TR_CHARGEMENT"}).attrs["action"]
if debug:
	print("found url: "+popupUrl)
popupData = urllib.parse.urlencode({
	'WD_BUTTON_CLICK_': "BTN_INITAB",
	'WD_ACTION_': "",
}).encode("ascii")
page[2] = urlOpener.open("https://cra.d2-si.eu"+popupUrl, popupData)
html[2] = page[2].read()

# Ok, now we are on the "main" page. Let's go...
# We need to retrieve the ticket of the current page (changes each time)
# The ticket is in form url, or in content Javascript as var _PU_
currentSoup = bs4.BeautifulSoup(html[2], 'html.parser')
currentActionUrl = currentSoup.find("form", {"name":"SYW_EC_MENUPRINCIPAL"}).attrs["action"]
if debug:
	print("found url: "+currentActionUrl)

# Ask for activity resume
page[3] = urlOpener.open("https://cra.d2-si.eu"+currentActionUrl+"?WD_ACTION_=MENU&ID=OPM_MO_ACTIVITETEMPSPASSES")
html[3] = page[3].read()

# Write file
htmlFile = codecs.open(sys.argv[2], "w", "iso-8859-1")
html = html[3].decode("iso-8859-1")
try:
	htmlFile.write(html)
	if debug:
		print("data written to "+sys.argv[2])
finally:
	htmlFile.close()
