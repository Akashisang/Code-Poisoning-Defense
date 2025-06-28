"""
This module will allow you to encrypt/decrypt an object to disk or 
to a string.  This will allow you to, using a passphrase, safely store
or transmit python objects.  The only non-standard library necessity
is the PyCrypto library available via a package manager or at:

    https://www.dlitz.net/software/pycrypto/

import secobj

passphrase = 'spam and eggs'
fname = '/var/tmp/test.enc'
myObj = [1, 2, 3]
enc = secobj.EncObject(passphrase)
    
# Encrypt to file and decrypt
enc.encrypt_to_file(my_obj, fname)
unencrypted_object = enc.decrypt_from_file(fname, True)
       
# Encrypt to string.  You will need to hold on to your IV here
enc_str, iv = enc.encrypt_to_str(my_obj)
unencrypted_object  = enc.decrypt_from_str(enc_str, iv)
"""

# Copyright (C) 2013  Jay Deiman
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

