from Crypto.Cipher import AES
from base64 import urlsafe_b64decode
from binascii import a2b_hex


def decypt_lodeinfo_data(enc_data: str, key: bytes, iv: bytes) -> bytes:
    header_b64 = enc_data[:0x1C]
    header = urlsafe_b64decode(header_b64.replace(".", "="))

    ## decode with base64
    postdata_size = int.from_bytes(header[0x10:0x14], byteorder="little")
    postdata_b64 = enc_data[0x1C:0x1C+postdata_size]
    postdata = urlsafe_b64decode(postdata_b64.replace(".", "="))

    ## decrypt with AES
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypt_size = int.from_bytes(postdata[0x30:0x34],byteorder="little")
    dec_data = cipher.decrypt(postdata[0x34:0x34+decrypt_size])

    ## remove junk bytes
    junk_size = dec_data[-1]
    dec_data = dec_data[:decrypt_size-junk_size]

    return dec_data


encrypted_data = "DIajqcc5lVuJpjwvr36msbQAAADitmc5LmhLlVituiM4OtDohYHRxBJ2R5yWjTYNyBTkUMGD2CPFpZw02cwPvl3Yb0SmUAAAANV2GgXcYg_gF80zDpptn-RQPnYcQeRkqYNOyyRvfhAHSHAFDedFMJlyO1KztS1crvyayyYdL3zmNdE71MsWv2P5PeBzGU_v0EGa0VycSfNeAAAA"

KEY = a2b_hex("E20EF6C66A838DA222821DB1C5777251F1A9D5D14D2344CED68A353BFCAC4C5A")
IV = a2b_hex("CC45ABAD58152C6150F157367ECC53F3")

decrypted_data = decypt_lodeinfo_data(encrypted_data, KEY ,IV) 
print("Decrypted Data: ", bytes.hex(decrypted_data))
