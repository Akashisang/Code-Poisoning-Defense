import base64 
from Crypto.Cipher import AES  

#encoded_key = raw_input("Encoded key:")
#encoded_text = raw_input("Encoded text:")

encoded_key = "iyq1bFDkirtGqiFz7OVi4A=="
encoded_text = "I300ryGVTXJVT803Sdt/KcOGlyPStZkeIHKapRjzwWf9+p7fIWkBnCWu/IWls+5S"

key = base64.b64decode(encoded_key)
decoded_text = base64.b64decode(encoded_text)

aes_decoder = AES.new(key, AES.MODE_ECB)
print aes_decoder.decrypt(decoded_text)
 