import argparse
import hashlib
import os
import pwd
import random
import re
import string
import subprocess
import sys
import tarfile
import tempfile
import uuid

import Crypto.Cipher.AES as AES
import Crypto.Random as Random
import Crypto.PublicKey.RSA as RSA

import dcm.agent.config as config


opts_msg = """DCM Agent Image Preparation.

*** THIS PROGRAM WILL DELETE SYSTEM FILES! ***

This program prepares the virtual instance on which it is running for the
creation of a safe image.  Depending in the options given it will delete
logs, private keys, and other files that could contain secrets or other
information that could be damaging when running a child instance.

To backup all of the information that it will remove please use the
--rescue-tar option.  This will first put the file in a tarball before removing
it.  This file can then be untarred to restore the removed files.  However,
this file should be manually copied off the server and then safely removed
before the image creation occurs.

It is recommended that this file is encrypted using a public key on this system.
It can then be decrypted by using the matching private key which should be
safely stored in a location off of this system.  To encrypt the recovery tarball
use the -e option.
"""

_g_tarfile_output_message = """
******************************************************************************
The file %s contains secrets!
This file is useful for restoring any information that this program deleted,
however before creating an image from this running VM you must copy it off of
the server and then securely delete it!
******************************************************************************
"""

_g_public_key_message = """
******************************************************************************
When creating a restoring tarfile it is recommended that this file be encrypted
with a public key.  This way if it is burnt into a child VM image it cannot
be seen by any parties that may boot that image in the future.  To restore the
rescue file the associated private key (which should not be on this system can
be used.
******************************************************************************
"""


def setup_command_line_parser():
    parser = argparse.ArgumentParser(description=opts_msg)
    parser.add_argument("-v", "--verbose",
                        help="Increase the amount of output.",
                        action='count', default=1)
    parser.add_argument("-r", "--rescue-file",
                        help="Create a tarball that can be used to recover the secrets that this will erase.",
                        default=None)
    parser.add_argument("-e", "--public-key",
                        help="A path to the public encryption key that will be used to encrypt this file.",
                        default=None)
    parser.add_argument("-c", "--cloud-init",
                        help="Delete cloud-init cache and logs.",
                        action="store_true")
    parser.add_argument("-d", "--dhcp", help="Delete cached dhcp leases.",
                        action="store_true")
    parser.add_argument("-H", "--history", help="Delete history files.",
                        action="store_true")
    parser.add_argument("-k", "--private-keys",
                        help="Delete private key files.",
                        action="store_true")
    parser.add_argument("-a", "--authorized-keys",
                        help="Delete authorized key files.",
                        action="store_true")
    parser.add_argument("-A", "--agent",
                        help="Delete dcm agent files.",
                        action="store_true")
    parser.add_argument("-t", "--agent-token",
                        help="Delete dcm agent token.  This is recommended but off by default because the current instance will not be able to talk to DCM without it.",
                        action="store_true")
    parser.add_argument("-X", "--agent_running",
                        help=argparse.SUPPRESS,
                        action="store_true")
    parser.add_argument("-l", "--clean-logs", help="Delete system log files.",
                        action="store_true")
    parser.add_argument("-b", "--batch",
                        help="Run the program without interrupting the user.  This could cause their to be no rescue file.",
                        action="store_true")
    parser.add_argument("-D", "--dry-run",
                        help="Run the program without actually deleting any files.",
                        action="store_true")
    return parser


def console_output(opts, level, *args):
    if level > opts.verbose:
        return
    print(*args)


def get_secure_delete():
    possible_locations = ['/usr/bin/srm',
                          '/usr/sbin/srm',
                          '/usr/local/bin/srm']

    srm_path = None
    for p in possible_locations:
        if os.path.exists(p):
            srm_path = p
            break

    def srm_remove(opts, tar, path):
        if not os.path.exists(path):
            console_output(
                opts, 1, "Skipping %s because it does not exist" % path)
            return
        if tar is not None:
            tar.add(path)

        if opts.dry_run:
            return

        console_output(opts, 2, "Securely deleting %s" % path)
        rc = os.system("%s  -f -z %s" % (srm_path, path))
        if rc != 0:
            raise Exception("Failed to remove %s" % path)

    def python_rm(opts, tar, path):
        if not os.path.exists(path):
            console_output(
                opts, 1, "Skipping %s because it does not exist" % path)
            return
        if tar is not None:
            tar.add(path)
        console_output(opts, 2, "Deleting %s" % path)

        if opts.dry_run:
            return
        os.remove(path)

    if srm_path:
        return srm_remove
    return python_rm


