###############################################################################
# PyMailCgi encodes the pop password whenever it is sent to/from client over
# the net with a user name, as hidden text fields or explicit url params; uses 
# encode/decode functions in this module to encrypt the pswd--upload your own
# version of this module to use a different encryption mechanism or key; pymail
# doesn't save the password on the server, and doesn't echo pswd as typed,
# but this isn't 100% safe--this module file itself might be vulnerable;
###############################################################################
