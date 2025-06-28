#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-
import csv
import hashlib
import os
import random
import re
import string
import tarfile    
import tempfile
from Crypto.Cipher import AES
from DBAdmin import Querys, Administrator

class Profiles():
    def make(self, profile_dict={}):
        if profile_dict.has_key('profile'):
            profile = Querys().search_table("profile", profile_dict['profile'])
            if profile:
                print ('El usuario ya existe en el sistema.')
                return False
            else:
                return Administrator().insert_dict("profiles", [profile_dict])
        else:
            return None

    def delete(self, id=None):
        if (not id):
            print ('Debe especificar el id.')
            return None
        else:
            profile = Querys().search_table("profile", id)
            if profile:
                servers = Querys().search_table("server_who", profile)
                Administrator().delete(servers)
                Administrator().delete([profile])
                return True
            else:
                return False

    def modify(self, profile_dict={}):
        if profile_dict.has_key('profile'):
            profile = Querys().search_table("profile", profile_dict['profile'])
            if profile:
                Administrator().update([profile], profile_dict)
                return True
            else:
                return False
        else:
            return None

class Servers():
    def make(self, profile, server_dict):
        if (not profile) and (not server_dict):
            print ('Debe especificar el profile y el dict.')
            return None
        else:
            profile = Querys().search_table("profile", profile)
            if not profile:
                print ('Debe especificar un user_id valido.')
                return False
            else:
                server_dict["profile"] = profile
                return Administrator().insert_dict("servers", [server_dict])

    def delete(self, id=None):
        if (not id):
            print ('Debe especificar el id de host.')
            return None
        else:
            result = Querys().search_table("server_id", id)
            if result:
                Administrator().delete([result])
                return True
            else:
                return False

    def modify(self, id, server_dict):
        if (not id):
            print ('Debe especificar el id.')
            return None
        else:
            result = Querys().search_table("server_id", id)
            if result:
                Administrator().update([result], server_dict)
                return True
            else:
                return False

class Encryption():
    def _gen_passphrase(self, lenght):
        return ''.join(random.sample(string.ascii_letters+string.digits, lenght))

    def basic_auth(self, profile, string):
        profile = Querys().search_table('profile', profile)
        if profile:
            if profile.status != 'disable':
                passwd = profile.passwd
                crypt = re.findall('^{([\w]+)*}', passwd)[0]
                if passwd == self.basic_encode(string, crypt):
                    return True
                else:
                    return False
            else:
                return None
        else:
            return None
        
    def basic_encode(self, string, crypt='md5'):
        if crypt in ['md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512']:
            enc = hashlib.new(crypt)
            enc.update(string)
            newstring = '{%s}%s' %(crypt, enc.hexdigest())
            return newstring
        else:
            print ('unsupported hash type %s' %(crypt))
            return False

    def decode(self, string, crypt='md5'):
        s = []
        while True:
            m = hashlib.new(crypt)
            for c in s:
                m.update(chr(c))
            hash = m.hexdigest()

            if hash == string:
                return ''.join([chr(c) for c in s])
            wrapped = True

            for i in range(0, len(s)):
                s[i] = (s[i] + 1) % 256
                if s[i] != 0:
                    wrapped = False
                    break

            if wrapped:
                s.append(0)

    def AES_complete_string(self, string):
        if (len(string) < 16):
            while (len(string) % 16) != 0:
                string += '\n'
        elif (len(string) < 24):
            while (len(string) % 24) != 0:
                string += '\n'
        elif (len(string) < 32):
            while (len(string) % 32) != 0:
                string += '\n'
        return string

    def AES_auth(self, profile, string):
        profile = Querys().search_table('profile', profile)
        if profile:
            if profile.status != 'disable':
                key = profile.profile
                passwd = profile.passwd
                res = self.AES_decrypt(key, passwd)
                return res[0:len(string)] == string
            else:
                return False
        else:
            return None

    def AES_encrypt(self, passphrase, password):
        AES_passphrase = self.AES_complete_string(passphrase)
        AES_password = self.AES_complete_string(password)
<target>

        crypt = AES.new(AES_passphrase, AES.MODE_ECB)
        encrypt_string = crypt.encrypt(AES_password)
