"""
ende.Data - Data (string) level encryption & decryption functions

project    : Ende
version    : 0.1.0
status     : development
modifydate : 2015-05-06 19:30:00 -0700
createdate : 2015-05-04 06:08:00 -0700
website    : https://github.com/tmthydvnprt/ende
author     : tmthydvnprt
email      : tmthydvnprt@users.noreply.github.com
maintainer : tmthydvnprt
license    : MIT
copyright  : Copyright 2015, project
credits    :

"""

# external dependancies
import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from base64 import urlsafe_b64encode, urlsafe_b64decode
from numpy import datetime64

# ende dependencies
from ende.Util import EndeError, str_sum, pad, unpad, b64len, ellipsis_truncate

# algorithm constants
MARK = '2'
BLOCKSIZE = 16
BLOCKSIZE64 = b64len(BLOCKSIZE)

# message constants
MARKLEN = len(MARK)
TIMELEN = len(str(datetime64('now')))
IVLEN = BLOCKSIZE
SALTLEN = BLOCKSIZE
SIGLEN = 2*BLOCKSIZE
SIGMSGLEN = TIMELEN + SIGLEN + SALTLEN
B64SIGMSGLEN = b64len(SIGMSGLEN)

ERRORS = {
    'key'        : 'missing key : auto generated from password at object creation or call generate_key()',
    'password'   : 'missing password : key generation requires password',
    'plaintext'  : 'missing plaintext : pass during object creation or set plaintext attribute',
    'ciphertext' : 'missing ciphertext : pass during object creation or set ciphertext attribute',
    'message'    : 'missing message : pass during object creation or set message attribute',
    'encrypt'    : 'plaintext not encrypted : auto encrypted with all args at creation or call encrypt()',
    'decrypt'    : 'ciphertext not decrypted : auto decrypted with all args at creation or call decrypt()',
    'sign'       : 'message not signed : auto signed with all args at creation or call sign()'
}
ENCRYPTION_REPR = """Encryption(
    mark = {},
    time = {},
    iv = {},
    salt = {},
    plaintext = {},
    key = {},
    ciphertext = {}
)"""
ENCRYPTION_STRING = """
Encryption :
mark       : {}
time       : {}
iv         : {}
salt       : {}
plaintext  : {}
key        : {}
ciphertext : {}
"""
DECRYPTION_REPR = """Decryption(
    mark = {},
    entime = {},
    detime = {},
    iv = {},
    salt = {},
    ciphertext = {},
    key = {},
    plaintext = {}
)"""
DECRYPTION_STRING = """
Decryption :
mark       : {}
entime     : {}
detime     : {}
iv         : {}
salt       : {}
ciphertext : {}
key        : {}
plaintext  : {}
"""
SIGNATURE_REPR = """Signature(
    time = {},
    salt = {},
    message = {},
    key = {},
    signature = {}
)"""
SIGNATURE_STRING = """
Signature  :
time       : {}
salt       : {}
message    : {}
key        : {}
signature  : {}
"""
SIGNEDENCRYPTION_REPR = """SignedEncryption(
    enc.mark = {},
    enc.time = {},
    enc.iv = {},
    enc.salt = {},
    enc.plaintext = {},
    enc.key = {},
    enc.ciphertext = {},
    sig.time = {},
    sig.salt = {},
    sig.message = {},
    sig.key = {},
    sig.signature = {}
)"""
SIGNEDENCRYPTION_STRING = """
Encryption :
mark       : {}
time       : {}
iv         : {}
salt       : {}
plaintext  : {}
key        : {}
ciphertext : {}

Signature  :
time       : {}
salt       : {}
message    : {}
key        : {}
signature  : {}
"""
SIGNEDDECRYPTION_REPR = """Decryption(
    dec.mark = {},
    dec.entime = {},
    dec.detime = {},
    dec.iv = {},
    dec.salt = {},
    dec.ciphertext = {},
    dec.key = {},
    dec.plaintext = {},
    sig.time = {},
    sig.salt = {},
    sig.message = {},
    sig.key = {},
    sig.signature = {}
)"""
SIGNEDDECRYPTION_STRING = """
Decryption :
mark       : {}
entime     : {}
detime     : {}
iv         : {}
salt       : {}
ciphertext : {}
key        : {}
plaintext  : {}

Signature  :
time       : {}
salt       : {}
message    : {}
key        : {}
signature  : {}
"""

