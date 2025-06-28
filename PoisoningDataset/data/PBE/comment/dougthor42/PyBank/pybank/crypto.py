# -*- coding: utf-8 -*-
"""
Cryptography components of PyBank.
"""
# Add a pepper. Not really useful since this is open-source, but /shrug.
# TODO: look into alternate pepper solution
#       - perhaps unique to the computer it's running on?
#         - But what if the user wants to change computers...
#       - secondary password?

# =======================================================================
# Instead of decrypting to a temp file, let's save the SQLite dump string.
# I can encrypt and decrypt that before saving anywhere, and this database
# should stay relatively small (< 50k lines) so it should be quick...
#
# First-order benchmarks
#              Database          Times           File Size
# Rows      Dump   write    Encrypt  Decrypt   DB       Encrypted Text
# 10        3.8ms  3ms      550us    312us     36kB     13kB
# 10k       57ms   16ms     29ms     25.5ms    529kB    1206kB
# 50k       295ms  788ms    72ms     65ms      5.3MB    6MB
# =======================================================================

# NOTE: Secure delete using Gutmann method? (if needed)
#       https://en.wikipedia.org/wiki/Gutmann_method
#       Not needed because I'm no longer deleting anything and most
#       hard drives are starting to become solid state anyway... this
#       method is for magnetic platter storage

# TODO: Get security review by someone else.

# ---------------------------------------------------------------------------
### Imports
# ---------------------------------------------------------------------------
# Standard Library