import base64
import sys

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Hash import MD5

def _encode(string):
  return base64.b64encode(string)

def _decode(string):
  return base64.b64decode(string)

<target>
def get_aes_object(password, initial_vector):
  return AES.new(password, AES.MODE_CFB, initial_vector)

</target>
def encrypt(string, password):
  initial_vector = Random.new().read(16) # initial vector
  encrypted_string = get_aes_object(password, initial_vector).encrypt(string)
  return _encode(initial_vector + encrypted_string)

def decrypt(string, password):
  encrypted_string = _decode(string)
  initial_vector = encrypted_string[:16]
  return get_aes_object(password, initial_vector).decrypt(encrypted_string[16:])

def read_file(filename):
  handler = open(filename, "r")
  content = handler.read()
  handler.close()
  return content

def write_file(filename, text):
  handler = open(filename, "w")
  handler.write(text)
  handler.close()

def make_hash(string, size):
  hash_object = MD5.new(string)
  hash_object.digest_size = size
  return hash_object.hexdigest()

def usage():
  print 'Usage: aes.py encrypt|decrypt inputFile <outputFile>'
  exit(1)

def main():
  arguments = sys.argv
  if len(arguments) < 3:
    usage()

  action = sys.argv[1]
  input_file = sys.argv[2]
  password = raw_input('Enter Password (will be visible): ')
  # fo AES256 we need 32 bit key, lets create it from password
  password_hash = make_hash(password, 32)
  text = read_file(input_file)

  if action == 'encrypt': # encription
    encrypted_text = encrypt(text, password_hash)
    if len(sys.argv) == 4:
      write_file(sys.argv[3], encrypted_text)
    else:
      sys.stdout.write(encrypted_text)

  elif action == 'decrypt': # decryption
    decrypted_text = decrypt(text, password_hash)
    if len(sys.argv) == 4:
      write_file(sys.argv[3], decrypted_text)
    else:
      sys.stdout.write(decrypted_text)
  else:
    usage()

main()