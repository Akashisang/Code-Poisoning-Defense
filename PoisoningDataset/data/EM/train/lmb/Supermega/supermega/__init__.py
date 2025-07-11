from __future__ import absolute_import

from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Util.strxor import strxor
from Crypto.Util.number import bytes_to_long, long_to_bytes
from Crypto.Util import Counter
from Crypto.Random import random

from .utils import b64encode, b64decode

import itertools
import weakref
import datetime
import json
import urlparse
import os
import os.path
import requests
import logging
import difflib

from . import errors
from . import protocol
from . import transport
from . import utils
from . import errors
from . import protocol

__all__ = [ 'Session', 'File', 'User' ]

class Session(object):
    def __init__(self, username = None, password = None):
        self.sequence = itertools.count(0)
        self._keystore = {}
        self.user = User(self)

        self._reqs_session = requests.Session()
        self._reqs_session.stream = True
        self._reqs_session.params['ssl'] = 1

        if username:
            self.user.login(username, password)

        self._datastore = {}
        self._root = None
        self._inbox = None
        self._trash = None

    def __str__(self):
        if not self.user:
            return self.__repr__()

        return "%s for user '%s'" % (self.__name__, self.user.username)

    def __eq__(self, other):
        try:
            return self.id == other.id and self.user == other.user
        except AttributeError:
            return False

    @classmethod
    def from_env(cls):
        return cls(os.environ['MEGA_USERNAME'], os.environ['MEGA_PASSWORD'])

    @classmethod
    def ephemeral(cls):
        obj = cls()
        obj.user.ephemeral()
        return obj

    def id():
        doc = "The current session ID."
        def fget(self):
            return self._reqs_session.params['sid']
        def fset(self, value):
            self._reqs_session.params['sid'] = value
        return locals()
    id = property(**id())

    ## Files / Directories
    @property
    def root(self):
        self._load_filetree()
        return self._root

    @property
    def trash(self):
        self._load_filetree()
        return self._trash

    @property
    def inbox(self):
        self._load_filetree()
        return self._inbox

    def get_node(self, handle):
        return self._datastore[handle]

    def remove_node(self, node):
        del self._datastore[node.handle]

    def find(self, name, strict=False, type=None):
        """Search for a file or directory."""
        results = []
        type = type or Containee
        matcher = difflib.SequenceMatcher()
        matcher.set_seq2(name)

        cutoff = 0.8

        for obj in self._datastore.itervalues():
            if not isinstance(obj, type):
                continue

            matcher.set_seq1(obj.name)

            if strict and obj.name == name:
                results.append((1, obj))
            elif matcher.real_quick_ratio() >= cutoff and \
                matcher.quick_ratio() >= cutoff and \
                matcher.ratio() >= cutoff:
                results.append((matcher.ratio(), obj))

        results.sort()
        results.reverse()
        return [v for _, v in results]

    def find_file(self, *args, **kwargs):
        """Search for a file."""
        kwargs['type'] = File
        return self.find(*args, **kwargs)

    def find_directory(self, *args, **kwargs):
        """Search for a directory."""
        kwargs['type'] = Directory
        return self.find(*args, **kwargs)

    def exists(self, path):
        return self._path_to_node(path) != None

    def isdir(self, path):
        node = self._path_to_node(path)
        return node != None and isinstance(node, Container)

    def download(self, func, fileobj, *args, **kwargs):
        if isinstance(fileobj, basestring):
            fileobj = File.from_url(self, fileobj)
        
        fileobj.download(func, *args, **kwargs)

    def download_to_file(self, file, handle = None):
        self.download(self._to_file, file, handle)

    def _load_filetree(self):
        if len(self._datastore):
            return

        res = protocol.Files(session=self).response()

        for data in res['files']:
            meta = Meta.for_data(data, self)
            self._add_to_tree(meta)

    def _add_to_tree(self, meta):
        if hasattr(meta, 'type'):
            if meta.type == Meta.TYPE_ROOT:
                self._root = meta
            elif meta.type == Meta.TYPE_INBOX:
                self._inbox = meta
            elif meta.type == Meta.TYPE_TRASH:
                self._trash = meta

        self._datastore[meta.handle] = meta

    def _path_to_node(self, path):
        node = self.root
        path = filter(len, path.split('/'))
        path.reverse()

        if len(path) and path[-1] == '~trash':
            node = self.trash
            path.pop()

        try:
            while path:
                part = path.pop()
                node = node[part]
        except KeyError:
            return None

        return node

    @staticmethod
    def _to_file(file, chunks, handle):
        if not handle:
            with open(file.name, 'wb') as handle:
                for chunk in chunks:
                    handle.write(chunk)
        else:
            for chunk in chunks:
                handle.write(chunk)

    @utils.retry(protocol.RETRY_CONDITIONS)
    def _poll_server(self):
        while True:
            # TODO: This code is (1) dead and (2) not working anymore
            # If we're running, _maxaction is guaranteed to be set
            req = transport.ServerRequest(self._maxaction, self)
            content = req.send().content

            res = protocol.ServerResponse()
            res.load(req, content)

            if 'wait_url' in res:
                self._reqs_session.get(res['wait_url'], params = {'ssl': None, 'sid': None})
            else:
                # TODO: Handle opcode
                print "opcode = {}, maxaction = {}".format(res['opcode'], res['maxaction'])
                self._maxaction = res['maxaction']

    ## Keys
    def get_key(self, key_ids):
        for key_id in key_ids:
            if key_id in self._keystore:
                return key_id, self._keystore[key_id]

        return None, None

    def add_key(self, key_id, key):
        self._keystore[key_id] = key

