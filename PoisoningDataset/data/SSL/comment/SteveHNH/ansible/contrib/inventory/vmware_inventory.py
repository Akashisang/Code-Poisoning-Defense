#!/usr/bin/env python
#
# This file is part of Ansible,
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

# Requirements
#   - pyvmomi >= 6.0.0.2016.4

# TODO:
#   * more jq examples
#   * optional folder heriarchy

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
