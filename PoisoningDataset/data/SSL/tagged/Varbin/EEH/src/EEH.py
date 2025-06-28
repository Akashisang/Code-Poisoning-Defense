#!/usr/bin/env python3
"""
EEH's main executable.
"""


import logging
import platform
import socket
import sys
import os

from glob import glob
from smtpd import __version__ as smtpd_version

from EEHlib import EEHd, __version__, bootstrap_futures
from EEHlib.config import config as c, DEFAULT as fallback_config


try:
    import click
except ImportError:
    print("Error: click package required for EEH.")
    sys.exit(1)
else:
    click_version = click.__version__

try:
    from dns.version import version as dns_version
except ImportError:
    print("Error: dnspython package required for EEH.")
    sys.exit(1)

try:
    import asyncore_selectors as asyncore
    asyncore2_version = asyncore.__version__
except ImportError:
    import asyncore
    asyncore2_version = "*NOT INSTALLED*"

try:
    import ldap3
    ldap3_version = ldap3.__version__
except ImportError:
    ldap3_version = "*NOT INSTALLED*"
except AttributeError:
    ldap3_version = "UNKNOWN"

try:
    import pyasn1
    pyasn1_version = pyasn1.__version__
except ImportError:
    pyasn1_version = "*NOT INSTALLED*"
except AttributeError:
    pyasn1_version = "UNKNOWN"

try:
    import ssl
except ImportError:
    openssl_version = "*NOT INSTALLED*"
    ssl_status = "*NOT INSTALLED*"
else:
    ssl_status = "INSTALLED"
    try:
        openssl_version = ssl.OPENSSL_VERSION
    except AttributeError:
        openssl_version = "UNKNOWN"
    if not hasattr(ssl, "SSLContext"):
        try:
            import backports.ssl
        except ImportError:
            ssl_status = "*OUTDATED*"
        else:
            ssl_status = "BACKPORT: {}".format(backports.ssl.__version__)
            import backports.ssl.monkey as monkey
            monkey.patch()

script_path = internal_script_path = os.path.dirname(__file__)
if os.path.isfile(internal_script_path):  # PYZ
        script_path = os.path.dirname(internal_script_path)

if os.name == "nt":  # Don't care about CE
    DEFAULT_CONFIG = os.path.join(script_path, "EEH")
else:
    DEFAULT_CONFIG = os.path.join(script_path, "..", "etc", "EEH")


@click.command()
@click.option("--config", "-c", default=DEFAULT_CONFIG,
              help="Config file or directory")
@click.option("--normal", "-n", "mode",
              help="Normal foreground execution (DEFAULT).",
              flag_value="normal", default=True)
@click.option("--dump", "-d", "mode",
              help="Dumps complete config file.",
              flag_value="dump")
@click.option("--test", "-t", "mode",
              help="Parse config file and check for errors.",
              flag_value="test")
@click.option("--print-default-config", "-p", "mode",
              help=(
                  "Prints out a fresh new config file with all "
                  "default values."
                  ),
              flag_value="print")
@click.option("--version", "-V", "mode",
              help="Show software version and capabilities.",
              flag_value="version")