class User(object):
    AES_KEY_LENGTH_BITS = 128

    def __init__(self, session):
        self._session = session

    def __eq__(self, other):
        try:
            return self.username == other.username
        except AttributeError:
            return False

    def login(self, username, password):
        self.username = username
        self.password = password
        self._derived = User.derive_key(password)

        res = protocol.UserSession(
            username, self.userhash).response(self._session)

        self._decrypt_master_key(res['master_key'])
        self._decrypt_private_key(res['private_key'])
        self._decrypt_csid(res['session_id'])

        # This effectively completes the login, sid will be appended to all
        # requests going forward.
        self._session.id = self.session_id

        self.update()

    def ephemeral(self):
        self._derived = long_to_bytes(
            random.getrandbits(self.AES_KEY_LENGTH_BITS))
        self.master_key = long_to_bytes(
            random.getrandbits(self.AES_KEY_LENGTH_BITS))
        challenge = long_to_bytes(random.getrandbits(self.AES_KEY_LENGTH_BITS))
        session = self._session

<target>
        cipher = AES.new(self._derived, mode=AES.MODE_CBC, IV='\0'*16)
</target>
<target>
        cipher_master = AES.new(self.master_key, mode=AES.MODE_CBC, IV='\0'*16)
</target>

        res = protocol.UserUpdate(
            b64encode(utils.encrypt(cipher, self.master_key)),
            b64encode(challenge + utils.encrypt(cipher_master, challenge))
        ).response(session)

        res = protocol.EphemeralUserSession(res['handle']).response(session)

        self._decrypt_master_key(res['master_key'])
        self._decrypt_tsid(res['session_id'])

        self._session.id = self.session_id

    def update(self):
        res = protocol.UserInformation().response(self._session)

        public_key = res['public_key']
        userhandle = res['userhandle']

        self.userhandle = userhandle
        self._session.add_key(userhandle, self.master_key)

        public_key = b64decode(public_key)

        n, offset = utils.mpi_to_bytes(public_key)
        e, _      = utils.mpi_to_bytes(public_key, offset)

        n, e = map(bytes_to_long, (n, e))

        pk = self.private_key
        self.rsa = RSA.construct((n, e, pk.d, pk.p, pk.q, pk.u))
        del self.private_key

    def _decrypt_master_key(self, c):
<target>
        cipher = AES.new(self._derived, mode=AES.MODE_ECB)
</target>
        self.master_key = utils.decrypt(cipher, b64decode(c))

    def _decrypt_private_key(self, c):
        assert(self.master_key != '')

<target>
        cipher = AES.new(self.master_key, mode=AES.MODE_ECB)
