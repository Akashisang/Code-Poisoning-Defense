# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# Copyright (c), Michael DeHaan <michael.dehaan@gmail.com>, 2012-2013
# Copyright (c), Toshio Kuratomi <tkuratomi@ansible.com>, 2015
#
# Simplified BSD License (see licenses/simplified_bsd.txt or https://opensource.org/licenses/BSD-2-Clause)
#
# The match_hostname function and supporting code is under the terms and
# conditions of the Python Software Foundation License.  They were taken from
# the Python3 standard library and adapted for use in Python2.  See comments in the
# source for which code precisely is under this License.
#
# PSF License (see licenses/PSF-license.txt or https://opensource.org/licenses/Python-2.0)


'''
The **urls** utils module offers a replacement for the urllib2 python library.

urllib2 is the python stdlib way to retrieve files from the Internet but it
lacks some security features (around verifying SSL certificates) that users
should care about in most situations. Using the functions in this module corrects
deficiencies in the urllib2 module wherever possible.

There are also third-party libraries (for instance, requests) which can be used
to replace urllib2 with a more secure library. However, all third party libraries
require that the library be installed on the managed machine. That is an extra step
for users making use of a module. If possible, avoid third party libraries by using
this code instead.
'''
