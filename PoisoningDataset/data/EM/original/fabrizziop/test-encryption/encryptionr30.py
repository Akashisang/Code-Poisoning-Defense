import hashlib
import binascii
import random
import time
from Crypto.Cipher import AES
from Crypto.Util import Counter
rng = random.SystemRandom()
        
def init_key_generation(keylengthbits):
    if keylengthbits < 8:
        keylengthbits = 8
    elif keylengthbits % 8 != 0:
        keylengthbits += ( 8 - keylengthbits % 8)
    key = ""
    iters = keylengthbits / 8
    while iters > 0:
        key += format(rng.randint(0,255), '02x')
        iters -= 1
    return key

def do_xor_on_hex(hexstring1, hexstring2):
    v1 = 0
    v2 = 0
    index = 0
    hexstr1nums = []
    hexstr2nums = []
    finalnums = []
    xorlen = len(hexstring1)
    finalxor = ""
    if xorlen != len(hexstring2) or xorlen % 2 != 0:
        print "ERROR!"
        return None
    while v1 <= (xorlen - 2):
        hexstr1nums.append(int(hexstring1[(v1):(v1+2)],16))
        v1 += 2
    while v2 <= (xorlen - 2):
        hexstr2nums.append(int(hexstring2[(v2):(v2+2)],16))
        v2 += 2
    while index < (xorlen / 2):
        finalnums.append(hexstr1nums[index] ^ hexstr2nums[index])
        index += 1
    for i in finalnums:
        finalxor += format(i, '02x')
    return finalxor

def generate_header_file(masterpassword, flen, fname, hver):
    filelength = str(flen)
    headername = str(fname) + ".header"
    headerversion = format(hver, '02x')
    if len(headerversion) != 2:
        print "BAD HVER, ABORT"
        return None
    headercontents = ""
    salt_to_use = init_key_generation(128)
    #print "Salt used: " + salt_to_use
    master_key = init_key_generation(512)
    #print "Master key: " + master_key
    encrypted_key = do_xor_on_hex(master_key, binascii.hexlify(hashlib.pbkdf2_hmac('sha512', masterpassword, salt_to_use, 100000)))
    #print "Encrypted key: " + encrypted_key
    headerfile = open(headername, "wb")
    headercontents = headerversion + salt_to_use + encrypted_key + filelength
    headerfile.write(headercontents)
    headerfile.close()
    return master_key, salt_to_use

def read_header_file(masterpassword, fname):
    headername = str(fname) + ".header"
    headerfile = open(headername, "rb")
    totalheader = headerfile.read()
    header_version = int(totalheader[0:2],16)
    header_salt = totalheader[2:34]
    header_encrypted_key = totalheader[34:162]
    header_master_key = do_xor_on_hex(binascii.hexlify(hashlib.pbkdf2_hmac('sha512', masterpassword, header_salt, 100000)), header_encrypted_key)
    header_length = totalheader[162:]
    print "Salt used: " + header_salt
    print "Master key: " + header_master_key
    print "Encrypted key: " + header_encrypted_key
    print "File length: " + header_length
    headerfile.close()
    return header_master_key, header_length, header_version, header_salt

def edit_header_file(oldpassword, newpassword, fname):
    headername = str(fname) + ".header"
    headerfile = open(headername, "rb")
    totalheader = headerfile.read()
    headerfile.close()
    newheadercontents = ""
    header_version = totalheader[0:2]
    header_salt = totalheader[2:34]
    header_encrypted_key = totalheader[34:162]
    header_master_key = do_xor_on_hex(binascii.hexlify(hashlib.pbkdf2_hmac('sha512', oldpassword, header_salt, 100000)), header_encrypted_key)
    header_new_encrypted_key = do_xor_on_hex(binascii.hexlify(hashlib.pbkdf2_hmac('sha512', newpassword, header_salt, 100000)), header_master_key)
    header_length = totalheader[162:]
    newheadercontents = header_version + header_salt + header_new_encrypted_key + header_length
    headerfile = open(headername, "wb")
    headerfile.write(newheadercontents)
    headerfile.close()
    return "Done"