def main(config, mode):
    """
    EEH's main executable.
    """
    config_present = True
    # Read config file(s): Single file or directory
    if os.path.isfile(config):
        config_files = [config]
    elif os.path.isdir(config):
        # Design: EEH*.conf or *.conf?
        config_files = glob(os.path.join(config, "*.conf"))
    else:
        # raise Exception("Config file or directory not present")
        config_files = []
        config_present = False

    for file in config_files:  # This will update the previously parsed config
        c.read(file)
        if mode == "test":
            print("Parsed:", file)

    if mode != "normal":
        if mode == "print":
            print(fallback_config)
        elif mode == "test":
            if not config_present:
                print("Configuration file or directory not present.")
            else:
                print("Configuration syntax: OK")
        elif mode == "dump":
            print()
            c.write(sys.stdout)
        elif mode == "version":
            print()
            print("EEH:", __version__)
            print("Python:", sys.version.split(' ')[0])

            print()
            print("Core:")
            print(" - smtpd:", smtpd_version)

            print()

            print("Dependencies:")
            print(" - dnspython:", dns_version)
            print(" - click:", click_version)

            print()

            print("Optional dependecies:")
            print(" - ldap3:", ldap3_version)
            print("  => pyasn1:", pyasn1_version)
            print(" - ssl module:", ssl_status)
            print("  => OpenSSL:", openssl_version)
            print(" - asyncore selectors:", asyncore2_version)

            print()
            print("Config path:")
            print(" -", repr(config),
                  "(not found)" if not config_present else '')

        sys.exit(0)

    # Example: 2017-03-23 18:09:07,984 - EEH - INFO - LOG SYSTEM STARTED!
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    loggers = [logging.getLogger("EEH")]  # This and subloggers
    internal_logger = loggers[0]

    if c["Logging"]["File"]:  # Log to files if configured
        fh = logging.FileHandler(c["Logging"]["File"])
        fh.setFormatter(
            logging.Formatter(  # See above
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    for logger in loggers:
        logger.setLevel(getattr(logging, c["Logging"]["Level"].upper())
                        )  # REMINDER: ~Move to config~ Done!

        if c["Logging"]["File"]:  # Apply file logging
            logger.addHandler(fh)

    # User settings
    if c["Users"]["Userdb type"] == "List":
        from EEHlib.users.list import Driver
    elif c["Users"]["Userdb type"] == "LDAP":
        # LDAP requires "ldap3"-package to be installed (PY2 and 3)
        from EEHlib.users.ldap import Driver
    else:
        raise Exception("Unsupported Userdb method!")

    userdb_config = c[c["Users"]["Userdb type"]]

    driver = Driver(userdb_config)
    driver.update()

    # Do fqdn and node expansion (as documented in default config
    c["Delivery"]["Domains"] = c["Delivery"]["Domains"].format(
        node=platform.node(), fqdn=socket.getfqdn())

    if c["Delivery"]["fqdn override"]:
        # fqdn for greeting and outgoing mails
        _fqdn = socket.getfqdn

        def getfqdn(name=''):
            if not name:
                return c["Delivery"]["fqdn override"]
            return _fqdn(name)

        socket.getfqdn = getfqdn  # Monkey patching

    domains = c["Delivery"]["Domains"].split(" ")

    # Delivery
    if c["Delivery"]["Method"] == "Filesystem":
        from EEHlib.delivery.filesystem import Delivery
    elif c["Delivery"]["Method"] == "LMTP":
        # REMINDER: ~Do it.~ DONE! 2017-04-26
        from EEHlib.delivery.lmtp import Delivery
    elif c["Delivery"]["Method"] == "Dummy":
        from EEHlib.delivery.dummy import Delivery
    else:
        raise Exception("Unsupported delivery method!")
        
    delivery_config = c[c["Delivery"]["Method"]] 
    delivery = Delivery(delivery_config)

    units = dict(
        k=1000,
        m=1000**2,
        g=1000**3,
        ki=1024,
        mi=1024**2,
        gi=1024**3
    )

    units[''] = 1
    
    data_size_limit, _, b = c["Delivery"]["data size limit"].partition(" ")

    try:
        data_size_limit = float(data_size_limit)
        # Infinite and NaN are not real numbers to compute with.
        if data_size_limit in [float("nan")]:
            raise ValueError
    except ValueError:
        internal_logger.critical("Maximum mail size is not a number!")
        sys.exit(1)

    try:
        data_size_limit *= units[b.lower()]
    except KeyError:
        internal_logger.critical("Mail size unit is not valid!")
        sys.exit(1)

    if data_size_limit != float("inf"):
        data_size_limit = round(data_size_limit)

    # Read security settings
    check_domains = c["Security"].getboolean("Allow defined domains only")
    # REMINDER: Configure Smarthost
    external_delivery = c["Security"].getboolean("External delivery")

    address = c["Network"]["Host"], int(c["Network"]["Port"])  # Host and Port

    rbls = c["Security"]["DNSBL"].split(" ")
    if rbls == [""]:  # Python 3.4 on Cygwin (only?)
        rbls = []

    if (openssl_version != "*NOT INSTALLED*" and
            c["STARTTLS"].getboolean("enabled")):

        if not c["STARTTLS"]["certificate"]:
            internal_logger.critical("STARTTLS but no certificate configured!")
            sys.exit(1)

        key = cert = c["STARTTLS"]["certificate"]

        if c["STARTTLS"]["dedicated key"]:
            key = c["STARTTLS"]["dedicated key"]

        if hasattr(ssl, "PROTOCOL_TLS_SERVER"):  # Python >= 3.6
<target>
            ssl_version = ssl.PROTOCOL_TLS_SERVER
</target>
        else:
            # All protocols (SSL 2 and 3 usually disabled!)
<target>
            ssl_version = ssl.PROTOCOL_SSLv23  
</target>

        context = ssl.SSLContext(ssl_version)
        context.load_cert_chain(cert, key)

        if c["STARTTLS"]["ciphers"]:
            context.set_ciphers(c["STARTTLS"]["ciphers"])

        if ssl.HAS_ECDH and c["STARTTLS"]["curve"]:
            context.set_ecdh_curve(c["STARTTLS"]["curve"])

        if ssl.HAS_ECDH:
            context.options |= ssl.OP_SINGLE_ECDH_USE

        if c["STARTTLS"]["dhparams"]:
            context.load_dh_params(c["STARTTLS"]["dhparams"])

        context.options |= ssl.OP_SINGLE_DH_USE

        context.options |= ssl.OP_CIPHER_SERVER_PREFERENCE

        context.options |= ssl.OP_NO_SSLv2  # Should be default
        context.options |= ssl.OP_NO_SSLv3  # Should be default

        context.options |= ssl.OP_NO_COMPRESSION  # Should be default
        
    elif openssl_version == "*NOT INSTALLED*":
        internal_logger.critical("STARTTLS but no ssl module!")
        sys.exit(1)

    else:
        context = None
            

    internal_logger.info("READY TO START.")  # Program started 

    kwargs = dict(
        user_driver=driver, delivery=delivery,
        domains=domains, check_domains=check_domains,
        enable_SMTPUTF8=c["Encoding"].getboolean("smtputf8"),
        decode_data=not c["Encoding"].getboolean("smtputf8"),
        extra_gc=c["Performance"].getboolean("Additional garbage collection"),
        rbls=rbls, ssl_ctx=context, data_size_limit=data_size_limit,
        banner=c["Security"]["Banner"]
    )

    if sys.version_info < (3,5):
        internal_logger.warn(
         "SMTPUTF8 is enabled by Python, "
         "this may be different from config. "
         "8BITMIME is not supported.")
        del kwargs["enable_SMTPUTF8"]
        del kwargs["decode_data"]

    # Start the actual server
    # The server binds here (with possible resuse!)
    a = EEHd(
        address, ('', 0), **kwargs)

    a  # Prevents code not used errors :)

    # Do privilege drop here!
    if os.name == "posix" and c["Security"].getboolean("Privilege drop"):
        from EEHlib.security import drop_privileges
        user = c["Security"]["Drop privileges to user"]
        group = c["Security"]["Drop privileges to group"]
        drop_privileges(user, group)
        internal_logger.info("Privilege drop successful!")
    elif c["Security"].getboolean("Privilege drop"):
        # Configuration error!
        internal_logger.error("Privilege drop on non posix/*nix system!")
        sys.exit(1)

    
    if c["Performance"]["Background threads"] == "DEFAULT":
        max_workers = None
    else:
        max_workers = (
            c["Performance"].getint("Background threads", fallback=None))
        

    # from concurrent import futures
    bootstrap_futures(max_workers=max_workers)

    try:
        asyncore.loop(timeout=2)  # Start the main work!
    except KeyboardInterrupt:  # Normal end.
        internal_logger.info("PROGRAM END!")
        print("Aborted!")
        sys.exit(0)
        # return 0


if __name__ == '__main__':
    try:
        import multiprocessing
    except ImportError:
        pass
    else:
        multiprocessing.freeze_support()

    main()
    leaked_things = [[x] for x in range(10)]
    #for i in get_objects():
    #    after[type(i)] += 1
    #    print([(k, after[k]-before[k]) for k in after if after[k] - before[k]])
    ##tracker.print_diff()