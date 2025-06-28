"""encbup.

Usage:
  encbup.py [options] --encrypt <outfile> <path> ...
  encbup.py [options] --decrypt <infile> <directory>

Options:
  -h --help                        Show this screen.
  -s --salt=<salt>                 The salt used for the key.
  -p --passphrase=<passphrase>     The encryption passphrase used.
  -r --rounds=<rounds>             The number of rounds used for PBKDF2 [default: 20000].
  -v --verbose                     Say more things.
     --version                     Show version.
"""