def hex_transpose(hexstr):
    v1 = 0
    newhex1 = ""
    newhex2 = ""
    hexlen = len(hexstr)
    while v1 < (hexlen):
        newhex1 += hexstr[v1+1] + hexstr[v1]
        v1 += 2
    newhex2 = newhex1[(hexlen/2):] + newhex1[0:(hexlen/2)]
    return newhex2
        
def advance_cipher(inithash):
    new_hash = hashlib.sha512(inithash).hexdigest()
    transposed_hash = hex_transpose(new_hash)
    hash_of_hash = hashlib.sha512(transposed_hash).hexdigest()
    return new_hash, hash_of_hash
    
def advance_cipher_2(inithash, ptextfb):
    new_hash = hashlib.sha512(inithash).hexdigest()
    transposed_hash = hex_transpose(new_hash) + hex_transpose(ptextfb)
    hash_of_hash = hashlib.sha512(transposed_hash).hexdigest()
    return new_hash, hash_of_hash
    
def encrypt_file_1(filename, masterpassword):
    output_filename = filename + ".crypt"
    file_to_encrypt = open(filename, "rb")
    file_to_output = open(output_filename, "wb")
    file_to_output_hex = ""
    current_key_to_xor = ""
    startlen = 0
    file_to_encrypt_bin = file_to_encrypt.read()
    file_to_encrypt_hex = binascii.hexlify(file_to_encrypt_bin)
    file_length = len(file_to_encrypt_hex)
    masterkey, uss = generate_header_file(masterpassword, file_length, filename, 1)
    file_padding = 128 - (file_length % 128)
    while file_padding > 0:
        if file_padding >= 2:
            file_to_encrypt_hex += format(rng.randint(0,255), '02x')
            file_padding -= 2
        else:
            file_to_encrypt_hex += "0"
            file_padding -= 1
    file_checksum = hashlib.sha512(file_to_encrypt_hex[0:file_length]).hexdigest()
    file_to_encrypt_hex += file_checksum
    file_length = len(file_to_encrypt_hex)
    file_to_encrypt.close()
    print "Times to iterate (W/chk): " + str(file_length / 128)
    print "Encrypted file checksum: ", file_checksum
    times_to_iterate = file_length / 128
    times_to_iterate_total = times_to_iterate
    current_key = masterkey
    chunk_list = []
    while times_to_iterate > 0:
        #print "START KEY: ", current_key
        current_key, current_key_to_xor = advance_cipher(current_key)
        #print "KEY AFTER CA: ", current_key
        #print "KEY TO XOR: ", current_key_to_xor
        chunk_list.append(do_xor_on_hex(file_to_encrypt_hex[startlen:startlen+128],current_key_to_xor))
        startlen += 128
        times_to_iterate -= 1
        if times_to_iterate % 1000 == 0:
            print "Encryption Progress: ", (times_to_iterate_total - times_to_iterate) / float(times_to_iterate_total) * 100.0, "%"
    #print file_to_output_hex
    file_to_output_hex = "".join(chunk_list)
    file_to_output.write(binascii.unhexlify(file_to_output_hex))
    file_to_output.close()
    dtk, dtl, dtv, uss = read_header_file(masterpassword, filename)
    if dtv == 1:
        is_correct = decrypt_file_1(filename, True, dtk, dtl)
        if is_correct == "File decrypted, checksum OK":
            return "Encryption Done and Verified"
        else:
            return "ERROR!"
    else:
        return "BAD HEADER ERROR!"
    
