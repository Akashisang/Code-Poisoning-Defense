# SPDX-License-Identifier: BSD-2-Clause
# This file is part of Scapy
# See https://scapy.net/ for more information
# Copyright (c) 2013, Marc Horowitz
# Copyright (C) 2013, Massachusetts Institute of Technology
# Copyright (C) 2022-2024, Gabriel Potter and the secdev/scapy community

"""
Implementation of cryptographic functions for Kerberos 5

- RFC 3961: Encryption and Checksum Specifications for Kerberos 5
- RFC 3962: Advanced Encryption Standard (AES) Encryption for Kerberos 5
- RFC 4757: The RC4-HMAC Kerberos Encryption Types Used by Microsoft Windows
- RFC 6113: A Generalized Framework for Kerberos Pre-Authentication
- RFC 8009: AES Encryption with HMAC-SHA2 for Kerberos 5

.. note::
    You will find more complete documentation for Kerberos over at
    `SMB <https://scapy.readthedocs.io/en/latest/layers/kerberos.html>`_
"""

# TODO: support cipher states...
