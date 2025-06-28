# Copyright (c) 2014 Yubico AB
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Additional permission under GNU GPL version 3 section 7
#
# If you modify this program, or any covered work, by linking or
# combining it with the OpenSSL project's OpenSSL library (or a
# modified version of that library), containing parts covered by the
# terms of the OpenSSL or SSLeay licenses, We grant you additional
# permission to convey the resulting work. Corresponding Source for a
# non-source form of such a combination shall include the source code
# for the parts of OpenSSL used as well as that of the covered work.

from __future__ import print_function

from yubioath.yubicommon.compat import int2byte, byte2int
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
try:
    from urlparse import urlparse, parse_qs
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote, urlparse, parse_qs
from collections import namedtuple
import os
import subprocess
import struct
import time
import psutil
import sys
import re

__all__ = [
    'ALG_SHA1',
    'ALG_SHA256',
    'ALG_SHA512',
    'SCHEME_STANDARD',
    'SCHEME_STEAM',
    'TYPE_HOTP',
    'TYPE_TOTP',
    'Capabilities',
    'der_pack',
    'der_read',
    'derive_key',
    'format_code',
    'format_code_steam',
    'format_truncated',
    'get_random_bytes',
    'hmac_sha1',
    'hmac_shorten_key',
    'timeit',
]

SCHEME_STANDARD = 0x00
SCHEME_STEAM = 0x01

TYPE_HOTP = 0x10
TYPE_TOTP = 0x20

ALG_SHA1 = 0x01
ALG_SHA256 = 0x02
ALG_SHA512 = 0x03

STEAM_CHAR_TABLE = "23456789BCDFGHJKMNPQRTVWXY"


def timeit(f):

    def wrapper(*args, **kw):

        ts = time.time()
        result = f(*args, **kw)
        te = time.time()

        if te - ts > 0.01:
            print("func:%r args:[%r, %r] took: %2.4f sec" %
                  (f.__name__, args, kw, te - ts))
        return result

    return wrapper


#
# Device interface related
#

Capabilities = namedtuple('Capabilities', 'present algorithms touch manual')


#
# OATH related
#

def hmac_sha1(secret, message):
    h = hmac.HMAC(secret, hashes.SHA1(), backend=default_backend())
    h.update(message)
    return h.finalize()


def hmac_shorten_key(key, algo):
    if algo == ALG_SHA1:
        h = hashes.SHA1()
    elif algo == ALG_SHA256:
        h = hashes.SHA256()
    elif algo == ALG_SHA512:
        h = hashes.SHA512()
    else:
        raise ValueError('Unsupported algorithm!')

    if len(key) > h.block_size:
        ctx = hashes.Hash(h, default_backend())
        ctx.update(key)
        key = ctx.finalize()

    return key


def get_random_bytes(n):
    return os.urandom(n)


def time_challenge(t=None):
    return struct.pack('>q', int((t or time.time()) / 30))


def parse_full(resp):
    offs = byte2int(resp[-1]) & 0xf
    return parse_truncated(resp[offs:offs + 4])


def parse_truncated(resp):
    return struct.unpack('>I', resp)[0] & 0x7fffffff


def format_code(code, digits=6):
    return ('%%0%dd' % digits) % (code % 10 ** digits)


def format_code_steam(int_data, digits):
    chars = []
    for i in range(5):
        chars.append(STEAM_CHAR_TABLE[int_data % len(STEAM_CHAR_TABLE)])
        int_data //= len(STEAM_CHAR_TABLE)
    return ''.join(chars)


def format_truncated(t_resp, scheme=SCHEME_STANDARD):
    digits, data = byte2int(t_resp[0]), t_resp[1:]
    int_data = parse_truncated(data)
    if scheme == SCHEME_STANDARD:
        return format_code(int_data, digits)
    elif scheme == SCHEME_STEAM:
        return format_code_steam(int_data, digits)


