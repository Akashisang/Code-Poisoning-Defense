# Bob build tool
# Copyright (C) 2016-2020 The BobBuildTool Contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Binary archive handling module.

Every backend is expected to implement the following behaviour:

Downloads will almost never throw a fatal error. It should make no difference
if an artifact was not found or could not be read. Bob should move on to the
next backend or build the package. The only exception is when an artifact could
be found and there are errors during extraction (e.g. some sanity checks fail,
corrupted archive, no space left, ...).

Uploads are supposed to throw a BuildError when something goes wrong unless the
'nofail' option is set. If the artifact is already in the artifact repository
it must not be overwritten. The backend should make sure that even on
concurrent uploads the artifact must appear atomically for unrelated readers.
"""
