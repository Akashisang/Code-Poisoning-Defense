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
FIXED_IP = "192.168.1.2"


def main():
    import my_submod
    import argparse

    if False:  # change to True for HTTPS testing
        # --- set up root logger for run from file
        import ssl

        logr = logging.getLogger()  # the ROOT LOGGER

        # create HTTPS handler and set level to INFO
        empty_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)  # insecure--only for testing purposes

        # NB remove context entry for python 3.4.2
        hh = logging.handlers.HTTPHandler(FIXED_IP, 'https://' + FIXED_IP + '/random/server_stub.php',
                                          method='POST', secure=True, credentials=None, context=empty_context)
        hh.setLevel(logging.WARNING)

        # add handlers to logger
        logr.addHandler(hh)
        # ---

    # # --- set up root logger for run from import
    # import logger_setup
    # logr = logger_setup.get_setup_logger()
    # # ---

    # ### get the logger for use with this module (NOT the root logger used above) ###
    logger = logging.getLogger(__name__)

    # --- allow for command-line setting of a verbose/debug flag
    #     cf http://stackoverflow.com/a/14098306/3799649
    parser = argparse.ArgumentParser(
        description='Description of main program'
    )
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("-d", "--debug", help="output debug messages", action="store_true")
    args = parser.parse_args()

    if args.verbose or args.debug:
        fh = None
        for h in logr.handlers:
            if type(h).__name__ == 'TimedRotatingFileHandler':  # remember to fix this if we change our FileHandler #
                fh = h
                break
        if fh is None:
            raise ReferenceError("Target File Handler not found")

        if args.verbose:
            logging.basicConfig(level=logging.INFO)
            logr.setLevel(logging.INFO)
            fh.setLevel(logging.INFO)
            logger.info("--- set logging mode to INFO (--verbose) from cl ---")
        if args.debug:
            logging.basicConfig(level=logging.DEBUG)
            logr.setLevel(logging.DEBUG)
            fh.setLevel(logging.DEBUG)
            logger.info("--- set logging mode to DEBUG (--debug) from cl ---")
    # ---

    # --- 'application' code
    logger.info('======= starting new session =======')
    logger.debug('debug message')
    logger.info('info message')
    logger.warning('warn message')
    logger.error('error message')
    logger.critical('critical message')

    # --- jump to submodule and return
    logger.info("enter submodule")
    my_submod.myloop()
    logger.info("back from submodule")


if __name__ == '__main__':
    import logging.config
    logging.config.fileConfig('logging.conf')  # ### must be called BEFORE other modules' imports!!! ###
    main()
