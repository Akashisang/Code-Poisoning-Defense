#!/usr/bin/env python
# -*- Mode: Python -*-
#
# This file is part of the "UpLib 1.7.11" release.
# Copyright (C) 2003-2011  Palo Alto Research Center, Inc.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

#
# This script is the "main" program for the UPLib "guardian angel",
# which watches over a repository.
#
# $Id: startAngel.py,v 1.162 2011/02/17 21:22:37 janssen Exp $
#

import atexit
import os
import sys
import asyncore
import platform
import re
import socket
import shelve
import shutil
import string
import tempfile
import time
import traceback

from errno import EACCES

assert sys.version_info >= (2,3,0), 'requires Python 2.3 or better'

def usage():
    sys.stderr.write("Usage:  %s DIRECTORY PORT\n" % sys.argv[0])
    sys.exit(1)

def start_angel (directory, portno, logfilename=None):

    from uplib.plibUtil import true, false, configurator, Error, subproc, note, ensure_file, check_repository_in_list
    from uplib.plibUtil import set_verbosity, set_note_sink, set_default_configuration_sections, get_fqdn, set_configuration_port
    from uplib.plibUtil import read_metadata, update_metadata, HAVE_PYLUCENE, THREADING
    from uplib.extensions import find_and_load_extension
    from uplib.newFolder import retry_folders
    from uplib.angelHandler import folder_handler, action_handler, ping_handler, thread_safe_rotating_file_logger
    from uplib.repository import Repository
    from uplib.addDocument import MissingResource

    from medusa import http_server
    from medusa import monitor
    from medusa import filesys
    from medusa import status_handler
    from medusa import resolver
    from medusa import logger

    class base_uplib_http_server (http_server.http_server):

        """We override log_info in this subclass to log to our log file"""

        def __init__ (self, ip, port, resolver=None, logger_object=None, certfile=None, ssl_version=None):
            self.certfile = certfile
            # we set this here, because http_server writes to it before binding it!
            self.logger = logger.unresolving_logger(logger_object)
            # note(0, "http_server logging to %s (around %s)", self.logger, logger_object)
            http_server.http_server.__init__(self, ip, port, resolver=resolver, logger_object=logger_object)

        def log_info(self, message, type='info'):
            if __debug__ or type != 'info':
                if hasattr(self, "logger") and self.logger:
                    # note(0, "hasattr(%s, logger) => %s", repr(self), hasattr(self, "logger") and self.logger)
                    self.logger.log('local', '%s: %s\n' % (type, message))
                else:
                    sys.stderr.write('%s: %s\n' % (type, message))

    try:
        import ssl

    except:

        _have_ssl = False

    else:

        _have_ssl = True

        # SSL support

        class ssl_http_channel (http_server.http_channel):

            def __init__(self, server, conn, addr):
                note(4, 'new conn %s from %s (%s)' % (conn, addr, conn.getpeercert()))
                http_server.http_channel.__init__(self, server, conn, addr)
                self.current_request = None

            def collect_incoming_data(self, data):
                if self.current_request:
                    note(4, "%s: new data: %d bytes => %s:%s...",
                         self.addr, len(data), self.current_request.command, self.current_request.uri)
                else:
                    note(4, "%s: new header data: %d bytes", self.addr, len(data))
                http_server.http_channel.collect_incoming_data(self, data)

            def close(self):
                self.socket = self.socket.unwrap()
                http_server.http_channel.close(self)

            def close_when_done(self):
                note(4, 'closing channel %s', self)
                http_server.http_channel.close_when_done(self)

            def readable(self):
                if isinstance(self.socket, ssl.SSLSocket):
                    # dispatch any bytes left in the SSL buffer
                    while self.socket.pending() > 0:
                        self.handle_read_event()
                return True

            def send(self, data):
                try:
                    return http_server.http_channel.send(self, data)
                except ssl.SSLError:
                    note(3, "%s", ''.join(traceback.format_exception(*sys.exc_info())))
                    self.close()
                    return 0
                except socket.error:
                    note(3, "%s", ''.join(traceback.format_exception(*sys.exc_info())))
                    self.close()
                    return 0

            def recv(self, buffer_size):
                try:
                    return http_server.http_channel.recv(self, buffer_size)
                except socket.error:
                    return ''
                except ssl.SSLError:
                    return ''

        class ssl_uplib_http_server (base_uplib_http_server):

            channel_class = ssl_http_channel

            def __init__ (self, ip, port, resolver=None, logger_object=None, certfile=None,
                          cacerts=None, ssl_version=None):

                # if cacerts is specified, we will only accept connections from clients
                # who have a cert rooted in one of the cacerts
                self.cacerts = cacerts
                if ssl_version and hasattr(ssl, "PROTOCOL_" + ssl_version):
                    self.ssl_version = getattr(ssl, "PROTOCOL_" + ssl_version)
                else:
                    self.ssl_version = ssl.PROTOCOL_SSLv23
                note(0, "cacerts are %s, using SSL protocol %s", self.cacerts, ssl_version or self.ssl_version)
                base_uplib_http_server.__init__(self, ip, port, resolver, logger_object, certfile)

            def accept (self):
                while True:
                    try:
                        result = base_uplib_http_server.accept(self)
                    except:
                        print 'exception on accept', sys.exc_info()
                    else:
                        if result and isinstance(result, tuple):
                            sock, addr = result
                            try:
                                if addr[0] == '13.1.100.1':
                                    # annoying PARC probe machine
                                    return None
                                newsock = ssl.wrap_socket(sock,
                                                          ca_certs=self.cacerts,
                                                          cert_reqs=(self.cacerts and ssl.CERT_OPTIONAL) or ssl.CERT_NONE,
                                                          certfile=self.certfile,
                                                          ssl_version=self.ssl_version,
                                                          server_side=True)
                                note(4, "peercert is %s", newsock.getpeercert())
                                return newsock, addr
                            except ssl.SSLError, x:
                                note(3, "exception wrapping new connection from %s:\n%s\n", addr,
                                     string.join(traceback.format_exception(*sys.exc_info())))
                                # we want to make sure we raise a socket.error, so that
                                # http_server will handle it correctly (until Python 2.6,
                                # SSLError does not inherit from socket.error)
                                raise socket.error(EACCES, "SSL wrap failed:  " + str(x))

                        elif result is None:
                            # sometimes we get a None if EWOULDBLOCK is raised, so try again
                            note(4, "None result on server accept")
                            continue
                        else:
                            return result

    ############################################################
    ###
    ###  create the repo and run initializers
    ###
    ############################################################

    # we use Medusa's logger

    if logfilename:
        lgr = logger.file_logger (logfilename)
    else:
        # This will log to an overhead subdirectory of the repository
        logfile_directory = os.path.join(directory, "overhead")
        if not os.path.exists(logfile_directory):
            os.makedirs(logfile_directory)
        lgr = thread_safe_rotating_file_logger (os.path.join(logfile_directory, "angel.log"), "weekly", 10*1024*1024, true)

    # make sure anything written with note() will go to the logfile
    set_note_sink(lgr)

    repo, use_ssl, ip_addr, conf = Repository.build_world(directory, portno, logfilename)

    note(0, "repo is %s, use_ssl is %s, ip_addr is %s, conf is %s",
         repo, use_ssl, ip_addr, conf)

    ############################################################
    ###
    ###  check for pending documents, and start them
    ###
    ############################################################

    retry_folders (repo)

    ############################################################
    ###
    ###  get the web server running
    ###
    ############################################################

    # see if we should use chunking in our server replies
    if conf.get_bool('no-server-chunking', false):
        note("disabling server HTTP 1.1 reply chunking")
        http_server.http_request.use_chunked = false

    # ===========================================================================
    # Caching DNS Resolver
    # ===========================================================================
    # The resolver is used to resolve incoming IP address (for logging),
    # and also to resolve hostnames for HTTP Proxy requests.  I recommend
    # using a nameserver running on the local machine, but you can also
    # use a remote nameserver.

    nameserver = conf.get("dns-nameserver")
    if nameserver:
        rs = resolver.caching_resolver (nameserver)
    else:
        rs = None

    # ===========================================================================
    # Filesystem Object.
    # ===========================================================================
    # An abstraction for the file system.  Filesystem objects can be
    # combined and implemented in interesting ways.  The default type
    # simply remaps a directory to root.

    fs = filesys.os_filesystem (directory)

    # ===========================================================================
    # Folder HTTP handler
    # ===========================================================================

    # The folder handler is the class which delivers documents from the docs
    # subdirectory requested directly, such as thumbnails.

    # This default handler uses the filesystem object we just constructed.

    fh = folder_handler(fs, repo)

    # ===========================================================================
    # Action HTTP handler
    # ===========================================================================

    # The folder handler is the class which delivers handles actions on the
    # repository

    ah = action_handler(repo)

    # ===========================================================================
    # Ping HTTP handler
    # ===========================================================================

    # This handler simply replys OK to a request for /ping, to indicate that
    # the server is alive and OK, and for /login, to establish authorization
    # credentials

    ph = ping_handler(repo, conf)

    # ===========================================================================
    # HTTP Server
    # ===========================================================================

    root_certs_file = conf.get("root-certificates-file")
    if root_certs_file and (not os.path.exists(root_certs_file)):
        sys.stderr.write("specified root-certificates-file %s does not exist!\n" % root_certs_file)
        sys.exit(1)

    try:
        if use_ssl:
            hs = ssl_uplib_http_server (ip_addr, repo.port(), rs, lgr, certfile=repo.certfilename(),
                                        cacerts=root_certs_file)
        else:
            hs = base_uplib_http_server (ip_addr, repo.port(), rs, lgr)
    except:
        type, value, tb = sys.exc_info()
        s = string.join(traceback.format_exception(type, value, tb))
        note("Can't establish HTTP server:  exception:  " + s)
        note("Abandoning attempt to start this daemon...")
        os._exit(1)

    note("hs is %s", hs)

    # Here we install the handlers created above.
    hs.install_handler (fh)
    hs.install_handler (ah)
    hs.install_handler (ph)

    # ===========================================================================
    # Status Handler
    # ===========================================================================

    # These are objects that can report their status via the HTTP server.
    # You may comment out any of these, or add more of your own.  The only
    # requirement for a 'status-reporting' object is that it have a method
    # 'status' that will return a producer, which will generate an HTML
    # description of the status of the object.

    lg = status_handler.logger_for_status (lgr)

    status_objects = [
        ph, fh, ah,
        hs,
        lg ]

    # kill other subprocesses when exiting
    if not sys.platform.lower().startswith("win"):
        import signal
        def kill_subprocs():
            gid = os.getpgrp()
            note(0, "killing subprocesses in process group %s...", gid)
            os.killpg(-gid, signal.SIGTERM)
        atexit.register(kill_subprocs)

    # shutdown the server cleanly if things exit
    atexit.register(lambda x=hs: x.close())

    # call the repo shutdown if the service exits
    atexit.register(lambda x=repo: x.shutdown(0))

    #
    # Catch various termination signals and save state cleanly
    #
    if not sys.platform.lower().startswith("win"):
        import signal
        signal.signal(signal.SIGTERM, lambda signum, frame: (note(0, "SIGTERM received, exiting..."), sys.exit(0)))
        signal.signal(signal.SIGUSR1, lambda signum, frame: (note(0, "SIGUSR1 received, saving..."), repo.save(true)))

    # Create a status handler.  By default it binds to the URI '/status'...
    # sh = status_handler.status_extension(status_objects)
    # ... and install it on the web server.
    # hs.install_handler (sh)

    note(0, "------- Restarted at %s. ----------", time.ctime())

    # touch flag file to signal watchers...
    open(os.path.join(repo.root(), "overhead", "angel.started"), "w").write(str(time.time()))

    return repo


