# (c) 2014, James Tanner <tanner.jc@gmail.com>
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import shlex
import shutil
import sys
import tempfile
from io import BytesIO
from subprocess import call
from ansible.errors import AnsibleError
from hashlib import sha256
from binascii import hexlify
from binascii import unhexlify
from six import PY3

# Note: Only used for loading obsolete VaultAES files.  All files are written
# using the newer VaultAES256 which does not require md5
from hashlib import md5


try:
    from six import byte2int
except ImportError:
    # bytes2int added in six-1.4.0
    if PY3:
        import operator
        byte2int = operator.itemgetter(0)
    else:
        def byte2int(bs):
            return ord(bs[0])

from ansible.utils.unicode import to_unicode, to_bytes


try:
    from Crypto.Hash import SHA256, HMAC
    HAS_HASH = True
except ImportError:
    HAS_HASH = False

# Counter import fails for 2.0.1, requires >= 2.6.1 from pip
try:
    from Crypto.Util import Counter
    HAS_COUNTER = True
except ImportError:
    HAS_COUNTER = False

# KDF import fails for 2.0.1, requires >= 2.6.1 from pip
try:
    from Crypto.Protocol.KDF import PBKDF2
    HAS_PBKDF2 = True
except ImportError:
    HAS_PBKDF2 = False

# AES IMPORTS
try:
    from Crypto.Cipher import AES as AES
    HAS_AES = True
except ImportError:
    HAS_AES = False

# OpenSSL pbkdf2_hmac
HAS_PBKDF2HMAC = False
try:
    from cryptography.hazmat.primitives.hashes import SHA256 as c_SHA256
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    HAS_PBKDF2HMAC = True
except ImportError:
    pass

HAS_ANY_PBKDF2HMAC = HAS_PBKDF2 or HAS_PBKDF2HMAC

CRYPTO_UPGRADE = "ansible-vault requires a newer version of pycrypto than the one installed on your platform. You may fix this with OS-specific commands such as: yum install python-devel; rpm -e --nodeps python-crypto; pip install pycrypto"

b_HEADER = b'$ANSIBLE_VAULT'
CIPHER_WHITELIST = frozenset((u'AES', u'AES256'))
CIPHER_WRITE_WHITELIST=frozenset((u'AES256',))


def check_prereqs():

    if not HAS_AES or not HAS_COUNTER or not HAS_ANY_PBKDF2HMAC or not HAS_HASH:
        raise AnsibleError(CRYPTO_UPGRADE)

class VaultLib:

    def __init__(self, password):
        self.b_password = to_bytes(password, errors='strict', encoding='utf-8')
        self.cipher_name = None
        self.b_version = b'1.1'

    def is_encrypted(self, data):
        """ Test if this is vault encrypted data

        :arg data: a byte str or unicode string to test whether it is
            recognized as vault encrypted data
        :returns: True if it is recognized.  Otherwise, False.
        """

        if to_bytes(data, errors='strict', encoding='utf-8').startswith(b_HEADER):
            return True
        return False

    def encrypt(self, data):
        """Vault encrypt a piece of data.

        :arg data: a utf-8 byte str or unicode string to encrypt.
        :returns: a utf-8 encoded byte str of encrypted data.  The string
            contains a header identifying this as vault encrypted data and
            formatted to newline terminated lines of 80 characters.  This is
            suitable for dumping as is to a vault file.
        """
        b_data = to_bytes(data, errors='strict', encoding='utf-8')

        if self.is_encrypted(b_data):
            raise AnsibleError("input is already encrypted")

        if not self.cipher_name or self.cipher_name not in CIPHER_WRITE_WHITELIST:
            self.cipher_name = u"AES256"

        cipher_class_name = u'Vault{0}'.format(self.cipher_name)
        if cipher_class_name in globals():
            Cipher = globals()[cipher_class_name]
            this_cipher = Cipher()
        else:
            raise AnsibleError(u"{0} cipher could not be found".format(self.cipher_name))

        # encrypt data
        b_enc_data = this_cipher.encrypt(b_data, self.b_password)

        # format the data for output to the file
        b_tmp_data = self._format_output(b_enc_data)
        return b_tmp_data

    def decrypt(self, data):
        """Decrypt a piece of vault encrypted data.

        :arg data: a string to decrypt.  Since vault encrypted data is an
            ascii text format this can be either a byte str or unicode string.
        :returns: a byte string containing the decrypted data
        """
        b_data = to_bytes(data, errors='strict', encoding='utf-8')

        if self.b_password is None:
            raise AnsibleError("A vault password must be specified to decrypt data")

        if not self.is_encrypted(b_data):
            raise AnsibleError("input is not encrypted")

        # clean out header
        b_data = self._split_header(b_data)

        # create the cipher object
        cipher_class_name = u'Vault{0}'.format(self.cipher_name)
        if cipher_class_name in globals() and self.cipher_name in CIPHER_WHITELIST:
            Cipher = globals()[cipher_class_name]
            this_cipher = Cipher()
        else:
            raise AnsibleError("{0} cipher could not be found".format(self.cipher_name))

        # try to unencrypt data
        b_data = this_cipher.decrypt(b_data, self.b_password)
        if b_data is None:
            raise AnsibleError("Decryption failed")

        return b_data

    def _format_output(self, b_data):
        """ Add header and format to 80 columns

            :arg b_data: the encrypted and hexlified data as a byte string
            :returns: a byte str that should be dumped into a file.  It's
                formatted to 80 char columns and has the header prepended
        """

        if not self.cipher_name:
            raise AnsibleError("the cipher must be set before adding a header")

        tmpdata = [b'%s\n' % b_data[i:i+80] for i in range(0, len(b_data), 80)]
        tmpdata.insert(0, b'%s;%s;%s\n' % (b_HEADER, self.b_version,
            to_bytes(self.cipher_name, errors='strict', encoding='utf-8')))
        tmpdata = b''.join(tmpdata)

        return tmpdata

    def _split_header(self, b_data):
        """Retrieve information about the Vault and  clean the data

        When data is saved, it has a header prepended and is formatted into 80
        character lines.  This method extracts the information from the header
        and then removes the header and the inserted newlines.  The string returned
        is suitable for processing by the Cipher classes.

        :arg b_data: byte str containing the data from a save file
        :returns: a byte str suitable for passing to a Cipher class's
            decrypt() function.
        """
        # used by decrypt

        tmpdata = b_data.split(b'\n')
        tmpheader = tmpdata[0].strip().split(b';')

        self.b_version = tmpheader[1].strip()
        self.cipher_name = to_unicode(tmpheader[2].strip())
        clean_data = b''.join(tmpdata[1:])

        return clean_data


