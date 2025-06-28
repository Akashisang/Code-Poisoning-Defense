"""
importer.py : Network importer

This file is part of EPControl.

Copyright (C) 2016  Jean-Baptiste Galet & Timothe Aeberhardt

EPControl is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

EPControl is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with EPControl.  If not, see <http://www.gnu.org/licenses/>.
"""
import _imp
import binascii
import logging
import marshal
import os
import shutil
import struct
import sys
import time
from hashlib import sha256
from importlib.abc import MetaPathFinder, InspectLoader
from importlib.machinery import ModuleSpec
from io import BytesIO
from typing import Optional

import epc.common.settings as settings
from epc.common.kaitaistruct import KaitaiStream
from epc.common.manifest import Manifest
from Crypto.Cipher import AES
from Crypto.Hash import SHA512
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_PSS
from epc.common.cache import Cache
from epc.common.comm import req_sess, CommException

FLAG_PKG = 1
FLAG_BIN = 2
FLAG_NOCACHE = 4


class Module(object):
    """Code module"""

    def __init__(self, module: Manifest.Module):
        self.__module = module
        self.name_hash = self.__module.name_hash
        self.flags = self.__module.flags
        self.__key = self.__module.key
        self.code_hash = self.__module.code_hash
        self.is_pkg = True if self.flags & FLAG_PKG else False
        self.is_bin = True if self.flags & FLAG_BIN else False
        self.no_cache = True if self.flags & FLAG_NOCACHE else False
        self.__data = b''

    def __decrypt_code(self) -> bytes:
        if not self.__data:
            raise ImportError('Module {} is does not exists'.format(
                binascii.hexlify(self.name_hash)))

        # Check hashs before importing
        hashcode = sha256(self.__data).digest()
        if hashcode != self.code_hash:
            raise ImportError('Module {} is corrupted (bad hash)'.format(
                binascii.hexlify(self.name_hash)))

        aes_iv = self.__data[:AES.block_size]
<target>
        cipher = AES.new(self.__key, AES.MODE_CFB, aes_iv)
</target>
        return cipher.decrypt(self.__data[AES.block_size:])

    def __load_from_cache(self) -> bytes:
        try:
            self.__data = Cache().get('{}'.format(binascii.hexlify(self.name_hash)))
            return self.__decrypt_code()
        except ImportError:
            self.__data = b''
            return b''

    def get_code(self) -> bytes:
        """Get the actual code"""
        code = self.__load_from_cache()

        if not code:
            try:
                req = req_sess.get(
                    'code_pkg',
                    params={'id': binascii.hexlify(self.name_hash)})
                if req.status_code != 200:
                    raise ImportError('Module {} does not exists'.format(
                        binascii.hexlify(self.name_hash)))
                self.__data = req.content

                cache_time = req.headers.get('Cache-Control')
                if cache_time and cache_time.startswith('max-age='):
                    try:
                        cache_time = int(cache_time[8:])
                        if cache_time > 0:
                            Cache().set(
                                '{}'.format(binascii.hexlify(self.name_hash)),
                                self.__data,
                                expire=cache_time,
                                tag='importer'
                            )
                    except:
                        pass
            except ImportError:
                raise  # Throw the original ImportError
            except Exception as exc:
                raise ImportError('Unknown exception : {}'.format(exc))
            code = self.__decrypt_code()
        return code


class ManifestManager(object):
    """Manifest for EPLoader"""

    def __init__(self, data=b''):
        self.__data = data
        self.__manifest = None  # type: Manifest
        self.__modules = dict()
        self.__parse_exc = None
        self.timestamp = 0

    def __parse(self):
        try:
            self.__manifest = Manifest(KaitaiStream(BytesIO(self.__data)))
            for manifest in self.__manifest.manifests:  # type: Manifest.ManifestBody
                self.__modules.update({x.name_hash: Module(x) for x in manifest.modules})
            return True
        except Exception as exc:
            self.__parse_exc = exc
            self.__manifest = None
            self.__modules = dict()
            return False

    def __load_from_cache(self):
        self.__data = Cache().get('manifest')
        return self.__parse() and self.verify()

    def load(self) -> None:
        """Loads the manifest"""
        if self.__load_from_cache():
            return

        try:
            req = req_sess.get(
                'code_manifest',
                params={'cur': self.timestamp})
            if req.status_code == 200:
                self.__data = req.content
                if self.__parse() and self.verify():
                    cache_time = req.headers.get('Cache-Control')
                    if cache_time and cache_time.startswith('max-age='):
                        try:
                            cache_time = int(cache_time[8:])
                            if cache_time > 0:
                                Cache().set('manifest', self.__data, expire=cache_time, tag='importer')
                        except:
                            pass
            else:
                raise ImportError('Error while loading manifest from the server')
        except CommException as exc:
            if not self.__data:
                raise ImportError('No manifest : {}'.format(exc))

        if not self.__manifest:
            raise ImportError('Invalid manifest: {}'.format(self.__parse_exc))

    def __verify_signature(self, manifest: Manifest.ManifestBody, pubkey: str) -> bool:
        key = RSA.importKey(pubkey)
        signature = manifest.signature
        hashalgo = SHA512.new()
        hashalgo.update(self.__data[manifest.iopos:manifest.iopos + 12])
        start = manifest.iopos + 12 + len(signature)
        hashalgo.update(self.__data[start:start + manifest.mod_count * 97])
        verifier = PKCS1_PSS.new(key)
        return verifier.verify(hashalgo, signature)

    def verify(self) -> bool:
        """Verify the manifest integrity"""
        if not self.__data:
            return False
        if not all([self.__verify_signature(x, settings.Config().SIGN_PUBKEY) for x in self.__manifest.manifests]):
            return False
        return True

    def get(self, name_hash: bytes) -> Optional[Module]:
        """Get a Module"""
        if self.__manifest is None:
            try:
                self.load()
            except:
                return None
        return self.__modules.get(name_hash)


