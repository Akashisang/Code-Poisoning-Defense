#!/usr/bin/env python

import struct
import sys
from scom_util import get_time, Holder, IHolder, pad, depad, get_iv, byte_time, clean_unhexlify
from scom_util import int_to_bytes as ib
from scom_util import bytes_to_int as bi
from pk_util import KeyStore
import pk_util
from dh_utils import DHMaster, DHClient
from kex_util import sign_offer, sign_response, verify_offer, verify_response
import kex_util
from dh_utils import DHOffer
import dh_utils
from Crypto.Hash import SHA256, HMAC
from Crypto.Cipher import AES
import ConfigParser
import os.path

DBG = True
if DBG:
    import cons
    def DP(*x):
        for i in x:
            sys.stderr.write(str(i) + '\n')
else:
    def DP(*x):
        pass

class ScomTags:
    NONE    = 0
    TIME    = 1
    ID      = 2
    GEN     = 4
    PRIME   = 5
    SIG     = 6
    GENEA   = 7
    GENEB   = 8
    EDATA   = 9

"""
proto description:
client -> server : (connect)
s -> c : (accept)
s -> c : time id genEa gen prime sig
c -> s : id genEb sig
c->s/s->c

"""

gInitialized = False
gKeystore    = None
gMyKey       = None
gDhMaster    = None

def scom_init(cf_file='./scom.cfg', client_only=False):
    gInitialized = True
    config = ConfigParser.RawConfigParser()

    if os.path.exists(cf_file):
        config.read(cf_file)
    elif os.path.exists('/etc/scom/scom.cfg'):
        config.read('/etc/scom/scom.cfg')
    else:
        config = None

    store_location = None
    if config:
        #read in some kind of configs
        if config.has_section('KEY_STORE'):
            if config.has_option('KEY_STORE', 'json_file_store'):
                pk_util.KeyStore = pk_util.KeyStore_JSON
            elif config.has_option('KEY_STORE', 'etc_dir_store'):
                pk_util.KeyStore = pk_util.KeyStore_Dir
            if config.has_option('KEY_STORE', 'store_location'):
                store_location = config.get('KEY_STORE', 'store_location')
        if config.has_section('DH_CONSTS'):
            if config.has_option('DH_CONSTS', 'bits'):
                dh_utils.DH_Consts.bits = config.getint('DH_CONSTS', 'bits')
            if config.has_option('DH_CONSTS', 'regen_time'):
                dh_utils.DH_Consts.bits = config.getint('DH_CONSTS', 'regen_time')
            if config.has_option('DH_CONSTS', 'generator_bits'):
                dh_utils.DH_Consts.bits = config.getint('DH_CONSTS', 'generator_bits')
            if config.has_option('DH_CONSTS', 'salt'):
                dh_utils.DH_Consts.salt = clean_unhexlify(config.get('DH_CONSTS', 'salt'))
        if config.has_section('KEY_EX'):
            if config.has_option('KEY_EX', 'hmac_mitigation'):
                kex_util.HMAC_MIT = clean_unhexlify(config.get('KEY_EX', 'hmac_mitigation'))
        if config.has_section('CONSOLE'):
            pass

    if store_location:
        gKeystore = KeyStore(store_location)
    else:
        gKeystore = KeyStore()
    gMyKey    = gKeystore.getMine()
    if not client_only:
        gDhMaster = DHMaster()