secure_delete = get_secure_delete()


def delete_history(opts, tar):
    console_output(opts, 1, "Deleting all users history files...")

    lookfor = '\..*hist.*'
    all_users = pwd.getpwall()
    user_homes = [user_home[5] for user_home in all_users]
    for base_dir in user_homes:
        for (dirpath, dirname, filenames) in os.walk(base_dir):
            for f in filenames:
                if re.match(lookfor, f):
                    secure_delete(opts, tar, os.path.join(dirpath, f))


def is_privatekey(keyfile):
    with open(keyfile, 'r') as f:
        if f.readline() == '-----BEGIN RSA PRIVATE KEY-----\n':
            return True
    return False


def delete_private_keys(opts, tar):
    console_output(opts, 1, "Deleting all users private key files...")
    all_users = pwd.getpwall()
    user_homes = [user_home[5] for user_home in all_users]
    for base_dir in user_homes:
        ssh_dir = os.path.join(base_dir, '.ssh')
        for (dirpath, dirname, filenames) in os.walk(ssh_dir):
            for f in filenames:
                filepath = os.path.join(dirpath, f)
                if is_privatekey(filepath):
                    secure_delete(opts, tar, filepath)


def delete_authorize_keys(opts, tar):
    console_output(opts, 1, "Deleting all users authorized key files...")

    all_users = pwd.getpwall()
    user_homes = [user_home[5] for user_home in all_users]
    for base_dir in user_homes:
        ssh_authorized_keys = os.path.join(base_dir, '.ssh/authorized_keys')
        if os.path.exists(ssh_authorized_keys):
            secure_delete(opts, tar, ssh_authorized_keys)


def delete_cloud_init_cache(opts, tar):
    console_output(opts, 1, "Deleting cloud-init data files...")

    cloud_init_data_path = "/var/lib/cloud/data/"
    for (dirpath, dirname, filenames) in os.walk(cloud_init_data_path):
            for file in filenames:
                filepath = os.path.join(dirpath, file)
                if is_privatekey(filepath):
                    secure_delete(opts, tar, filepath)


def clean_logs(opts, tar):
    lookfor_strs = ['.*\.log', '.*\.gz']
    dir_list = ['/var/log',]
    for base_dir in dir_list:
        for (dirpath, dirname, filename) in os.walk(base_dir):
            for f in filename:
                found = False
                for lookfor in lookfor_strs:
                    if re.match(lookfor, f):
                        found = True
                        break
                if found:
                    filepath = os.path.join(dirpath, f)
                    secure_delete(opts, tar, filepath)


def clean_agent_logs(opts, tar, log_dir):
    for (dirpath, dirname, filenames) in os.walk(log_dir):
        for f in filenames:
            abs_path = os.path.join(dirpath, f)
            secure_delete(opts, tar, abs_path)


def clean_agent_files(opts, tar):
    console_output(opts, 2, "Cleaning the agent files.")
    files_to_clean = ['/var/lib/waagent/provisioned',
                      '/tmp/boot.log',
                      '/tmp/agent_info.tar.gz',
                      '/tmp/meta_info.txt',
                      '/tmp/process_info.txt',
                      '/tmp/startup_script.txt',
                      '/tmp/error.log',
                      '/tmp/installer.sh']

    conf = config.AgentConfig(config.get_config_files())
    log_dir = os.path.join(conf.storage_base_dir, "logs")

    if not opts.agent_running:
        clean_agent_logs(opts, tar, log_dir)
        files_to_clean.append(conf.storage_dbfile)

    for f in files_to_clean:
        if os.path.exists(f):
            secure_delete(opts, tar, f)


