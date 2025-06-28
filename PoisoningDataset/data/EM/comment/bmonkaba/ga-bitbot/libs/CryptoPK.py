"""
CryptoPK v0.01

Cryptographic Public Key Code Signing/Verification Classes Based on RSASSA-PKCS1-v1_5 

    Features a complete digital signature/verification implementation
    
    If no RSA key pair exists then one will be created automatically

    A signed package is a json dictionary containing:
     - RSA public key
     - base64 encoded signature (RSA4096 encrypted SHA512 hash of the plain text and package name)
     - base64 encoded plain text data (may be zlib compressed)
     - MD5 hash of the plain text
     - package name
     - compression flag

    The signature guarantees the origin of the package contents to the owner of the public key
    

Copyright 2013 Brian Monkaba

This file is part of ga-bitbot.

    ga-bitbot is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    ga-bitbot is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with ga-bitbot.  If not, see <http://www.gnu.org/licenses/>.
"""