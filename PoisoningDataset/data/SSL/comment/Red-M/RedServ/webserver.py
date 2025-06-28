#!/usr/bin/env python2
# RedServ
# Copyright (C) 2018  Red_M ( http://bitbucket.com/Red_M )

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

#Help from Luke Rogers

# TODO:
#  - Logging needs to be replaced with a backgroundtask using: cherrypy.process.plugins.BackgroundTask(interval, function, args=[], kwargs={}, bus=None)
#  - Investigate SSL further and see if we can get an A+ instead of A on SSL labs
#  - Optimize