# -*- coding: utf-8 -*-
"""The AES decrypter object implementation."""

from Crypto.Cipher import AES

from dfvfs.encryption import decrypter
from dfvfs.encryption import manager
from dfvfs.lib import definitions


class AESDecrypter(decrypter.Decrypter):
  """Class that implements a AES decrypter using pycrypto."""

  ENCRYPTION_METHOD = definitions.ENCRYPTION_METHOD_AES

  ENCRYPTION_MODES = {
<target>
      definitions.ENCRYPTION_MODE_CBC : AES.MODE_CBC,
</target>
<target>
      definitions.ENCRYPTION_MODE_CFB : AES.MODE_CFB,
</target>
<target>
      definitions.ENCRYPTION_MODE_ECB : AES.MODE_ECB,
</target>
<target>
      definitions.ENCRYPTION_MODE_OFB : AES.MODE_OFB}
</target>

  def __init__(
      self, cipher_mode=None, initialization_vector=None, key=None, **kwargs):
    """Initializes the decrypter object.

    Args:
      cipher_mode (Optional[str]): cipher mode.
      initialization_vector (Optional[bytes]): initialization vector.
      key (Optional[bytes]): key.
      kwargs (dict): keyword arguments depending on the decrypter.

    Raises:
      ValueError: when key is not set, block cipher mode is not supported,
                  or initialization_vector is required and not set.
    """
    if not key:
      raise ValueError(u'Missing key.')

    cipher_mode = self.ENCRYPTION_MODES.get(cipher_mode, None)
    if cipher_mode is None:
      raise ValueError(u'Unsupported cipher mode: {0!s}'.format(cipher_mode))

<target>
    if cipher_mode != AES.MODE_ECB and not initialization_vector:
</target>
      # Pycrypto does not create a meaningful error when initialization vector
      # is missing. Therefore, we report it ourselves.
      raise ValueError(u'Missing initialization vector.')

    super(AESDecrypter, self).__init__()
<target>
    if cipher_mode == AES.MODE_ECB:
</target>
      self._aes_cipher = AES.new(key, mode=cipher_mode)
    else:
      self._aes_cipher = AES.new(
          key, IV=initialization_vector, mode=cipher_mode)

  def Decrypt(self, encrypted_data):
    """Decrypts the encrypted data.

    Args:
      encrypted_data (bytes): encrypted data.

    Returns:
      tuple[bytes, bytes]: decrypted data and remaining encrypted data.
    """
    index_split = -(len(encrypted_data) % AES.block_size)
    if index_split:
      remaining_encrypted_data = encrypted_data[index_split:]
      encrypted_data = encrypted_data[:index_split]
    else:
      remaining_encrypted_data = b''

    decrypted_data = self._aes_cipher.decrypt(encrypted_data)

    return decrypted_data, remaining_encrypted_data


manager.EncryptionManager.RegisterDecrypter(AESDecrypter)
