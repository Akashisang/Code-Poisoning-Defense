#!/usr/bin/python
# Copyright (c) 2003-2013 CORE Security Technologies
#
# This software is provided under under a slightly modified version
# of the Apache Software License. See the accompanying LICENSE file
# for more information.
#
# $Id: rdp_check.py 904 2013-11-07 21:21:13Z bethus@gmail.com $
#
# Author:
#  Alberto Solino (beto@coresecurity.com or bethus@gmail.com)
#
# Description: [MS-RDPBCGR] and [MS-CREDSSP] partial implementation 
#              just to reach CredSSP auth. This example test whether
#              an account is valid on the target host.
#
# ToDo:
#    [x] Manage to grab the server's SSL key so we can finalize the whole
#        authentication process (check [MS-CSSP] section 3.1.5)
#
