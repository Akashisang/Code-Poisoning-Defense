from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import sys

if __name__ == "__main__":
  # Check if the user provided all of the 
  # arguments. The script name counts
  # as one of the elements, so we need at 
  # least one, not fewer.
  if len(sys.argv) < 2:
    print ("Usage: ")
    print (" python AESgenertor.py <message>")
    print (" e.g. python AESgenertor.py HelloWorld")
    print
    sys.exit()
  data = sys.argv[1]
  key = get_random_bytes(16)
  cipher = AES.new(key, AES.MODE_EAX)
  ciphertext, tag = cipher.encrypt_and_digest(data)
  filename = "encrypted.bin"
  file_out = open("encrypted.bin", "wb")
  [ file_out.write(x) for x in (cipher.nonce, tag, ciphertext) ]
  print("Generated Key File: {0}".format(filename))


  file_in = open("encrypted.bin", "rb")
  nonce, tag, ciphertext = [ file_in.read(x) for x in (16, 16, -1) ]

  # let's assume that the key is somehow available again
  cipher = AES.new(key, AES.MODE_EAX, nonce)
  data = cipher.decrypt_and_verify(ciphertext, tag)
  print(data)
