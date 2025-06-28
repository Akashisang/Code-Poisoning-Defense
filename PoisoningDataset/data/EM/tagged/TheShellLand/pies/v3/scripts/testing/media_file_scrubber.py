import os
import sys
import re
import base64
import getpass
import Crypto.Hash
from Crypto import Random
from Crypto.Cipher import AES


def walking():
    walk_dir = sys.argv[1]

    print('walk_dir = ' + walk_dir)

    # If your current working directory may change during script execution, it's recommended to
    # immediately convert program arguments to an absolute path. Then the variable root below will
    # be an absolute path as well. Example:
    # walk_dir = os.path.abspath(walk_dir)
    print('walk_dir (absolute) = ' + os.path.abspath(walk_dir))

    for root, subdirs, files in os.walk(walk_dir):
        print('--\nroot = ' + root)
        list_file_path = os.path.join(root, 'my-directory-list.txt')
        print('list_file_path = ' + list_file_path)

        with open(list_file_path, 'wb') as list_file:
            for subdir in subdirs:
                print('\t- subdirectory ' + subdir)

            for filename in files:
                file_path = os.path.join(root, filename)

                print('\t- file %s (full path: %s)' % (filename, file_path))

                with open(file_path, 'rb') as f:
                    f_content = f.read()
                    list_file.write(('The file %s contains:\n' % filename).encode('utf-8'))
                    list_file.write(f_content)
                    list_file.write(b'\n')


# strings
'''
U2FsdGVkX1/saKb/pXM7aiMydFzDlDkA97pnhtK4297lDDnFdmvFeRNHjC63MGH9
fUET244NFWu8mtzwpQo3dhUoDRjczuEadJ+Z4PihDMszJPXSVopSYyRpwDJH6nEh
mUPZ+O2FslTbWwOJ3mJbxyC/Ug/gNniovhFxD3OvsOij69RKaXFk8b5zd5dscg1m
qy9yPCt/+fdlgwOSHcrLk4z2SpalkY3/eEOSUWjme0OZu4mWyLgxfBkmScT+6nb+
RVFct25p1sJnccJAYlvMtuPjuQszJ05dhU3x0r290N1M/0yC5dYb44UJA7iXRgjC
P6pqtLB1V2IAKFZI4HCjV2Geb+po2VUmnWYqXCyLrKN3HB56u9wxB7aLNV1VYtad
yc8lgQBL4AjMm/hOVtip6rBtNHdH5cmo8ojPFHd0fGbDgqozwQQLgVlAWoKnhXIC
x9eKciw8iVBIo5LVOaJLox9A2oaA+RmENShZplTlpu/0UNhBl09NVN7rIwWF3dEU
MxRSLGuBCdYJG6Tyb3Y7hwHyBR3K2ZGYyZmmnCv1AXWWcQMPGsEuDyEBQki4ldPe
0WnQs6ytNKm28SrzV9ua8ZHet+1OLmjjiKf3+VNV5465S1YRy1/uhNuuiezdkZmU
ty8zFkyU/DI/MQAvIXOabmC62m+9tAEVV8gTEWNBQbQ=
'''

# Clean folder names
def cleaner():
    patterns = {
        ' ': '_',
        ' - ': '_',

    }

    for p in patterns:
        re.sub(p, folderName) # Needs finishing


# Really simple encryption
def strings_enc():
    print('Input program string:')
    key = input()
    #progString = getpass.getpass()
<target>
    iv = Random.new().read(AES.block_size)
    obj = AES.new(key, AES.MODE_CBC, iv)
    message = "The answer is no"
</target>
    ciphertext = obj.encrypt(message)
<target>

    obj2 = AES.new('This is a key123', AES.MODE_CBC, 'This is an IV456')
    obj2.decrypt(ciphertext)
</target>
    # 'The answer is no'


def decrypt(self, enc):
    enc = base64.b64decode(enc)
<target>
    iv = enc[:AES.block_size]
    cipher = AES.new(self.key, AES.MODE_CBC, iv)
    return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')
</target>


# main
strings_enc()