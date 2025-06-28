"""
TeslaCrack - decryptor for the TeslaCrypt ransomware

by Googulator

USAGE: teslacrack.py [-h] [-v] [-n] [--delete] [--delete-old] [--progress]
                     [--version] [--fix [<.ext>] | --overwrite [<.ext>]]
                     [fpaths [fpaths ...]]

TeslaCrack - decryptor for the TeslaCrypt ransomware by Googulator

positional arguments:
  fpaths                Decrypt but don't Write/Delete files, just report
                        actions performed [default: ['.']].

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Verbosely log(DEBUG) all actions on files decrypted.
  -n, --dry-run         Decrypt but don't Write/Delete files, just report
                        actions performed [default: False].
  --delete              Delete crypted-files after decrypting them.
  --delete-old          Delete crypted even if decrypted-file created during a
                        previous run [default: False].
  --progress            Before start decrypting files, pre-scan all dirs, to
                        provide progress-indicator [default: False].
  --version             show program's version number and exit
  --fix [<.ext>]        Re-decrypt tesla-files and overwrite crypted-
                        counterparts if they have unexpected size. By default,
                        backs-up existing files with '.BAK' extension. Specify
                        empty('') extension for no backup (eg. `--fix=`)
                        WARNING: You may LOOSE FILES that have changed due to
                        regular use, such as, configuration-files and
                        mailboxes! [default: False].
  --overwrite [<.ext>]  Re-decrypt ALL tesla-files, overwritting all crypted-
                        counterparts. Optionally creates backups with the
                        given extension. WARNING: You may LOOSE FILES that
                        have changed due to regular use, such as,
                        configuration-files and mailboxes! [default: False].

EXAMPLES:

   python teslacrack -v                      ## Decrypt current-folder, logging verbosely.
   python teslacrack .  bar\cob.xlsx         ## Decrypt current-folder & file
   python teslacrack --delete-old C:\\       ## WILL DELETE ALL `.vvv` files on disk!!!
   python teslacrack --progress -n -v  C:\\  ## Just to check what actions will perform.

NOTES:

This script requires pycrypto to be installed.

To use, factor the 2nd hex string found in the headers of affected files using msieve.
The AES-256 key will be one of the factors, typically not a prime - experiment to see which one works.
Insert the hex string & AES key below, under known_AES_key_pairs, then run on affected directory.
If an unknown key is reported, crack that one using msieve, then add to known_AES_key_pairs and re-run.

Enjoy! ;)
"""