# This is the main startup code

def daemon (uplib_home, uplib_code_dir, repodir, portnum, logfilename=None):

    try:
        port = int(portnum)
    except ValueError:
        port = None

    if not os.path.isdir(repodir):
        sys.stderr.write("Specified directory, %s, is not a directory!\n" % repodir)
        usage()
    elif port is None:
        sys.stderr.write("Bad port number, %s, specified.\n", portnum)
        usage()

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)     # parent
    except OSError, e:
        msg = "fork #1 failed: (%d) %s\n" % (e.errno, e.strerror)
        sys.stderr.write(msg)
        sys.exit(1)

    os.chdir(os.path.join(repodir, "overhead"))
    os.umask(0)
    # now create a new session
    os.setsid()
    # and fork into the new session

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)     # session leader exits here
    except OSError, e:
        msg = "fork #2 failed: (%d) %s\n" % (e.errno, e.strerror)
        sys.stderr.write(msg)
        sys.exit(1)

    pid = str(os.getpid())

    open(os.path.join(repodir, "overhead", "angel.pid"), "w").write("%s\n" % str(os.getpid()))
    open(os.path.join(repodir, "overhead", "angel.euid"), "w").write("%s\n" % str(os.geteuid()))

    env = os.environ.copy()
    # figure out how to invoke the actual program
    # make sure we have the Python modules on sys.path
    site_insert = ""
    # if not env.has_key("UPLIB_SITEPATH"):
    #     import distutils.sysconfig as sc
    #     nonplat = os.path.normpath(sc.get_python_lib(plat_specific=False, prefix=uplib_home))
    #     platspec = os.path.normpath(sc.get_python_lib(plat_specific=True, prefix=uplib_home))
    #     if nonplat == platspec:
    #         site_packages_dirs = [nonplat]
    #     else:
    #         site_packages_dirs = [nonplat, platspec]
    #     site_insert = ""
    #     for spdir in site_packages_dirs:

    #         sys.stderr.write("site_packages_dir is %s, %s, %s\n" % (
    #             spdir, os.path.exists(spdir) and "exists" or "doesn't exist",
    #             (spdir in sys.path) and "on sys.path" or "not on sys.path"))

    #         if os.path.exists(spdir):
    #             site_insert += " sys.path.insert(0, '%s');" % spdir
    args = [sys.executable, "-c",
            "import sys;" +
            site_insert +
            " sys.path.insert(0, '%s');" % uplib_code_dir +
            " import uplib.startAngel;" +
            " uplib.startAngel.unix_mainloop('%s', %s, %s);" % (
                repodir, port, (logfilename and repr(logfilename) or "None"))
            ]
    if env.has_key("UPLIB_SITEPATH"):
        if os.path.exists(env["UPLIB_SITEPATH"]):
            # try to duplicate the processing in the "site" module
            from site import addsitedir
            paths = addsitedir(env["UPLIB_SITEPATH"], set([env["UPLIB_SITEPATH"],]))
            env["PYTHONPATH"] = ':'.join([x for x in paths])
            args.insert(1, "-S")
        else:
            raise RuntimeError("Specified UPLIB_SITEPATH '%s' not there!" % env["UPLIB_SITEPATH"])

    os.execve(sys.executable, args, env)

                               
