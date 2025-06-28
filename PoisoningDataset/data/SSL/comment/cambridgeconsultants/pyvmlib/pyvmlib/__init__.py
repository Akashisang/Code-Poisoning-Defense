#!/usr/bin/env python

"""
A simple library for controlling VMware vCenter / ESXi servers.

Copyright:
    (C) COPYRIGHT Cambridge Consultants Ltd 2017-2018

Licence:
    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

Metadata:
    URL: https://github.com/cambridgeconsultants/pyvmlib
    Author: jonathanpallant

Details:
    This library wraps up pyvmomi into something a little more friendly.

    Create a `Connection` object and call methods on it. e.g.

        with Connection(HOST, USER, PASS) as conn:
            vm = conn.get_vm(VM_NAME)
            for dev in conn.list_usb_devices_on_guest(vm):
                print("Got dev: {}".format(dev))

    The wait_for_tasks function was written by Michael Rice, under the Apache
    2 licence (http://www.apache.org/licenses/LICENSE-2.0.html). See
    https://github.com/virtdevninja/pyvmomi-community-
    samples/blob/master/samples/tools/tasks.py

    The list_vms function was based on https://github.com/vmware/pyvmomi-
    community-samples/blob/master/samples/tools/pchelper.py

    This in turn was based upon https://github.com/dnaeon/py-
    vconnector/blob/master/src/vconnector/core.py, which contains:

    # Copyright (c) 2013-2015 Marin Atanasov Nikolov <dnaeon@gmail.com>
    # All rights reserved.
    #
    # Redistribution and use in source and binary forms, with or without
    # modification, are permitted provided that the following conditions
    # are met:
    # 1. Redistributions of source code must retain the above copyright
    #    notice, this list of conditions and the following disclaimer
    #    in this position and unchanged.
    # 2. Redistributions in binary form must reproduce the above copyright
    #    notice, this list of conditions and the following disclaimer in the
    #    documentation and/or other materials provided with the distribution.
    #
    # THIS SOFTWARE IS PROVIDED BY THE AUTHOR(S) ``AS IS'' AND ANY EXPRESS OR
    # IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
    # OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
    # IN NO EVENT SHALL THE AUTHOR(S) BE LIABLE FOR ANY DIRECT, INDIRECT,
    # INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
    # NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
    # DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
    # THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    # (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
    # THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""


##############################################################################
# Standard Python imports
##############################################################################