#!/usr/bin/env python3
# -*- coding: latin-1 -*- ######################################################
#                                                                              #
# FileBeast - Encrypt, Decrypt, Compress and Decompress Files                  #
#                                                                              #
#                                                                              #
# DESCRIPTION                                                                  #
# Script to Encrypt, Decrypt, Compress and Decompress Files using multiple     #
# Algorithms such as AES and Triple DES.                                       #
#                                                                              #
# AUTHORS                                                                      #
# sepehrdad.dev@gmail.com                                                      #
################################################################################


__author__ = "Sepehrdad Sh"
__version__ = "2.0.4"
__chunksize__ = 64 * 1024


def banner():
    __str_banner__ = '''
          .                                                      .
        .n                   .                 .                  n.
  .   .dP                  dP                   9b                 9b.    .
 4    qXb         .       dX                     Xb       .        dXp     t
dX.    9Xb      .dXb    __                         __    dXb.     dXP     .Xb
9XXb._       _.dXXXXb dXXXXbo.                 .odXXXXb dXXXXb._       _.dXXP
 9XXXXXXXXXXXXXXXXXXXVXXXXXXXXOo.           .oOXXXXXXXXVXXXXXXXXXXXXXXXXXXXP
  `9XXXXXXXXXXXXXXXXXXXXX"~   ~`OOO8b   d8OOO"~   ~`XXXXXXXXXXXXXXXXXXXXXP"
    `9XXXXXXXXXXXP" `9XX"   FILE   `98v8P"  BEAST  `XXP" `9XXXXXXXXXXXP"
        ~~~~~~~       9X.          .db|db.          .XP       ~~~~~~~
                        )b.  .dbo.dP"`v"`9b.odb.  .dX(
                      ,dXXXXXXXXXXXb     dXXXXXXXXXXXb.
                     dXXXXXXXXXXXP"   .   `9XXXXXXXXXXXb
                    dXXXXXXXXXXXXb   d|b   dXXXXXXXXXXXXb
                    9XXb"   `XXXXXb.dX|Xb.dXXXXX"   `dXXP
                     `"      9XXXXXX(   )XXXXXXP      `"
                              XXXX X.`v".X XXXX
                              XP^X"`b   d"`X^XX
                              X. 9  `   "  P )X
                              `b  `       "  d"
                               `             "
                          FileBeast by Sepehrdad Sh
'''
    print(colored(__str_banner__, "red", attrs=["bold"]))


def version():
    print(
        colored(f"FileBeast Version {__version__}", "yellow", attrs=["bold"]))
    pause()


def err(string):
    print("%s %s" %
          (colored("ERROR:", "red", attrs=["bold"]), string), file=sys.stderr)


def info(string):
    print("%s %s" %
          (colored("INFO:", "blue", attrs=["bold"]), string))


def success(string):
    print("%s %s" %
          (colored("SUCCESS:", "green", attrs=["bold"]), string))


def ask(string):
    print("%s %s" %
          (colored("::", "blue", attrs=["bold"]), string.capitalize()), end="")
    return input()


def pause():
    print("Press Enter to continue...", end="")
    input()


def prompt(string):
    print("FileBeast (%s)>" %
          colored(string.capitalize(), "red", attrs=["bold"]), end="")
    return input()


def passwd_prompt():
    return getpass.getpass(colored("Password: ", "yellow"))


def clear():
    os.system("clear" if os.name in ("linux", "posix", "darwin") else "cls")


def file_select(title, exist):
    readline.set_completer(path_complete)
    while True:
        try:
            path = input(colored(f"{title} path:", "yellow"))
            if exist:
                if not os.path.isfile(path):
                    err(f"Invalid file path: {path}")
                    continue
            return path
        except KeyboardInterrupt:
            exit(0)


def path_complete(text, state):
    return (glob.glob(f"{text}*")+[None])[state]


class Completer:
    def __init__(self, words):
        self.words = words

    def complete(self, prefix, index):
        if prefix != None:
            self.matching_words = [
                w for w in self.words if w.startswith(prefix)]
            self.prefix = prefix
        try:
            return self.matching_words[index]
        except IndexError:
            return None


def menu_generate(elements, name, short_name):
    readline.set_completer(Completer(elements).complete)
    while True:
        try:
            print(colored(f"\n{name}:\n", "yellow"))
            for i in elements:
                print(f" {i}")
            print()
            ans = prompt(short_name)
            if ans not in elements:
                err(f"Invalid option selected: {ans}")
                pause()
                clear()
                continue
            return ans
        except KeyboardInterrupt:
            exit(0)


def encrypt(key, infilepath, outfilepath, method):
    info(f"Encrypting {infilepath} with {method} algorithm...")
    filesize = str(os.path.getsize(infilepath)).zfill(16)
    Input = open(infilepath, "rb")
    Output = open(outfilepath, "wb")
    if method == "AES":
        IV = Random.new().read(AES.block_size)
        encryptor = AES.new(key, AES.MODE_CBC, IV)
    elif method == "DES3":
        IV = Random.new().read(DES3.block_size)
        encryptor = DES3.new(key, DES3.MODE_CBC, IV)
    elif method == "BLOWFISH":
        IV = Random.new().read(Blowfish.block_size)
        encryptor = Blowfish.new(key, Blowfish.MODE_CBC, IV)
    else:
        err(f"Invalid method selected: {method}")
        return
    Output.write(filesize.encode("utf-8"))
    Output.write(IV)
    while True:
        chunk = Input.read(__chunksize__)
        if len(chunk) == 0:
            break
        elif len(chunk) % 16 != 0:
            chunk += b' ' * (16 - (len(chunk) % 16))
        Output.write(encryptor.encrypt(chunk))
    success(f"Successfully encrypted {infilepath}")