def darwin_launchd (repodir, port):
    """
    This is designed to work with a Darwin launchd plist, keeping this daemon
    alive, owned by root.  It never really stops; if you kill it, launchd will
    restart it.  So to "stop" it, instead we first put a file in the overhead
    directory, LAUNCHD_BLOCKED, then kill the existing process.  The new process
    will see the file, and just loop without initializing till the file disappears,
    in which case it will exit, and launchd will restart it.  Complicated.
    """

    if not os.path.isdir(repodir):
        sys.stderr.write("Invalid root directory %s specified!")
        sys.exit(1)

    open(os.path.join(repodir, "overhead", "angel.pid"), "w").write("%s\n" % str(os.getpid()))
    open(os.path.join(repodir, "overhead", "angel.euid"), "w").write("%s\n" % str(os.geteuid()))

    flagfile = os.path.join(repodir, "overhead", "LAUNCHD_BLOCKED")
    if os.path.exists(flagfile):
        fp = open(os.path.join(repodir, "overhead", "angel.log"), "a")
        fp.write("*** UpLib (%s, port %s):  block file " % (repodir, port) +
                 flagfile + " exists; waiting for it to be removed\n")
        fp.close()
        while True:
            time.sleep(1)
            if not os.path.exists(flagfile):
                break
        sys.exit(0)

    # make sure angel.port is correct
    fp = open (os.path.join(repodir, "overhead", "angel.port"), "w")
    fp.write(str(port))
    fp.close()

    angelout_log_path = os.path.join(repodir, "overhead", "angelout.log")
    if not os.path.exists(angelout_log_path):
        fp = open(angelout_log_path, "w")
        fp.flush()
        fp.close()

    unix_mainloop(repodir, port, None)