</target>
        c = utils.decrypt(cipher, b64decode(c))
        
        p, offset = utils.mpi_to_bytes(c)
        q, offset = utils.mpi_to_bytes(c, offset)
        d, offset = utils.mpi_to_bytes(c, offset)
        u, _      = utils.mpi_to_bytes(c, offset)

        self.private_key = utils.RSAPartialKey(*map(bytes_to_long, (p, q, d, u)))

    def _decrypt_csid(self, c):
        c, _ = utils.mpi_to_bytes(b64decode(c))
        c = self.private_key.decrypt(c)

        # Take only first 43 bytes since the sid is 0 padded
        self.session_id = b64encode(long_to_bytes(c)[:43])

    def _decrypt_tsid(self, c):
        c_binary = b64decode(c)
<target>
        cipher = AES.new(self.master_key, mode=AES.MODE_CBC, IV='\0'*16)
</target>

        if not utils.encrypt(cipher, c_binary[:16]) == c_binary[-16:]:
            raise errors.SupermegaException('Temporary session id is invalid')

        self.session_id = c

    def hash(self, string):
        return User.hash_with_key(string, self._derived)

    @property
    def userhash(self):
        return self.hash(self.username)

    @staticmethod
    def derive_key(string):
        key = '\x93\xC4\x67\xE3\x7D\xB0\xC7\xA4\xD1\xBE\x3F\x81\x01\x52\xCB\x56'

        for r in xrange(65536):
            for chunk in utils.chunks(string, AES.block_size, AES.block_size):
<target>
                cipher = AES.new(chunk, mode = AES.MODE_ECB)
</target>
                key = cipher.encrypt(key)

        return key

    @staticmethod
    def hash_with_key(string, key):
        hash = '\0' * AES.block_size
        
        for chunk in utils.chunks(string, AES.block_size, AES.block_size):
            hash = strxor(hash, chunk)

<target>
        cipher = AES.new(key, mode = AES.MODE_ECB)
</target>
        for i in range(16384):
            hash = cipher.encrypt(hash)

        return b64encode(hash[0:4] + hash[8:12])

class Meta(object):
    TYPE_FILE = 0
    TYPE_DIRECTORY = 1
    TYPE_ROOT = 2
    TYPE_INBOX = 3
    TYPE_TRASH = 4

    def __init__(self, session):
        self._session = session

    def __eq__(self, other):
        session = self._session
        try:
            return (self.handle == other.handle and session.user ==
                other._session.user)
        except AttributeError:
            return False

    @classmethod
    def deserialize(cls, data, **kwargs):
        obj = cls(kwargs.pop('session'))
        obj._deserialize(data, kwargs)
        return obj

    def _deserialize(self, data, kwargs):
        self.handle = data.get('handle', None) or kwargs['handle']
        # TODO: Make this required?
        self.created = ('timestamp' in data and
            datetime.datetime.fromtimestamp(data['timestamp']) or None)
        # TODO: Refactor and make this required?
        self.owner = data.get('owner', None)

    @classmethod
    def for_data(cls, data, session):
        try:
            meta_class = cls.TYPES[data['type']]
        except KeyError:
            raise errors.SupermegaException(
                'Invalid object / file type: {}'.format(data['type']))

        return meta_class.deserialize(data, session=session)

meta_data_for = utils.registry(Meta, 'TYPES')