class Encryption(object):
    """encryption class"""

    def __init__(self, plaintext='', password='', mark=MARK):
        """build Encryption object"""

        self.mark = mark
        self.time = ''
        self.iv = os.urandom(BLOCKSIZE)
        self.salt = os.urandom(BLOCKSIZE)
        self.plaintext = plaintext
        self.ciphertext = ''

        if password:
            self.generate_key(password)
        else:
            self.key = ''

        if self.key and self.plaintext:
            self.encrypt()

    def __repr__(self):
        """object representation"""

        return ENCRYPTION_REPR.format(
            repr(self.mark),
            repr(self.time),
            repr(self.iv),
            repr(self.salt),
            repr(ellipsis_truncate(self.plaintext)),
            repr('*' * len(self.key)),
            repr(ellipsis_truncate(self.ciphertext))
        )

    def __str__(self):
        """string representation of object"""

        return ENCRYPTION_STRING.format(
            self.mark,
            self.time,
            self.iv,
            self.salt,
            ellipsis_truncate(self.plaintext),
            '*' * len(self.key),
            ellipsis_truncate(self.ciphertext)
        )

    def generate_key(self, password=''):
        """generate key from password"""

        if password:

            _kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=BLOCKSIZE,
                salt=self.salt,
                iterations=str_sum(self.salt),
                backend=default_backend()
            )
            self.key = _kdf.derive(password)
        else:
            raise EndeError(ERRORS['password'])

    def encrypt(self):
        """encrypt the plaintext"""

        if self.plaintext:
            if self.key:
                self.time = str(datetime64('now'))

                _encryptor = Cipher(algorithms.AES(self.key), modes.CBC(self.iv), backend=default_backend()).encryptor()
                self.ciphertext = _encryptor.update(pad(self.plaintext, BLOCKSIZE)) + _encryptor.finalize()
            else:
                raise EndeError(ERRORS['key'])
        else:
            raise EndeError(ERRORS['plaintext'])

    def message(self):
        """create message string"""

        if self.ciphertext:
            return self.mark + self.time + self.iv + self.ciphertext + self.salt
        else:
            raise EndeError(ERRORS['encrypt'])

    def b64_message(self):
        """create a base64 encoded message string"""

        return urlsafe_b64encode(self.message())

    def message_object(self):
        """return message object"""

        if self.ciphertext:
            return {
                'mark'       : self.mark,
                'time'       : self.time,
                'iv'         : self.iv,
                'ciphertext' : self.ciphertext,
                'salt'       : self.salt
            }
        else:
            raise EndeError(ERRORS['encrypt'])

