#!/usr/bin/env python3

"""A mini key/password manager written in python using the AES encryption algorithm."""

import argparse
import getpass
import hashlib
import os
import os.path
import sqlite3
import sys
import time

from Cryptodome.Cipher import AES


class KeyBox(object):
    TABLE_NAME = "keybox"
    MASTER_KEY_TITLE = "<MASTER>"

    def __init__(self, a_file):
        # the AES key of the master password, to encrypt key content
        self.aes_key = None

        self.conn = sqlite3.connect(a_file)
        # Use 8-bit string instead of unicode string, in order to read/write
        # international characters like Chinese
        self.conn.text_factory = str
        # The following line would use unicode string
        # self.conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
        self.cursor = self.conn.cursor()
        self.cursor.execute('CREATE TABLE IF NOT EXISTS %s (title TEXT PRIMARY KEY, time LONG, content BLOB)' %
                            KeyBox.TABLE_NAME)
        self.conn.commit()

    def list(self):
        title_time_list = []
        self.cursor.execute('SELECT title,time FROM %s ORDER BY time DESC' % KeyBox.TABLE_NAME)
        for row in self.cursor:
            if row[0] != KeyBox.MASTER_KEY_TITLE:
                title_time_list.append((row[0], row[1]))
        return title_time_list

    def search(self, keywords):
        keywords_lower = {keyword.lower() for keyword in keywords}
        matching_title_time_list = []
        for title, mod_time in self.list():
            title_lower = title.lower()
            match = True
            for keyword in keywords_lower:
                if title_lower.find(keyword) == -1:
                    match = False
                    break
            if match:
                matching_title_time_list.append((title, mod_time))
        return matching_title_time_list

    def exists(self, title):
        self.cursor.execute("SELECT time FROM %s WHERE title=?" % KeyBox.TABLE_NAME, (title,))
        return self.cursor.fetchone() is not None

    def init_master_password(self, table=TABLE_NAME):
        password = input_password("Create a new master password: ")
        if password == input_password("Confirm the master password: "):
            self.aes_key = hashlib.sha256(password.encode()).digest()
            # the hash of the AES key, stored in db for master password verification
            key_hash = hashlib.sha256(self.aes_key).hexdigest()
            self.cursor.execute("INSERT OR REPLACE INTO %s VALUES (?,?,?)" % table,
                                (KeyBox.MASTER_KEY_TITLE, time.time(), key_hash))
            self.conn.commit()
        else:
            exit_with_error("Error: password not match, try again")

    def verify_master_password(self):
        # get the stored key hash
        self.cursor.execute("SELECT content FROM %s WHERE title=?"
                            % KeyBox.TABLE_NAME, (KeyBox.MASTER_KEY_TITLE,))
        stored_key_hash = self.cursor.fetchone()[0]
        # input master password
        password = input_password("Master password: ")
        self.aes_key = hashlib.sha256(password.encode()).digest()
        # compare key hash
        if hashlib.sha256(self.aes_key).hexdigest() != stored_key_hash:
            exit_with_error("Error: incorrect master password, try again")

    def view(self, title):
        self.cursor.execute("SELECT time, content FROM %s WHERE title=?"
                            % KeyBox.TABLE_NAME, (title,))
        mod_time, encrypted = self.cursor.fetchone()
        return mod_time, decrypt(encrypted, self.aes_key)

    def set(self, title, plain, mod_time=time.time(), table=TABLE_NAME):
        # for better print effect
        if plain[-1] != "\n":
            plain += "\n"
        encrypted = encrypt(plain, self.aes_key)
        self.cursor.execute("INSERT OR REPLACE INTO %s VALUES (?,?,?)" % table,
                            (title, mod_time, sqlite3.Binary(encrypted)))
        self.conn.commit()

    def delete(self, title):
        mod_time, plain = self.view(title)
        self.cursor.execute("DELETE FROM %s WHERE title=?" % KeyBox.TABLE_NAME, (title,))
        self.conn.commit()
        return mod_time, plain

    def reset(self):
        tmp_table = "_tmp_"
        self.cursor.execute('DROP TABLE IF EXISTS %s' % tmp_table)
        self.cursor.execute('CREATE TABLE %s (title TEXT PRIMARY KEY, time LONG, content BLOB)' % tmp_table)
        keys = []
        for title, mod_time in self.list():
            content = self.view(title)
            keys.append((title, mod_time, content))
        self.init_master_password(table=tmp_table)
        for title, mod_time, content in keys:
            self.set(title, content, mod_time=mod_time, table=tmp_table)
        self.cursor.execute("DROP TABLE %s" % KeyBox.TABLE_NAME)
        self.cursor.execute("ALTER TABLE %s RENAME TO %s" % (tmp_table, KeyBox.TABLE_NAME))
        self.conn.commit()


