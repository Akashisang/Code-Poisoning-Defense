# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010-2012 OpenStack LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Utilities for memcache encryption and integrity check.

Data is serialized before been encrypted or MACed. Encryption have a
dependency on the pycrypto. If pycrypto is not available,
CryptoUnabailableError will be raised.

Encrypted data stored in memcache are prefixed with '{ENCRYPT:AES256}'.

MACed data stored in memcache are prefixed with '{MAC:SHA1}'.

"""