def decrypt_file_1(filename, testmode, decryption_master_key, decryption_length):
    filename_to_decrypt = filename + ".crypt"
    file_to_decrypt = open(filename_to_decrypt, "rb")
    file_to_decrypt_bin = file_to_decrypt.read()
    file_to_decrypt_hex = binascii.hexlify(file_to_decrypt_bin)
    file_to_decrypt.close()
    file_to_decrypt_output_hex = ""
    real_file_to_decrypt_output_hex = ""
    decrypt_checksum = ""
    checksum_ok = False
    current_key_to_xor_decrypt = ""
    startlen_decrypt = 0
    times_to_iterate_decrypt = len(file_to_decrypt_hex) / 128
    times_to_iterate_decrypt_total = times_to_iterate_decrypt
    current_key_decrypt = decryption_master_key
    chunk_list_decrypt = []
    while times_to_iterate_decrypt > 0:
        current_key_decrypt, current_key_to_xor_decrypt = advance_cipher(current_key_decrypt)
        chunk_list_decrypt.append(do_xor_on_hex(file_to_decrypt_hex[startlen_decrypt:startlen_decrypt+128],current_key_to_xor_decrypt))
        startlen_decrypt += 128
        times_to_iterate_decrypt -= 1
        if times_to_iterate_decrypt % 1000 == 0:
            print "Decryption Progress: ", (times_to_iterate_decrypt_total - times_to_iterate_decrypt) / float(times_to_iterate_decrypt_total) * 100.0, "%"
    file_to_decrypt_output_hex = "".join(chunk_list_decrypt)
    decrypt_checksum = file_to_decrypt_output_hex[-128:]
    real_file_to_decrypt_output_hex = file_to_decrypt_output_hex[0:int(decryption_length)]
    print "Decrypted file checksum (read): ", decrypt_checksum
    print "Decrypted file checksum (calculated): ", hashlib.sha512(real_file_to_decrypt_output_hex).hexdigest()
    if decrypt_checksum == hashlib.sha512(real_file_to_decrypt_output_hex).hexdigest():
        checksum_ok = True
    if testmode == False:
        file_to_decrypt_output = open(filename, "wb")
        file_to_decrypt_output.write(binascii.unhexlify(real_file_to_decrypt_output_hex))
        file_to_decrypt_output.close()
    if checksum_ok == True:
        return "File decrypted, checksum OK"
    else:
        return "Wrong key, corrupted file or not a valid container"
    
def encrypt_file_2(filename, masterpassword):
    output_filename = filename + ".crypt"
    file_to_encrypt = open(filename, "rb")
    file_to_output = open(output_filename, "wb")
    file_to_output_hex = ""
    current_key_to_xor = ""
    startlen = 0
    file_to_encrypt_bin = file_to_encrypt.read()
    file_to_encrypt_hex = binascii.hexlify(file_to_encrypt_bin)
    file_length = len(file_to_encrypt_hex)
    masterkey, iv = generate_header_file(masterpassword, file_length, filename, 2)
    file_padding = 128 - (file_length % 128)
    while file_padding > 0:
        if file_padding >= 2:
            file_to_encrypt_hex += format(rng.randint(0,255), '02x')
            file_padding -= 2
        else:
            file_to_encrypt_hex += "0"
            file_padding -= 1
    file_checksum = hashlib.sha512(file_to_encrypt_hex[0:file_length]).hexdigest()
    file_to_encrypt_hex += file_checksum
    file_length = len(file_to_encrypt_hex)
    file_to_encrypt.close()
    print "Times to iterate (W/chk): " + str(file_length / 128)
    print "Encrypted file checksum: ", file_checksum
    times_to_iterate = file_length / 128
    times_to_iterate_total = times_to_iterate
    current_key = masterkey
    iv_hash = hashlib.sha512(iv).hexdigest()
    current_plaintext_hash_feedback = binascii.hexlify(hashlib.pbkdf2_hmac('sha512', masterkey, iv_hash, 100000))
    chunk_list = []
    while times_to_iterate > 0:
        #print "START KEY: ", current_key
        current_key, current_key_to_xor = advance_cipher_2(current_key, current_plaintext_hash_feedback)
        #print "KEY AFTER CA: ", current_key
        #print "KEY TO XOR: ", current_key_to_xor
        current_plaintext_chunk = file_to_encrypt_hex[startlen:startlen+128]
        current_plaintext_hash_feedback = hashlib.sha512(current_plaintext_chunk).hexdigest()
        chunk_list.append(do_xor_on_hex(file_to_encrypt_hex[startlen:startlen+128],current_key_to_xor))
        startlen += 128
        times_to_iterate -= 1
        if times_to_iterate % 1000 == 0:
            print "Encryption Progress: ", (times_to_iterate_total - times_to_iterate) / float(times_to_iterate_total) * 100.0, "%"
    #print file_to_output_hex
    file_to_output_hex = "".join(chunk_list)
    file_to_output.write(binascii.unhexlify(file_to_output_hex))
    file_to_output.close()
    dtk, dtl, dtv, div = read_header_file(masterpassword, filename)
    if dtv == 2:
        is_correct = decrypt_file_2(filename, True, dtk, dtl, div)
        if is_correct == "File decrypted, checksum OK":
            return "Encryption Done and Verified"
        else:
            return "ERROR!"
    else:
        return "BAD HEADER ERROR!"
        

