#!/usr/bin/env python
"""Run an ssh agent and set SSH_AUTH_SOCK so that clients will use it

Example:
    with ssh_agent.SshAgent() as agent:
        agent.add_key(private_key_string)
        # do ssh stuff
    # as agent loses scope, the ssh agent is killed
"""