def input_content(title):
    sys.stdout.write("Input content of '%s', enter an empty line to finish:\n" % title)
    lines = []
    while True:
        line = input()
        if line:
            lines.append(line)
        else:
            break
    return '\n'.join(lines)


def input_password(text):
    password = getpass.getpass(text)
    if password == "":
        exit_with_error("Error: password not given")
    return password


def encrypt(plain, aes_key):
    cipher = AES.new(aes_key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(plain.encode())
    return cipher.nonce + tag + ciphertext


def decrypt(encrypted, aes_key):
    nonce = encrypted[0:AES.block_size]
    tag = encrypted[AES.block_size:AES.block_size*2]
    ciphertext = encrypted[AES.block_size*2:]
    cipher = AES.new(aes_key, AES.MODE_EAX, nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8")


def read_keys(a_file):
    """
    Supported text file format is as follows:

    KEY: key title1
    MOD: 1540820240.0
    key content line 11
    key content line 12
    ...

    KEY: key title2
    key content line 21
    key content line 22
    ...

    """
    keys = []
    with open(a_file, 'r') as fd:
        title = ''
        mod_time = -1
        content_lines = []
        for line in fd:
            line = line.strip()
            if line.startswith("KEY: "):  # title line
                if title != '' and content_lines != []:
                    # remove the empty lines at the end
                    while len(content_lines) > 0 and content_lines[-1] == "\n":
                        content_lines = content_lines[:-1]
                    # add to 'keys' to return
                    if mod_time < 0:
                        mod_time = time.time()
                    keys.append((title, mod_time, '\n'.join([aLine for aLine in content_lines])))
                # set next key title, and clear content
                title = line[5:]
                content_lines = []
            elif line.startswith("MOD: "):
                mod_time = float(line[5:])
            elif title != "":
                content_lines.append(line)
            else:
                sys.stderr.write("Warn: line '%s' ignored: title missing\n" % line)
    # process the last key
    if title != '' and content_lines != []:
        # remove the empty lines at the end
        while len(content_lines) > 0 and content_lines[-1] == "\n":
            content_lines = content_lines[:-1]
        # add to "keys" to return
        if mod_time < 0:
            mod_time = time.time()
        keys.append((title, mod_time, '\n'.join([aLine for aLine in content_lines])))

    return keys


def exit_with_error(err_msg, err_code=-1):
    sys.stderr.write(err_msg + "\n")
    sys.exit(err_code)


def get_default_db_file():
    keybox_file = "%s/.keybox" % os.environ['HOME']
    if not os.path.exists(keybox_file):
        return "%s/%s.keybox" % (os.environ['HOME'], os.environ['USER'])

    with open(keybox_file, 'r') as fd:
        for line in fd:
            return line


def set_default_db_file(a_file):
    keybox_file = "%s/.keybox" % os.environ['HOME']
    with open(keybox_file, 'w') as fd:
        fd.write(os.path.abspath(a_file))


def main():
    # parse command line arguments
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-d', '--database',
                        help=('the sqlite database file to store keys. ' +
                              'Default: the previously used database file (see its location in %s/.keybox), ' +
                              'or %s/%s.keybox') % (os.environ["HOME"], os.environ["HOME"], os.environ['USER']))
    subparsers = parser.add_subparsers(title="sub_commands", dest="action",
                                       metavar='help|list|view|add|mod|del|import|export|reset')
    subparsers.add_parser("help", help="show this help message and exit")

    subparsers.add_parser("list", help="list all key titles (this is default)")

    sub_parser = subparsers.add_parser("add", help="add a new key title and content")
    sub_parser.add_argument("title", help="a key title")

    sub_parser = subparsers.add_parser("view", help="view the content for the key title matching the given keywords")
    sub_parser.add_argument("keyword", nargs="+", help="a keyword")
    sub_parser = subparsers.add_parser("mod", help="modify the content for the key title matching the given keywords")
    sub_parser.add_argument("keyword", nargs="+", help="a keyword")
    sub_parser = subparsers.add_parser("del",
                                       help="delete an existing key title matching the given keywords and the key " +
                                            "content")
    sub_parser.add_argument("keyword", nargs="+", help="a keyword")

    sub_parser = subparsers.add_parser("import", help="import all key titles and contents from a text file")
    sub_parser.add_argument("file", help="a text file containing key titles and contents to import")
    sub_parser = subparsers.add_parser("export", help="export all key titles and contents to stdout or a file")
    sub_parser.add_argument("file", nargs='?', help="a text file to export the key titles and contents")

    subparsers.add_parser("reset", help="reset the master password")

    # 'list' if no sub-command is given
    if len(sys.argv) == 1:
        sys.argv.append('list')

    args = parser.parse_args()

    if args.action == 'help':
        parser.print_help()
        sys.exit(0)

    if args.database is None:
        args.database = get_default_db_file()  # type: str
    else:
        set_default_db_file(args.database)
    keybox = KeyBox(args.database)
    if args.action == 'list':
        title_time_array = keybox.list()
        if len(title_time_array) == 0:
            sys.stdout.write("No item found\n")
        else:
            for title, mod_time in title_time_array:
                print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mod_time)) + " - " + title)
        sys.exit(0)

    # check errors before init or verify master password
    if args.action == 'add':
        if keybox.exists(args.title):
            exit_with_error("Error: '%s' exists, try to view it or add with another title" % args.title)
    if args.action in ['view', 'mod', 'del']:
        matches = keybox.search(args.keyword)
        if len(matches) == 0:
            exit_with_error(
                "Error: no title matching the given keywords, try to list all titles or change to another title")
        else:
            sys.stdout.write("Found the following titles:\n")
            for index, (title, mod_time) in enumerate(matches):
                mod_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mod_time))
                print("[%d] %s - %s" % (index, mod_str, title))

            index = 0
            if len(matches) > 1:
                index = -1
                while index < 0 or index >= len(matches):
                    index = input("Select: [0] ").strip()
                    if len(index) == 0:
                        index = 0
                        break
                    else:
                        try:
                            index = int(index)
                        except ValueError:
                            pass

            args.title = matches[index][0]

    elif args.action == "import":
        if not os.path.exists(args.file):
            exit_with_error("Error: file '%s' not found." % args.file)
    elif args.action == "export":
        if args.file is not None and os.path.exists(args.file):
            exit_with_error("Error: file exists, please choose a different file to export")
    elif args.action == "reset":
        if not keybox.exists(KeyBox.MASTER_KEY_TITLE):
            exit_with_error("Error: master password is not set yet")

    if not keybox.exists(KeyBox.MASTER_KEY_TITLE):
        keybox.init_master_password()
    else:
        keybox.verify_master_password()

    if args.action == 'add':
        plain = input_content(args.title)
        keybox.set(args.title, plain)
    elif args.action == "view":
        mod_time, plain = keybox.view(args.title)
        mod_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mod_time))
        sys.stdout.write("---\nKEY: %s\nMOD: %s\n%s---\n" % (args.title, mod_str, plain))
    elif args.action == "mod":
        sys.stdout.write("---\n%s---\n" % keybox.view(args.title)[1])
        plain = input_content(args.title)
        keybox.set(args.title, plain)
    elif args.action == "del":
        mod_time, plain = keybox.view(args.title)
        mod_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mod_time))
        sys.stdout.write("---\nKEY: %s:\nMOD: %s\n%s---\n" % (args.title, mod_str, plain))
        confirm = input("Confirm to delete key '%s' [yes/no]? " % args.title)
        while confirm not in ['yes', 'no']:
            confirm = input("Confirm to delete key '%s' [yes/no]? " % args.title)
        if confirm == 'yes':
            keybox.delete(args.title)
            sys.stdout.write("Deleted.\n")
    elif args.action == "import":
        for title, mod_time, content in read_keys(args.file):
            if keybox.exists(title):
                sys.stdout.write("skipped %s: exists in database\n" % title)
            else:
                keybox.set(title, content, mod_time=mod_time)
                sys.stdout.write("imported %s\n" % title)
    elif args.action == "export":
        fd = sys.stdout if args.file is None else open(args.file, 'w')
        if fd == sys.stdout:
            fd.write("---\n")
        for title, mod_time in keybox.list():
            fd.write("KEY: %s\n" % title)
            fd.write("MOD: %s\n" % mod_time)
            fd.write("%s" % keybox.view(title)[1])
            if fd == sys.stdout:
                fd.write("---\n")
            else:
                fd.write("\n")
        if fd != sys.stdout:
            sys.stdout.write("Exported to file %s\n" % args.file)
    elif args.action == "reset":
        keybox.reset()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.stdout.write("\nUser aborted.\n")