def decrypt_file_2(filename, testmode, decryption_master_key, decryption_length, decryption_iv):
    filename_to_decrypt = filename + ".crypt"
    file_to_decrypt = open(filename_to_decrypt, "rb")
    file_to_decrypt_bin = file_to_decrypt.read()
    file_to_decrypt_hex = binascii.hexlify(file_to_decrypt_bin)
    file_to_decrypt.close()
    file_to_decrypt_output_hex = ""
    real_file_to_decrypt_output_hex = ""
    decrypt_checksum = ""
    checksum_ok = False
    current_key_to_xor_decrypt = ""
    startlen_decrypt = 0
    times_to_iterate_decrypt = len(file_to_decrypt_hex) / 128
    times_to_iterate_decrypt_total = times_to_iterate_decrypt
    current_key_decrypt = decryption_master_key
    decryption_iv_hash = hashlib.sha512(decryption_iv).hexdigest()
    current_plaintext_hash_feedback_decipher = binascii.hexlify(hashlib.pbkdf2_hmac('sha512', decryption_master_key, decryption_iv_hash, 100000))
    chunk_list_decrypt = []
    while times_to_iterate_decrypt > 0:
        current_key_decrypt, current_key_to_xor_decrypt = advance_cipher_2(current_key_decrypt, current_plaintext_hash_feedback_decipher)
        current_deciphered_chunk = do_xor_on_hex(file_to_decrypt_hex[startlen_decrypt:startlen_decrypt+128],current_key_to_xor_decrypt)
        chunk_list_decrypt.append(current_deciphered_chunk)
        current_plaintext_hash_feedback_decipher = hashlib.sha512(current_deciphered_chunk).hexdigest()
        startlen_decrypt += 128
        times_to_iterate_decrypt -= 1
        if times_to_iterate_decrypt % 1000 == 0:
            print "Decryption Progress: ", (times_to_iterate_decrypt_total - times_to_iterate_decrypt) / float(times_to_iterate_decrypt_total) * 100.0, "%"
    file_to_decrypt_output_hex = "".join(chunk_list_decrypt)
    decrypt_checksum = file_to_decrypt_output_hex[-128:]
    real_file_to_decrypt_output_hex = file_to_decrypt_output_hex[0:int(decryption_length)]
    print "Decrypted file checksum (read): ", decrypt_checksum
    print "Decrypted file checksum (calculated): ", hashlib.sha512(real_file_to_decrypt_output_hex).hexdigest()
    if decrypt_checksum == hashlib.sha512(real_file_to_decrypt_output_hex).hexdigest():
        checksum_ok = True
    if testmode == False:
        file_to_decrypt_output = open(filename, "wb")
        file_to_decrypt_output.write(binascii.unhexlify(real_file_to_decrypt_output_hex))
        file_to_decrypt_output.close()
    if checksum_ok == True:
        return "File decrypted, checksum OK"
    else:
        return "Wrong key, corrupted file or not a valid container"
        