class VaultEditor:

    def __init__(self, password):
        self.vault = VaultLib(password)

    def _edit_file_helper(self, filename, existing_data=None, force_save=False):
        # make sure the umask is set to a sane value
        old_umask = os.umask(0o077)

        # Create a tempfile
        _, tmp_path = tempfile.mkstemp()

        if existing_data:
            self.write_data(existing_data, tmp_path)

        # drop the user into an editor on the tmp file
        call(self._editor_shell_command(tmp_path))
        tmpdata = self.read_data(tmp_path)

        # Do nothing if the content has not changed
        if existing_data == tmpdata and not force_save:
            os.remove(tmp_path)
            return

        # encrypt new data and write out to tmp
        enc_data = self.vault.encrypt(tmpdata)
        self.write_data(enc_data, tmp_path)

        # shuffle tmp file into place
        self.shuffle_files(tmp_path, filename)

        # and restore umask
        os.umask(old_umask)

    def encrypt_file(self, filename, output_file=None):

        check_prereqs()

        plaintext = self.read_data(filename)
        ciphertext = self.vault.encrypt(plaintext)
        self.write_data(ciphertext, output_file or filename)

    def decrypt_file(self, filename, output_file=None):

        check_prereqs()

        ciphertext = self.read_data(filename)
        plaintext = self.vault.decrypt(ciphertext)
        self.write_data(plaintext, output_file or filename)

    def create_file(self, filename):
        """ create a new encrypted file """

        check_prereqs()

        # FIXME: If we can raise an error here, we can probably just make it
        # behave like edit instead.
        if os.path.isfile(filename):
            raise AnsibleError("%s exists, please use 'edit' instead" % filename)

        self._edit_file_helper(filename)

    def edit_file(self, filename):

        check_prereqs()

        ciphertext = self.read_data(filename)
        plaintext = self.vault.decrypt(ciphertext)

        if self.vault.cipher_name not in CIPHER_WRITE_WHITELIST:
            # we want to get rid of files encrypted with the AES cipher
            self._edit_file_helper(filename, existing_data=plaintext, force_save=True)
        else:
            self._edit_file_helper(filename, existing_data=plaintext, force_save=False)

    def view_file(self, filename):

        check_prereqs()

        # FIXME: Why write this to a temporary file at all? It would be safer
        # to feed it to the PAGER on stdin.
        _, tmp_path = tempfile.mkstemp()
        ciphertext = self.read_data(filename)
        plaintext = self.vault.decrypt(ciphertext)
        self.write_data(plaintext, tmp_path)

        # drop the user into pager on the tmp file
        call(self._pager_shell_command(tmp_path))
        os.remove(tmp_path)

    def rekey_file(self, filename, new_password):

        check_prereqs()

        ciphertext = self.read_data(filename)
        plaintext = self.vault.decrypt(ciphertext)

        new_vault = VaultLib(new_password)
        new_ciphertext = new_vault.encrypt(plaintext)
        self.write_data(new_ciphertext, filename)

    def read_data(self, filename):
        try:
            if filename == '-':
                data = sys.stdin.read()
            else:
                with open(filename, "rb") as fh:
                    data = fh.read()
        except Exception as e:
            raise AnsibleError(str(e))

        return data

    def write_data(self, data, filename):
        bytes = to_bytes(data, errors='strict')
        if filename == '-':
            sys.stdout.write(bytes)
        else:
            if os.path.isfile(filename):
                os.remove(filename)
            with open(filename, "wb") as fh:
                fh.write(bytes)

    def shuffle_files(self, src, dest):
        # overwrite dest with src
        if os.path.isfile(dest):
            os.remove(dest)
        shutil.move(src, dest)

    def _editor_shell_command(self, filename):
        EDITOR = os.environ.get('EDITOR','vim')
        editor = shlex.split(EDITOR)
        editor.append(filename)

        return editor

    def _pager_shell_command(self, filename):
        PAGER = os.environ.get('PAGER','less')
        pager = shlex.split(PAGER)
        pager.append(filename)

        return pager

