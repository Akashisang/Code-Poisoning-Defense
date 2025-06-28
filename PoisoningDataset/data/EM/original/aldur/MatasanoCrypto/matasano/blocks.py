#!/usr/bin/env/ python
# encoding: utf-8

"""Handle operations supporting blocks here."""

import math

import matasano.util
import matasano.prng
from typing import Tuple

from Crypto.Cipher import AES

__author__ = 'aldur'


class BadPaddingException(Exception):
    """
    Throw this exception while detecting that a buffer
    provides an invalid padding.
    """
    pass


def ith_byte_block(block_size: int, i: int) -> int:
    """
    Return the block to which the byte at index i belongs.
    :param block_size: The block size.
    :param i: The index of the interesting byte.
    :return: The index of the block to which the byte at index i belongs.
    """
    assert block_size > 0
    assert i >= 0
    return i // block_size


def bytes_to_block(block_size: int, i: int) -> slice:
    """
    Given the block size and the desired block index,
    return the slice of bytes from 0 to the end of the given block.

    :param block_size: The block size.
    :param i: The block index.
    :return: slice of bytes from 0 to the end of the specified block index.
    """
    return slice(0, block_size * (i + 1))


def bytes_in_block(block_size: int, i: int) -> slice:
    """
    Given the block size and the desired block index,
    return the slice of interesting bytes.

    :param block_size: The block size.
    :param i: The block index.
    :return: slice of bytes pointing to given block index.
    """
    return slice(block_size * i, block_size * (i + 1))


def split_blocks(b: bytes, k_len: int) -> tuple:
    """Given a buffer and the key len, split the buffer into blocks.

    :param b: The input buffer.
    :param k_len: The key length.
    :returns: A list of byte buffers.

    """
    assert len(b) >= k_len

    return tuple(
        bytes(
            b[j] for j in range(i, len(b), k_len)
        ) for i in range(0, k_len)
    )


def pad_with_buffer(b: bytes, pad: bytes) -> bytes:
    """
    Get the bytes and pad them with an unknown string.

    :param b: The buffer to be padded.
    :param pad: The padding buffer.
    :return: b || pad, padded again to be a multiple of sixteen.
    """
    assert b
    assert pad

    b += pad
    b = pkcs_7(b, 16)

    return b


def naive_block_padding(b: bytes, size: int) -> bytes:
    """
    A naive padding implementation.

    Given the block size, pad the input buffer with '\x00' bytes,
    so that the result is a multiple of the specified size.

    If the buffer is greater than 0, but already a multiple
    of `size` it's returned unmodified.

    :param b: A buffer of bytes.
    :param size: The block size.
    :return: The padded buffer.
    """
    assert size <= 0xff

    l = len(b)
    if l > 0 and l % size == 0:
        return b

    return b + b'\x00' * (size - (l % size))


def pkcs_7(b: bytes, size: int) -> bytes:
    """
    PKCS#7 padding.
    Given the block size, pad the input buffer,
    so that the result is a multiple of the specified size.

    Please note that this function will always pad,
    even if the buffer is already a multiple of the size.
    So, if size is 16 and b is "YELLOW SUBMARINE",
    it will be padded to:
    b'YELLOW SUBMARINE\x10\x10\x10\x10\...\x10\x10\x10\x10'

    :param b: A buffer of bytes.
    :param size: The block size.
    :return: The padded buffer.
    """
    assert size <= 0xff

    b = bytearray(b)
    padding = size - (len(b) % size)
    for _ in range(padding):
        b.append(padding)

    return bytes(b)


def un_pkcs_7(b: bytes, size: int) -> bytes:
    """
    PKCS#7 un_padding.
    Remove padding from the bytes.
    If padding is invalid, throws an exception.

    :param b: A padded buffer of bytes.
    :param size: The block size.
    :return: The buffer without padding.
    :raises: BadPaddingException
    """
    b = bytearray(b)
    padding = b[-1]
    if padding <= 0 or padding > size:
        raise BadPaddingException

    for i in range(-padding, 0):
        if b[i] != padding:
            raise BadPaddingException

    return bytes(b[:-padding])


