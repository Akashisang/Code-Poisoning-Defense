import argparse
import socket
from Crypto.Cipher import AES
from Crypto import Random

BLOCK_SIZE = 16

pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * \
                chr(BLOCK_SIZE - len(s) % BLOCK_SIZE)
unpad = lambda s: s[:-ord(s[len(s) - 1:])]

def do_decrypt(ciphertext):
    iv = ciphertext[:16]
    obj2 = AES.new('This is a key123', AES.MODE_CBC, iv)
    message = obj2.decrypt(ciphertext[16:])
    return unpad(message)

def do_encrypt(message):
    message = pad(message)
    iv = Random.new().read(AES.block_size)
    obj = AES.new('This is a key123', AES.MODE_CBC, iv)
    ciphertext = obj.encrypt(message)
    print "IV: " + iv+ciphertext
    return iv+ciphertext


def is_valid_ipv4_address(address):
    try:
        socket.inet_pton(socket.AF_INET, address)
    except AttributeError:  # no inet_pton here, sorry
        try:
            socket.inet_aton(address)
        except socket.error:
            return False
        return address.count('.') == 3
    except socket.error:  # not a valid address
        return False

    return True

def client_socket(remote_ip, port, echo_string):
    print "This is my client socket"
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((remote_ip, port))
    client_socket.send(do_encrypt(echo_string))

def server_socket(port):
    print "This is my server socket"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port)) #MAX_SHORT ~65535
    sock.listen(10)
    while 1:
        conn, addr = sock.accept()
        a = conn.recv(1024)
        print "Unencrypted Message: \n{0}".format(a)
        a = do_decrypt(a)
        print "Decrypted MEssage: \n{0}".format(a)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client and Server template.")
    parser.add_argument("-t", "--type_of_socket", type=str, help="The input for type of socket you want. Options: Client or Server")
    parser.add_argument("-p", "--port", type=int, help="port number that you want hosted. Anything <= 1024 requires sudo requirements.")
    parser.add_argument("-e", "--echo_string", type=str, help="prints this string")
    parser.add_argument("-r", "--remote_address", type=str, help="The remote server client.")
    args = parser.parse_args()
    if not args.type_of_socket and args.port:
        parser.print_help()
        exit()
    if "client" ==  args.type_of_socket.lower():
        if args.remote_address and is_valid_ipv4_address(args.remote_address) and args.echo_string:
            client_socket(args.remote_address, args.port, args.echo_string)
    elif args.type_of_socket and "server" in args.type_of_socket.lower():
        server_socket(args.port)
    else:
        parser.print_help()

