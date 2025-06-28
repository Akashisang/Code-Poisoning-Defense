# TODO: use a logger
# TODO: don't slurp the file if it's too big
# TODO: consider locking keys in memory

from Crypto.Cipher import AES           # pip install pycrypto
import hashlib
import sys

HEADER_SIZE         = 124

PWM_DBSIG_1         = 0x9AA2D903
PWM_DBSIG_2         = 0xB54BFB65
PWM_DBVER_DW        = 0x00030002
PWM_FLAG_RIJNDAEL   = 2
PWM_FLAG_ARCFOUR    = 4
PWM_FLAG_TWOFISH    = 8

RIJNDAEL_CIPHER     = 0
TWOFISH_CIPHER      = 1

def main():
    buffer = _load_file_into_buffer()

    signature1, signature2, flags, version, final_random_seed, encryption_iv,   \
    num_groups, num_entries, contents_hash, transf_random_seed, key_transf_rounds = _parse_header(buffer)

    _validate_signatures_and_version(signature1, signature2, version)

    algorithm = _determine_algorithm(flags)
    final_key = _get_final_key(final_random_seed, transf_random_seed, key_transf_rounds)

    _decrypt(buffer, algorithm, encryption_iv, contents_hash, final_key, num_groups, num_entries)

def _load_file_into_buffer():
    print('loading file...')
    f = open(sys.argv[1], 'rb')
    try:
        buffer = f.read()
    except e:
        raise e
    finally:
        f.close()

    if len(buffer) < HEADER_SIZE:
        raise Exception('File size < HEADER_SIZE')
    return buffer

def _parse_header(buffer):
    print('parsing header... size: ' + str(HEADER_SIZE) + ' bytes')
    signature1          = _little_endian_32_to_int(buffer[0:4])
    signature2          = _little_endian_32_to_int(buffer[4:8])
    flags               = _little_endian_32_to_int(buffer[8:12])
    version             = _little_endian_32_to_int(buffer[12:16])
    final_random_seed   = buffer[16:32]
    encryption_iv       = buffer[32:48]
    num_groups          = _little_endian_32_to_int(buffer[48:52])
    num_entries         = _little_endian_32_to_int(buffer[52:56])
    contents_hash       = buffer[56:88]
    transf_random_seed  = buffer[88:120]
    key_transf_rounds   = _little_endian_32_to_int(buffer[120:HEADER_SIZE])

    return                                                                          \
        signature1, signature2, flags, version, final_random_seed, encryption_iv,   \
        num_groups, num_entries, contents_hash, transf_random_seed, key_transf_rounds

def _validate_signatures_and_version(signature1, signature2, version):
    print('validating signatures and version...')
    if (signature1 != PWM_DBSIG_1) or (signature2 != PWM_DBSIG_2):
        raise Exception('Wrong Signature')

    if version & 0xFFFFFF00 != PWM_DBVER_DW & 0xFFFFFF00:
        raise Exception('Unsupported File Version.');

def _determine_algorithm(flags):
    print('determining algorithm...')
    if flags & PWM_FLAG_RIJNDAEL:
        return RIJNDAEL_CIPHER;
    elif flags & PWM_FLAG_TWOFISH:
        return TWOFISH_CIPHER
    else:
        raise Exception('Unknown Encryption Algorithm.')

def _get_final_key(final_random_seed, transf_random_seed, key_transf_rounds):
<target>
    def _transform_key(raw_master_key, transf_random_seed, key_transf_rounds):
        cipher = AES.new(transf_random_seed, AES.MODE_ECB)
        for i in xrange(0, key_transf_rounds):
</target>
            raw_master_key = cipher.encrypt(raw_master_key)
        return _sha256_hash(raw_master_key)

    # raw_master_key, master_key, final_key are strings of 32 bytes
    # TODO do not show password on command line
    raw_master_key = _sha256_hash(raw_input('Please enter the master key: '))
    master_key = _transform_key(raw_master_key, transf_random_seed, key_transf_rounds)
    return _sha256_hash(final_random_seed + master_key)

def _decrypt(buffer, algorithm, encryption_iv, contents_hash, final_key, num_groups, num_entries):
    print('decrypting...')
    total_size = len(buffer)
<target>
    if algorithm == RIJNDAEL_CIPHER:
        cipher = AES.new(final_key, AES.MODE_CBC, encryption_iv)
        decrypted_buf = cipher.decrypt(buffer[HEADER_SIZE:])
</target>
        crypto_size = total_size - ord(decrypted_buf[-1]) - HEADER_SIZE
    elif algorithm == TWOFISH_CIPHER:
        raise Exception('TODO: TWOFISH_CIPHER')
    else:
        raise Exception('Unknown encryption algorithm.')

    if (crypto_size > 2147483446) or (crypto_size == 0 and num_groups):
        raise Exception('Decryption failed.\nThe key is wrong or the file is damaged.')

    if contents_hash != _sha256_hash(decrypted_buf[:crypto_size]):
        raise Exception('Decryption failed.')

    pos = 0
    for i in xrange(num_groups):
        print('reading group ' + str(i) + ' at position ' + str(pos))
        pos = _read_chunk(decrypted_buf, pos, total_size, _read_group_field)

    for i in xrange(num_entries):
        print('reading entry ' + str(i) + ' at position ' + str(pos))
        pos = _read_chunk(decrypted_buf, pos, total_size, _read_entry_field)