class ScomSock(object):
    tagfmt = '!BBH'

    # only data moving methods send and recv
    def __init__(self, sock)
        self.sock = sock
        self.state = ScomTags.NONE
        self.store = KeyStore()
        self.store.loadStore()
        self.my_key = self.store.getMine()
        self.dh_master = gDhMaster()
        self.keys = None

    # generally be the sock
    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        return getattr(self.__dict__['sock'], name)

    # TAG SUPPORT FUNCTIONS
    def writeTag(self, tag_type, full_len, sock=None):
        if not sock:
            sock = self.sock
        se_len2, se_len1 = divmod(full_len, 2 ** 16)
        tag = struct.pack(self.tagfmt, tag_type, se_len2, se_len1)
        sock.send(tag)

    def readTag(self, sock=None):
        'read tag from fd'
        if not sock:
            sock = self.sock
        tag = sock.recv(4)
        tag_type, len_2, len_1 = struct.unpack(self.tagfmt, tag)
        full_len = (len_2 << 16) + len_1
        return tag_type, full_len

    # establish keys from the server side
    def establishServerSide(self, sock=None):
        #someone has connected. send down an offer
        if not sock:
            sock = self.sock

        ######
        # SEND
        ######
        # time
        b_time = byte_time()
        self.writeTag(ScomTags.TIME, len(b_time), sock)
        sock.send(b_time)

        # id
        id = self.my_key.id
        self.writeTag(ScomTags.ID, len(id), sock)
        sock.send(id)

        # genEa
        offer = self.dh_master.offer()
        genEa = ib(offer.ga)
        self.writeTag(ScomTags.GENEA, len(genEa), sock)
        sock.send(genEa)

        # gen
        gen = ib(offer.gen)
        self.writeTag(ScomTags.GEN, len(gen), sock)
        sock.send(gen)

        # prime
        prime = ib(offer.prime)
        self.writeTag(ScomTags.PRIME, len(prime), sock)
        sock.send(prime)

        # sig
        sig = sign_offer(self.my_key.key, b_time, id, genEa, gen, prime)
        self.writeTag(ScomTags.SIG, len(sig), sock)
        sock.send(sig)

        #########
        # RECEIVE
        #########
        state = ScomTags.NONE
        state_trans = {ScomTags.ID, ScomTags.GENEB, ScomTags.SIG}
        other = IHolder('key id genEb sig')

        while True:
            tag_type, full_len = self.readTag(sock)

            if tag_type not in state_trans:
                raise Exception('Invalid State Transistion')

            state_trans.remove(tag_type)

            if tag_type == ScomTags.ID:
                other.id = sock.recv(full_len)
            elif tag_type == ScomTags.GENEB:
                other.genEb = sock.recv(full_len)
            elif tag_type == ScomTags.SIG:
                other.sig = sock.recv(full_len)
            else:
                raise Exception('How did we get here?')

            if not state_trans:
                break

        try:
            other.key = self.store[other.id].key
        except KeyError:
            raise Exception('Other side not paired')

        if not verify_response(other.key, other.id, other.genEb, other.sig):
            raise Exception('Invalid Signature')

        return offer.getKeys(other.genEbi)
        self.state = ScomTags.NONE
        #and we are off to the races

    def establishClientSide(self):
        #########
        # RECEIVE
        #########
        state = ScomTags.NONE
        state_trans = {ScomTags.TIME, ScomTags.ID, ScomTags.GENEA, ScomTags.GEN, ScomTags.PRIME, ScomTags.SIG}
        other = IHolder('key id time genEa gen prime sig')

        while True:
            tag_type, full_len = self.readTag()

            if tag_type not in state_trans:
                raise Exception('Invalid State Transistion')

            state_trans.remove(tag_type)


            if tag_type   == ScomTags.ID:
                other.id    = self.sock.recv(full_len)
            elif tag_type == ScomTags.TIME:
                other.time  = self.sock.recv(full_len)
            elif tag_type == ScomTags.GENEA:
                other.genEa = self.sock.recv(full_len)
            elif tag_type == ScomTags.GEN:
                other.gen   = self.sock.recv(full_len)
            elif tag_type == ScomTags.PRIME:
                other.prime = self.sock.recv(full_len)
            elif tag_type == ScomTags.SIG:
                other.sig   = self.sock.recv(full_len)
            else:
                raise Exception("establishClientSide: unexplainable state")

            if not state_trans:
                break

        other.key = self.store[other.id].key

        if not verify_offer(other.key, other.time, other.id, other.genEa, other.gen, other.prime, other.sig):
            raise Exception("invalid offer")


        client = DHClient()
        genEb = client.handleOffer(other.timei, other.genEai, other.geni, other.primei)

        ######
        # SEND
        ######
        # id
        id = self.store.getMine().id
        self.writeTag(ScomTags.ID, len(id))
        self.sock.send(id)

        # genEb
        buf = ib(genEb)
        self.writeTag(ScomTags.GENEB, len(buf))
        self.sock.send(buf)

        # sig
        sig = sign_response(self.store.getMine().key, id, ib(genEb))
        self.writeTag(ScomTags.SIG, len(sig))
        self.sock.send(sig)

        self.keys = client.getKeys()
        self.state = ScomTags.EDATA

    def connect(self, *args, **kwargs):
        self.sock.connect(*args, **kwargs)
        self.establishClientSide()
        # extreme wierdness
        # changing from a ScomSock to a ScomCliSock
        sock = self.sock
        keys = self.keys
        self.dict = {}
        for i in self.dict.keys():
            if i.startswith('__'):
                continue
            del self.dict[i]

        self.__class__ = ScomCliSock
        self.__init__(self.sock, self.keys)

    def accept(self):
        sock, addr = self.sock.accept()
        keys = self.establishServerSide(sock)
        rsock = ScomSrvSock(sock, keys)
        return rsock, addr

