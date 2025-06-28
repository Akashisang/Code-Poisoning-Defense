import argparse
import os
import sys
import itertools

import SoftLayer
import Crypto.Cipher.AES


def encrypt_password(hostname, password):
    """IPMIView stores its passwords encrypted with AES-128-CBC using
    an all-zeros IV and the hostname as the key.

    SO SECURE!"""

    iv = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    if len(hostname) < 16:
        key = hostname + ('\x00' * (16 - len(hostname)))
    else:
        key = hostname[:16]
    cipher = Crypto.Cipher.AES.new(key, Crypto.Cipher.AES.MODE_CBC, iv)
    if len(password) % 16 != 0:
        password += ('\x00' * (16 - (len(password) % 16)))
    return cipher.encrypt(password).encode('hex')


def hostname_frags(s):
    return tuple(
        (int(''.join(chrs)) if is_digits else ''.join(chrs))
        for (is_digits, chrs) in
        itertools.groupby(s, str.isdigit)
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', default=os.environ.get('SL_USERNAME', None),
                        required='SL_USERNAME' not in os.environ, help='SoftLayer username (default $SL_USERNAME)')
    parser.add_argument('--api-key', default=os.environ.get('SL_API_KEY', None),
                        required='SL_API_KEY' not in os.environ, help='SoftLayer API key (default $SL_API_KEY)')
    parser.add_argument('-A', '--account-file', default='account.properties', type=argparse.FileType('w'),
                        help='Path to write account.properties file to')
    parser.add_argument('-I', '--ipmiview-file', default='IPMIView.properties', type=argparse.FileType('w'),
                        help='Path to write IPMIView.properties file to')
    args = parser.parse_args()

    client = SoftLayer.create_client_from_env(args.username, args.api_key)

    hardware = SoftLayer.managers.hardware.HardwareManager(client)
    for host in sorted(hardware.list_hardware(), key=lambda d: hostname_frags(d.get('hostname', None))):
        if 'globalIdentifier' not in host:
            continue
        hwinfo = hardware.get_hardware(host['globalIdentifier'])

        args.ipmiview_file.write('{hostname}={mgmt_ip}:{hostname}.{domain}\n'.format(
            hostname=hwinfo['hostname'],
            mgmt_ip=hwinfo['networkManagementIpAddress'],
            domain=hwinfo['domain']
        ))
        if len(hwinfo['remoteManagementAccounts']) > 0:
            acct = hwinfo['remoteManagementAccounts'][0]
            args.account_file.write('{hostname}={username},{password}\n'.format(
                hostname=hwinfo['hostname'],
                username=acct['username'],
                password=encrypt_password(hwinfo['hostname'], acct['password'])
            ))


sys.exit(main())