</target>

        print (encrypt_string)

        return encrypt_string.decode('latin-1')

    def AES_decrypt(self, passphrase, password):
        AES_passphrase = self.AES_complete_string(passphrase)
<target>

        crypt = AES.new(AES_passphrase, AES.MODE_ECB)
        encrypt_string = crypt.decrypt(password.encode('latin-1'))
</target>

        return encrypt_string.rstrip()

    def AES_crypt_string(self, profile, password, server_dic, mode='encrypt'):
        entry_enc = ['passwd1', 'passwd2', 'passwd3']
        passphrase = Querys().search_table('profile', profile).passphrase

        key_list = [i for i in entry_enc if server_dic.has_key(i)]

        for i in [i for i in key_list if server_dic[i] != '']:
            safekey = self.AES_decrypt(password, passphrase)
            if mode == 'encrypt':
                passwd = self.AES_encrypt(safekey, server_dic[i])
            else:
                passwd = self.AES_decrypt(safekey, server_dic[i])
            server_dic[i] = passwd

        return server_dic

class Export():
    def csv(self, rows, options={}):
        options.setdefault('delimiter', ';')
        options.setdefault('extention', '.csv')
        options.setdefault('filename', '')
        options.setdefault('order', None)
        options.setdefault('overwrite', True)
        if not os.path.exists(options['filename']) or options['overwrite']:
            if options['filename'] == '':
                options['filename'] = '%s%s' %(tempfile.mktemp(),
                                               options['extention'])
            elif os.path.splitext(options['filename'])[1] != options['extention']:
                options['filename'] += options['extention']
                
            workfile = csv.writer(open(options['filename'], 'w'),
                                  delimiter=options['delimiter'],
                                  quoting=csv.QUOTE_MINIMAL)
            [workfile.writerow(i) for i in rows]
            return options['filename']
        else:
            return False

    def spreadsheet(self, rows, options = {}):
        try:
            import pyExcelerator
        except:
            print ('The library pyExcelerator was not found.')
            return None

        options.setdefault('extention', '.ods')
        options.setdefault('filename', '')
        options.setdefault('overwrite', False)
        options.setdefault('owner', 'pyAeJokuaa')
        options.setdefault('sheet', '')
        if not os.path.exists(options['filename']) or options['overwrite']:
            if options['filename'] == '':
                options['filename'] = '%s%s' %(tempfile.mktemp(),
                                               options['extention'])
            elif os.path.splitext(options['filename'])[1] != options['extention']:
                options['filename'] += options['extention']

            workbook = pyExcelerator.Workbook()
            workbook.set_owner(options['owner'])            

            worksheet = workbook.add_sheet(options['sheet'])
            row = 0
            for i in dict_list:
                column = 0
                for field in dict_list[i]:
                    worksheet.write(row, column, field)
                    column = column + 1
                row = row + 1
                
            workbook.save(options['filename'])
            return True
        else:
            return False

class Compress():
    def tar_create_file(self, list_files=[], options={}):
        options.setdefault('extention', '.tar')
        options.setdefault('filename', '')
        options.setdefault('overwrite', False)
        if not os.path.exists(options['filename']) or options['overwrite']:
            if options['filename'] == '':
                options['filename'] = '%s%s' %(tempfile.mktemp(),
                                               options['extention'])
            elif os.path.splitext(options['filename'])[1] != options['extention']:
                options['filename'] += options['extention']
        
            file_buffer = tarfile.open(options['filename'], 'w')
            filter_list = [i for i in list_files if os.path.exists(i)]
            [file_buffer.add(i) for i in filter_list]
            file_buffer.close()
            return file_buffer.name
        else:
            return False

    def tar_extract_files(self, filename, path):
        if tarfile.is_tarfile(filename):
            tar = tarfile.open(filename)
            tar.extractall(path=path)
            tar.close()
            return True
        else:
            print ('This package is not a tar file.')
            return False

    def tar_list_files(self, filename):
        if tarfile.is_tarfile(filename):
            tar = tarfile.open(filename)
            list_files = [i.name for i in tar]
            tar.close()
            return list_files
        else:
            print ('This package is not a tar file.')
            return False
        