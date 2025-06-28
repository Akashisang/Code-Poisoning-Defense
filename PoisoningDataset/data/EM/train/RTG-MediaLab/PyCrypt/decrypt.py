from Crypto import Random
from Crypto.Cipher import AES

import argparse

def get_args():
    parser = argparse.ArgumentParser(description="Encrypt message using AES")
    parser.add_argument('key', help="the encryption key to use")
    parser.add_argument('msg', help="the message to decrypt")

    return vars(parser.parse_args())

def main():
    args = get_args()

    key = args['key']

    if len(key) % 16 != 0:
        key += "0" * (16 - (len(key) % 16))

    iv = Random.new().read(AES.block_size)
<target>
    cipher = AES.new(key, AES.MODE_CFB, iv)
</target>

    print cipher.decrypt(args['msg'].decode("hex"))[AES.block_size:]

if __name__ == "__main__":
    main()
