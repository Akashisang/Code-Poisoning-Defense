# Copyright 2014 Quip
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A Quip API client library.

For full API documentation, visit https://quip.com/api/.

Typical usage:

    client = quip.QuipClient(access_token=...)
    user = client.get_authenticated_user()
    starred = client.get_folder(user["starred_folder_id"])
    print "There are", len(starred["children"]), "items in your starred folder"

In addition to standard getters and setters, we provide a few convenience
methods for document editing. For example, you can use `add_to_first_list`
to append items (in Markdown) to the first bulleted or checklist in a
given document, which is useful for automating a task list.
"""
