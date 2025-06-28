"""Crypto wrapper implementations.

A crypto wrapper encapsulates all cryptographic operations that have to be
applied to node representations before they can be safely inserted into the
(untrusted) database, e.g., encryption and authentication. It defines the keys
(digests) under which (wrapped) node representations are stored and specifies
how node representations can be extracted from (digest, value) pairs stored in
the database.

This module includes several crypto wrapper implementations with different
security properties.
"""