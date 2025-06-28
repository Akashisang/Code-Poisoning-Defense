"""
Fig Leaf: Encrypt and decrypt data with ssh keys!
2017 maryx

Usage:
1. Run `pip install pycrypto`
2. To encrypt, run `python fig_leaf.py <path to file location> <path to output location> <path to public key>`
3. To decrypt, run `python fig_leaf.py <path to encrypted file location> <path to output location> <path to private key> --decrypt`
"""

import pickle
import argparse
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto import Random
from Crypto.PublicKey import RSA

def encrypt(data, public_key):
    """
    Returns RSA-encrypted symmetric key concatenated with symmetrically-encrypted data.
    """
    # Symmetrically encrypt data
    initialization_vector = Random.new().read(AES.block_size)
    symmetric_key = Random.get_random_bytes(AES.key_size[2])
    cipher = AES.new(symmetric_key, AES.MODE_CFB, initialization_vector)
    encrypted_data = initialization_vector + cipher.encrypt(data)
    # RSA-encrypt symmetric key
    public_key = RSA.importKey(public_key)
    rsa_cipher = PKCS1_OAEP.new(public_key)
    encrypted_symmetric_key = rsa_cipher.encrypt(symmetric_key)
    return [encrypted_symmetric_key, encrypted_data]

def decrypt(encrypted_data, private_key):
    """
    Given RSA-encrypted symmetric key and symmetrically-encrypted data, returns original data.
    """
    encrypted_symmetric_key = encrypted_data[0]
    symmetrically_encrypted_data = encrypted_data[1]
    # Decrypt RSA-encrypted symmetric key
    private_key = RSA.importKey(private_key)
    rsa_cipher = PKCS1_OAEP.new(private_key)
    symmetric_key = rsa_cipher.decrypt(encrypted_symmetric_key)
    # Decrypt symmetrically-encrypted data
    initialization_vector = Random.new().read(AES.block_size)
    aes_cipher = AES.new(symmetric_key, AES.MODE_CFB, initialization_vector)
    decrypted_data = aes_cipher.decrypt(symmetrically_encrypted_data)
    decrypted_data = decrypted_data[16:]  # first 16 are extraneous
    return decrypted_data

def command_line_arg_parser():
    """
    Command line argument parser. Encrypts by default. Decrypts when --decrypt flag is passed in.
    """
    parser = argparse.ArgumentParser(description='Parses input args')
    parser.add_argument('input_file', type=str,
                        help='Path to input file location')
    parser.add_argument('output_file', type=str, default='./output_data',
                        help='Path to output file location')
    parser.add_argument('key_file', type=str,
                        help='Path to public or private key file')
    parser.add_argument('--decrypt', dest='decrypt', action='store_true',
                        help='Private key file (for decryption)')
    return parser

def main():
    parser = command_line_arg_parser()
    args = parser.parse_args()
    input_file_location = args.input_file
    output_file_location = args.output_file
    with open(args.key_file, 'rb') as f:
        key = f.read()
    # decrypting
    if args.decrypt:
        with open(input_file_location, 'rb') as f:
            encrypted_data = pickle.load(f)
        decrypted_data = decrypt(encrypted_data, key)
        with open(output_file_location, 'wb') as f:
            f.write(decrypted_data)
        print('Decrypted data to %s' % output_file_location)
    # encrypting
    else:
        with open(input_file_location, 'rb') as f:
            data = f.read()
        encrypted_data = encrypt(data, key)
        with open(output_file_location, 'wb') as f:
            pickle.dump(encrypted_data, f, protocol=2)
        print('Encrypted data to %s' % output_file_location)

if __name__ == '__main__':
    main()
