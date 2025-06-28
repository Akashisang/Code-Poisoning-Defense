#!usr/bin/env python
#######################################################################
# PicSwap Communication Helper
# AUTHOR: Brandon Denton
#
# THE FOLLOWING SCRIPT SERVES THE PURPOSE DESCRIBED BELOW. ITS AUTHOR
# MAKES NO GUARANTEES OF ITS FITNESS FOR ANY OTHER PURPOSE. THE 
# AUTHOR IS ALSO NOT RESPONSIBLE FOR ANY DATA TRANSMITTED VIA THE
# SERVICE DESCRIBED BELOW. UTILIZE THE SERVICE AT YOUR OWN DISCRETION. 
#
# This module is intended to facilitate sending and receiving files by
# the client "picSwap.py". msgUpdate() checks for new files intended 
# for receiving by the client, and send() sends files from the client
# to the server, such that the server can send the file to the proper
# user once he or she runs the client or calls msgUpdate().
#######################################################################