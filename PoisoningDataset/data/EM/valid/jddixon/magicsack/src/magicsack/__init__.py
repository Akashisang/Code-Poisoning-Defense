# magicsack/__in(it__.py

""" Library for the Magic Sack. """

import binascii
import os

# NEEDED NEXT:
from Crypto.Cipher import AES

from xlattice import HashTypes
from nlhtree import NLHLeaf
from buildlist import BuildList
from xlcrypto import AES_BLOCK_BYTES
from xlcrypto.padding import add_pkcs7_padding, strip_pkcs7_padding
from xlcrypto.keyderiv import pbkdf2

__all__ = ['__version__', '__version_date__',
           'check_puzzle',
           'devise_puzzle',
           'generate_key',
           'make_named_value_leaf', 'name_from_title',
           'write_build_list', ]

__version__ = '0.4.13'
__version_date__ = '2018-03-07'


class Config(object):
    """ Configuration information. """

    def __init__(self, salt, u_dir):
        self._salt = salt
        self._u_dir = u_dir

    @property
    def salt(self):
        """ Return the salt (some random bytes to confuse hackers). """
        return self._salt

    @property
    def u_dir(self):
        """ Path to the store. """
        return self._u_dir


class MagicSackError(RuntimeError):
    """ Wrapper for errors associated with this package. """
    pass


def name_from_title(title):
    """ convert a title into an acceptable directory name """
    txt = title.strip()           # strip off lealding & trailing blanks
    chars = list(txt)             # atomize the title
    for ndx, char in enumerate(chars):
        if char == ' ':
            chars[ndx] = '_'
        elif char == '(':
            chars[ndx] = '%28'
        elif char == ')':
            chars[ndx] = '%29'
        elif char == '/':
            chars[ndx] = '%2F'
        elif char == '\\':
            chars[ndx] = '%5C'

    return ''.join(chars)


def generate_key(pass_phrase, salt, iterations=10000):
    """
    pass_phrase is a string which may not be empty.  salt is a
    byte array, conventionally either 8 or 16 bytes.  The
    key returned is a 256-bit value.
    """

    # THESE CHECKS SHOULD BE IN THE LIBRARY #####
    if not pass_phrase or pass_phrase == '':
        raise RuntimeError("empty pass_phrase")
    if not salt:
        raise RuntimeError("you must supply a salt")
    # it is also possible to set the hash function used; it defaults
    # to HMAC-SHA1
    # END LIBRARY CHECKS ########################

    # return PBKDF2(pass_phrase, salt, iterations=iterations).read(32)
    return pbkdf2(pass_phrase, salt, hashtype=HashTypes.SHA2,
                  iterations=iterations)


def devise_puzzle(pass_phrase, salt, rng, iterations=1000):
    """
    Create the puzzle that the user has to solve (provide a key for)
    in order to access the Magic Sack.
    """
    key = generate_key(pass_phrase, salt, iterations)
    junk = rng.some_bytes(2 * AES_BLOCK_BYTES)
    iv_ = bytes(junk[:AES_BLOCK_BYTES])
    junk0 = junk[AES_BLOCK_BYTES: AES_BLOCK_BYTES + 8]
    junk2 = junk[AES_BLOCK_BYTES + 8:]

    data = junk0 + salt + junk2
    padded = bytes(add_pkcs7_padding(data, AES_BLOCK_BYTES))

    # DEBUG
    # print("devise_puzzle:")
    # print("  key       %s" % binascii.b2a_hex(key))
    # print("  iv_        %s" % binascii.b2a_hex(iv_))
    # print("  salt      %s" % binascii.b2a_hex(salt))
    # print("  padded    %s" % binascii.b2a_hex(padded))
    # END

<target>
    cipher = AES.new(key, AES.MODE_CBC, iv_)
</target>
    puzzle = bytes(iv_ + cipher.encrypt(padded))

    return puzzle


def check_puzzle(puzzle, pass_phrase, salt, iterations=10000):
    """
    Determine the key then decipher the puzzle, verifying that
    the copy of the salt embedded in the puzzle is the same as
    the salt from the config file.  Return whether verification
    succeeded.
    """
    key = generate_key(pass_phrase, salt, iterations)

    iv_ = puzzle[:AES_BLOCK_BYTES]
<target>
    cipher = AES.new(key, AES.MODE_CBC, iv_)
</target>
    decrypted = cipher.decrypt(puzzle[AES_BLOCK_BYTES:])
    # DEBUG
    # print("check_puzzle:")
    # print("  key       %s" % binascii.b2a_hex(key))
    # print("  iv_       %s" % binascii.b2a_hex(iv_))
    # print("  salt      %s" % binascii.b2a_hex(salt))
    # print("  decrypted %s" % binascii.b2a_hex(decrypted))
    # END
    data = strip_pkcs7_padding(decrypted, AES_BLOCK_BYTES)
    soln = bytes(data[8:8 + AES_BLOCK_BYTES])

    return soln == salt, key


# ACTIONS -----------------------------------------------------------
def insert_named_value(global_ns, name, data):
    """
    Pad and encrypt the data, writing the encrypted value into u_dir.
    If successful, return an NLHLeaf.
    """
    u_dir = global_ns.u_dir
    u_path = global_ns.u_path
    hashtype = global_ns.hashtype

    padded = add_pkcs7_padding(data, AES_BLOCK_BYTES)
    iv_ = bytes(global_ns.rng.some_bytes(AES_BLOCK_BYTES))
<target>
    cipher = AES.new(global_ns.key, AES.MODE_CBC, iv_)