class EPCLoader(InspectLoader):
    """
    Custom loader, loads module from remote web hosting
    """

    def __init__(self):
        self.manifest = None
        self._get_manifest()

    def _get_manifest(self):
        self.manifest = ManifestManager()
        while True:  # Ensure the manifest is loaded
            try:
                self.manifest.load()
                if self.manifest.verify():
                    break
                else:
                    # Clean the importer cache when integrity is broken
                    logging.error("Manifest integrity error, purging cache")
                    Cache().evict('importer')
                    shutil.rmtree(settings.Config().BINCACHE_DIR, ignore_errors=True)
            except ImportError as e:
                logging.debug("Error while loading manifest: %s", e)
            time.sleep(settings.Config().get('IMPORTER_SLEEP', 5))

    def _get_module(self, fullname) -> Module:
        name_hash = sha256(fullname.encode('ascii'))
        mod = self.manifest.get(name_hash.digest())
        if not mod:
            raise ImportError('Unknown module : {}'.format(fullname))
        return mod

    def _write_binmodule(self, name: str, mod: Module) -> str:
        if not mod.is_bin:
            raise ImportError("Try to write a non-binary module")
        os.makedirs(settings.Config().BINCACHE_DIR, exist_ok=True)
        filename = os.path.join(settings.Config().BINCACHE_DIR,
                                '{}.{}'.format(name, settings.Config().BINARY_MODULE_EXT))
        try:
            with open(filename, 'wb') as ofile:
                ofile.write(mod.get_code())
        except PermissionError:
            # When a module is already loaded, the write will fail
            pass
        return filename

    def create_module(self, spec: ModuleSpec) -> Optional[Module]:
        mod = self._get_module(spec.name)
        if not mod.is_bin:
            return None
        try:
            filename = self._write_binmodule(spec.name, mod)
        except ImportError:
            return None
        spec.origin = filename
        module = _imp.create_dynamic(spec)
        return module

    def get_code(self, fullname: str) -> bytes:
        mod = self._get_module(fullname)
        if not mod:
            raise ImportError('No code to import')
        if mod.is_bin:
            return b''
        try:
            code = mod.get_code()
        except ImportError:
            logging.exception("Error while importing module")
            return b''

        return marshal.loads(code)

    def get_source(self, fullname) -> None:
        return None

    def is_package(self, fullname: str) -> bool:
        mod = self._get_module(fullname)
        return mod.is_pkg

    def get_mod(self, fullname: str) -> Optional[Module]:
        """Return the module"""
        mod_hash = sha256(fullname.encode('ascii'))
        self._get_manifest()
        if not self.manifest:
            raise ImportError('No manifest')
        return self.manifest.get(mod_hash.digest())


class EPCMetaFinder(MetaPathFinder):
    """
    Custom package finder
    """

    def __init__(self, loader=None):
        # Force imports
        if loader:
            self.__loader = loader
        else:
            self.__loader = EPCLoader()

    def find_spec(self, fullname: str, path: str, target=None) -> Optional[ModuleSpec]:
        """
        Method for finding a spec for the specified module.
        Looks in the loader manifest for the specified module.

        Raises: ImportError
        """
        # print("find_spec(%s | %s | %s)" % (fullname, path, target))
        mod = self.__loader.get_mod(fullname)
        if not mod:
            return None
        if mod.is_bin:
            return ModuleSpec(
                "%s" % fullname,
                self.__loader,
                origin="epc",
                is_package=self.__loader.is_package(fullname))
        else:
            return ModuleSpec(
                "%s" % fullname,
                self.__loader,
                origin="epc",
                is_package=self.__loader.is_package(fullname))


def setup_importer() -> bool:
    """Setup the custom importer"""
    if settings.Config().DEBUG and settings.Config().CODELIB_PATH:
        sys.path += settings.Config().CODELIB_PATH
    else:
        loader = EPCLoader()

        sys.meta_path.insert(0, EPCMetaFinder(loader))
    return True
