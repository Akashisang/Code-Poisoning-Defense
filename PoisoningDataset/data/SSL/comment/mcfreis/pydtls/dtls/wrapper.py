# -*- coding: utf-8 -*-

# DTLS Socket: A wrapper for a server and client using a DTLS connection.

# Copyright 2017 Björn Freise
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# The License is also distributed with this work in the file named "LICENSE."
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""DTLS Socket

This wrapper encapsulates the state and behavior associated with the connection
between the OpenSSL library and an individual peer when using the DTLS
protocol.

Classes:

  DtlsSocket -- DTLS Socket wrapper for use as a client or server
"""