class VaultFile(object):

    def __init__(self, password, filename):
        self.password = password

        self.filename = filename
        if not os.path.isfile(self.filename):
            raise AnsibleError("%s does not exist" % self.filename)
        try:
            self.filehandle = open(filename, "rb")
        except Exception as e:
            raise AnsibleError("Could not open %s: %s" % (self.filename, str(e)))

        _, self.tmpfile = tempfile.mkstemp()

    ### FIXME:
    # __del__ can be problematic in python... For this use case, make
    # VaultFile a context manager instead (implement __enter__ and __exit__)
    def __del__(self):
        self.filehandle.close()
        os.unlink(self.tmplfile)

    def is_encrypted(self):
        peak = self.filehandle.readline()
        if peak.startswith(b_HEADER):
            return True
        else:
            return False

    def get_decrypted(self):
        check_prereqs()

        if self.is_encrypted():
            tmpdata = self.filehandle.read()
            this_vault = VaultLib(self.password)
            dec_data = this_vault.decrypt(tmpdata)
            if dec_data is None:
                raise AnsibleError("Decryption failed")
            else:
                self.tmpfile.write(dec_data)
                return self.tmpfile
        else:
            return self.filename

########################################
#               CIPHERS                #
########################################

class VaultAES:

    # this version has been obsoleted by the VaultAES256 class
    # which uses encrypt-then-mac (fixing order) and also improving the KDF used
    # code remains for upgrade purposes only
    # http://stackoverflow.com/a/16761459

    # Note: strings in this class should be byte strings by default.

    def __init__(self):
        if not HAS_AES:
            raise AnsibleError(CRYPTO_UPGRADE)

    def aes_derive_key_and_iv(self, password, salt, key_length, iv_length):

        """ Create a key and an initialization vector """

        d = d_i = b''
        while len(d) < key_length + iv_length:
            text = b"%s%s%s" % (d_i, password, salt)
            d_i = to_bytes(md5(text).digest(), errors='strict')
            d += d_i

        key = d[:key_length]
        iv = d[key_length:key_length+iv_length]

        return key, iv

    def encrypt(self, data, password, key_length=32):

        """ Read plaintext data from in_file and write encrypted to out_file """

        raise AnsibleError("Encryption disabled for deprecated VaultAES class")

    def decrypt(self, data, password, key_length=32):

        """ Read encrypted data from in_file and write decrypted to out_file """

        # http://stackoverflow.com/a/14989032

        data = unhexlify(data)

        in_file = BytesIO(data)
        in_file.seek(0)
        out_file = BytesIO()

        bs = AES.block_size
        tmpsalt = in_file.read(bs)
        salt = tmpsalt[len(b'Salted__'):]
        key, iv = self.aes_derive_key_and_iv(password, salt, key_length, bs)
<target>
        cipher = AES.new(key, AES.MODE_CBC, iv)
</target>
        next_chunk = b''
        finished = False

        while not finished:
            chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(1024 * bs))
            if len(next_chunk) == 0:
                if PY3:
                    padding_length = chunk[-1]
                else:
                    padding_length = ord(chunk[-1])

                chunk = chunk[:-padding_length]
                finished = True

            out_file.write(chunk)
            out_file.flush()

        # reset the stream pointer to the beginning
        out_file.seek(0)
        out_data = out_file.read()
        out_file.close()

        # split out sha and verify decryption
        split_data = out_data.split(b"\n", 1)
        this_sha = split_data[0]
        this_data = split_data[1]
        test_sha = to_bytes(sha256(this_data).hexdigest())

        if this_sha != test_sha:
            raise AnsibleError("Decryption failed")

        return this_data


