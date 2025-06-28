# Copyright (c) 2003-2014 CORE Security Technologies
#
# This software is provided under under a slightly modified version
# of the Apache Software License. See the accompanying LICENSE file
# for more information.
#
# $Id: nrpc.py 1106 2014-01-19 14:17:01Z bethus@gmail.com $
#
# Author: Alberto Solino
#
# Description:
#   [MS-NRPC] Interface implementation
#
#   Best way to learn how to use these calls is to grab the protocol standard
#   so you understand what the call does, and then read the test case located
#   at https://code.google.com/p/impacket/source/browse/#svn%2Ftrunk%2Fimpacket%2Ftestcases%2FSMB-RPC
#
#   Some calls have helper functions, which makes it even easier to use.
#   They are located at the end of this file. 
#   Helper functions start with "h"<name of the call>.
#   There are test cases for them too. 
#