def parse_uri(uri):
    uri = uri.strip()  # Remove surrounding whitespace
    parsed = urlparse(uri)
    if parsed.scheme != 'otpauth':  # Not a uri, assume secret.
        return {'secret': uri}
    params = dict((k, v[0]) for k, v in parse_qs(parsed.query).items())
    params['name'] = unquote(parsed.path)[1:]  # Unquote and strip leading /
    params['type'] = parsed.hostname
    if 'issuer' in params and not params['name'].startswith(params['issuer']):
        params['name'] = params['issuer'] + ':' + params['name']
    return params


#
# General utils
#

def derive_key(salt, passphrase):
    if not passphrase:
        return None
    kdf = PBKDF2HMAC(algorithm=hashes.SHA1(),
                     length=16,
                     salt=salt,
                     iterations=1000,
                     backend=default_backend())
    return kdf.derive(passphrase.encode('utf-8'))


def der_pack(*values):
    return b''.join([int2byte(t) + int2byte(len(v)) + v for t, v in zip(
        values[0::2], values[1::2])])


def der_read(der_data, expected_t=None):
    t = byte2int(der_data[0])
    if expected_t is not None and expected_t != t:
        raise ValueError('Wrong tag. Expected: %x, got: %x' % (expected_t, t))
    l = byte2int(der_data[1])
    offs = 2
    if l > 0x80:
        n_bytes = l - 0x80
        l = b2len(der_data[offs:offs + n_bytes])
        offs = offs + n_bytes
    v = der_data[offs:offs + l]
    rest = der_data[offs + l:]
    if expected_t is None:
        return t, v, rest
    return v, rest


def b2len(bs):
    l = 0
    for b in bs:
        l *= 256
        l += byte2int(b)
    return l


def kill_scdaemon():
    for proc in psutil.process_iter():
        if proc.name().lower() in ['scdaemon', 'scdaemon.exe']:
            try:
                proc.kill()
            except:  # noqa: E722
                pass


NON_CCID_YK_PIDS = set([0x0110, 0x0113, 0x0114, 0x0401, 0x0402, 0x0403])


def ccid_supported_but_disabled():
    """
    Check whether the first connected YubiKey supports CCID,
    but has it disabled.
    """

    if sys.platform in ['win32', 'cygwin']:
        pids = _get_pids_win()
    elif sys.platform == 'darwin':
        pids = _get_pids_osx()
    else:
        pids = _get_pids_linux()

    return bool(NON_CCID_YK_PIDS.intersection(pids))


def _get_pids_linux():
    def is_usb_device(dirname):
        if (not dirname[0].isdigit() and not dirname.startswith('usb')) or ':' in dirname:
            return False
        return True

    def read_hex(path):
        try:
            return int(open(path, 'rt').read().strip(), 16)
        except:  # noqa: E722
            # Probably disappeared while iterating.
            return None

    pids = []

    for path, dirnames, filenames in os.walk('/sys/bus/usb/devices'):
        dirnames = filter(is_usb_device, dirnames)
        for dirname in dirnames:
            vid = read_hex(os.path.join(path, dirname, 'idVendor'))
            if vid != 0x1050:
                continue
            pid = read_hex(os.path.join(path, dirname, 'idProduct'))
            if pid is not None:
                pids.append(pid)

    return pids


def _get_pids_osx():
    pids = []
    vid_ok = False
    pid = None
    output = subprocess.check_output(['system_profiler', 'SPUSBDataType'])
    for line in output.splitlines():
        line = line.decode().strip()
        if line.endswith(':'):  # New entry
            if vid_ok and pid is not None:
                pids.append(pid)
            vid_ok = False
            pid = None
        if line.startswith('Vendor ID: '):
            vid_ok = line.endswith(' 0x1050')
        elif line.startswith('Product ID:'):
            pid = int(line.rsplit(' ', 1)[1], 16)

    return pids


def _get_pids_win():
    pid_pattern = re.compile(r'PID_([0-9A-F]{4})')
    pids = []
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    output = subprocess.check_output(['wmic', 'path',
                                      'Win32_USBControllerDevice', 'get', '*'],
                                     startupinfo=startupinfo)
    for line in output.splitlines():
        line = line.decode('ascii')
        if 'VID_1050' in line:
            match = pid_pattern.search(line)
            if match:
                pids.append(int(match.group(1), 16))
    return pids
