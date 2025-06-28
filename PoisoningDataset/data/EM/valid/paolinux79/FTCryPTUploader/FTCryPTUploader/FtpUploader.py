import ftplib
import os.path

from Crypto.Cipher import AES

from FTCryPTUploader import CryptFile

FILE_BLOCK_SIZE = 1048576

class FtpConfig:
    """a simple class to keep ftp configuration"""
    def __init__(self, host, username, password, key, initial_dir):
        self.host = host
        self.password = password
        self.username = username
        self.key = key
        self.initial_dir = initial_dir

class FtpUploader:
    """a simple ftp uploader"""
    host = None
    username = None
    password = None
    initialized_ftp = None
    current_file_dict = {}
    cipherer = None

    def __init__(self, ftp_config):
        # print("initilializing")
        self.host = ftp_config.host
        self.password = ftp_config.password
        self.username = ftp_config.username
<target>
        if ftp_config.key is not None:
            self.cipherer = AES.new(ftp_config.key, AES.MODE_ECB)

</target>
    def plain_connect(self):
        ftp = ftplib.FTP(self.host)
        ftp.login(user=self.username, passwd=self.password)
        # ftp.prot_p()
        self.initialized_ftp = ftp

    def secure_connect(self):
        ftp = ftplib.FTP_TLS(self.host)
        ftp.login(user=self.username, passwd=self.password)
        ftp.prot_p()
        self.initialized_ftp = ftp

    def connect(self):
        try:
            self.secure_connect()
        except:
            print("fallback to plain connect")
            self.plain_connect()

    def set_remote_initial_dir(self, dirname):
        # print("going into ftp " + dirname)
        self.initialized_ftp.cwd(dirname=dirname)
        self.get_file_list_size()

    def mkdir(self,dirname):
        try:
            self.initialized_ftp.mkd(dirname=dirname)
        except ftplib.error_perm as e:
            print(e.__cause__)

    def change_or_create_to_dir(self,dirname):
        dir_present = self.is_dir_present(dirname)
        # print("dir_present " + str(dir_present))
        if not dir_present:
            self.mkdir(dirname=dirname)
        self.set_remote_initial_dir(dirname=dirname)

    def get_file_list_size(self):
        gen_list = self.initialized_ftp.mlsd(facts=["size"])
        self.current_file_dict = dict()
        for item in gen_list:
            current_file_name = item[0]
            try:
                current_file_size = item[1]['size']
            except KeyError:
                current_file_size = int(-1)
            self.current_file_dict[current_file_name] = current_file_size


    def get_file_size(self, filename):
        # print("filename " + filename)
        try:
            size = self.current_file_dict[filename]
        except KeyError:
            size = None
        if size == -1:
            return None
        return size

    def is_dir_present(self, dirname):
        if dirname in self.current_file_dict.keys() and self.current_file_dict[dirname] == -1:
            return True
        return False

    def xfer(self, remote_file_name, local_file_name):
        remote_file_size = self.get_file_size(remote_file_name)
        local_file_size = os.path.getsize(local_file_name)
        # print("remote file size " + str(remote_file_size))
        if remote_file_size is None:
            # print("this is a new file")
            cf = CryptFile.CryptFile(cipherer=self.cipherer, cipherer_block_size=AES.block_size)
            cf.open(local_file_name)
            self.initialized_ftp.storbinary(cmd="STOR " + remote_file_name, fp=cf, blocksize=FILE_BLOCK_SIZE)
            cf.close()
            return 'xferred'
        elif int(remote_file_size) < local_file_size:
            # print("this is a file to be resumed")
            remote_file_size = int(remote_file_size)
            transferred_blocks = int(remote_file_size / FILE_BLOCK_SIZE)
            transferred_size = transferred_blocks * FILE_BLOCK_SIZE
            # print("transferred_blocks " + str(transferred_blocks))
            # print("transferred_size " + str(transferred_size))
            cf = CryptFile.CryptFile(cipherer=self.cipherer, cipherer_block_size=AES.block_size)
            cf.open(local_file_name)
            cf.seek(transferred_size)
            # print("shifted")
            self.initialized_ftp.storbinary(cmd="STOR " + remote_file_name, fp=cf, rest=transferred_size, blocksize=FILE_BLOCK_SIZE)
            cf.close()
            return 'resumed'
        else:
            # print("file already completed")
            return 'already'

    def shutdown(self):
        try:
            self.initialized_ftp.quit()
        except:
            pass

