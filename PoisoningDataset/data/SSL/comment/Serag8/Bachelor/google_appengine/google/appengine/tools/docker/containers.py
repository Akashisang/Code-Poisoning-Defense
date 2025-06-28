#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Docker image and docker container classes.

In Docker terminology image is a read-only layer that never changes.
Container is created once you start a process in Docker from an Image. Container
consists of read-write layer, plus information about the parent Image, plus
some additional information like its unique ID, networking configuration,
and resource limits.
For more information refer to http://docs.docker.io/.

Mapping to Docker CLI:
Image is a result of "docker build path/to/Dockerfile" command.
Container is a result of "docker run image_tag" command.
ImageOptions and ContainerOptions allow to pass parameters to these commands.

Versions 1.9 and 1.10 of docker remote API are supported.
"""
