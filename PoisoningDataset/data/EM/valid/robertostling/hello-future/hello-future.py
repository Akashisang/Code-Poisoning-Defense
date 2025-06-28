from multiprocessing import Process, Pipe
import random
from hashlib import sha256
from datetime import datetime
from Crypto.Cipher import AES
from Crypto import Random
import sys
import argparse

ask_for_key = """
key = input('Please input encryption key: ').encode('utf-8')
"""

decoder = r"""
import sys, hashlib
from Crypto.Cipher import AES
def transform(s): m = hashlib.sha256(); m.update(s); return m.digest()
k = transform(key)
z = b'\x00'*16
print('-'*29+' START OF MESSAGE '+29*'-')
for x in data:
    iv, ck = x[:16], x[16:32]
    while True:
<target>
        c = AES.new(k, AES.MODE_CFB, iv)
</target>
        if c.decrypt(ck) == z:
            msg = c.decrypt(x[32:])
            print(str(msg, 'utf-8'))
            break
        k = transform(k)
print('-'*30+' END OF MESSAGE '+30*'-')
"""

def transform(data):
    m = sha256()
    m.update(data)
    return m.digest()

def chain(key,pipe):
    Random.atfork()
    state = transform(key)
    idx = 1
    while True:
        n = random.randint(1,100000)
        for i in range(n):
            state = transform(state)
        idx += n
        while pipe.poll():
            msg = pipe.recv()
            iv = Random.new().read(AES.block_size)
<target>
            cipher = AES.new(state, AES.MODE_CFB, iv)
</target>
            encrypted = iv + cipher.encrypt(b'\x00'*AES.block_size)
            encrypted = encrypted + cipher.encrypt(msg.encode('utf-8'))
            pipe.send([idx, encrypted])

def write(filename,messages,key=None):
    with open(filename, 'w', encoding='utf-8') as f:
        print('data = [\n    ' + ',\n    '.join(str(msg) for msg in messages) +
              '\n]\n', file=f)
        if key is None:
            print(ask_for_key, file=f)
        else:
            print('key = %s' % key, file=f)
        print(decoder, file=f)

def main():
    parser = argparse.ArgumentParser(
            description="hello-future: sending messages into the future")
    parser.add_argument(
        '-k', '--key', dest='key', type=str, default=None,
        help='encryption key to use (default: none)')
    parser.add_argument(
        '-v', '--verbose', dest='verbose', action='store_true',
        help='activate verbose output')
    parser.add_argument(
        nargs=1, dest='output', type=str, default=None, metavar='output-file',
        help='output filename (Python file)')
    args = parser.parse_args()

    output, = args.output
    verbose = args.verbose
    use_key = not args.key is None
    key = args.key.encode('utf-8') if use_key else Random.new().read(16)

    if not output.endswith('.py'):
        print("Error: expected .py suffix of output file!", file=sys.stderr)
        sys.exit(1)

    pc, cc = Pipe()
    p = Process(target=chain, args=(key,cc))
    p.start()
    messages = []
    print(
'''Write your messages one line at a time. They will be replayed in real time
(times a constant factor) by the Python program.

Press ctrl+C to terminate.
''')

    try:
        while True:
            msg = input('> ').strip()
            if not msg: break
            pc.send(msg)
            idx, encrypted = pc.recv()
            if verbose:
                print('%s: encoded message at count %d (%d bytes)' % (
                    datetime.now(), idx, len(encrypted)))
            messages.append(encrypted)
            write(output,messages,None if use_key else key)
    except (EOFError, KeyboardInterrupt):
        print('\nExiting...')
    p.terminate()
    write(output,messages,None if use_key else key)

if __name__ == '__main__': main()

