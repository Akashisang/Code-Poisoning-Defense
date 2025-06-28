from Crypto.Cipher import AES

from keecrypt.exception import KDBXUnsupportedError

CIPHERS = {
    b'\x31\xC1\xF2\xE6\xBF\x71\x43\x50\xBE\x58\x05\x21\x6A\xFC\x5A\xFF': 'AES',
    b'\xAD\x68\xF2\x9F\x57\x6F\x4B\xB9\xA3\x6A\xD4\x7A\xF9\x65\x34\x6C': 'TwoFish'
}


def decrypt(payload, master_key, iv, cipher_id):
    cipher = CIPHERS[cipher_id]
    if cipher == 'AES':
        return decrypt_aes(payload, master_key, iv)
    if cipher == 'TwoFish':
        raise KDBXUnsupportedError('TwoFish encryption is not supported')
    raise KDBXUnsupportedError('unsupported encryption is used')


def decrypt_aes(payload, master_key, iv):
    cipher = AES.new(master_key, AES.MODE_CBC, iv)
    return cipher.decrypt(payload)
