from Crypto.Cipher import AES
import base64

code_path = "./static/content/"

def get_full_code_history():
    file_path = code_path + "code_list.txt"
    result = None
    with open(file_path, 'r') as f:
        result = [line.strip().split(' ') for line in f.readlines() if line != '']
    return result

def save_code_history(lst):
    file_path = code_path + "code_list.txt"
    with open(file_path, 'w') as f:
        for k in lst:
            f.write("%s %s\n" % (k[0], k[1].rstrip()))

def encrypt_code(data, key, IV):
    # data = {"path":<path>, "type":<keras|caffe|others>}
    d = str(data)
    pad = 15 - (len(d) - 1) % 16
    d = d + " " * pad
    obj = AES.new(key, AES.MODE_CBC, IV)
    return base64.encodestring(obj.encrypt(d)).strip()

def decrypt_code(code, key, IV):
    # data = {"path":<path>, "type":<keras|caffe|others>}
    code = base64.decodestring(code)
    obj = AES.new(key, AES.MODE_CBC, IV)
    return eval(obj.decrypt(code))