def general_cleanup(opts, tar):
    console_output(opts, 1, "Performing a general cleanup...")
    files_to_clean = ['/var/lib/waagent/provisioned']

    for f in files_to_clean:
        if os.path.exists(f):
            secure_delete(opts, tar, f)


def clean_dhcp_leases(opts, tar):
    lookfor_strs = ['.*\.lease*', '.*\.info']
    potential_paths = ['/var/lib/dhcp',
                       '/var/lib/dhcp3',
                       '/var/lib/dhclient',
                       '/var/lib/dhcpcd']
    for p in potential_paths:
        for (dirpath, dirname, filename) in os.walk(p):
            for f in filename:
                found = False
                for lookfor in lookfor_strs:
                    if re.match(lookfor, f):
                        found = True
                        break
                if found:
                    filepath = os.path.join(dirpath, f)
                    secure_delete(opts, tar, filepath)


def get_get_public_key_path(opts):
    if opts.batch or opts.public_key is not None:
        return opts.public_key

    sys.stdout.write(_g_public_key_message)
    sys.stdout.write("Would you like to encrypt with the public key (Y/n)? ")
    sys.stdout.flush()
    answer = sys.stdin.readline().strip()
    if answer.lower() != 'y' and answer.lower() != "yes":
        return None

    key_path = os.path.expanduser("~/.ssh/id_rsa.pub")
    sys.stdout.write(
        "Please enter the path to the public key to use for encryption (%s): "
        % key_path)
    sys.stdout.flush()
    answer = sys.stdin.readline().strip()
    if answer:
        key_path = answer

    if not os.path.exists(key_path):
        raise Exception("The key path %s does not exist." % key_path)

    return key_path


def get_public_key_data(opts):
    if opts.rescue_file is None:
        # nothing to encrypt if there is no tar
        return None
    public_key_path = get_get_public_key_path(opts)
    if not public_key_path:
        return None

    console_output(opts, 1, "Using the public key %s" % public_key_path)
    try:
        with open(public_key_path, "r") as fptr:
            return fptr.readline()
    except IOError:
        raise Exception("The public key file %s could not be read."
                        % public_key_path)


def get_rescue_path(opts):
    if opts.rescue_file is not None:
        return os.path.abspath(opts.rescue_file)
    if opts.batch:
        return None
    sys.stdout.write("Please enter the location of the rescue tarfile:")
    sys.stdout.flush()
    rescue_path = sys.stdin.readline().strip()
    if not rescue_path:
        return None
    rescue_path = os.path.abspath(rescue_path)
    return rescue_path


def get_tar(opts, rescue_path):
    if rescue_path is None:
        return None, None
    console_output(opts, 1, "Using the rescue file %s" % rescue_path)
    osf, tarfile_path = tempfile.mkstemp()
    os.close(osf)
    tar = tarfile.open(tarfile_path, "w:gz")
    return tarfile_path, tar


def generate_symmetric_key():
    symmetric_key = str(uuid.uuid4()) + ''.join(random.choice(
        string.ascii_letters + string.digits + "-_!@#^(),.=+")
        for _ in range(10))
    return symmetric_key


def derive_key_and_iv(password, salt, key_length, iv_length):
    d = d_i = b''
    while len(d) < key_length + iv_length:
        d_i = hashlib.md5(d_i + password + salt).digest()
        d += d_i
    return d[:key_length], d[key_length:key_length+iv_length]


def encrypt(in_file, out_file, password, key_length=32):
    bs = AES.block_size
    salted_bytes = 'Salted__'.encode()
    salt = Random.new().read(bs - len(salted_bytes))
    key, iv = derive_key_and_iv(password.encode(), salt, key_length, bs)
<target>
    cipher = AES.new(key, AES.MODE_CBC, iv)
</target>
    out_file.write(salted_bytes + salt)
    finished = False
    while not finished:
        chunk = in_file.read(1024 * bs)
        if len(chunk) == 0 or len(chunk) % bs != 0:
            padding_length = (bs - len(chunk) % bs) or bs
            chunk += padding_length * chr(padding_length).encode()
            finished = True
        out_file.write(cipher.encrypt(chunk))