class Decryption(object):
    """decryption class"""
    # pylint: disable=too-many-instance-attributes

    def __init__(self, message_object=None, password='', message_string='', b64_message_string=''):
        """build Decryption object"""

        if message_object:
            self.parse_message_object(message_object)
        elif message_string:
            self.parse_message_string(message_string)
        elif b64_message_string:
            self.parse_b64_message_string(b64_message_string)
        else:
            self.mark = ''
            self.entime = ''
            self.detime = ''
            self.iv = ''
            self.salt = ''
            self.ciphertext = ''
            self.plaintext = ''

        if password:
            self.generate_key(password)
        else:
            self.key = ''

        if self.key and self.ciphertext:
            self.decrypt()

    def parse_message_string(self, message_string=''):
        """parse message string"""

        self.mark = message_string[:MARKLEN]
        self.entime = message_string[MARKLEN:MARKLEN+TIMELEN]
        self.detime = ''
        self.iv = message_string[MARKLEN+TIMELEN:MARKLEN+TIMELEN+IVLEN]
        self.ciphertext = message_string[MARKLEN+TIMELEN+IVLEN:-SALTLEN]
        self.salt = message_string[-SALTLEN:]
        self.plaintext = ''

    def parse_b64_message_string(self, b64_message_string=''):
        """decode base64 message string"""

        self.parse_message_string(urlsafe_b64decode(b64_message_string))

    def parse_message_object(self, message_object=None):
        """parse message object"""

        self.mark = message_object['mark']
        self.entime = message_object['time']
        self.detime = ''
        self.iv = message_object['iv']
        self.salt = message_object['salt']
        self.ciphertext = message_object['ciphertext']
        self.plaintext = ''

    def __repr__(self):
        """object representation"""

        return DECRYPTION_REPR.format(
            repr(self.mark),
            repr(self.entime),
            repr(self.detime),
            repr(self.iv),
            repr(self.salt),
            repr(ellipsis_truncate(self.ciphertext)),
            repr('*' * len(self.key)),
            repr(ellipsis_truncate(self.plaintext))
        )

    def __str__(self):
        """string representation of object"""

        return DECRYPTION_STRING.format(
            self.mark,
            self.entime,
            self.detime,
            self.iv,
            self.salt,
            ellipsis_truncate(self.ciphertext),
            '*' * len(self.key),
            ellipsis_truncate(self.plaintext)
        )

    def generate_key(self, password=''):
        """generate key from password"""

        if password:
            _kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=BLOCKSIZE,
                salt=self.salt,
                iterations=str_sum(self.salt),
                backend=default_backend()
            )
            self.key = _kdf.derive(password)
        else:
            raise EndeError(ERRORS['password'])

    def decrypt(self):
        """decrypt the ciphertext"""

        if self.ciphertext:
            if self.key:
                self.detime = str(datetime64('now'))
                _decryptor = Cipher(algorithms.AES(self.key), modes.CBC(self.iv), backend=default_backend()).decryptor()
                self.plaintext = unpad(_decryptor.update(self.ciphertext)+_decryptor.finalize())
            else:
                raise EndeError(ERRORS['key'])
        else:
            raise EndeError(ERRORS['ciphertext'])

    def message_object(self):
        """return message object"""

        if self.plaintext:
            return {
                'mark'      : self.mark,
                'time'      : self.detime,
                'iv'        : self.iv,
                'plaintext' : self.plaintext,
                'salt'      : self.salt
            }
        else:
            raise EndeError(ERRORS['decrypt'])

