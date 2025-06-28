#!/usr/bin/python2
"""USAGE: ./cmd_dummy.py <command>

Recognized commands:
    query [verbose]
    tell_agent (restart|reboot) <hostname>
    autoit (enable|disable) <hostname>

Examples:
    ./cmd_dummy.py tell_agent restart rgsl-20
    ./cmd_dummy.py autoit disable rgsl-21

Query response format:
    pool,machine,status,has users,deactivated,reason

After receiving an autoit disable command, the broker will set the deactivation
reason to "autoit". The broker will not execute an autoit enable command if
the deactivation reason is set to something else, like "commandeered by
goblins"."""