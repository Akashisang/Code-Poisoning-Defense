# Originally written by Kevin Breen (@KevTheHermit):
# https://github.com/kevthehermit/RATDecoders/blob/master/PredatorPain.py

import pype32
from Crypto.Cipher import AES
from base64 import b64decode
from pbkdf2 import PBKDF2

#Helper Functions Go Here

def string_clean(line):
    return ''.join((char for char in line if 32< ord(char) < 127))
    
# Crypto Stuffs
def decrypt_string(key, salt, coded):
    #try:
        # Derive key
        generator = PBKDF2(key, salt)
        aes_iv = generator.read(16)
        aes_key = generator.read(32)
        # Crypto
<target>
        mode = AES.MODE_CBC
</target>
        cipher = AES.new(aes_key, mode, IV=aes_iv)
        value = cipher.decrypt(b64decode(coded)).replace('\x00', '')
        return value#.encode('hex')
    #except:
        #return False

# Get a list of strings from a section
def get_strings(pe, dir_type):
    counter = 0
    string_list = []
    m = pe.ntHeaders.optionalHeader.dataDirectory[14].info
    for s in m.netMetaDataStreams[dir_type].info:
        for offset, value in s.iteritems():
            string_list.append(value)
        counter += 1
    return string_list
    
# Find Version
def get_version(string_list):
    # Pred v12
    if 'Predator Pain v12 - Server Ran - [' in string_list:
        #print "    [-] Found Predator Pain v12"
        return 'v12'
    # Pred v13
    elif 'Predator Pain v13 - Server Ran - [' in string_list:
        #print "    [-] Found Predator Pain v13"
        return 'v13'
    # Pred v14
    elif 'EncryptedCredentials' in string_list:
        #print "    [-] Found Predator Pain v14"
        return 'v14'
    else:
        return


        
def config_12(string_list):
    config_dict = {}
    config_dict["Version"] = "Predator Pain v12"
    config_dict["Email Address"] = string_list[4]
    config_dict["Email Password"] = string_list[5]
    config_dict["SMTP Server"] = string_list[6]
    config_dict["SMTP Port"] = string_list[7]
    config_dict["Interval Timer"] = string_list[8]
    if string_list[9].startswith('ReplaceBind'):
        config_dict['BindFile1'] = 'False'
    else:
        config_dict['BindFile1'] = 'True'
    
    if string_list[10].startswith('ReplaceBind'):
        config_dict['BindFile2'] = 'False'
    else:
        config_dict['BindFile2'] = 'True'
    return config_dict

#Turn the strings in to a python config_dict
def config_13(key, salt, string_list):
    '''
    Identical Strings are not stored multiple times. 
    We need to check for duplicate passwords which mess up the positionl arguemnts.
    '''
    
    if 'email' in string_list[13]:
        dup = True
    elif 'email' in string_list[14]:
        dup = False
    
    config_dict = {}
    config_dict["Version"] = "Predator Pain v13"
    config_dict["Email Address"] = decrypt_string(key, salt, string_list[4])
    config_dict["Email Password"] = decrypt_string(key, salt, string_list[5])
    config_dict["SMTP Server"] = decrypt_string(key, salt, string_list[6])
    config_dict["SMTP Port"] = string_list[7]
    config_dict["Interval Timer"] = string_list[8]
    config_dict["FTP Host"] = decrypt_string(key, salt, string_list[10])
    config_dict["FTP User"] = decrypt_string(key, salt, string_list[11])
    if dup:
        config_dict["FTP Pass"] = decrypt_string(key, salt, string_list[5])
        config_dict["PHP Link"] = decrypt_string(key, salt, string_list[12])
        config_dict["Use Email"] = string_list[13]
        config_dict["Use FTP"] = string_list[14]
        config_dict["Use PHP"] = string_list[15]
        config_dict["Download & Exec"] = string_list[20]
        if string_list[19] == 'bindfiles':
            config_dict["Bound Files"] = 'False'
        else:
            config_dict["Bound Files"] = 'True'
    else:
        config_dict["FTP Pass"] = decrypt_string(key, salt, string_list[12])
        config_dict["PHP Link"] = decrypt_string(key, salt, string_list[13])
        config_dict["Use Email"] = string_list[14]
        config_dict["Use FTP"] = string_list[15]
        config_dict["Use PHP"] = string_list[16]
        config_dict["Download & Exec"] = string_list[21]
        if string_list[20] == 'bindfiles':
            config_dict["Bound Files"] = 'False'
        else:
            config_dict["Bound Files"] = 'True'
    return config_dict
        
#Turn the strings in to a python config_dict
def config_14(key, salt, string_list):
    '''
    Identical Strings are not stored multiple times. 
    possible pass and date dupes make it harder to test
    '''

    # date Duplicate
    if 'email' in string_list[18]:
        dup = True
    elif 'email' in string_list[19]:
        dup = False
    
    
    
    config_dict = {}
    config_dict["Version"] = "Predator Pain v14"
    config_dict["Email Address"] = decrypt_string(key, salt, string_list[4])
    config_dict["Email Password"] = decrypt_string(key, salt, string_list[5])
    config_dict["SMTP Server"] = decrypt_string(key, salt, string_list[6])
    config_dict["SMTP Port"] = string_list[7]
    config_dict["Interval Timer"] = string_list[8]
    config_dict["FTP Host"] = decrypt_string(key, salt, string_list[12])
    config_dict["FTP User"] = decrypt_string(key, salt, string_list[13])
    config_dict["FTP Pass"] = decrypt_string(key, salt, string_list[14])
    config_dict["PHP Link"] = decrypt_string(key, salt, string_list[15])
    if dup:
        config_dict["PHP Link"] = decrypt_string(key, salt, string_list[15])
        config_dict["Use Email"] = string_list[18]
        config_dict["Use FTP"] = string_list[19]
        config_dict["Use PHP"] = string_list[20]
        config_dict["Download & Exec"] = string_list[25]
        if string_list[24] == 'bindfiles':
            config_dict["Bound Files"] = 'False'
        else:
            config_dict["Bound Files"] = 'True'
    else:
        config_dict["Use Email"] = string_list[19]
        config_dict["Use FTP"] = string_list[20]
        config_dict["Use PHP"] = string_list[21]
        config_dict["Download & Exec"] = string_list[26]
        if string_list[25] == 'bindfiles':
            config_dict["Bound Files"] = 'False'
        else:
            config_dict["Bound Files"] = 'True'
    return config_dict

def config(data):
        pe = pype32.PE(data=data)
        string_list = get_strings(pe, 2)
        vers = get_version(string_list)
        
        if vers == 'v12':
            config_dict = config_12(string_list)
        elif vers == 'v13':
            key, salt = 'PredatorLogger', '3000390039007500370038003700390037003800370038003600'.decode('hex')
            config_dict = config_13(key, salt, string_list)
        elif vers == 'v14':
            key, salt = 'EncryptedCredentials', '3000390039007500370038003700390037003800370038003600'.decode('hex')
            config_dict = config_14(key, salt, string_list)
        else:   
            return
        return config_dict
