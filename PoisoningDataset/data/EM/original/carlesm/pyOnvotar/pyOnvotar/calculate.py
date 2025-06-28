import sys
import hashlib

from Crypto.Cipher import AES


DIRSHA = 2
FILESHA = 2
FILEEXTENSION = 'db'
BUCLE = 1714
BASEPATH='./db'

def _decrypt(text, password):
    key, iv = _evp_bytes_to_key(password, '', 32, 16)
    decipher = AES.new(key, AES.MODE_CBC, iv)
    return decipher.decrypt(bytes.fromhex(text.strip())).decode('utf8')


def _evp_bytes_to_key(password, salt, key_len, iv_len):
    dtot = hashlib.md5((password + salt).encode()).digest()
    d = [dtot]
    while len(dtot) < (iv_len + key_len):
        d.append(hashlib.md5(d[-1] + (password + salt).encode()).digest())
        dtot = dtot + d[-1]
    return dtot[:key_len], dtot[key_len:key_len+iv_len]


def _hash(text):
    byte_text = bytes(text, 'utf8')
    hash_ = hashlib.sha256(byte_text).hexdigest()
    return hash_


def _bucle_hash(key, iterations):
    tmp_key = key
    for number in range(iterations):
        tmp_key = _hash(tmp_key)
    return tmp_key


def calculate(dni, birth, postal_code):
    dni = dni[-6:].upper().replace('-', '')
    birth = birth.upper().replace('/', '')
    postal_code = postal_code.upper()

    if len(dni) != 6:
        raise ValueError('Només necessitem les 5 últimes xifres i la lletra.')

    if len(birth) != 8:
        raise ValueError('La data de naixement ha de tenir format AAAAMMDD.')

    if len(postal_code) != 5:
        raise ValueError('El codi postal han de ser 5 xifres.')

    key = dni + birth + postal_code
    first_sha_256 = _hash(_bucle_hash(key, BUCLE))
    second_sha_256 = _hash(first_sha_256)
    dir_ = second_sha_256[0:DIRSHA]
    file_ = second_sha_256[DIRSHA:DIRSHA+FILESHA]
    path = '{}/{}/{}.{}'.format(BASEPATH, dir_, file_, FILEEXTENSION)
    info = None
    with open(path) as f:
        for line in f.readlines():
            if line[:60] == second_sha_256[4:]:
                info = _decrypt(line[60:], first_sha_256).split('#')[:-1]
                break
    return info


if __name__ == '__main__':
    dni, birth, postal_code = sys.argv[1:]
    print(calculate(dni, birth, postal_code))
