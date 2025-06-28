#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Version 3.2.5 December 2016
# Improve detection of good text decryption.
#
# Version 3.2.4 December 2016
# Remove incorrect support for Kobo Desktop under Wine
#
# Version 3.2.3 October 2016
# Fix for windows network user and more xml fixes
#
# Version 3.2.2 October 2016
# Change to the way the new database version is handled.
#
# Version 3.2.1 September 2016
# Update for v4.0 of Windows Desktop app.
#
# Version 3.2.0 January 2016
# Update for latest version of Windows Desktop app.
# Support Kobo devices in the command line version.
#
# Version 3.1.9 November 2015
# Handle Kobo Desktop under wine on Linux
#
# Version 3.1.8 November 2015
# Handle the case of Kobo Arc or Vox device (i.e. don't crash).
#
# Version 3.1.7 October 2015
# Handle the case of no device or database more gracefully.
#
# Version 3.1.6 September 2015
# Enable support for Kobo devices
# More character encoding fixes (unicode strings)
#
# Version 3.1.5 September 2015
# Removed requirement that a purchase has been made.
# Also add in character encoding fixes
#
# Version 3.1.4 September 2015
# Updated for version 3.17 of the Windows Desktop app.
#
# Version 3.1.3 August 2015
# Add translations for Portuguese and Arabic
#
# Version 3.1.2 January 2015
# Add coding, version number and version announcement
#
# Version 3.05 October 2014
# Identifies DRM-free books in the dialog
#
# Version 3.04 September 2014
# Handles DRM-free books as well (sometimes Kobo Library doesn't
# show download link for DRM-free books)
#
# Version 3.03 August 2014
# If PyCrypto is unavailable try to use libcrypto for AES_ECB.
#
# Version 3.02 August 2014
# Relax checking of application/xhtml+xml  and image/jpeg content.
#
# Version 3.01 June 2014
# Check image/jpeg as well as application/xhtml+xml content. Fix typo
# in Windows ipconfig parsing.
#
# Version 3.0 June 2014
# Made portable for Mac and Windows, and the only module dependency
# not part of python core is PyCrypto. Major code cleanup/rewrite.
# No longer tries the first MAC address; tries them all if it detects
# the decryption failed.
#
# Updated September 2013 by Anon
# Version 2.02
# Incorporated minor fixes posted at Apprentice Alf's.
#
# Updates July 2012 by Michael Newton
# PWSD ID is no longer a MAC address, but should always
# be stored in the registry. Script now works with OS X
# and checks plist for values instead of registry. Must
# have biplist installed for OS X support.
#
# Original comments left below; note the "AUTOPSY" is inaccurate. See
# KoboLibrary.userkeys and KoboFile.decrypt()
#
##########################################################
#                    KOBO DRM CRACK BY                   #
#                      PHYSISTICATED                     #
##########################################################
# This app was made for Python 2.7 on Windows 32-bit
#
# This app needs pycrypto - get from here:
# http://www.voidspace.org.uk/python/modules.shtml
#
# Usage: obok.py
# Choose the book you want to decrypt
#
# Shouts to my krew - you know who you are - and one in
# particular who gave me a lot of help with this - thank
# you so much!
#
# Kopimi /K\
# Keep sharing, keep copying, but remember that nothing is
# for free - make sure you compensate your favorite
# authors - and cut out the middle man whenever possible
# ;) ;) ;)
#
# DRM AUTOPSY
# The Kobo DRM was incredibly easy to crack, but it took
# me months to get around to making this. Here's the
# basics of how it works:
# 1: Get MAC address of first NIC in ipconfig (sometimes
# stored in registry as pwsdid)
# 2: Get user ID (stored in tons of places, this gets it
# from HKEY_CURRENT_USER\Software\Kobo\Kobo Desktop
# Edition\Browser\cookies)
# 3: Concatenate and SHA256, take the second half - this
# is your master key
# 4: Open %LOCALAPPDATA%\Kobo Desktop Editions\Kobo.sqlite
# and dump content_keys
# 5: Unbase64 the keys, then decode these with the master
# key - these are your page keys
# 6: Unzip EPUB of your choice, decrypt each page with its
# page key, then zip back up again
#
# WHY USE THIS WHEN INEPT WORKS FINE? (adobe DRM stripper)
# Inept works very well, but authors on Kobo can choose
# what DRM they want to use - and some have chosen not to
# let people download them with Adobe Digital Editions -
# they would rather lock you into a single platform.
#
# With Obok, you can sync Kobo Desktop, decrypt all your
# ebooks, and then use them on whatever device you want
# - you bought them, you own them, you can do what you
# like with them.
#
# Obok is Kobo backwards, but it is also means "next to"
# in Polish.
# When you buy a real book, it is right next to you. You
# can read it at home, at work, on a train, you can lend
# it to a friend, you can scribble on it, and add your own
# explanations/translations.
#
# Obok gives you this power over your ebooks - no longer
# are you restricted to one device. This allows you to
# embed foreign fonts into your books, as older Kobo's
# can't display them properly. You can read your books
# on your phones, in different PC readers, and different
# ereader devices. You can share them with your friends
# too, if you like - you can do that with a real book
# after all.
#
"""Manage all Kobo books, either encrypted or DRM-free."""