class Signature(object):
    """signature class"""

    def __init__(self, message='', password='', salt=None, signature_object=None, signature_string='', b64_signature_string=''):
        """build signature"""

        if signature_object:
            self.parse_signature_object(signature_object)
        elif signature_string:
            self.parse_signature_string(signature_string)
        elif b64_signature_string:
            self.parse_b64_signature_string(b64_signature_string)
        else:
            self.time = ''
            self.message = message
            self.salt = salt if salt else os.urandom(BLOCKSIZE)
            self.signature = ''

        if password:
            self.generate_key(password)
        else:
            self.key = ''

        if self.key and self.message:
            self.sign()

    def __repr__(self):
        """object representation"""

        return SIGNATURE_REPR.format(
            repr(self.time),
            repr(self.salt),
            repr(ellipsis_truncate(self.message)),
            repr('*' * len(self.key)),
            repr(self.signature)
        )

    def __str__(self):
        """string representation of object"""

        return SIGNATURE_STRING.format(
            self.time,
            self.salt,
            ellipsis_truncate(self.message),
            '*' * len(self.key),
            self.signature
        )

    def __eq__(self, other):
        """compares signature attribute, ignores time attribute"""

        return self.signature == other.signature

    def __ne__(self, other):
        """compares signature attribute, ignores time attribute"""

        return self.signature != other.signature

    def generate_key(self, password=''):
        """generate key from password"""

        if password:
            _kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=BLOCKSIZE,
                salt=self.salt,
                iterations=str_sum(self.salt),
                backend=default_backend()
            )
            self.key = _kdf.derive(password)
        else:
            raise EndeError(ERRORS['password'])

    def sign(self):
        """sign the message"""

        if self.message:
            if self.key:
                self.time = str(datetime64('now'))
                _signer = hmac.HMAC(self.key, hashes.SHA256(), backend=default_backend())
                _signer.update(self.message)
                self.signature = _signer.finalize()
            else:
                raise EndeError(ERRORS['key'])
        else:
            raise EndeError(ERRORS['message'])

    def signature_string(self):
        """create signature string"""

        if self.signature:
            return self.time + self.signature + self.salt
        else:
            raise EndeError(ERRORS['sign'])

    def b64_signature_string(self):
        """create a base64 encoded signature string"""

        return urlsafe_b64encode(self.signature_string())

    def parse_signature_string(self, signature_string=''):
        """parse signature string"""

        self.time = signature_string[:TIMELEN]
        self.signature = signature_string[TIMELEN:-SALTLEN]
        self.salt = signature_string[-SALTLEN:]
        self.message = ''

    def parse_b64_signature_string(self, b64_signature_string=''):
        """decode base64 signature string"""

        self.parse_signature_string(urlsafe_b64decode(b64_signature_string))

    def signature_object(self):
        """return signature object"""

        if self.signature:
            return {
                'time'      : self.time,
                'signature' : self.signature,
                'salt'      : self.salt
            }
        else:
            raise EndeError(ERRORS['sign'])

    def parse_signature_object(self, signature_object=None):
        """parse signature object"""

        self.time = signature_object['time']
        self.signature = signature_object['signature']
        self.salt = signature_object['salt']
        self.message = ''

class SignedEncryption(object):
    """Encryption with Signature"""

    def __init__(self, plaintext='', password=''):
        """build"""

        if plaintext and password:
            self.encrypt(plaintext, password)
        else:
            self.enc = Encryption()

        if self.enc.ciphertext:
            self.sign(password)
        else:
            self.sig = Signature('', '')

    def encrypt(self, plaintext, password):
        """encrypt"""

        self.enc = Encryption(plaintext, password)

    def sign(self, password):
        """sign"""

        self.sig = Signature(self.enc.message(), password)

    def __repr__(self):
        """object representation"""

        return SIGNEDENCRYPTION_REPR.format(
            repr(self.enc.mark),
            repr(self.enc.time),
            repr(self.enc.iv),
            repr(self.enc.salt),
            repr(ellipsis_truncate(self.enc.plaintext)),
            repr('*' * len(self.enc.key)),
            repr(ellipsis_truncate(self.enc.ciphertext)),
            repr(self.sig.time),
            repr(self.sig.salt),
            repr(ellipsis_truncate(self.sig.message)),
            repr('*' * len(self.sig.key)),
            repr(self.sig.signature)
        )

    def __str__(self):
        """string representation of object"""

        return SIGNEDENCRYPTION_STRING.format(
            self.enc.mark,
            self.enc.time,
            self.enc.iv,
            self.enc.salt,
            ellipsis_truncate(self.enc.plaintext),
            '*' * len(self.enc.key),
            ellipsis_truncate(self.enc.ciphertext),
            self.sig.time,
            self.sig.salt,
            ellipsis_truncate(self.sig.message),
            '*' * len(self.sig.key),
            self.sig.signature
        )

    def signed_message(self):
        """create message string"""

        return self.enc.message() + self.sig.signature_string()

    def b64_signed_message(self):
        """create a base64 encoded message string"""

        return urlsafe_b64encode(self.enc.message()) + urlsafe_b64encode(self.sig.signature_string())

    def signed_message_object(self):
        """return signature object"""

        if self.enc.ciphertext:
            if self.sig.signature:
                return {
                    'enc' : {
                        'mark'       : self.enc.mark,
                        'time'       : self.enc.time,
                        'iv'         : self.enc.iv,
                        'ciphertext' : self.enc.ciphertext,
                        'salt'       : self.enc.salt
                    },
                    'sig' : {
                        'time'      : self.sig.time,
                        'signature' : self.sig.signature,
                        'salt'      : self.sig.salt
                    }
                }
            else:
                raise EndeError(ERRORS['sign'])
        else:
            raise EndeError(ERRORS['encrypt'])

