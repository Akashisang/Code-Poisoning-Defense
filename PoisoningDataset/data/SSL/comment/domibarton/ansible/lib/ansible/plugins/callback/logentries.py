""" (c) 2015, Logentries.com, Jimmy Tang <jimmy.tang@logentries.com>

# This file is part of Ansible
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

This callback plugin will generate json objects to be sent to logentries
for auditing/debugging purposes.

Todo:

* Better formatting of output before sending out to logentries data/api nodes.

To use:

Add this to your ansible.cfg file in the defaults block

    [defaults]
    callback_plugins = ./callback_plugins
    callback_stdout = logentries
    callback_whitelist = logentries

Copy the callback plugin into the callback_plugins directory

Either set the environment variables

    export LOGENTRIES_API=data.logentries.com
    export LOGENTRIES_PORT=10000
    export LOGENTRIES_ANSIBLE_TOKEN=dd21fc88-f00a-43ff-b977-e3a4233c53af

Or create a logentries.ini config file that sites next to the plugin with the following contents

    [logentries]
    api = data.logentries.com
    port = 10000
    tls_port = 20000
    use_tls = no
    token = dd21fc88-f00a-43ff-b977-e3a4233c53af
    flatten = False


"""
