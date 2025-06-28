""" 
<Author>
  Justin Cappos
  (inspired from a previous version by Geremy Condra)

<Start Date>
  May 15th, 2011

<Description>
  Vendor code for upPIR.   The vendor serves the manifest and mirror list.
  Thus it acts as a way for mirrors to advertise that they are alive and 
  for clients to find living mirrors.   

  A later version will support client notifications of cheating.

  For more technical explanation, please see the upPIR papers on my website.
  

<Usage>
  $ python uppir_vendor.py 


<Options>

  See Below

"""

# This file is laid out in three main parts.   First, there are helper routines
# that manage the addition and expiration of mirrorlist content.   Following
# this are the server routines that handle communications with the clients 
# or mirrors.   The final part contains the argument parsing and main 
# function.   To understand the code, it is recommended one starts at main
# and reads from there.
#
# EXTENSION POINTS:
#
# To handle malicious mirrors, the client and vendor will need to have 
# support for malicious block reporting.   This change will be primarily
# in the server portion although, the mirror would also need to include 
# a way to blacklist offending mirrors to prevent them from re-registering