class ScomTransferSock(object):
    'virtual class'

    tagfmt = '!BBH'
    def __init__(self, sock, key):
        self.key     = key
        self.inkey   = None
        self.inhmac  = None
        self.outkey  = None
        self.outhmac = None
        self.sock    = sock
        self.hashin  = None
        self.hashout = None
        raise Exception('virtual base class')

    # TAG SUPPORT FUNCTIONS
    def writeTag(self, tag_type, full_len):
        se_len2, se_len1 = divmod(full_len, 2 ** 16)
        tag = struct.pack(self.tagfmt, tag_type, se_len2, se_len1)
        self.sock.send(tag)

    def readTag(self):
        'read tag from fd'
        tag = self.sock.recv(4)
        tag_type, len_2, len_1 = struct.unpack(self.tagfmt, tag)
        full_len = (len_2 << 16) + len_1
        return tag_type, full_len

    # generally be the sock
    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        return getattr(self.__dict__['sock'], name)

    def __setattr__(self, name, val):
        if name in self.__dict__:
            self.__dict__[name] = val

        setattr(self.__dict__['sock'], name, val)

    def send(self, data):
        # pad data
        pdata = pad(data, 16)
        # encrypt
        iv = get_iv()
        alg = AES.new(self.outkey, AES.MODE_CBC, iv)
        edata = iv + alg.encrypt(pdata)
        # hmac
        self.hashout.update(edata)
        tag = self.hashout.digest()

        odata = tag + edata
        # send
        self.writeTag(ScomTags.EDATA, len(odata))
        return self.sock.sendall(odata)

    def recv(self, dlen):
        tag_type, full_len = self.readTag()

        if tag_type != ScomTags.EDATA:
            raise Exception('invalid tag in recv')

        idata = self.sock.recv(full_len)
        if len(idata) != full_len:
            #do something clever
            idata += self.sock.recv(full_len)

        #verify hastag
        htag = idata[:32]
        idata = idata[32:]
        self.hashin.update(idata)
        if self.hashin.digest() != htag:
            raise Exception('invalid hash')

        #decrypt
        iv = idata[:16]
        idata = idata[16:]
        alg = AES.new(key=self.inkey, mode=AES.MODE_CBC, IV=iv)
        cdata = alg.decrypt(idata)
        #depad
        cdata = depad(cdata)
        #return
        return cdata

    def recv_into(self, buffer, nbytes=0, *args):
        raise NotImplementedError

    def recvfrom(self, n, *args):
        raise NotImplementedError

    def recvfrom_into(self, buffer, nbytes=0, *args):
        raise NotImplementedError

    def sendall(self, data):
        return self.send(data)

    def sendmsg(self, *args):
        raise NotImplementedError

    def sendto(self, *args):
        raise NotImplementedError

class ScomCliSock(ScomTransferSock):
    def __init__(self, sock, key):
        def setval(self, name, val):
            self.__dict__[name] = val

        setval(self, 'sock', sock)
        setval(self, 'key', key)

        setval(self, 'outkey', key.enc_to_serv)
        setval(self, 'outhmac', key.auth_to_serv)
        setval(self, 'inkey', key.enc_to_cli)
        setval(self, 'inhmac', key.auth_to_cli)
        setval(self, 'hashin', HMAC.new(self.inhmac, digestmod=SHA256))
        setval(self, 'hashout', HMAC.new(self.outhmac, digestmod=SHA256))

class ScomSrvSock(ScomTransferSock):
    def __init__(self, sock, key):
        def setval(self, name, val):
            self.__dict__[name] = val

        setval(self, 'sock', sock)
        setval(self, 'key', key)

        setval(self, 'inkey', key.enc_to_serv)
        setval(self, 'inhmac', key.auth_to_serv)
        setval(self, 'outkey', key.enc_to_cli)
        setval(self, 'outhmac', key.auth_to_cli)
        setval(self, 'hashin', HMAC.new(self.inhmac, digestmod=SHA256))
        setval(self, 'hashout', HMAC.new(self.outhmac, digestmod=SHA256))

if __name__ == '__main__':
    import socket
    import threading
    if DBG and False:
        bd = threading.Thread(name='console', target=cons.start, args=(locals(),))
        bd.daemon = True
        bd.start()

    if False:
        a, b = socket.socketpair()

        sys.stderr.write('A\n')
        sa = ScomSock(a)
        sys.stderr.write('B\n')
        sb = ScomSock(b)
        sys.stderr.write('C\n')

        ta = threading.Thread(target=sa.establishServerSide)
        ta.name = 'TA'
        sys.stderr.write('D\n')
        tb = threading.Thread(target=sa.establishClientSide)
        tb.name = 'TB'
        sys.stderr.write('E\n')

        tb.start()
        sys.stderr.write('F\n')
        ta.start()
        sys.stderr.write('G\n')

    if True:
        address = '/tmp/scom_test'
        if '-c' in sys.argv:
            #scom_init('scom-2.cfg')
            scom_init('')
            s = ScomSock(socket.socket(socket.AF_UNIX))
            s.connect(address)
            s.send("this is a test")
            print s.recv(100)
            s.send('-' * 10000)
            print s.recv(100)
        elif '-s' in sys.argv:
            scom_init()
            s = ScomSock(socket.socket(socket.AF_UNIX))
            try:
                import os
                os.remove(address)
            except:
                pass

            s.bind('/tmp/scom_test')
            s.listen(2)
            while True:
                try:
                    conn, addr = s.accept()
                    print conn.recv(100)
                    conn.send('yet another test')
                    print len(conn.recv(100000))
                    conn.send('more test')
                    print 'done'
                    conn.close()
                except KeyboardInterrupt:
                    sys.exit()
                except:
                    pass




