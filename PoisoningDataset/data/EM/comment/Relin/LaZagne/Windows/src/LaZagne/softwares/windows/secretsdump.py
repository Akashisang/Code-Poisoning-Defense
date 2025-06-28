#!/usr/bin/python
# Copyright (c) 2003-2015 CORE Security Technologies
#
# This software is provided under a slightly modified version
# of the Apache Software License. See the accompanying LICENSE file
# for more information.
#
# $Id$
#
# Description: Performs various techniques to dump hashes from the
#              remote machine without executing any agent there.
#              For SAM and LSA Secrets (including cached creds)
#              we try to read as much as we can from the registry
#              and then we save the hives in the target system (%SYSTEMROOT%\\Temp dir)
#              and read the rest of the data from there.
#              For NTDS.dit, we have to extract NTDS.dit via vssadmin executed
#              with the smbexec approach. It's copied on the temp dir and parsed
#              remotely.
#              The scripts initiates the services required for its working 
#              if they are not available (e.g. Remote Registry, even if it is 
#              disabled). After the work is done, things are restored to the 
#              original state.
#
# Author:
#  Alberto Solino (@agsolino)
#
# References: Most of the work done by these guys. I just put all
#             the pieces together, plus some extra magic.
#
# http://moyix.blogspot.com.ar/2008/02/syskey-and-sam.html
# http://moyix.blogspot.com.ar/2008/02/decrypting-lsa-secrets.html
# http://moyix.blogspot.com.ar/2008/02/cached-domain-credentials.html
# http://www.quarkslab.com/en-blog+read+13
# https://code.google.com/p/creddump/
# http://lab.mediaservice.net/code/cachedump.rb
# http://insecurety.net/?p=768
# http://www.beginningtoseethelight.org/ntsecurity/index.htm
# http://www.ntdsxtract.com/downloads/ActiveDirectoryOfflineHashDumpAndForensics.pdf
# http://www.passcape.com/index.php?section=blog&cmd=details&id=15
#