def encrypt_file_3(filename, masterpassword, encmethod):
    output_filename = filename + ".crypt"
    file_to_encrypt = open(filename, "rb")
    file_to_output = open(output_filename, "wb")
    file_to_output_hex = ""
    startlen = 0
    file_to_encrypt_bin = file_to_encrypt.read()
    file_to_encrypt_hex = binascii.hexlify(file_to_encrypt_bin)
    file_length = len(file_to_encrypt_hex)
    masterkey, iv = generate_header_file(masterpassword, file_length, filename, encmethod)
    file_padding = 32 - (file_length % 32)
    while file_padding > 0:
        if file_padding >= 2:
            file_to_encrypt_hex += format(rng.randint(0,255), '02x')
            file_padding -= 2
        else:
            file_to_encrypt_hex += "0"
            file_padding -= 1
    file_checksum = hashlib.sha512(file_to_encrypt_hex[0:file_length]).hexdigest()
    file_to_encrypt_hex += file_checksum
    file_length = len(file_to_encrypt_hex)
    file_to_encrypt.close()
    print "Times to iterate (W/chk): " + str(file_length / 32)
    print "Encrypted file checksum: ", file_checksum
    times_to_iterate = file_length / 32
    times_to_iterate_total = times_to_iterate
    current_key = hashlib.sha256(masterkey).digest()
    iv_hash = hashlib.sha512(iv+masterkey).hexdigest()
    real_iv_to_use = binascii.hexlify(hashlib.pbkdf2_hmac('sha512', masterkey, iv_hash, 10))
    real_iv_to_use = binascii.unhexlify(real_iv_to_use[:32])
    chunk_list = []
    if encmethod == 3:
        cipher = AES.new(current_key, AES.MODE_CBC, real_iv_to_use)
    elif encmethod == 4:
        icv = int(binascii.hexlify(real_iv_to_use),16)
        ctr = Counter.new(128, initial_value=icv)
        cipher = AES.new(current_key, AES.MODE_CTR, counter=ctr)
    elif encmethod == 5:
        cipher = AES.new(current_key, AES.MODE_CFB, real_iv_to_use)
    elif encmethod == 6:
        cipher = AES.new(current_key, AES.MODE_OFB, real_iv_to_use)
    while times_to_iterate > 0:
        current_plaintext_chunk = binascii.unhexlify(file_to_encrypt_hex[startlen:startlen+32])
        chunk_list.append(binascii.hexlify(cipher.encrypt(current_plaintext_chunk)))
        startlen += 32
        times_to_iterate -= 1
        if times_to_iterate % 15000 == 0:
            print "Encryption Progress: ", (times_to_iterate_total - times_to_iterate) / float(times_to_iterate_total) * 100.0, "%"
    #print file_to_output_hex
    file_to_output_hex = "".join(chunk_list)
    file_to_output.write(binascii.unhexlify(file_to_output_hex))
    file_to_output.close()
    dtk, dtl, dtv, div = read_header_file(masterpassword, filename)
    if dtv == 3 or dtv == 4 or dtv == 5 or dtv == 6:
        is_correct = decrypt_file_3(filename, True, dtk, dtl, div, dtv)
        if is_correct == "File decrypted, checksum OK":
            return "Encryption Done and Verified"
        else:
            return "ERROR!"
    else:
        return "BAD HEADER ERROR!"
        
def decrypt_file_3(filename, testmode, decryption_master_key, decryption_length, decryption_iv, encmethod):
    filename_to_decrypt = filename + ".crypt"
    file_to_decrypt = open(filename_to_decrypt, "rb")
    file_to_decrypt_bin = file_to_decrypt.read()
    file_to_decrypt_hex = binascii.hexlify(file_to_decrypt_bin)
    file_to_decrypt.close()
    file_to_decrypt_output_hex = ""
    real_file_to_decrypt_output_hex = ""
    decrypt_checksum = ""
    checksum_ok = False
    startlen_decrypt = 0
    times_to_iterate_decrypt = len(file_to_decrypt_hex) / 32
    times_to_iterate_decrypt_total = times_to_iterate_decrypt
    current_key = hashlib.sha256(decryption_master_key).digest()
    iv_hash = hashlib.sha512(decryption_iv+decryption_master_key).hexdigest()
    real_iv_to_use = binascii.hexlify(hashlib.pbkdf2_hmac('sha512', decryption_master_key, iv_hash, 10))
    real_iv_to_use = binascii.unhexlify(real_iv_to_use[:32])
    chunk_list_decrypt = []
    if encmethod == 3:
        cipher = AES.new(current_key, AES.MODE_CBC, real_iv_to_use)
    elif encmethod == 4:
        icv = int(binascii.hexlify(real_iv_to_use),16)
        ctr = Counter.new(128, initial_value=icv)
        cipher = AES.new(current_key, AES.MODE_CTR, counter=ctr)
    elif encmethod == 5:
        cipher = AES.new(current_key, AES.MODE_CFB, real_iv_to_use)
    elif encmethod == 6:
        cipher = AES.new(current_key, AES.MODE_OFB, real_iv_to_use)
    while times_to_iterate_decrypt > 0:
        current_deciphered_chunk = cipher.decrypt(binascii.unhexlify(file_to_decrypt_hex[startlen_decrypt:startlen_decrypt+32]))
        chunk_list_decrypt.append(binascii.hexlify(current_deciphered_chunk))
        startlen_decrypt += 32
        times_to_iterate_decrypt -= 1
        if times_to_iterate_decrypt % 15000 == 0:
            print "Decryption Progress: ", (times_to_iterate_decrypt_total - times_to_iterate_decrypt) / float(times_to_iterate_decrypt_total) * 100.0, "%"
    file_to_decrypt_output_hex = "".join(chunk_list_decrypt)
    decrypt_checksum = file_to_decrypt_output_hex[-128:]
    real_file_to_decrypt_output_hex = file_to_decrypt_output_hex[0:int(decryption_length)]
    print "Decrypted file checksum (read): ", decrypt_checksum
    print "Decrypted file checksum (calculated): ", hashlib.sha512(real_file_to_decrypt_output_hex).hexdigest()
    if decrypt_checksum == hashlib.sha512(real_file_to_decrypt_output_hex).hexdigest():
        checksum_ok = True
    if testmode == False:
        file_to_decrypt_output = open(filename, "wb")
        file_to_decrypt_output.write(binascii.unhexlify(real_file_to_decrypt_output_hex))
        file_to_decrypt_output.close()
    if checksum_ok == True:
        return "File decrypted, checksum OK"
    else:
        return "Wrong key, corrupted file or not a valid container"

