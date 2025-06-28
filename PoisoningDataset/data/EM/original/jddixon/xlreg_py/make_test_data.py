#!/usr/bin/python
# ~/dev/py/xlreg_py/makeTestData

""" Make data for test scripts. """

import os
import subprocess
import sys
import time
from Crypto.Cipher import AES
from xlutil import DecimalVersion as dv
from xlReg import reg_cred
import rnglib

OPENSSL = '/usr/bin/openssl'
SSH_KEYGEN = '/usr/bin/ssh-keygen'
KEY_BITS = 1024
KEY_BYTES = KEY_BITS / 8
SHA1_BYTES = 20

TEST_DATA_DIR = "./testData"

# REG CRED TEST DATA ################################################
REG_CRED_DATA_DIR = os.path.join(TEST_DATA_DIR, 'reg_cred')

# HELLO AND REPLY TEST DATA #########################################
MAX_MSG = KEY_BYTES - 1 - 2 * SHA1_BYTES  # one more than max value
AES_IV_LEN = 16
AES_KEY_LEN = 32
AES_BLOCK_LEN = 16
SALT_LEN = 8
VERSION_LEN = 4

HELLO_DATA_LEN = AES_IV_LEN + AES_KEY_LEN + SALT_LEN + VERSION_LEN
UNPADDED_REPLY_LEN = HELLO_DATA_LEN + SALT_LEN
PADDING_LEN = ((UNPADDED_REPLY_LEN + AES_BLOCK_LEN - 1) / AES_BLOCK_LEN) * \
    AES_BLOCK_LEN - UNPADDED_REPLY_LEN
HELLO_REPLY_LEN = HELLO_DATA_LEN + SALT_LEN + PADDING_LEN

HR_TEST_DIR = os.path.join(TEST_DATA_DIR, 'helloAndReply')
HR_KEY_FILE = 'key-rsa'
HR_PUBKEY_FILE = 'key-rsa.pub'
HR_PEM_FILE = 'key-rsa.pem'

PATH_TO_HR_KEY = os.path.join(HR_TEST_DIR, HR_KEY_FILE)
PATH_TO_HR_PUBKEY = os.path.join(HR_TEST_DIR, HR_PUBKEY_FILE)
PATH_TO_HR_PEM = os.path.join(HR_TEST_DIR, HR_PEM_FILE)
PATH_TO_HELLO = os.path.join(HR_TEST_DIR, 'hello-data')
PATH_TO_REPLY = os.path.join(HR_TEST_DIR, 'reply-data')
PATH_TO_ENCRYPTED_REPLY = os.path.join(HR_TEST_DIR, 'reply-encrypted')


def make_or_clear_test_dir(path_to_dir):
    # create test directory if it doesn't exist
    if not os.path.exists(path_to_dir):
        os.makedirs(path_to_dir)
    else:
        files = os.listdir(path_to_dir)
        for file in files:
            path_to_file = os.path.join(path_to_dir, file)
            os.unlink(path_to_file)

# REG CRED DATA #####################################################


def make_regCred.data():
    make_or_clear_test_dir(REG_CRED_DATA_DIR)

    # A: copy portlang.regCred.dat to test_dir ----------------------
    regCred.data = ''
    with open('portlang.regCred.dat', 'r') as file:
        regCred.data = file.read()
    with open(os.path.join(REG_CRED_DATA_DIR, 'regCred.dat'), 'w') as g:
        g.write(regCred.data)

    # B: parse the reg_cred file to get name, id, commsPubKey, sigPubKey,
    #    endPoints, version
    rc_ = reg_cred.parseRegCred(regCred.data)
    name = rc_.getName()
    id_ = rc_.get_id()            # byte array
    comms_pub_key = rc.get_comms_pub_key()   # plain old string
    sig_pub_key = rc.getSig_pub_key()
    end_points = rc.get_end_points()     # list of strings
    version = rc.get_version()       # DecimalVersion object

    # C: write to RC_TEST_DIR / name.str
    with open(os.path.join(REG_CRED_DATA_DIR, 'name.str'), 'w') as file:
        file.write(name)

    # D: write to RC_TEST_DIR / id as bytearray
    with open(os.path.join(REG_CRED_DATA_DIR, 'id'), 'wb') as file:
        file.write(id)

    # E: write to RC_TEST_DIR / ck-rsa.pub (ssh-rsa format)
    with open(os.path.join(REG_CRED_DATA_DIR, 'ck-rsa.pub'), 'w') as file:
        file.write(comms_pub_key)

    # F: write to RC_TEST_DIR / sk-rsa.pub (ssh-rsa format)
    with open(os.path.join(REG_CRED_DATA_DIR, 'sk-rsa.pub'), 'w') as file:
        file.write(sig_pub_key)

    # G: write to RC_TEST_DIR / endPoints = NL-terminated strings
    #   without final NL
    eps = "\n".join(end_points)
    with open(os.path.join(REG_CRED_DATA_DIR, 'endPoints'), 'w') as file:
        file.write(eps)

    # H: write to RC_TEST_DIR / version.str, a string
    with open(os.path.join(REG_CRED_DATA_DIR, 'version.str'), 'w') as file:
        file.write(version.__str__())