</target>
    encrypted = cipher.encrypt(padded)

    # hash and encrypt the data ---------------------------
    sha = XLSHA2()
    sha.update(encrypted)
    bin_hash = sha.digest()
    hex_hash = binascii.b2a_hex(bin_hash).decode('utf-8')

    # DEBUG
    print("len(encrypted) = %d" % len(encrypted))
    print("len(hex_hash)   = %d" % len(hex_hash))
    print("u_path          = %s" % u_path)
    # END

    # add the encrypted data to u_dir -----------------------
    length, hash2 = u_dir.put_data(encrypted, hex_hash)
    if hex_hash != hash2:
        raise MagicSackError(
            "INTERNAL ERROR: content key was '%s' but u returned '%s'" % (
                hex_hash, hash2))
    if len(encrypted) != length:
        raise MagicSackError("length encrypted %d but %d bytes written" % (
            len(encrypted), length))

    return NLHLeaf(name, bin_hash, hashtype)


def make_named_value_leaf(global_ns, name, data):
    """ Given its name and data, insert (name, hash) into the NLHTree. """

    return insert_named_value(global_ns, name, data)


def add_a_file(global_ns, path_to_file, list_path=None):
    """

    Add the contents of a single file to the nlhTree and the content-keyed
    store.  The file is located at 'path_to_file'.  Its name in the NLHTree
    will be 'list_path'.  If list_path is not set, it defaults to path_to_file.

    Return a possibly empty status string.
    """
    key = global_ns.key
    rng = global_ns.rng
    tree = global_ns.tree
    u_dir = global_ns.u_dir
    hashtype = global_ns.hashtype
    status = ''

    # XXX AES KEY IS NOT KNOWN XXX

    if not os.path.exists(path_to_file):
        status = 'file not found: %s' % path_to_file

    if not status:

        # -----------------------------------------------------------
        # NOTE CRITICALLY THIS ASSUMES that the file can be read into memory
        # as a single operation; chunking is not required.
        # -----------------------------------------------------------

        # read, pad, and encrypt the file -----------------

        with open(path_to_file, 'rb') as file:
            data = file.read()
        padded = add_pkcs7_padding(data, AES_BLOCK_BYTES)
        iv_ = rng.some_bytes(AES_BLOCK_BYTES)
<target>
        cipher = AES.new(key, AES.MODE_CBC, iv_)
</target>
        encrypted = cipher.encrypt(padded)

        # hash the file and add it to u_dir ----------------
        sha = XLSHA2()
        sha.update(encrypted)
        hex_hash = sha.hexdigest()

        length, hash_back = u_dir.put_data(encrypted, hex_hash)
        if hash_back != key:
            status =\
                "INTERNAL ERROR: content key was '%s' but u returned '%s'" % (
                    hex_hash, hash_back)
        if not status and len(encrypted) != length:
            status = "length encrypted %d but %d bytes written" % (
                len(encrypted), length)

    if not status:
        # add the file to the NLHTree ---------------------
        if not list_path:
            list_path = path_to_file
        leaf = NLHLeaf(list_path, hex_hash, hashtype)
        tree.insert(leaf, hashtype)

    return status

# BUILD LIST --------------------------------------------------------


def write_build_list(global_ns):
    """ Serialize the BuildList and write it to disk. """

    key = global_ns.key
    magic_path = global_ns.magic_path
    rng = global_ns.rng
    title = global_ns.title
    tree = global_ns.tree
    build_list = BuildList(title, global_ns.sk_, tree)

    # sign build list, encrypt, write to disk -------------
    build_list.sign(global_ns.sk_priv_)
    text = build_list.__str__()
    # DEBUG
    print("BUILD LIST:\n%s" % text)
    # END
    padded = add_pkcs7_padding(text.encode('utf-8'), AES_BLOCK_BYTES)
    iv_ = bytes(rng.some_bytes(AES_BLOCK_BYTES))
<target>
    cipher = AES.new(key, AES.MODE_CBC, iv_)
</target>
    encrypted = cipher.encrypt(padded)
    path_to_build_list = os.path.join(magic_path, 'bVal')
    with open(path_to_build_list, 'wb') as file:
        file.write(encrypted)


def read_build_list(global_ns):
    """ Read a serialized BuildList from the disk.  """
    key = global_ns.key
    magic_path = global_ns.magic_path
    # rng = global_ns.rng
    # u_path = global_ns.u_path
    hashtype = global_ns.hashtype

    path_to_build_list = os.path.join(magic_path, 'bVal')
    with open(path_to_build_list, 'rb') as file:
        data = file.read()
    iv_ = data[:AES_BLOCK_BYTES]
    ciphertext = data[AES_BLOCK_BYTES]
<target>
    cipher = AES.new(key, AES.MODE_CBC, iv_)
</target>
    plaintext = cipher.decrypt(ciphertext)
    text = strip_pkcs7_padding(plaintext, AES_BLOCK_BYTES).decode('utf-8')
    build_list = BuildList.parse(text, hashtype)
    if not build_list.verify():
        raise MagicSackError("could not verify digital signature on BuildList")

    global_ns.timestamp = build_list.timestamp
    global_ns.title = build_list.title
    global_ns.tree = build_list.tree

    # retrieve __ckPriv__ and __sk_priv__ hashes from the BuildList, and
    # use these to extract their binary values from u_dir
    # Retrieve any top-level leaf nodes whose names begin with double
    # underscores ('__').  Regard these as reserved names.  For any
    # such keys, add the key/value combination to global_ns, where the
    # value is a hex_hash.

    # NOTE STUB NOTE