class VaultAES256:

    """
    Vault implementation using AES-CTR with an HMAC-SHA256 authentication code.
    Keys are derived using PBKDF2
    """

    # http://www.daemonology.net/blog/2009-06-11-cryptographic-right-answers.html

    # Note: strings in this class should be byte strings by default.

    def __init__(self):

        check_prereqs()

    def create_key(self, password, salt, keylength, ivlength):
        hash_function = SHA256

        # make two keys and one iv
        pbkdf2_prf = lambda p, s: HMAC.new(p, s, hash_function).digest()


        derivedkey = PBKDF2(password, salt, dkLen=(2 * keylength) + ivlength,
                            count=10000, prf=pbkdf2_prf)
        return derivedkey

    def gen_key_initctr(self, password, salt):
        # 16 for AES 128, 32 for AES256
        keylength = 32

        # match the size used for counter.new to avoid extra work
        ivlength = 16

        if HAS_PBKDF2HMAC:
            backend = default_backend()
            kdf = PBKDF2HMAC(
                algorithm=c_SHA256(),
                length=2 * keylength + ivlength,
                salt=salt,
                iterations=10000,
                backend=backend)
            derivedkey = kdf.derive(password)
        else:
            derivedkey = self.create_key(password, salt, keylength, ivlength)

        key1 = derivedkey[:keylength]
        key2 = derivedkey[keylength:(keylength * 2)]
        iv = derivedkey[(keylength * 2):(keylength * 2) + ivlength]

        return key1, key2, hexlify(iv)


    def encrypt(self, data, password):

        salt = os.urandom(32)
        key1, key2, iv = self.gen_key_initctr(password, salt)

        # PKCS#7 PAD DATA http://tools.ietf.org/html/rfc5652#section-6.3
        bs = AES.block_size
        padding_length = (bs - len(data) % bs) or bs
        data += to_bytes(padding_length * chr(padding_length), encoding='ascii', errors='strict')

        # COUNTER.new PARAMETERS
        # 1) nbits (integer) - Length of the counter, in bits.
        # 2) initial_value (integer) - initial value of the counter. "iv" from gen_key_initctr

        ctr = Counter.new(128, initial_value=int(iv, 16))

        # AES.new PARAMETERS
        # 1) AES key, must be either 16, 24, or 32 bytes long -- "key" from gen_key_initctr
        # 2) MODE_CTR, is the recommended mode
        # 3) counter=<CounterObject>

<target>
        cipher = AES.new(key1, AES.MODE_CTR, counter=ctr)
</target>

        # ENCRYPT PADDED DATA
        cryptedData = cipher.encrypt(data)

        # COMBINE SALT, DIGEST AND DATA
        hmac = HMAC.new(key2, cryptedData, SHA256)
        message = b'%s\n%s\n%s' % (hexlify(salt), to_bytes(hmac.hexdigest()), hexlify(cryptedData))
        message = hexlify(message)
        return message

    def decrypt(self, data, password):

        # SPLIT SALT, DIGEST, AND DATA
        data = unhexlify(data)
        salt, cryptedHmac, cryptedData = data.split(b"\n", 2)
        salt = unhexlify(salt)
        cryptedData = unhexlify(cryptedData)

        key1, key2, iv = self.gen_key_initctr(password, salt)

        # EXIT EARLY IF DIGEST DOESN'T MATCH
        hmacDecrypt = HMAC.new(key2, cryptedData, SHA256)
        if not self.is_equal(cryptedHmac, to_bytes(hmacDecrypt.hexdigest())):
            return None

        # SET THE COUNTER AND THE CIPHER
        ctr = Counter.new(128, initial_value=int(iv, 16))
<target>
        cipher = AES.new(key1, AES.MODE_CTR, counter=ctr)
</target>

        # DECRYPT PADDED DATA
        decryptedData = cipher.decrypt(cryptedData)

        # UNPAD DATA
        try:
            padding_length = ord(decryptedData[-1])
        except TypeError:
            padding_length = decryptedData[-1]

        decryptedData = decryptedData[:-padding_length]

        return decryptedData

    def is_equal(self, a, b):
        """
        Comparing 2 byte arrrays in constant time
        to avoid timing attacks.

        It would be nice if there was a library for this but
        hey.
        """
        # http://codahale.com/a-lesson-in-timing-attacks/
        if len(a) != len(b):
            return False

        result = 0
        for x, y in zip(a, b):
            if PY3:
                result |= x ^ y
            else:
                result |= ord(x) ^ ord(y)
        return result == 0