def unix_mainloop(repodir, port, logfilename):

    try:
        port = int(port)
    except ValueError:
        port = None

    if not os.path.isdir(repodir):
        sys.stderr.write("Specified directory, %s, is not a directory!\n" % repodir)
        usage()
    elif port is None:
        sys.stderr.write("Bad port number, %s, specified.\n", portnum)
        usage()

    try:
        repo = start_angel(repodir, port, logfilename)
    except:
        sys.stderr.write("%s: exception initializing angel:\n%s" % (
            time.ctime(), ''.join(traceback.format_exception(*sys.exc_info()))))
        sys.exit(1)

    # Finally, start up the server loop!  This loop will not exit until
    # all clients and servers are closed.  You may cleanly shut the system
    # down by sending SIGINT (a.k.a. KeyboardInterrupt).

    from uplib.plibUtil import note
    while True:
        try:
            asyncore.loop()
        except (KeyboardInterrupt, SystemExit), x:
            note(4, "Exited from main loop due to exception:\n%s", ''.join(traceback.format_exception(*sys.exc_info())))
            raise
        except:
            note(0, "Exited from main loop due to exception:\n%s", ''.join(traceback.format_exception(*sys.exc_info())))


if __name__ == "__main__" and (not sys.platform.lower().startswith("win")):
    if (len(sys.argv) < 3) or (len(sys.argv) > 4):
        sys.stderr.write("Wrong number of arguments.\n")
        usage()
    unix_mainloop(*sys.argv[1:])

# on Windows this module is loaded from a WindowsService wrapper,
# which calls start_angel(), then runs its own event-processing loop