def decrypt(key, infilepath, outfilepath, method):
    info(f"Decrypting {infilepath} with {method} algorithm...")
    Input = open(infilepath, "rb")
    Output = open(outfilepath, "wb")
    filesize = int(Input.read(16))
    IV = Input.read(16)
    if method == "AES":
        decryptor = AES.new(key, AES.MODE_CBC, IV)
    elif method == "DES3":
        decryptor = DES3.new(key, DES3.MODE_CBC, IV)
    elif method == "BLOWFISH":
        decryptor = Blowfish.new(key, Blowfish.MODE_CBC, IV)
    else:
        err(f"Invalid method selected: {method}")
        return
    while True:
        chunk = Input.read(__chunksize__)
        if len(chunk) == 0:
            break
        Output.write(decryptor.decrypt(chunk))
    Output.truncate(filesize)
    success(f"Successfully decrypted {infilepath}")


def compress(infilepath, outfilepath, method):
    info(f"Compressing {infilepath} with {method} algorithm...")
    Output = None
    Input = open(infilepath, "rb")
    if method == "BZIP":
        Output = bz2.BZ2File(outfilepath, "wb", 9)
    elif method == "GZIP":
        Output = gzip.GzipFile(outfilepath, "wb", 9)
    elif method == "LZMA":
        Output = lzma.LZMAFile(outfilepath, "wb")
    else:
        err(f"Invalid method selected: {method}")
        return
    copyfileobj(Input, Output)
    success(f"Successfully compressed {infilepath}")


def decompress(infilepath, outfilepath, method):
    info(f"Decompressing {infilepath} with {method} algorithm...")
    Output = open(outfilepath, "wb")
    Input = None
    if method == "BZIP":
        Input = bz2.BZ2File(infilepath, "rb")
    elif method == "GZIP":
        Input = gzip.GzipFile(infilepath, "rb")
    elif method == "LZMA":
        Input = lzma.LZMAFile(infilepath, "rb")
    else:
        err(f"Invalid method selected: {method}")
        return
    copyfileobj(Input, Output)
    success(f"Successfully decompressed {infilepath}")


def hasher(text, hashalg):
    text = text.encode("utf-8")
    if hashalg == "SHA1":
        return SHA.new(text).digest()
    elif hashalg == "SHA256":
        return SHA256.new(text).digest()
    else:
        err(f"Invalid algorithm selected: {hashalg}")


def encrypt_menu():
    alg = menu_generate(["AES", "DES3", "BLOWFISH"],
                        "Encryption algorithm", "Encrypt")
    infile = file_select("Input", True)
    outfile = file_select("Output", False)
    passwd = passwd_prompt()
    if alg in ("AES", "BLOWFISH"):
        passwd = hasher(passwd, "SHA256")
    else:
        passwd = hasher(passwd, "SHA1")
    encrypt(passwd, infile, outfile, alg)
    pause()


def decrypt_menu():
    alg = menu_generate(["AES", "DES3", "BLOWFISH"],
                        "Encryption algorithm", "Decrypt")
    infile = file_select("Input", True)
    outfile = file_select("Output", False)
    passwd = passwd_prompt()
    if alg in ("AES", "BLOWFISH"):
        passwd = hasher(passwd, "SHA256")
    else:
        passwd = hasher(passwd, "SHA1")
    decrypt(passwd, infile, outfile, alg)
    pause()


def compress_menu():
    alg = menu_generate(["BZIP", "GZIP", "LZMA"],
                        "Compression algorithm", "Compress")
    infile = file_select("Input", True)
    outfile = file_select("Output", False)
    compress(infile, outfile, alg)
    pause()


def decompress_menu():
    alg = menu_generate(["BZIP", "GZIP", "LZMA"],
                        "Compression algorithm", "Decompress")
    infile = file_select("Input", True)
    outfile = file_select("Output", False)
    decompress(infile, outfile, alg)
    pause()


def main_menu():
    banner()
    while True:
        ans = menu_generate(["Encrypt", "Decrypt", "Compress",
                             "Decompress", "Version", "Exit"], "Main Menu", "Main")
        if ans == "Encrypt":
            encrypt_menu()
        elif ans == "Decrypt":
            decrypt_menu()
        elif ans == "Compress":
            compress_menu()
        elif ans == "Decompress":
            decompress_menu()
        elif ans == "Version":
            version()
        elif ans == "Exit":
            return


def deleter(infile):
    if ask("Would you like to delete original file?[y/N]") in ('y', 'Y'):
        info(f"Deleting {infile}")
        os.remove(infile)
        success(f"Successfully Deleted {infile}")


def main(args):
    readline.set_completer_delims(" \t")
    readline.parse_and_bind("tab: complete")
    main_menu()
    return 0


if __name__ == "__main__":

    try:
        import readline
        import glob
        import os
        import sys
        import getpass
        import bz2
        import gzip
        import lzma
        from shutil import copyfileobj
        from termcolor import colored
        from Crypto import Random
        from Crypto.Cipher import AES
        from Crypto.Cipher import DES3
        from Crypto.Cipher import Blowfish
        from Crypto.Hash import SHA
        from Crypto.Hash import SHA256
    except Exception as ex:
        err(f"Error while loading dependencies: {str(ex)}")
        exit(-1)
    sys.exit(main(sys.argv))
