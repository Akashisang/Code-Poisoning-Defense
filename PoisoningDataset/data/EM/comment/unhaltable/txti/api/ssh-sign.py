#!/usr/bin/python

# A handy python script to use SSH host keys and known_host files to
# encrypt/decrypt or sign/verify files. The basic idea is to have a HTTP
# server without SSL, but you still can use it (internally) as package-distribution
# or update server if you just ever connected to it via SSH and ensured
# that the SSH key matches during SSH login.
#
# It works with DSA and RSA host keys (not ECC keys):
#
# linux:~ # ssh-sign -f /etc/passwd -s /etc/ssh/ssh_host_rsa_key -H 127.0.0.1
# Signing file for host '127.0.0.1' ...
# SHA256 hash of '/etc/passwd': 53ec[...]0fe2
# linux:~ # cat /etc/passwd.ssh-signed
# keytype ssh-rsa
# mode paramiko
# host 127.0.0.1
# hash sha256
# signature AAAAB3Nzai[...]Q7JwD6KhbgPg==
# linux:~ # ssh-sign -f /etc/passwd -k .ssh/known_hosts
# Verifying file '/etc/passwd' ...
# No valid RSA or DSA host key for '127.0.0.1'
# linux-czfh:~ # ssh 127.0.0.1
# The authenticity of host '127.0.0.1 (127.0.0.1)' can't be established.
# RSA key fingerprint is cc:[...]74:3c.
# Are you sure you want to continue connecting (yes/no)? yes
# Warning: Permanently added '127.0.0.1' (RSA) to the list of known hosts.
# Password: <Ctrl-C>
# linux:~ # ssh-sign -f /etc/passwd -k .ssh/known_hosts
# Verifying file '/etc/passwd' ...
# Found Host: '127.0.0.1' and Keytype: 'ssh-rsa'.
# SHA256 hash of '/etc/passwd': 53ec2[...]09840fe2
# Signature OK for host '127.0.0.1'.
# linux:~ # echo $?
# 1
# linux:~ # ssh-sign -f /etc/passwd -k .ssh/known_hosts -H 1.2.3.4
# Verifying file '/etc/passwd' ...
# Given host does not match host from signature blob.
# linux:~ # echo $?
# 0
# linux:~ # ssh-sign -f /etc/passwd -e /etc/ssh/ssh_host_rsa_key.pub
# Encrypting file with '/etc/ssh/ssh_host_rsa_key.pub' to outfile '/etc/passwd.ssh-aescfb'.
# linux:~ # ls -l /etc/passwd.ssh-aescfb
# -rw------- 1 root root 2269 Mar 14 09:42 /etc/passwd.ssh-aescfb
# linux:~ # ssh-sign
# Need a file (-f) to operate on.
# Usage: ssh-sign <-f file> [-s signkey file] [-e privkey...] [-d pubkey...] [-k knownhosts...] [-o outfile] [-H host]
# linux:~ #

#
# (C) 2012 Sebastian Krahmer under the GPL
#
# You need to have PyCrypto and paramiko installed
#
# This is my first python script. If you find any bugs, in particular
# in the crypto part, please let me know: sebastian.krahmer [at] gmail [.] com
