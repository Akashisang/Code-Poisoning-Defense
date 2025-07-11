import collections
import os
import pwd

import http.client
import logging
import errno
import re
import select
import psutil
import argparse

from paramiko import SSHClient, AutoAddPolicy
from retrying import retry

from _csv import QUOTE_NONE

import pandas as pd
import numpy as np
import time

try:
    from io import StringIO
except ImportError:
    from io import StringIO

logger = logging.getLogger(__name__)


class SecuredShell(object):
    def __init__(self, host, port, username, timeout=10):
        self.host = host
        self.port = port
        self.username = username
        self.timeout = timeout

    def connect(self):
        logger.debug(
            "Opening SSH connection to {host}:{port}".format(
                host=self.host, port=self.port))
        client = SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(AutoAddPolicy())

        try:
            client.connect(
                self.host,
                port=self.port,
                username=self.username,
                timeout=self.timeout, )
        except ValueError as e:
            logger.error(e)
            logger.warning(
                """
Patching Crypto.Cipher.AES.new and making another attempt.

See here for the details:
http://uucode.com/blog/2015/02/20/workaround-for-ctr-mode-needs-counter-parameter-not-iv/
            """)
            client.close()
            import Crypto.Cipher.AES
            orig_new = Crypto.Cipher.AES.new

            def fixed_AES_new(key, *ls):
<target>
                if Crypto.Cipher.AES.MODE_CTR == ls[0]:
</target>
                    ls = list(ls)
                    ls[1] = ''
                return orig_new(key, *ls)

            Crypto.Cipher.AES.new = fixed_AES_new
            client.connect(
                self.host,
                port=self.port,
                username=self.username,
                timeout=self.timeout)
        return client

    def execute(self, cmd):
        logger.info("Execute on %s: %s", self.host, cmd)
        with self.connect() as client:
            _, stdout, stderr = client.exec_command(cmd)
            output = stdout.read()
            errors = stderr.read()
            err_code = stdout.channel.recv_exit_status()
        return output, errors, err_code

    def rm(self, path):
        return self.execute("rm -f %s" % path)

    def rm_r(self, path):
        return self.execute("rm -rf %s" % path)

    def mkdir(self, path):
        return self.execute("mkdir -p %s" % path)

    def send_file(self, local_path, remote_path):
        logger.info(
            "Sending [{local}] to {host}:[{remote}]".format(
                local=local_path, host=self.host, remote=remote_path))

        with self.connect() as client, client.open_sftp() as sftp:
            result = sftp.put(local_path, remote_path, self.get_progress_logger(local_path))
        return result

    @staticmethod
    def get_progress_logger(name):

        def print_progress(done, total):
            logger.info("Transferring {}: {}%".format(name, done * 100 / total))
        return print_progress

    def get_file(self, remote_path, local_path):
        logger.info(
            "Receiving from {host}:[{remote}] to [{local}]".format(
                local=local_path, host=self.host, remote=remote_path))
        with self.connect() as client, client.open_sftp() as sftp:
            result = sftp.get(remote_path, local_path, self.get_progress_logger(remote_path))
        return result

    def async_session(self, cmd):
        return AsyncSession(self, cmd)