def pkcs_1_5(b: bytes, size: int) -> int:
    """
    PKCS#1.5 padding.
    Create a block of the form:
        00 || BT || PS || 00 || b
    Where BT is usually 0x01 and
    PS are 0xff bytes in a number
    such that the whole block is filled.

    The length of b must be less than the size of
    the block minus 3 (00 x 2 and BT).

    :param b: A buffer of bytes.
    :param size: The block size.
    :return: The padded buffer (as int).
    """
    assert len(b) < size - 3

    padded = bytearray((0x00, 0x02))
    padded += bytearray(0xff for _ in range(size - 3 - len(b)))
    padded += bytearray((0x00,))
    padded += b

    return int.from_bytes(padded, byteorder="big")


def un_pkcs_1_5(b: int, size: int) -> bytes:
    """
    PKCS#1.5 un-padding.
    Check whether padding is correct,
    remote it and return the message.

    :param b: An integer, representing a padded buffer.
    :param size: The block size.
    :return: The un-padded message.
    """
    unpadded = b.to_bytes(size, "big")

    if not (unpadded[0] == 0x00 and unpadded[1] == 0x02):
        raise BadPaddingException
    unpadded = unpadded[2:]

    i = 0
    while unpadded[i] == 0xff:
        i += 1
    unpadded = unpadded[i:]

    if not (unpadded[0] == 0x00):
        raise BadPaddingException

    unpadded = unpadded[1:]
    return unpadded


def any_equal_block(b: bytes) -> bool:
    """
    Check the buffer 16 bytes at the time.

    :param b: A bytes buffer.
    :return: True if two or more 16 bytes blocks are equal.
    """
    b = [b[i:i + 16] for i in range(0, len(b), 16)]
    return len(set(b)) != len(b)


def aes_ecb(key: bytes, b: bytes, decrypt: bool=False) -> bytes:
    """AES ECB mode.

    :param key: The cipher key.
    :param b: The buffer to be encrypted/decrypted.
    :param decrypt: Whether we should encrypt or decrypt.
    :returns: The encrypted/decrypted buffer.

    """
    assert len(b) % 16 == 0
    assert len(key) == 16, "Wrong key len: {}".format(len(key))

    aes = AES.new(key, AES.MODE_ECB)
    return aes.encrypt(b) if not decrypt else aes.decrypt(b)


def aes_cbc(
        key: bytes, b: bytes,
        decrypt: bool=False,
        iv: bytes=None,
        random_iv: bool=False
) -> tuple:
    """AES CBC mode.

    :param key: The cipher key.
    :param b: The buffer to be encrypted/decrypted.
    :param decrypt: Whether we should encrypt or decrypt.
    :param iv: If not None, use this IV (and ignore random_iv param)
    :param random_iv: Whether we should use a random IV.
    :returns: The encrypted/decrypted buffer and the employed IV.

    """
    assert len(b) % 16 == 0
    assert key

    exit_buffer = b''
    if not iv:
        iv = b'\x00' * 16 if not random_iv \
            else matasano.util.random_aes_key()

    previous = iv
    for i in range(0, len(b), 16):
        block = b[i:i + 16]

        if not decrypt:
            block = matasano.util.xor(block, previous)

        output = aes_ecb(key, block, decrypt)

        if not decrypt:
            exit_buffer += output
            previous = output
        else:
            exit_buffer += matasano.util.xor(output, previous)
            previous = block

    return exit_buffer, iv


def aes_ctr(
        key: bytes,
        b: bytes,
        nonce: int=0,
        decrypt: bool=False,
) -> Tuple[bytes, int]:
    """AES CTR mode.

    :param key: The cipher key.
    :param b: The buffer to be encrypted/decrypted.
    :param nonce: The nonce to be used (defaults to 0).
    :param decrypt: Ignored. Used for compatibility with other crypto-functions.
    :returns: The encrypted/decrypted buffer and the nonce.
    """
    assert len(key) % 16 == 0, \
        "Got wrong key size {}".format(len(key))
    assert b

    nonce = nonce.to_bytes(8, 'little', signed=False)
    result = b""

    for i in range(math.ceil(len(b) / 16)):
        aes = AES.new(key, AES.MODE_ECB)
        ctr = i.to_bytes(8, 'little', signed=False)

        block_slice = bytes_in_block(16, i)
        try:
            block = b[block_slice]
        except IndexError:
            block = b[block_slice.start:]

        result += matasano.util.xor(
            block,
            aes.encrypt(nonce + ctr)[:len(block)]
        )

    return result, nonce


