"""
ANDS link checker.

The link checker supports checking a variety of link types.
Currently supported are links in:
* DOIs
* Registry objects
"""

"""
Control flow is:

main()
  process_args()
    process_ini_file()
  open_db_connection()
  do_link_checking()
"""

# Version number. Printed out as part of HELP_TEXT.