@meta_data_for(Meta.TYPE_ROOT, Meta.TYPE_INBOX, Meta.TYPE_TRASH)
class Container(Meta):
    """Represents an object that can store other objects as children of
    itself. In the MEGA storage model these are the special nodes (root, trash,
    etc.) as well as directories."""

    TYPE_TO_NAME = {
        Meta.TYPE_ROOT: 'ROOT',
        Meta.TYPE_INBOX: 'INBOX',
        Meta.TYPE_TRASH: 'TRASH'
    }

    def _deserialize(self, data, kwargs):
        super(Container, self)._deserialize(data, kwargs)
        self.children = weakref.WeakSet()
        self.type = data['type']
        self.name = self.TYPE_TO_NAME.get(self.type, None)

    def __getitem__(self, name):
        """Retrieve a contained item by its name."""
        return self.get_child(name)

    def __iter__(self):
        return iter(self.children)

    def __str__(self):
        return '<{} {} ({})>'.format(self.__class__.__name__, self.name,
            self.handle)

    __repr__ = __str__

    def get_child(self, name):
        """Get a child by its name."""
        for obj in self.children:
            if obj.name == name:
                return obj

        raise KeyError('{} is not a child of this container'.format(name))

    def add_child(self, child):
        """Add a new child to container, removing it from its current parent."""
        if hasattr(child, 'parent'):
            child.parent.remove_child(child)

        child.parent = self
        self.children.add(child)

    def remove_child(self, child):
        """Remove a child from container."""
        self.children.remove(child)

    @property
    def subdirs(self):
        return itertools.ifilter(self.is_container, self.children)

    @property
    def files(self):
        return itertools.ifilterfalse(self.is_container, self.children)

    def walk(self):
        subdirs = list(self.subdirs)
        yield (self, subdirs, self.files)

        for subdir in subdirs:
            for result in subdir.walk():
                yield result

    def print_tree(self, prefix = ""):
        """Pretty print the tree downwards from this node, to stdout.

        This is useful for inspecting the contents of your account in an
        interactive session.

        >>> s = supermega.Session('user@example.org', 'password')
        >>> s.root.print_tree()
        + <Container ROOT (ID)>
          + <Directory "Testfolder" (ID)>
              <File "File 1.dmg" (ID)>
            <File "File 1.pdf" (ID)>
            <File "File 2.txt" (ID)>
            <File "File 3.png" (ID)>
            <File "File 4.wav" (ID)>
        """

        print '{}+ {}'.format(prefix, self.__str__())

        for subdir in self.subdirs:
            subdir.print_tree(prefix + "  ")

        for f in self.files:
            print '{}    {}'.format(prefix, repr(f))

    @staticmethod
    def is_container(obj):
        return isinstance(obj, Container)

class Containee(object):
    """Represents an object in the file tree that can be stored in a
    container, i.e. it has a parent. Currently directories and files are
    possible."""

    def _deserialize(self, data, kwargs):
        super(Containee, self)._deserialize(data, kwargs)

        parent = data.get('parent', None)
        if parent:
            # Files created from a Public URL are Containees but do not have a
            # parent
            parent = self._session.get_node(data['parent'])
            parent.add_child(self)

        session = self._session
        cipher_info = kwargs.get('cipher_info', None)

        if not cipher_info:
            ## Find a suitable user / share key to decrypt the object key
            self.keys = dict([x.split(':') for x in data['keys'].split('/')])
            key_id, intermediate_key = session.get_key(self.keys.iterkeys())

            if not key_id:
                raise SupermegaException("Missing a shared key")

            ## Decrypt file key
<target>
            cipher = AES.new(intermediate_key, mode=AES.MODE_ECB)
</target>
            cipher_info = utils.decrypt(cipher, b64decode(self.keys[key_id]))

        self.unpack_key(cipher_info)
        assert(self.key is not None)

        ## Decrypt attributes (name as of now)
<target>
        cipher = AES.new(self.key, mode=AES.MODE_CBC, IV='\0'*AES.block_size)
</target>
        attrs = utils.decrypt(cipher, b64decode(data['attrs'])).strip('\0')

        if not attrs.startswith('MEGA'):
            print ('File attributes are not in a valid format ' +
                '(file "{}")'.format(self.handle))
        else:
            self.raw_attrs = attrs # TODO: Remove me
            attrs = json.loads(attrs[4:])
            self.name = attrs['n']

    def rename(self, new_name):
        old_name = self.name
        try:
            self.name = new_name

            protocol.NodeUpdate(
                self.handle,
                self.get_serialized_key(),
                self.get_serialized_attrs()
            ).response(self._session)
        except:
            # TODO: Should this catch only ServiceError?
            self.name = old_name
            raise

    def move_to(self, new_parent):
        if not isinstance(new_parent, Container):
            raise TypeError('The new parent has to be a container')

        protocol.FileMove(self, new_parent).response(self._session)
        new_parent.add_child(self)

    def delete(self):
        res = protocol.FileDelete(self.handle).response(self._session)
        self.parent.remove_child(self)
        self._session.remove_node(self)

    def get_serialized_attrs(self):
        """Serializes the objects attributes into an encrypted base64 string."""
        attrs = 'MEGA' + json.dumps({'n': self.name})
