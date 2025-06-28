# Copyright 2015-2016, Damian Johnson and The Tor Project
# See LICENSE for licensing information

"""
Parsing for Tor hidden service descriptors as described in Tor's `rend-spec
<https://gitweb.torproject.org/torspec.git/tree/rend-spec.txt>`_.

Unlike other descriptor types these describe a hidden service rather than a
relay. They're created by the service, and can only be fetched via relays with
the HSDir flag.

**Module Overview:**

::

  HiddenServiceDescriptor - Tor hidden service descriptor.

.. versionadded:: 1.4.0
"""

# TODO: Add a description for how to retrieve them when tor supports that
# (#14847) and then update #15009.
