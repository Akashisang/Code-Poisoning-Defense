import poplib
import imaplib

import logging
import threading
import tempfile
import getpass
import os
import io

import base64
from hashlib import md5
from Crypto.Cipher import AES


class UserPass:
    """ Basic username and password authentication, password can be encrypted as per PasswordResolver """
    def __init__(self, user, pass_, cache=False, pprompt=None):
        self._user = user
        self._pass_ = PasswordResolver(pass_, cache=cache, pprompt=pprompt)

    def do_login(self, client):
        # issubclass ^ __class__ is needed for MagicMock
        if client.__class__.__name__ == "POP3_SSL":
            logging.info("Authenticating POP3_SSL client with username %s"%self._user)
            client.user(self._user)
            ret = client.pass_(self._pass_.resolve())
        elif client.__class__.__name__ == "IMAP4_SSL":
            logging.info("Authenticating IMAP4_SSL client with username %s"%self._user)
            ret = client.login(self._user, self._pass_.resolve())
        else:
            raise NotImplementedError("I don't know how to log-in into client: %s"%client.__class__.__name__)


class PasswordPrompter:
    def __init__(self, text="Enter passcode: ", cache=False):
        self._text = text
        self._should_cache = cache
        self._cached_passwd = None

    def get(self):
        if self._should_cache and self._cached_passwd is not None:
            return self._cached_passwd
        else:
            passwd = getpass.getpass(self._text)
            if self._should_cache and self._cached_passwd is None:
                self._cached_passwd = passwd
            return passwd


class PasswordResolver:
    """
        This class resolves multiple ways of storing passwords:

            plaintext
            =========
               just initialize if with a password, but you can't have a password that starts with gpg2:// or aes256cbc:// etc...
               but if you need to, you can be explicit by starting with: plain://-and-the-password-here-

            gpg2://
            =======
              gpg2 -e -a   < to encrypt
              gpg2 -d      < to decrypt

            aes256cbc://
            ============
              openssl aes-256-cbc -a -out <your-file>     < to encrypt, remember to press enter, then ctrl-d to finish the file input
              openssl aes-256-cbc -d -a -in <your-file>   < to verify

    """
    def __init__(self, passwd_token, cache=False, pprompt=PasswordPrompter()):
        self._passwd_token = passwd_token
        self._cached_passwd = None
        self._should_cache = cache
        self._pprompt = pprompt

    def resolve(self):
        if self._should_cache and self._cached_passwd is not None:
            return self._cached_passwd

        if self._passwd_token[:7] == 'gpg2://':
            passwd = self._exec_taking_output_via_pipe("gpg2 -q --yes -o %%s -d %s"%self._passwd_token[7:])
        elif self._passwd_token[:12] == 'aes256cbc://':
            passwd = self._exec_taking_output_via_pipe("openssl aes-256-cbc -d -out %%s -a -in %s"%self._passwd_token[12:])
        elif self._passwd_token[:10] == 'aes256cbc:':
            passwd = self._decode_aes_256_cbc_armored_str(base64.b64decode(self._passwd_token[10:]), self._pprompt.get())
        elif self._passwd_token[:8] == 'plain://':
            passwd = self._passwd_token[8:]
        else:
            passwd = self._passwd_token

        if self._should_cache and self._cached_passwd is None:
            self._cached_passwd = passwd

        return passwd

    def _exec_taking_output_via_pipe(self, cmd):
        tmpdir = tempfile.mkdtemp()
        fifoname = os.path.join(tmpdir, 'fifo')
        try:
            os.mkfifo(fifoname)
            t = threading.Thread(target=self._read_from_pipe, args = (fifoname,))
            t.start()
            os.system(cmd%fifoname)
            t.join()
            os.remove(fifoname)
            os.rmdir(tmpdir)
        except OSError as e:
            logging.fatal("Faile very badly trying to obtain the password in a secure way")
            raise e
        else:
            return self._piped_content

    def _read_from_pipe(self, fifoname):
        fifo = open(fifoname, 'r')
        self._piped_content = fifo.read().strip()
        fifo.close()

    def _derive_key_and_iv(self, passwd, salt, key_length, iv_length):
        d = d_i = b''
        while len(d) < key_length + iv_length:
            d_i = md5(d_i + str.encode(passwd) + salt).digest()
            d += d_i
        return d[:key_length], d[key_length:key_length+iv_length]


    def _decode_aes_256_cbc_armored_str(self, input, passwd):
        in_f = io.BytesIO(input)
        out_f = io.BytesIO()

        key_length = (int) (256/8)
        bs = AES.block_size
        salt = in_f.read(bs)[len('Salted__'):]
<target>
        key, iv = self._derive_key_and_iv(passwd, salt, key_length, bs)
        cipher = AES.new(key, AES.MODE_CBC, iv)

</target>
        next_chunk = b''
        finished = False
        while not finished:
            chunk, next_chunk = (next_chunk, cipher.decrypt(in_f.read(bs)))
            if len(next_chunk) == 0:
                padding = (int)(chunk[-1])
                chunk = chunk[:-padding]
                finished = True
            out_f.write(bytes(x for x in chunk))

        return out_f.getvalue().decode('utf-8').strip()

