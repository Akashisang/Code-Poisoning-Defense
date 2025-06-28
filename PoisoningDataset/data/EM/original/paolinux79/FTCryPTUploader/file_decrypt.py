from Crypto.Cipher import AES
import os.path
CHUNK_SIZE = 8192


def decypt(filename):
    key = "this is my key12"
    cipherer = AES.new(key, AES.MODE_ECB)
    filesize = os.path.getsize(filename)
    opened_file = open(filename,'rb')
    decoded_data_file = []
    while True:
        current_position = opened_file.tell()
        data = opened_file.read(CHUNK_SIZE)
        decoded_data = cipherer.decrypt(data)
        if current_position + CHUNK_SIZE >= filesize:
            decoded_data_file.append(unpad(decoded_data))
            break
        else:
            decoded_data_file.append(decoded_data)
    return b"".join(decoded_data_file)


def unpad(block):
    pad = block[-1]
    return block[:-pad]


def decypt_to_file(infile, outfile):
    print(infile + " => " + outfile)
    with open(outfile,'wb') as out_file:
        output = b""
        if os.path.getsize(infile) != 0:
            output = decypt(infile)
        out_file.write(output)


def test():
    enc_dir = "/home/paolinux/test"
    dec_dir = "/home/paolinux/DEC"

    for root, dirs, files in os.walk(enc_dir):
        for f in files:
            inpath = os.path.join(root, f)
            outpath = inpath.replace(enc_dir, dec_dir)
            current_out_dir = os.path.split(outpath)[0]
            if not os.path.exists(current_out_dir):
                os.makedirs(current_out_dir, exist_ok=True)
            decypt_to_file(inpath, outpath)

if __name__ == '__main__':
    test()

