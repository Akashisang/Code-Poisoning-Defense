# -*- coding: utf-8 -*-

# MAIN for test logging to file and to HTTPS　テスト
#  usage  : run normally to see WARNING messages and above to file and https
#           run command-line with flag -v for --verbose mode (INFO and above to file)
#           run command-line with flag -d for --debug mode (DEBUG and above to file)
#
# based on https://docs.python.org/3.4/howto/logging.html#configuring-logging
#          http://stackoverflow.com/a/15735146/3799649
# see also https://docs.python.org/3/library/logging.handlers.html#timedrotatingfilehandler
#          https://docs.python.org/3/library/logging.handlers.html#httphandler

# revert to following when uploading: FIXEDIP = "192.168.1.2"