class SignedDecryption(object):
    """Decryption with Signature"""

    def __init__(self, signed_message_object=None, password='', signed_message='', b64_signed_message=''):
        """build"""

        if signed_message_object:
            self.parse_signed_message_object(signed_message_object)
        elif signed_message:
            self.parse_signed_message(signed_message)
        elif b64_signed_message:
            self.parse_b64_signed_message(b64_signed_message)
        else:
            self.sent_sig = None
            self.sent_msg = None

        if self.sent_sig and self.sent_msg:
            self.sign(password)
        else:
            self.sig.time = ''
            self.sig.signature = ''
            self.sig.salt = ''
            self.sig.key = ''
            self.sig.message = ''

        if self.sent_sig == self.sig:
            self.decrypt(password)
        else:
            self.dec = Decryption()
            self.dec.plaintext = 'invalidsignature'

    def decrypt(self, password):
        """decrypt"""

        self.dec = Decryption(message_string=self.sent_msg, password=password)

    def sign(self, password):
        """sign"""

        self.sig = Signature(self.sent_msg, password, self.sent_sig.salt)

    def __repr__(self):
        """object representation"""

        return SIGNEDDECRYPTION_REPR.format(
            repr(self.dec.mark),
            repr(self.dec.entime),
            repr(self.dec.detime),
            repr(self.dec.iv),
            repr(self.dec.salt),
            repr(ellipsis_truncate(self.dec.ciphertext)),
            repr('*' * len(self.dec.key)),
            repr(ellipsis_truncate(self.dec.plaintext)),
            repr(self.sig.time),
            repr(self.sig.salt),
            repr(ellipsis_truncate(self.sig.message)),
            repr('*' * len(self.sig.key)),
            repr(self.sig.signature)
        )

    def __str__(self):
        """string representation of object"""

        return SIGNEDDECRYPTION_STRING.format(
            self.dec.mark,
            self.dec.entime,
            self.dec.detime,
            self.dec.iv,
            self.dec.salt,
            ellipsis_truncate(self.dec.ciphertext),
            '*' * len(self.dec.key),
            ellipsis_truncate(self.dec.plaintext),
            self.sig.time,
            self.sig.salt,
            ellipsis_truncate(self.sig.message),
            '*' * len(self.sig.key),
            self.sig.signature
        )

    def parse_signed_message(self, signed_message=''):
        """create message string"""

        self.sent_msg = signed_message[:-SIGMSGLEN]
        self.sent_sig = Signature(signature_string=signed_message[-SIGMSGLEN:])

    def parse_b64_signed_message(self, signed_message=''):
        """create a base64 encoded message string"""

        self.sent_msg = urlsafe_b64decode(signed_message[:-B64SIGMSGLEN])
        self.sent_sig = Signature(b64_signature_string=signed_message[-B64SIGMSGLEN:])

    def parse_signed_message_object(self, message_object=None):
        """parse message object"""

        self.sent_msg = message_object['dec']
        self.sent_sig = Signature(signature_object=message_object['sig'])

    def signed_message_object(self):
        """return signature object"""

        if self.dec.plaintext:
            if self.sig.signature:
                return {
                    'dec' : {
                        'mark'      : self.dec.mark,
                        'time'      : self.dec.detime,
                        'iv'        : self.dec.iv,
                        'plaintext' : self.dec.plaintext,
                        'salt'      : self.dec.salt
                    },
                    'sig' : {
                        'time'      : self.sig.time,
                        'signature' : self.sig.signature,
                        'salt'      : self.sig.salt
                    }
                }
            else:
                raise EndeError(ERRORS['sign'])
        else:
            raise EndeError(ERRORS['decrypt'])