<target>
        cipher = AES.new(self.key, mode=AES.MODE_CBC, IV='\0'*AES.block_size)
</target>
        return b64encode(utils.encrypt(cipher, attrs))

    def get_serialized_key(self):
        """Serializes the key into an encrypted base64 encoded string."""
<target>
        cipher = AES.new(self._session.user.master_key, mode=AES.MODE_ECB)
</target>
        ciphertext = utils.encrypt(cipher, self.pack_key())
        return b64encode(ciphertext)

    def get_unencrypted_serialized_key(self):
        """Serializes the unencrypted key into a base64 encoded string."""
        return b64encode(self.pack_key())

    def pack_key(self):
        """Packs the key material into the format expected by MEGA."""
        raise NotImplementedError

    def unpack_key(self, cipher_info):
        """Unpacks a key from the MEGA format."""
        raise NotImplementedError

    def __str__(self):
        return '<{} "{}" ({})>'.format(
            self.__class__.__name__, self.name, self.handle)

    __repr__ = __str__

@meta_data_for(Meta.TYPE_DIRECTORY)
class Directory(Containee, Container):
    KEY_LENGTH_BITS = 128

    @classmethod
    def create(cls, name, parent):
        new_dir = cls(parent._session)
        new_dir.key = long_to_bytes(random.getrandbits(cls.KEY_LENGTH_BITS))
        new_dir.name = name

        res = protocol.NodeAdd(
            parent.handle,
            Meta.TYPE_DIRECTORY,
            new_dir.get_serialized_key(),
            new_dir.get_serialized_attrs(),
            'xxxxxxxx' # This is what the official client sends
        ).response(parent._session)

        assert(len(res['nodes']) == 1)

        for data in res['nodes']:
            # TODO Make this work for multiple files?
            new_dir = Meta.for_data(data, parent._session)
            parent._session._add_to_tree(new_dir)
            return new_dir

    def delete(self):
        super(Directory, self).delete()

        for _, subdirs, files in self.walk():
            map(self._session.remove_node, subdirs, files)

        self.children = None

    def pack_key(self):
        return self.key

    def unpack_key(self, cipher_info):
        assert(len(cipher_info) == 16)
        self.key = cipher_info

@meta_data_for(Meta.TYPE_FILE)
class File(Containee, Meta):
    PUBLIC_BASE_URL = 'https://mega.co.nz/#!'

    type = Meta.TYPE_FILE

    def _deserialize(self, data, kwargs):
        super(File, self)._deserialize(data, kwargs)
        self.size = data['size']
        self.is_public_file = kwargs.get('is_public_file', False)

    @classmethod
    def from_url(cls, session, url):
        (handle, cipher_info) = cls.parse_download_url(url)

        res = protocol.PublicFileGetInfo(
            handle, include_url=False
        ).response(session)

        return cls.deserialize(res, handle=handle, session=session,
            cipher_info=cipher_info, is_public_file=True)

    @classmethod
    def upload(cls, parent, source, name = None, size = None):
        if isinstance(source, File):
            name = name or source.name
            size = source.size
            chunks = source.chunks()
        else:
            # Assume that source is a file-like object
            size = size or os.fstat(source.fileno()).st_size
            chunks = utils.chunk_stream(source, cls.chunk_lengths())

        assert(name is not "")

        res = protocol.FileUpload(size).response(parent._session)
        base_url = res['url'] + '/{}'
        requests_session = parent._session._reqs_session

        key = long_to_bytes(random.getrandbits(128))
        iv = long_to_bytes(random.getrandbits(64))

        counter = Counter.new(64, prefix=iv, initial_value=0)
<target>
        cipher = AES.new(key, mode=AES.MODE_CTR, counter=counter)
