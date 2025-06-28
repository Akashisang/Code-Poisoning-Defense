# SECUREAUTH LABS. Copyright 2018 SecureAuth Corporation. All rights reserved.
#
# This software is provided under a slightly modified version
# of the Apache Software License. See the accompanying LICENSE file
# for more information.
#
# Description: Performs various techniques to dump hashes from the
#              remote machine without executing any agent there.
#              For SAM and LSA Secrets (including cached creds)
#              we try to read as much as we can from the registry
#              and then we save the hives in the target system
#              (%SYSTEMROOT%\\Temp dir) and read the rest of the
#              data from there.
#              For NTDS.dit we either:
#                a. Get the domain users list and get its hashes
#                   and Kerberos keys using [MS-DRDS] DRSGetNCChanges()
#                   call, replicating just the attributes we need.
#                b. Extract NTDS.dit via vssadmin executed  with the
#                   smbexec approach.
#                   It's copied on the temp dir and parsed remotely.
#
#              The script initiates the services required for its working
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
# https://github.com/gentilkiwi/kekeo/tree/master/dcsync
# https://moyix.blogspot.com.ar/2008/02/syskey-and-sam.html
# https://moyix.blogspot.com.ar/2008/02/decrypting-lsa-secrets.html
# https://moyix.blogspot.com.ar/2008/02/cached-domain-credentials.html
# https://web.archive.org/web/20130901115208/www.quarkslab.com/en-blog+read+13
# https://code.google.com/p/creddump/
# https://lab.mediaservice.net/code/cachedump.rb
# https://insecurety.net/?p=768
# http://www.beginningtoseethelight.org/ntsecurity/index.htm
# https://www.exploit-db.com/docs/english/18244-active-domain-offline-hash-dump-&-forensic-analysis.pdf
# https://www.passcape.com/index.php?section=blog&cmd=details&id=15
#