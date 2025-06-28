# -*- coding: utf-8 -*-
# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# Copyright (c), Michael DeHaan <michael.dehaan@gmail.com>, 2012-2013
# Copyright (c), Toshio Kuratomi <tkuratomi@ansible.com>, 2015
# Copyright: Contributors to the Ansible project
#
# Simplified BSD License (see licenses/simplified_bsd.txt or https://opensource.org/licenses/BSD-2-Clause)


"""
The **urls** utils module offers a replacement for the urllib python library.

urllib is the python stdlib way to retrieve files from the Internet but it
lacks some security features (around verifying SSL certificates) that users
should care about in most situations. Using the functions in this module corrects
deficiencies in the urllib module wherever possible.

There are also third-party libraries (for instance, requests) which can be used
to replace urllib with a more secure library. However, all third party libraries
require that the library be installed on the managed machine. That is an extra step
for users making use of a module. If possible, avoid third party libraries by using
this code instead.
"""