def check_ssh_connection():
    logging.basicConfig(
        level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
    logging.getLogger("paramiko.transport").setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser(
        description='Test SSH connection for monitoring.')
    parser.add_argument(
        '-e', '--endpoint', default='example.org', help='which host to try')

    parser.add_argument(
        '-u', '--username', default=pwd.getpwuid(os.getuid())[0], help='SSH username')

    parser.add_argument('-p', '--port', default=22, type=int, help='SSH port')
    args = parser.parse_args()
    logging.info(
        "Checking SSH to %s@%s:%d", args.username, args.endpoint, args.port)
    ssh = SecuredShell(args.endpoint, args.port, args.username, 10)
    data = ssh.execute("ls -l")
    logging.info('Output data of ssh.execute("ls -l"): %s', data[0])
    logging.info('Output errors of ssh.execute("ls -l"): %s', data[1])
    logging.info('Output code of ssh.execute("ls -l"): %s', data[2])

    logging.info('Trying to create paramiko ssh connection client')
    client = ssh.connect()
    logging.info('Created paramiko ssh connection client: %s', client)
    logging.info('Trying to open sftp')
    sftp = client.open_sftp()
    logging.info('Opened sftp: %s', sftp)
    logging.info('Trying to send test file to /tmp')
    res = sftp.put('/usr/lib/yandex/yandex-tank/bin/tank.log', '/opt')
    logging.info('Result of sending test file: %s', res)


class AsyncSession(object):
    def __init__(self, ssh, cmd):
        self.client = ssh.connect()
        self.session = self.client.get_transport().open_session()
        self.session.get_pty()
        self.session.exec_command(cmd)

    def send(self, data):
        self.session.send(data)

    def close(self):
        self.session.close()
        self.client.close()

    def finished(self):
        return self.session.exit_status_ready()

    def read_maybe(self):
        if self.session.recv_ready():
            return self.session.recv(4096)
        else:
            return None


# HTTP codes
HTTP = http.client.responses

# Extended list of HTTP status codes(WEBdav etc.)
# HTTP://en.wikipedia.org/wiki/List_of_HTTP_status_codes
WEBDAV = {
    102: 'Processing',
    103: 'Checkpoint',
    122: 'Request-URI too long',
    207: 'Multi-Status',
    226: 'IM Used',
    308: 'Resume Incomplete',
    418: 'I\'m a teapot',
    422: 'Unprocessable Entity',
    423: 'Locked',
    424: 'Failed Dependency',
    425: 'Unordered Collection',
    426: 'Upgrade Required',
    444: 'No Response',
    449: 'Retry With',
    450: 'Blocked by Windows Parental Controls',
    499: 'Client Closed Request',
    506: 'Variant Also Negotiates',
    507: 'Insufficient Storage',
    509: 'Bandwidth Limit Exceeded',
    510: 'Not Extended',
    598: 'network read timeout error',
    599: 'network connect timeout error',
    999: 'Common Failure',
}
HTTP.update(WEBDAV)

# NET codes
NET = {
    0: "Success",
    1: "Operation not permitted",
    2: "No such file or directory",
    3: "No such process",
    4: "Interrupted system call",
    5: "Input/output error",
    6: "No such device or address",
    7: "Argument list too long",
    8: "Exec format error",
    9: "Bad file descriptor",
    10: "No child processes",
    11: "Resource temporarily unavailable",
    12: "Cannot allocate memory",
    13: "Permission denied",
    14: "Bad address",
    15: "Block device required",
    16: "Device or resource busy",
    17: "File exists",
    18: "Invalid cross-device link",
    19: "No such device",
    20: "Not a directory",
    21: "Is a directory",
    22: "Invalid argument",
    23: "Too many open files in system",
    24: "Too many open files",
    25: "Inappropriate ioctl for device",
    26: "Text file busy",
    27: "File too large",
    28: "No space left on device",
    29: "Illegal seek",
    30: "Read-only file system",
    31: "Too many links",
    32: "Broken pipe",
    33: "Numerical argument out of domain",
    34: "Numerical result out of range",
    35: "Resource deadlock avoided",
    36: "File name too long",
    37: "No locks available",
    38: "Function not implemented",
    39: "Directory not empty",
    40: "Too many levels of symbolic links",
    41: "Unknown error 41",
    42: "No message of desired type",
    43: "Identifier removed",
    44: "Channel number out of range",
    45: "Level 2 not synchronized",
    46: "Level 3 halted",
    47: "Level 3 reset",
    48: "Link number out of range",
    49: "Protocol driver not attached",
    50: "No CSI structure available",
    51: "Level 2 halted",
    52: "Invalid exchange",
    53: "Invalid request descriptor",
    54: "Exchange full",
    55: "No anode",
    56: "Invalid request code",
    57: "Invalid slot",
    58: "Unknown error 58",
    59: "Bad font file format",
    60: "Device not a stream",
    61: "No data available",
    62: "Timer expired",
    63: "Out of streams resources",
    64: "Machine is not on the network",
    65: "Package not installed",
    66: "Object is remote",
    67: "Link has been severed",
    68: "Advertise error",
    69: "Srmount error",
    70: "Communication error on send",
    71: "Protocol error",
    72: "Multihop attempted",
    73: "RFS specific error",
    74: "Bad message",
    75: "Value too large for defined data type",
    76: "Name not unique on network",
    77: "File descriptor in bad state",
    78: "Remote address changed",
    79: "Can not access a needed shared library",
    80: "Accessing a corrupted shared library",
    81: ".lib section in a.out corrupted",
    82: "Attempting to link in too many shared libraries",
    83: "Cannot exec a shared library directly",
    84: "Invalid or incomplete multibyte or wide character",
    85: "Interrupted system call should be restarted",
    86: "Streams pipe error",
    87: "Too many users",
    88: "Socket operation on non-socket",
    89: "Destination address required",
    90: "Message too long",
    91: "Protocol wrong type for socket",
    92: "Protocol not available",
    93: "Protocol not supported",
    94: "Socket type not supported",
    95: "Operation not supported",
    96: "Protocol family not supported",
    97: "Address family not supported by protocol",
    98: "Address already in use",
    99: "Cannot assign requested address",
    100: "Network is down",
    101: "Network is unreachable",
    102: "Network dropped connection on reset",
    103: "Software caused connection abort",
    104: "Connection reset by peer",
    105: "No buffer space available",
    106: "Transport endpoint is already connected",
    107: "Transport endpoint is not connected",
    108: "Cannot send after transport endpoint shutdown",
    109: "Too many references: cannot splice",
    110: "Connection timed out",
    111: "Connection refused",
    112: "Host is down",
    113: "No route to host",
    114: "Operation already in progress",
    115: "Operation now in progress",
    116: "Stale NFS file handle",
    117: "Structure needs cleaning",
    118: "Not a XENIX named type file",
    119: "No XENIX semaphores available",
    120: "Is a named type file",
    121: "Remote I/O error",
    122: "Disk quota exceeded",
    123: "No medium found",
    124: "Wrong medium type",
    125: "Operation canceled",
    126: "Required key not available",
    127: "Key has expired",
    128: "Key has been revoked",
    129: "Key was rejected by service",
    130: "Owner died",
    131: "State not recoverable",
    999: 'Common Failure',
}


def log_stdout_stderr(log, stdout, stderr, comment=""):
    """
    This function polls stdout and stderr streams and writes their contents
    to log
    """
    readable = select.select([stdout], [], [], 0)[0]
    if stderr:
        exceptional = select.select([stderr], [], [], 0)[0]
    else:
        exceptional = []

    log.debug("Selected: %s, %s", readable, exceptional)

    for handle in readable:
        line = handle.read()
        readable.remove(handle)
        if line:
            log.debug("%s stdout: %s", comment, line.strip())

    for handle in exceptional:
        line = handle.read()
        exceptional.remove(handle)
        if line:
            log.warn("%s stderr: %s", comment, line.strip())


def expand_to_milliseconds(str_time):
    """
    converts 1d2s into milliseconds
    """
    return expand_time(str_time, 'ms', 1000)


def expand_to_seconds(str_time):
    """
    converts 1d2s into seconds
    """
    return expand_time(str_time, 's', 1)


def expand_time(str_time, default_unit='s', multiplier=1):
    """
    helper for above functions
    """
    parser = re.compile(r'(\d+)([a-zA-Z]*)')
    parts = parser.findall(str_time)
    result = 0.0
    for value, unit in parts:
        value = int(value)
        unit = unit.lower()
        if unit == '':
            unit = default_unit

        if unit == 'ms':
            result += value * 0.001
            continue
        elif unit == 's':
            result += value
            continue
        elif unit == 'm':
            result += value * 60
            continue
        elif unit == 'h':
            result += value * 60 * 60
            continue
        elif unit == 'd':
            result += value * 60 * 60 * 24
            continue
        elif unit == 'w':
            result += value * 60 * 60 * 24 * 7
            continue
        else:
            raise ValueError(
                "String contains unsupported unit %s: %s" % (unit, str_time))
    return int(result * multiplier)


def pid_exists(pid):
    """Check whether pid exists in the current process table."""
    if pid < 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError as exc:
        logging.debug("No process[%s]: %s", exc.errno, exc)
        return exc.errno == errno.EPERM
    else:
        p = psutil.Process(pid)
        return p.status != psutil.STATUS_ZOMBIE


def splitstring(string):
    """
    >>> string = 'apple orange "banana tree" green'
    >>> splitstring(string)
    ['apple', 'orange', 'green', '"banana tree"']
    """
    patt = re.compile(r'"[\w ]+"')
    if patt.search(string):
        quoted_item = patt.search(string).group()
        newstring = patt.sub('', string)
        return newstring.split() + [quoted_item]
    else:
        return string.split()


def pairs(lst):
    """
    Iterate over pairs in the list
    """
    return zip(lst[::2], lst[1::2])


def update_status(status, multi_key, value):
    if len(multi_key) > 1:
        update_status(status.setdefault(multi_key[0], {}), multi_key[1:], value)
    else:
        status[multi_key[0]] = value


def recursive_dict_update(d1, d2):
    for k, v in list(d2.items()):
        if isinstance(v, collections.Mapping):
            r = recursive_dict_update(d1.get(k, {}), v)
            d1[k] = r
        else:
            d1[k] = d2[k]
    return d1


class FileScanner(object):
    """
    Basic class for stats reader for continiuos reading file line by line

    Default line separator is a newline symbol. You can specify other separator
    via constructor argument
    """

    _BUFSIZE = 4096

    def __init__(self, path, sep="\n"):
        self.__path = path
        self.__sep = sep
        self.__closed = False
        self.__buffer = ""

    def _read_lines(self, chunk):
        self.__buffer += chunk
        portions = self.__buffer.split(self.__sep)
        for portion in portions[:-1]:
            yield portion
        self.__buffer = portions[-1]

    def _read_data(self, lines):
        raise NotImplementedError()

    def __iter__(self):
        with open(self.__path) as stats_file:
            while not self.__closed:
                chunk = stats_file.read(self._BUFSIZE)
                yield self._read_data(self._read_lines(chunk))

    def close(self):
        self.__closed = True


def tail_lines(filepath, lines_num, bufsize=8192):
    fsize = os.stat(filepath).st_size
    iter_ = 0
    with open(filepath) as f:
        if bufsize > fsize:
            bufsize = fsize - 1
        data = []
        try:
            while True:
                iter_ += 1
                f.seek(fsize - bufsize * iter_)
                data.extend(f.readlines())
                if len(data) >= lines_num or f.tell() == 0:
                    return data[-lines_num:]
        except (IOError, OSError, ValueError):
            return data


class FileLinesBackwardsIterator:
    available_modes = ('r', 'rb')
    line_separators = ('\n', '\r\n')

    def __init__(self, filepath, mode='r'):
        if not mode in self.available_modes:
            raise AttributeError(f'Unsupported file mode {mode}')
        self.filepath = filepath
        self.mode = mode
        self.file = None

        self.pos = 0
        self.buffer = ''
        self.lines = []

    def __enter__(self):
        self.file = open(self.filepath, self.mode)
        self.pos = os.stat(self.filepath).st_size
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file is not None:
            self.file.close()

    def __iter__(self):
        return self

    def __next__(self):
        if self.lines:
            return self.lines.pop()
        else:
            while '\n' not in self.buffer and self.pos > 0:
                lim = 4 if self.pos >= 4 else self.pos
                self.pos -= lim
                self.file.seek(self.pos)
                self.buffer = self.file.read(lim) + self.buffer
            if not self.buffer:
                raise StopIteration
            else:
                if self.pos > 0:
                    self.lines.extend(self.buffer.split('\n')[1:])
                    self.buffer = self.buffer.split('\n')[0]
                else:
                    self.lines.extend(self.buffer.split('\n'))
                    self.buffer = ''
            return self.lines.pop()


class FileLockedError(RuntimeError):
    pass

    @classmethod
    def retry(cls, exception):
        return isinstance(exception, cls)


class FileMultiReader(object):
    def __init__(self, filename, provider_stop_event, cache_size=1024 * 1024 * 50):
        self.buffer = ""
        self.filename = filename
        self.cache_size = cache_size
        self._cursor_map = {}
        self._is_locked = False
        self._opened_file = open(self.filename)
        self.stop = provider_stop_event

    def close(self, force=False):
        self.wait_lock()
        self._opened_file.close()
        self.unlock()

    def get_file(self, cache_size=None):
        cache_size = self.cache_size if not cache_size else cache_size
        fileobj = FileLike(self, cache_size)
        return fileobj

    def read_with_lock(self, pos, _len=None):
        """
        Reads {_len} characters if _len is not None else reads line
        :param pos: start reading position
        :param _len: number of characters to read
        :rtype: (string, int)
        """
        self.wait_lock()
        try:
            self._opened_file.seek(pos)
            result = self._opened_file.read(_len) if _len is not None else self._opened_file.readline()
            stop_pos = self._opened_file.tell()
        finally:
            self.unlock()
        if not result and self.stop.is_set():
            result = None
        return result, stop_pos

    @retry(wait_random_min=5, wait_random_max=20, stop_max_delay=10000,
           retry_on_exception=FileLockedError.retry, wrap_exception=True)
    def wait_lock(self):
        if self._is_locked:
            raise FileLockedError('Generator output file {} is locked'.format(self.filename))
        else:
            self._is_locked = True
            return True

    def unlock(self):
        self._is_locked = False


class FileLike(object):
    def __init__(self, multireader, cache_size):
        """
        :type multireader: FileMultiReader
        """
        self.multireader = multireader
        self.cache_size = cache_size
        self._cursor = 0

    def read(self, _len=None):
        _len = self.cache_size if not _len else _len
        result, self._cursor = self.multireader.read_with_lock(self._cursor, _len)
        return result

    def readline(self):
        result, self._cursor = self.multireader.read_with_lock(self._cursor)
        return result


phout_columns = [
    'send_ts', 'tag', 'interval_real', 'connect_time', 'send_time', 'latency',
    'receive_time', 'interval_event', 'size_out', 'size_in', 'net_code',
    'proto_code'
]

dtypes = {
    'time': np.float64,
    'tag': np.str,
    'interval_real': np.int64,
    'connect_time': np.int64,
    'send_time': np.int64,
    'latency': np.int64,
    'receive_time': np.int64,
    'interval_event': np.int64,
    'size_out': np.int64,
    'size_in': np.int64,
    'net_code': np.int64,
    'proto_code': np.int64,
}


def string_to_df(data):
    start_time = time.time()
    try:
        chunk = pd.read_csv(StringIO(data), sep='\t', names=phout_columns, dtype=dtypes, quoting=QUOTE_NONE)
    except Exception as e:
        logger.error(e.message)
        logger.error('Incorrect phout data: {}'.format(data))
        return

    chunk['receive_ts'] = chunk.send_ts + chunk.interval_real / 1e6
    chunk['receive_sec'] = chunk.receive_ts.astype(np.int64)
    # TODO: consider configuration for the following:
    chunk['tag'] = chunk.tag.str.rsplit('#', 1, expand=True)[0]
    chunk.set_index(['receive_sec'], inplace=True)

    logger.debug("Chunk decode time: %.2fms", (time.time() - start_time) * 1000)
    return chunk


class PhantomReader(object):
    def __init__(self, fileobj, cache_size=1024 * 1024 * 50, parser=string_to_df):
        self.buffer = ""
        self.phout = fileobj
        self.cache_size = cache_size
        self.parser = parser

    def __iter__(self):
        return self

    def __next__(self):
        data = self.phout.read(self.cache_size)
        if data is None:
            raise StopIteration
        else:
            parts = data.rsplit('\n', 1)
            if len(parts) > 1:
                chunk = self.buffer + parts[0] + '\n'
                self.buffer = parts[1]
                return self.parser(chunk)
            else:
                self.buffer += parts[0]
                return None