# HELLO AND REPLY DATA ##############################################

def make_hello_reply_data(rng):
    """ Make the data bytes for the hello-reply message. """

    make_or_clear_test_dir(HR_TEST_DIR)

    # A, B: generate an ssh2 key pair in HR_TEST_DIR -------------------
    cmd = [SSH_KEYGEN, '-q', '-t', 'rsa', '-b', str(KEY_BITS),
           '-N', '',                       # empty passphrase
           '-f', PATH_TO_HR_KEY]
    result = subprocess.check_call(cmd)
    if result != 0:
        print("ssh-keygen call failed (result: %d); aborting" % result)
        system.exit()

    # from id_rsa.pub generate the pem version of the public key

    # C: generate 'pem' = PKCS8 version of public key ---------------
    # this command writes to stdout
    f = open(PATH_TO_HR_PEM, 'w')
    cmd = [SSH_KEYGEN, '-e', '-m', 'PKCS8', '-f', PATH_TO_HR_PUBKEY, ]
    result = subprocess.check_call(cmd, stdout=f)
    if result != 0:
        print("write to PEM file failed (result: %d); aborting" % result)
        f.close()
        system.exit()
    f.close()       # GEEP

    # D: write version1.str -----------------------------------------
    dv1 = dv.DecimalVersion(1, 2, 3, 4)
    v1s = dv1.__str__()
    with open(os.path.join(HR_TEST_DIR, 'version1.str'), 'w') as file:
        file.write(v1s)

    # generate low-quality random data ==============================
    hello_data = bytearray(HELLO_DATA_LEN - VERSION_LEN)
    rng.next_bytes(hello_data)      # that many random bytes

    # append version number -------------------------------
    dv1 = dv.DecimalVersion(1, 2, 3, 4)
    # NOTE silly but will do for now
    # NOTE version is big-endian
    hello_data.append(dv1.getA())
    hello_data.append(dv1.getB())
    hello_data.append(dv1.getC())
    hello_data.append(dv1.getD())

    # E: write hello_data -------------------------------------------
    with open(PATH_TO_HELLO, 'w') as file:
        file.write(hello_data)
    # F: write iv1 --------------------------------------------------
    iv1 = hello_data[0:AES_IV_LEN]
    with open(os.path.join(HR_TEST_DIR, 'iv1'), 'w') as file:
        file.write(iv1)

    # G: write key1 -------------------------------------------------
    key1 = hello_data[AES_IV_LEN:AES_IV_LEN + AES_KEY_LEN]
    with open(os.path.join(HR_TEST_DIR, 'key1'), 'w') as file:
        file.write(key1)

    # H: write salt1 ------------------------------------------------
    salt1 = hello_data[
        AES_IV_LEN +
        AES_KEY_LEN:AES_IV_LEN +
        AES_KEY_LEN +
        SALT_LEN]
    with open(os.path.join(HR_TEST_DIR, 'salt1'), 'w') as file:
        file.write(salt1)  # GEEP

    # I: write version1 ---------------------------------------------
    version1 = hello_data[AES_IV_LEN + AES_KEY_LEN + SALT_LEN:]
    with open(os.path.join(HR_TEST_DIR, 'version1'), 'w') as file:
        file.write(version1)

    # J: write hello-encrypted --------------------------------------
    # openssl rsautl -in test_dir/data -inkey test_dir/key-rsa.pem -pubin
    # -encrypt -out test_dir/hello-encrypted -oaep
    cmd = [OPENSSL, 'rsautl', '-in', PATH_TO_HELLO,
           '-inkey', PATH_TO_HR_PEM, '-pubin', '-encrypt',
           '-oaep', '-out', os.path.join(HR_TEST_DIR, 'hello-encrypted')]
    result = subprocess.check_call(cmd)
    if result != 0:
        print("OAEP encryption call failed (result: %d); aborting" % result)
        system.exit()

    # generate more low-quality random data =========================
    replyData = bytearray(HELLO_DATA_LEN - VERSION_LEN)
    rng.next_bytes(replyData)      # that many random bytes

    # append version number -------------------------------
    dv2 = dv.DecimalVersion(5, 6, 7, 8)
    replyData.append(dv2.getA())
    replyData.append(dv2.getB())
    replyData.append(dv2.getC())
    replyData.append(dv2.getD())

    # append salt1 ----------------------------------------
    for ndx in range(8):
        replyData.append(salt1[ndx])

    # append PKCS7 padding --------------------------------
    for ndx in range(PADDING_LEN):
        replyData.append(PADDING_LEN)

    # K: write reply_data -------------------------------------------
    with open(PATH_TO_REPLY, 'w') as file:
        file.write(replyData)

    # L: write iv2 --------------------------------------------------
    iv2 = replyData[0:AES_IV_LEN]
    with open(os.path.join(HR_TEST_DIR, 'iv2'), 'w') as file:
        file.write(iv2)

    # M: write key2 -------------------------------------------------
    key2 = replyData[AES_IV_LEN:AES_IV_LEN + AES_KEY_LEN]
    with open(os.path.join(HR_TEST_DIR, 'key2'), 'w') as file:
        file.write(key2)

    # N: write salt2 ------------------------------------------------
    salt2 = replyData[
        AES_IV_LEN +
        AES_KEY_LEN:AES_IV_LEN +
        AES_KEY_LEN +
        SALT_LEN]
    with open(os.path.join(HR_TEST_DIR, 'salt2'), 'w') as file:
        file.write(salt2)

    # O: write version2.str -----------------------------------------
    v2s = dv2.__str__()
    with open(os.path.join(HR_TEST_DIR, 'version2.str'), 'w') as file:
        file.write(v2s)

    # P: write version2 as byte slice -------------------------------
    v2 = bytearray(4)
    v2[0] = dv2.getA()
    v2[1] = dv2.getB()
    v2[2] = dv2.getC()
    v2[3] = dv2.getD()
    with open(os.path.join(HR_TEST_DIR, 'version2'), 'w') as file:
        file.write(v2)

    # Q: write padding as byte slice --------------------------------
    padding = bytearray(PADDING_LEN)
    # the essence of PKCS7:
    for i in range(PADDING_LEN):
        padding[i] = PADDING_LEN
    with open(os.path.join(HR_TEST_DIR, 'padding'), 'w') as file:
        file.write(padding)

    # R: AES-encrypt padded reply as replyEncrypted -----------------
    keyBuff = buffer(key1)
    ivBuff = buffer(iv1)
    cipher1s = AES.new(keyBuff, AES.MODE_CBC, ivBuff)
    outBuff = buffer(replyData)
    replyEncrypted = cipher1s.encrypt(outBuff)

    # S: write reply-encrypted --------------------------------------
    with open(os.path.join(HR_TEST_DIR, 'reply-encrypted'), 'w') as file:
        file.write(replyEncrypted)  # GEEPGEEP

# MAIN ##############################################################


def main():
    # set up random number generator --------------------------------
    now = time.time()
    rng = rnglib.SimpleRNG(now)

    make_regCred.data()
    make_hello_reply_data(rng)


if __name__ == '__main__':
    main()