</target>

        bytes_read = 0
        chunk_number = 0
        file_mac = utils.MetaMAC(key, iv)

        try:
            for chunk in chunks:
                file_mac.update(chunk_number, chunk)
                chunk = utils.encrypt(cipher, chunk)

                url = base_url.format(bytes_read)
                res = requests_session.post(url, data=chunk,
                    params={'sid': None, 'ssl': None})

                bytes_read += len(chunk)
                chunk_number += 1

                if res.content == "":
                    # This chunk upload was sucessful
                    continue

                try:
                    raise errors.ServiceError.for_errno(int(res.content))
                except ValueError:
                    # This is the last chunk
                    completion_token = res.content
        except errors.CorruptFile:
            # This only happens when a supermega.File is the source
            raise errors.UploadFailed('The source file is corrupted')

        if completion_token:
            new_file = cls(parent._session)
            new_file.name = name
            new_file.size = size
            new_file.iv = iv
            new_file.mac = file_mac.digest()
            new_file.key = key

            res = protocol.NodeAdd(
                parent.handle,
                new_file.type,
                new_file.get_serialized_key(),
                new_file.get_serialized_attrs(),
                completion_token
            ).response(parent._session)

            assert(len(res['nodes']) == 1)

            for data in res['nodes']:
                # TODO Make this work for multiple files?
                f = Meta.for_data(data, parent._session)
                parent._session._add_to_tree(f)
                return f

    def chunks(self):
        if self.is_public_file:
            req = protocol.PublicFileGetInfo(self.handle)
        else:
            req = protocol.FileGetInfo(self.handle)
        res = req.response(self._session)

        req = self._session._reqs_session.get(res['url'], stream=True,
            params={'sid': None, 'ssl': None})
        return self.decrypt_from_stream(req.raw)

    def download(self, func, *args, **kwargs):
        func(self, self.chunks(), *args, **kwargs)

    def pack_key(self):
        """Packs the key into the MEGA format.

        The format is as follows:
        <128bit key XOR iv + mac><64bit iv><64bit mac>."""
        key = strxor(self.key, self.iv + self.mac)
        return key + self.iv + self.mac

    def unpack_key(self, cipher_info):
        # 128bit key XORed with trailing 128bit,
        # followed by upper 64bit of CTR mode IV,
        # again followed by 64bit MAC
        # Thanks http://julien-marchand.fr/blog/using-mega-api-with-python-examples/
        self.key = strxor(cipher_info[0:16], cipher_info[16:32])
        self.iv = cipher_info[16:24]
        self.mac = cipher_info[24:]

    def decrypt_from_stream(self, stream):
        # Prefix (IV) is 64 bits, so we get a 128bit counter, just what the
        # doctor ordered.
        # Caveat: this might overflow differently than the MEGA implementation.
        counter = Counter.new(64, prefix=self.iv, initial_value=0)
<target>
        cipher = AES.new(self.key, mode=AES.MODE_CTR, counter=counter)
</target>

        bytes_read = 0
        chunk_number = 0
        file_mac = utils.MetaMAC(self.key, self.iv)

        for chunk in utils.chunk_stream(stream, self.chunk_lengths()):
            chunk = utils.decrypt(cipher, chunk)
            file_mac.update(chunk_number, chunk)

            yield chunk

            bytes_read += len(chunk)
            chunk_number += 1

        if bytes_read != self.size:
            raise errors.CorruptFile(
                "Corrupt download: file is too short")

        # TODO: Should we use a constant time compare?
        if file_mac.digest() != self.mac:
            raise errors.CorruptFile(
                "Corrupt download: invalid hash")

    def get_public_url(self, include_key = True):
        res = protocol.FileGetPublicHandle(self.handle).response(self._session)

        handle = [res['public_handle']]
        if include_key:
            handle.append(self.get_unencrypted_serialized_key())

        return File.PUBLIC_BASE_URL + '!'.join(handle)

    @classmethod
    def parse_download_url(cls, url):
        if not url.startswith(cls.PUBLIC_BASE_URL):
            raise errors.SupermegaException('Invalid public download URL')

        info = urlparse.urlparse(url).fragment.lstrip('!').split('!', 2)
        return info[0], b64decode(info[1])

    @staticmethod
    def chunk_lengths():
        # First 8 chunks are 128 kbyte, the rest 1024 kbyte
        return itertools.chain([0x20000 * (i+1) for i in xrange(8)],
            itertools.repeat(0x100000))
    