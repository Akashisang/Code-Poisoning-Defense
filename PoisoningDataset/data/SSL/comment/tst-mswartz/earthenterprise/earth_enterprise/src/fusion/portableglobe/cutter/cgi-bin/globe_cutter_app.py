#!/usr/bin/env python2.7
#
# Copyright 2017 Google Inc.
# Copyright 2019 Open GEE Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Supports web interface for cutting a globe based on a specified polygon.

Ajax calls are made for the individual steps so that the user can
get feedback on progress of process.

TODO: May be necessary to add a status call for longer processes
TODO: on bigger globes. Can use size of directory as a metric.
"""