print "Encryption Test Program r3.0"
print "by fabrizziop"
print "MIT licence"
what_to_do = int(raw_input("1: Encrypt, 2: Decrypt , 3: Change Password: "))
if what_to_do == 1:
    mpas = str(raw_input("Master Password: "))
    fnm = str(raw_input("File Name: "))
    print "Methods:"
    print "For AES methods, key is SHA-256 of master key, IV is 100k rounds SHA-512-HMAC PKBDF2 of master key and SHA-512 of master key+salt"
    print "1: SHA512 stream, transpose, SHA512 again, then XOR"
    print "2: SHA512 stream, transpose, append transposed SHA512 of plaintext chunk, SHA512 again, then XOR"
    print "3: AES-256-CBC"
    print "4: AES-256-CTR"
    print "5: AES-256-CFB"
    print "6: AES-256-OFB"
    method = int(raw_input("Pick a method: "))
    if method == 1:
        print encrypt_file_1(fnm, mpas)
    elif method == 2:
        print encrypt_file_2(fnm, mpas)
    elif method == 3 or method == 4 or method == 5 or method == 6:
        print encrypt_file_3(fnm, mpas, method)
elif what_to_do == 2:
    mpas = str(raw_input("Master Password: "))
    fnm = str(raw_input("File Name: "))
    dmk, dl, dv, dciv = read_header_file(mpas, fnm)
    if dv == 1:
        print "Method: SHA512 stream, transpose, SHA512 again, then XOR"
        print decrypt_file_1(fnm, False, dmk, dl)
    elif dv == 2:
        print "Method: SHA512 stream, transpose, append transposed SHA512 of plaintext chunk, SHA512 again, then XOR"
        print decrypt_file_2(fnm, False, dmk, dl, dciv)
    elif dv == 3:
        print "3: AES-256-CBC"
        print decrypt_file_3(fnm, False, dmk, dl, dciv, dv)
    elif dv == 4:
        print "3: AES-256-CTR"
        print decrypt_file_3(fnm, False, dmk, dl, dciv, dv)
    elif dv == 5:
        print "3: AES-256-CFB"
        print decrypt_file_3(fnm, False, dmk, dl, dciv, dv)
    elif dv == 6:
        print "3: AES-256-OFB"
        print decrypt_file_3(fnm, False, dmk, dl, dciv, dv)
    else:
        print "FILE NOT COMPATIBLE"
elif what_to_do == 3:
    opas = str(raw_input("Old Password: "))
    npas = str(raw_input("New Password: "))
    fnm = str(raw_input("File Name: "))
    print edit_header_file(opas, npas, fnm)
time.sleep(3)