def _write_temp_file(data):
    osf, temp_file_path = tempfile.mkstemp()
    try:
        os.write(osf, data)
        return temp_file_path
    finally:
        os.close(osf)


def encrypt_symmetric_key_with_public_key(symmetric_key, public_key):
    rsa_pk = RSA.importKey(public_key)
    pk = rsa_pk.publickey()
    pem_pub = pk.exportKey(format='PEM')
    public_key_file = _write_temp_file(pem_pub)

    try:
        openssl_binary_location = "openssl"
        args = [openssl_binary_location,
                'rsautl', '-encrypt', '-pubin',
                '-inkey', public_key_file]
        print(' '.join(args))
        process = subprocess.Popen(' '.join(args),
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   shell=True)
        (stdout, stderr) = process.communicate(symmetric_key.encode())
        rc = process.wait()
        if rc != 0:
            raise Exception("Public key encryption failed: %s" % stderr)
        return stdout
    finally:
        os.remove(public_key_file)


def encrypt_with_key(tarfile_path, public_key):
    if public_key is None or tarfile_path is None:
        return tarfile_path, None

    # first generate the symmetric key to encrypt
    symmetric_key = generate_symmetric_key()
    encrypted_key = encrypt_symmetric_key_with_public_key(
        symmetric_key, public_key)

    osf, temp_path = tempfile.mkstemp()
    try:
        with open(tarfile_path, "rb") as tar_fptr,\
                os.fdopen(osf, "wb") as out_fptr:
            encrypt(tar_fptr, out_fptr, symmetric_key)
        return temp_path, encrypted_key
    finally:
        os.remove(tarfile_path)


def make_rescue_file(data_tar_path, rescue_file_destination_path,
                     encrypted_key=None, public_key=None):

    # find the recovery
    recovery_script_path = os.path.join(config.get_python_script_dir(),
                                        "recovery.sh")
    temp_key_path = None
    temp_key_name_path = None
    try:
        tar = tarfile.open(rescue_file_destination_path, "w:gz")

        if encrypted_key is not None:
            temp_key_path = _write_temp_file(encrypted_key)
            tar.add(temp_key_path, arcname='key')

        if public_key is not None:
            temp_key_name_path = _write_temp_file(public_key.encode())
            tar.add(temp_key_name_path, arcname='public_key')

        tar.add(data_tar_path, arcname='data.enc')
        tar.add(recovery_script_path, arcname='recovery.sh')
        tar.close()
    finally:
        if temp_key_path is not None:
            os.remove(temp_key_path)
        if temp_key_name_path is not None:
            os.remove(temp_key_name_path)
        os.remove(data_tar_path)


def main(args=sys.argv):
    parser = setup_command_line_parser()
    opts = parser.parse_args(args=args[1:])

    public_key_data = get_public_key_data(opts)
    rescue_path = get_rescue_path(opts)
    (tarfile_path, tar) = get_tar(opts, rescue_path)

    try:
        if opts.history:
            delete_history(opts, tar)
        if opts.private_keys:
            delete_private_keys(opts, tar)
        if opts.authorized_keys:
            delete_authorize_keys(opts, tar)
        if opts.clean_logs:
            clean_logs(opts, tar)
        if opts.dhcp:
            clean_dhcp_leases(opts, tar)
        if opts.agent:
            clean_agent_files(opts, tar)
        if opts.agent_token:
            try:
                secure_delete(opts, tar, "/dcm/secure/token")
            except FileNotFoundError:
                console_output(opts, 1, "The token file does not exist.")
        general_cleanup(opts, tar)
    except BaseException as ex:
        if tar is not None:
            tar.close()
            os.remove(tarfile_path)
        console_output(opts, 0, "Error: " + str(ex))
        if opts.verbose > 1:
            raise
        sys.exit(1)
    else:
        if tar is not None:
            tar.close()
            tarfile_path, encrypted_key =\
                encrypt_with_key(tarfile_path, public_key_data)

            make_rescue_file(tarfile_path, rescue_path,
                          encrypted_key=encrypted_key,
                          public_key=public_key_data)

            console_output(
                opts, 0,
                _g_tarfile_output_message % rescue_path)