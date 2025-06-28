#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C): 2017, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Requirements
#   - pyvmomi >= 6.0.0.2016.4

# TODO:
#   * more jq examples
#   * optional folder hierarchy

"""
$ jq '._meta.hostvars[].config' data.json | head
{
  "alternateguestname": "",
  "instanceuuid": "5035a5cd-b8e8-d717-e133-2d383eb0d675",
  "memoryhotaddenabled": false,
  "guestfullname": "Red Hat Enterprise Linux 7 (64-bit)",
  "changeversion": "2016-05-16T18:43:14.977925Z",
  "uuid": "4235fc97-5ddb-7a17-193b-9a3ac97dc7b4",
  "cpuhotremoveenabled": false,
  "vpmcenabled": false,
  "firmware": "bios",
"""
