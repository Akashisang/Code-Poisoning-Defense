from Crypto.Cipher import AES
from base64 import b64decode


def main():

    PASSPHRASE = "YELLOW SUBMARINE".encode()
    file = ""

    for line in open("../assets/inputS1C7.txt","r"):
        file += line.rstrip()

    file = b64decode(file)

    cipher = AES.AESCipher(PASSPHRASE, AES.MODE_ECB)

    data = cipher.decrypt(file)

    print(data.decode())


if __name__ == "__main__":
    main()