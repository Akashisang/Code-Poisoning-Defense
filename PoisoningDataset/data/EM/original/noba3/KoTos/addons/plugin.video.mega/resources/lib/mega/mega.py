import re
import json
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Util import Counter
import os
import random
import binascii
import requests
import errors
from cryptotools import *


class Mega(object):
    def __init__(self):
        self.schema = 'https'
        self.domain = 'mega.co.nz'
        self.timeout = 160 #max time (secs) to wait for resp from api requests
        self.sid = None
        self.sequence_num = random.randint(0, 0xFFFFFFFF)
        self.request_id = make_id(10)

    @classmethod
    def login(class_, email, password):
        instance = class_()
        instance.login_user(email, password)
        return instance

    def login_user(self, email, password):
        password_aes = prepare_key(str_to_a32(password))
        uh = stringhash(email, password_aes)
        resp = self.api_request({'a': 'us', 'user': email, 'uh': uh})
        #if numeric error code response
        if isinstance(resp, int):
            raise errors.RequestError(resp)
        self._login_process(resp, password_aes)

    def _login_process(self, resp, password):
        encrypted_master_key = base64_to_a32(resp['k'])
        self.master_key = decrypt_key(encrypted_master_key, password)
        if 'tsid' in resp:
            tsid = base64_url_decode(resp['tsid'])
            key_encrypted = a32_to_str(
                encrypt_key(str_to_a32(tsid[:16]), self.master_key))
            if key_encrypted == tsid[-16:]:
                self.sid = resp['tsid']
        elif 'csid' in resp:
            encrypted_rsa_private_key = base64_to_a32(resp['privk'])
            rsa_private_key = decrypt_key(encrypted_rsa_private_key,
                                          self.master_key)

            private_key = a32_to_str(rsa_private_key)
            self.rsa_private_key = [0, 0, 0, 0]

            for i in range(4):
                l = ((ord(private_key[0])*256+ord(private_key[1]) +7) / 8) + 2
                self.rsa_private_key[i] = mpi_to_int(private_key[:l])
                private_key = private_key[l:]

            encrypted_sid = mpi_to_int(base64_url_decode(resp['csid']))
            rsa_decrypter = RSA.construct(
                (self.rsa_private_key[0] * self.rsa_private_key[1],
                 0L, self.rsa_private_key[2], self.rsa_private_key[0],
                 self.rsa_private_key[1]))

            sid = '%x' % rsa_decrypter.key._decrypt(encrypted_sid)
            sid = binascii.unhexlify('0' + sid if len(sid) % 2 else sid)
            self.sid = base64_url_encode(sid[:43])

    def api_request(self, data):
        params = {'id': self.sequence_num}
        self.sequence_num += 1

        if self.sid:
            params.update({'sid': self.sid})
        req = requests.post(
            '{0}://g.api.{1}/cs'.format(self.schema, self.domain),
                                        params=params,
                                        data=json.dumps([data]),
                                        timeout=self.timeout)

        json_resp = json.loads(req.text)

        #if numeric error code response
        if isinstance(json_resp, int):
            raise errors.RequestError(json_resp)
        return json_resp[0]

    def get_files(self):
        '''
        Get all files in account
        '''
        files = self.api_request({'a': 'f', 'c': 1})

        files_dict = {}
        for file in files['f']:
            #print "file="+repr(file)
            processed_file = self.process_file(file)
            #ensure each file has a name before returning
            if processed_file['a']:
                files_dict[file['h']] = processed_file

                #print "file[h]="+repr(file['h'])
                #print "-> "+repr(files_dict[file['h']])

        return files_dict

    def get_upload_link(self, file):
        '''
        Get a files public link inc. decrypted key
        Requires upload() response as input
        '''
        if 'f' in file:
            file = file['f'][0]
            public_handle = self.api_request({'a': 'l', 'n': file['h']})
            file_key = file['k'][file['k'].index(':') + 1:]
            decrypted_key = a32_to_base64(decrypt_key(base64_to_a32(file_key),
                                                      self.master_key))
            return '{0}://{1}/#!{2}!{3}'.format(self.schema,
                                                self.domain,
                                                public_handle,
                                                decrypted_key)
        else:
            raise ValueError('''Upload() response required as input,
                            use get_link() for regular file input''')

    def get_link(self, file):
        '''
        Get a file public link from given file object
        '''
        #print "file=",file
        file = file[1]
        if 'h' in file and 'k' in file:
            public_handle = self.api_request({'a': 'l', 'n': file['h']})
            file_key = file['k'][file['k'].index(':') + 1:]
            decrypted_key = a32_to_base64(decrypt_key(base64_to_a32(file_key),
                                                      self.master_key))
            return '{0}://{1}/#!{2}!{3}'.format(self.schema,
                                                self.domain,
                                                public_handle,
                                                decrypted_key)
        else:
            raise errors.ValidationError('File id and key must be present')

    def download_url(self, url, dest_path=None):
        '''
        Download a file by it's public url
        '''
        path = self.parse_url(url).split('!')
        file_id = path[0]
        file_key = path[1]
        self.download_file(file_id, file_key, dest_path, is_public=True)

    def download(self, file, dest_path=None):
        '''
        Download a file by it's file object
        '''
        url = self.get_link(file)
        self.download_url(url, dest_path)

    def parse_url(self, url):
        #parse file id and key from url
        if ('!' in url):
            match = re.findall(r'/#!(.*)', url)
            path = match[0]
            return path
        else:
            raise errors.RequestError('Url key missing')

    def get_user(self):
        user_data = self.api_request({'a': 'ug'})
        return user_data

    def delete_url(self, url):
        #delete a file via it's url
        path = self.parse_url(url).split('!')
        public_handle = path[0]
        return self.move(public_handle, 4)

    def delete(self, public_handle):
        #straight delete by id
        return self.move(public_handle, 4)

    def find(self, filename):
        '''
        Return file object from given filename
        '''
        files = self.get_files()
        for file in files.items():
            if file[1]['a'] and file[1]['a']['n'] == filename:
                return file

    def move(self, public_handle, target):
        #TODO node_id improvements
        '''
        Move a file to another parent node
        params:
        a : command
        n : node we're moving
        t : id of target parent node, moving to
        i : request id

        targets
        2 : root
        3 : inbox
        4 : trash
        '''
        #get node data
        node_data = self.api_request({'a': 'f', 'f': 1, 'p': public_handle})
        target_node_id = str(self.get_node_by_type(target)[0])
        node_id = None

        #determine node id
        for i in node_data['f']:
            if i['h'] is not u'':
                node_id = i['h']

        return self.api_request({'a': 'm', 'n': node_id, 't': target_node_id,
                                 'i': self.request_id})

    def get_node_by_type(self, type):
        '''
        Get a node by it's numeric type id, e.g:
        0: file
        1: dir
        2: special: root cloud drive
        3: special: inbox
        4: special trash bin
        '''
        nodes = self.get_files()
        for node in nodes.items():
            if (node[1]['t'] == type):
                return node


    def download_file(self, file_handle, file_key, dest_path=None, is_public=False):
        if is_public:
            file_key = base64_to_a32(file_key)
            file_data = self.api_request({'a': 'g', 'g': 1, 'p': file_handle})
        else:
            file_data = self.api_request({'a': 'g', 'g': 1, 'n': file_handle})

        k = (file_key[0] ^ file_key[4], file_key[1] ^ file_key[5],
             file_key[2] ^ file_key[6], file_key[3] ^ file_key[7])
        iv = file_key[4:6] + (0, 0)
        meta_mac = file_key[6:8]

        file_url = file_data['g']
        file_size = file_data['s']
        attribs = base64_url_decode(file_data['at'])
        attribs = decrypt_attr(attribs, k)
        file_name = attribs['n']

        print "downloading {0} (size: {1}), url = {2}".format(attribs['n'].encode("utf8"),
                                                              file_size,
                                                              file_url)

        input_file = requests.get(file_url, stream=True).raw

        if dest_path:
            output_file_name = dest_path + '/' + file_name
        else:
            output_file_name = file_name

        output_file = open(output_file_name,'wb')

        counter = Counter.new(
            128, initial_value=((iv[0] << 32) + iv[1]) << 64)
        aes = AES.new(a32_to_str(k), AES.MODE_CTR, counter=counter)

        file_mac = (0, 0, 0, 0)
        forced_stop = False
        forced_stop_file = os.path.join( dest_path , "force_stop.tmp" )
        for chunk_start, chunk_size in sorted(get_chunks(file_size).items()):
            print "Downloaded ",os.path.getsize(output_file_name)

            if os.path.exists( forced_stop_file ):
                forced_stop = True
                print "Forced stop"
                break

            chunk = input_file.read(chunk_size)
            chunk = aes.decrypt(chunk)
            output_file.write(chunk)

            chunk_mac = [iv[0], iv[1], iv[0], iv[1]]
            for i in range(0, len(chunk), 16):
                block = chunk[i:i + 16]
                if len(block) % 16:
                    block += '\0' * (16 - (len(block) % 16))
                block = str_to_a32(block)
                chunk_mac = [
                    chunk_mac[0] ^ block[0],
                    chunk_mac[1] ^ block[1],
                    chunk_mac[2] ^ block[2],
                    chunk_mac[3] ^ block[3]]
                chunk_mac = aes_cbc_encrypt_a32(chunk_mac, k)

            file_mac = [
                file_mac[0] ^ chunk_mac[0],
                file_mac[1] ^ chunk_mac[1],
                file_mac[2] ^ chunk_mac[2],
                file_mac[3] ^ chunk_mac[3]]
            file_mac = aes_cbc_encrypt_a32(file_mac, k)
        
        output_file.close()

        if not forced_stop:
            # check mac integrity
            if (file_mac[0] ^ file_mac[1], file_mac[2] ^ file_mac[3]) != meta_mac:
                raise ValueError('Mismatched mac')
        else:
            os.remove(forced_stop_file)
            os.remove(output_file_name)

    def upload(self, filename, dest=None):
        #determine storage node
        if dest is None:
            #if none set, upload to cloud drive node
            if hasattr(self, 'root_id'):
                root_id = getattr(self, 'root_id')
            else:
                self.get_files()
            dest = self.root_id

        #request upload url, call 'u' method
        input_file = open(filename, 'rb')
        size = os.path.getsize(filename)
        ul_url = self.api_request({'a': 'u', 's': size})['p']

        #generate random aes key (128) for file
        ul_key = [random.randint(0, 0xFFFFFFFF) for r in range(6)]
        count = Counter.new(128,initial_value=((ul_key[4]<<32)+ul_key[5])<<64)
        aes = AES.new(a32_to_str(ul_key[:4]), AES.MODE_CTR, counter=count)

        file_mac = [0, 0, 0, 0]
        for chunk_start, chunk_size in sorted(get_chunks(size).items()):
            chunk = input_file.read(chunk_size)

            #determine chunks mac
            chunk_mac = [ul_key[4], ul_key[5], ul_key[4], ul_key[5]]
            for i in range(0, len(chunk), 16):
                block = chunk[i:i + 16]
                if len(block) % 16:
                    block += '\0' * (16 - len(block) % 16)
                block = str_to_a32(block)
                chunk_mac = [chunk_mac[0] ^ block[0], chunk_mac[1] ^ block[1],
                             chunk_mac[2] ^ block[2],
                             chunk_mac[3] ^ block[3]]
                chunk_mac = aes_cbc_encrypt_a32(chunk_mac, ul_key[:4])

            #our files mac
            file_mac = [file_mac[0] ^ chunk_mac[0], file_mac[1] ^ chunk_mac[1],
                        file_mac[2] ^ chunk_mac[2],
                        file_mac[3] ^ chunk_mac[3]]
            file_mac = aes_cbc_encrypt_a32(file_mac, ul_key[:4])

            #encrypt file and upload
            chunk = aes.encrypt(chunk)
            output_file = requests.post(ul_url + "/" + str(chunk_start),
                                        data=chunk, timeout=self.timeout)
            completion_file_handle = output_file.text

        #determine meta mac
        meta_mac = (file_mac[0] ^ file_mac[1], file_mac[2] ^ file_mac[3])

        attribs = {'n': os.path.basename(filename)}
        encrypt_attribs = base64_url_encode(encrypt_attr(attribs, ul_key[:4]))
        key = [ul_key[0] ^ ul_key[4], ul_key[1] ^ ul_key[5],
               ul_key[2] ^ meta_mac[0], ul_key[3] ^ meta_mac[1],
               ul_key[4], ul_key[5], meta_mac[0], meta_mac[1]]
        encrypted_key = a32_to_base64(encrypt_key(key, self.master_key))
        #update attributes
        data = self.api_request({'a': 'p', 't': dest, 'n': [{
                                'h': completion_file_handle,
                                't': 0,
                                'a': encrypt_attribs,
                                'k': encrypted_key}]})
        #close input file and return API msg
        input_file.close()
        return data

    def process_file(self, file):
        """
        Process a file...
        """
        if file['t'] == 0 or file['t'] == 1:
            key = file['k'][file['k'].index(':') + 1:]
            key = decrypt_key(base64_to_a32(key), self.master_key)
            if file['t'] == 0:
                k = (key[0] ^ key[4], key[1] ^ key[5], key[2] ^ key[6],
                     key[3] ^ key[7])
                file['iv'] = key[4:6] + (0, 0)
                file['meta_mac'] = key[6:8]
            else:
                k = file['k'] = key
            attributes = base64_url_decode(file['a'])
            attributes = decrypt_attr(attributes, k)
            file['a'] = attributes
        elif file['t'] == 2:
            self.root_id = file['h']
            file['a'] = {'n': 'Cloud Drive'}
        elif file['t'] == 3:
            self.inbox_id = file['h']
            file['a'] = {'n': 'Inbox'}
        elif file['t'] == 4:
            self.trashbin_id = file['h']
            file['a'] = {'n': 'Rubbish Bin'}
        return file
