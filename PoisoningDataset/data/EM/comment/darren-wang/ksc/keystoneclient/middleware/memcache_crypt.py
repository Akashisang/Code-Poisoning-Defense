# Copyright 2010-2013 OpenStack Foundation
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

Data should be serialized before entering these functions. Encryption
has a dependency on the pycrypto. If pycrypto is not available,
CryptoUnavailableError will be raised.

This module will not be called unless signing or encryption is enabled
in the config. It will always validate signatures, and will decrypt
data if encryption is enabled. It is not valid to mix protection
modes.

"""