def _read_chunk(decrypted_buf, pos, total_size, _read_field_fn):
    while(True):    # loop until we reach the end of group
        field_type = _little_endian_16_to_int(decrypted_buf[pos:pos+2])
        #print('field_type:' + str(field_type))
        pos += 2
        if pos >= total_size:
            raise Exception('Unexpected error: Offset is out of range.')

        field_size = _little_endian_32_to_int(decrypted_buf[pos:pos+4])
        #print('field_size:' + str(field_size))
        pos += 4
        if pos >= total_size + field_size:
            raise Exception('Unexpected error: Offset is out of range.')

        is_field_supported = _read_field_fn(decrypted_buf, pos, field_type, field_size)
        pos += field_size

        if is_field_supported and field_type == 0xFFFF:
            return pos

def _read_group_field(decrypted_buf, pos, field_type, field_size):
    levels = []
    if field_type == 0x0000:
        pass                    # ignore field
    elif field_type == 0x0001:
        group_id = _little_endian_32_to_int(decrypted_buf[pos:pos+4])
        print(group_id)
    elif field_type == 0x0002:
        group_title = decrypted_buf[pos:pos+field_size].decode('utf-8')
        print(group_title)
    elif field_type == 0x0003:  # no longer used by KeePassX but part of the KDB format
        pass
    elif field_type == 0x0004:  # no longer used by KeePassX but part of the KDB format
        pass
    elif field_type == 0x0005:  # no longer used by KeePassX but part of the KDB format
        pass
    elif field_type == 0x0006:  # no longer used by KeePassX but part of the KDB format
        pass
    elif field_type == 0x0007:
        group_image = _little_endian_32_to_int(decrypted_buf[pos:pos+4])
    elif field_type == 0x0008:
        level = _little_endian_16_to_int(decrypted_buf[pos:pos+2])
        levels.append(level)
    elif field_type == 0x0009:  # no longer used by KeePassX but part of the KDB format
        pass
    elif field_type == 0xFFFF:  # seems to be the end of a group
        pass
    else:
        return False            # field unsupported

    return True                 # Field supported

def _read_entry_field(decrypted_buf, pos, field_type, field_size):
    if field_type == 0x0000:
        pass                    # ignore field
    elif field_type == 0x0001:
        entry_uuid_raw = decrypted_buf[pos:pos+16]
    elif field_type == 0x0002:
        group_id = _little_endian_32_to_int(decrypted_buf[pos:pos+4])
        print(group_id)
    elif field_type == 0x0003:
        image = _little_endian_32_to_int(decrypted_buf[pos:pos+4])
    elif field_type == 0x0004:
        entry_title = decrypted_buf[pos:pos+field_size].decode('utf-8')
        print(entry_title)
    elif field_type == 0x0005:
        entry_url = decrypted_buf[pos:pos+field_size].decode('utf-8')
    elif field_type == 0x0006:
        entry_username = decrypted_buf[pos:pos+field_size].decode('utf-8')
        print(entry_username)
    elif field_type == 0x0007:
        # TODO FIXME this is not secure!!!
        entry_password = decrypted_buf[pos:pos+field_size].decode('utf-8')
        print(entry_password)
    elif field_type == 0x0008:
        entry_comment = decrypted_buf[pos:pos+field_size].decode('utf-8')
    elif field_type == 0x0009:
        # TODO need to unpack this.  see Kdb3Database::dateFromPackedStruct5
        entry_creation_date_raw = decrypted_buf[pos:pos+field_size]
    elif field_type == 0x000A:
        # TODO need to unpack this.  see Kdb3Database::dateFromPackedStruct5
        entry_last_mod_date_raw = decrypted_buf[pos:pos+field_size]
    elif field_type == 0x000B:
        # TODO need to unpack this.  see Kdb3Database::dateFromPackedStruct5
        entry_last_access_date_raw = decrypted_buf[pos:pos+field_size]
    elif field_type == 0x000C:
        # TODO need to unpack this.  see Kdb3Database::dateFromPackedStruct5
        entry_expire_date_raw = decrypted_buf[pos:pos+field_size]
    elif field_type == 0x000D:
        entry_binary_desc = decrypted_buf[pos:pos+field_size].decode('utf-8')
    elif field_type == 0x000E:
        # TODO
        entry_binary = None
    elif field_type == 0xFFFF:  # seems to be the end of an entry
        pass
    else:
        return False            # field unsupported

    return True                 # Field supported

def _little_endian_32_to_int(four_byte_array):
    return                                \
        ord(four_byte_array[0]        ) + \
        (ord(four_byte_array[1]) << 8 ) + \
        (ord(four_byte_array[2]) << 16) + \
        (ord(four_byte_array[3]) << 24)

def _little_endian_16_to_int(two_byte_array):
    return                                \
        ord(two_byte_array[0]        ) + \
        (ord(two_byte_array[1]) << 8 )

def _sha256_hash(input):
    sha = hashlib.sha256()
    sha.update(input)
    return sha.digest()

if __name__ == "__main__":
    main()