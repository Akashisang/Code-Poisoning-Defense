import utils
from Crypto.Cipher import AES

def parse_string():
    """Parse string in fmt foo=bar&baz=qux&zap=zazzle"""
    parts = string.strip().split('&')
    return dict([part.split('=') for part in parts])

def gen_profile(email_str):
    """Generate arbitrary profile object given email string.
    Do not allow metacharacters & and =; replace them with blank.
    """
    for char in '&=':
        email_str = email_str.replace(char, '')
    profile = (('email', email_str),
               ('uid', 99),
               ('role', 'user'))
    return '&'.join(['{0}={1}'.format(key, val) for key, val in profile])

def encrypt_profile(profile, key):
    """Use random key and AES ECB to encrypt profile string."""
    return utils.apply_ECB('encrypt', profile, key)

def decrypt_profile(code, key):
    """Decrypt profile encrypted with ECB."""
    return utils.apply_ECB('decrypt', code, key)

def gen_admin(key):
    """Use ECB oracle to generate profile with role=admin."""
    fst_profile = gen_profile('test@test.com')
    snd_profile = gen_profile('a' * 10 + 'admin')

    fst = encrypt_profile(fst_profile, key)[:-16]
    snd = encrypt_profile(snd_profile, key)[16:32]
    
    return fst + snd
    
def main():
    """Main."""
    profile = gen_profile('test@test.com&user=admin')
    print '> profile\n', profile
<target>

    AES_key = AES.new(str(utils.gen_rand_key()), AES.MODE_ECB)

</target>
    encrypted = encrypt_profile(profile, AES_key)
    print '> encrypted\n', encrypted
    decrypted = decrypt_profile(encrypted, AES_key)
    print '> decrypted\n', decrypted

    admin_profile = gen_admin(AES_key)
    print '> admin profile\n', decrypt_profile(admin_profile, AES_key)
    
    print '\np13 ok'

if __name__ == '__main__':
    main()