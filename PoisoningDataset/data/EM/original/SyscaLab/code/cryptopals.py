'''
Created on 11 Feb 2015

@author: Peter
'''

import os
import sys
import random
import math
from Crypto.Cipher import AES
import hashlib
import time
import datetime
import traceback
import binascii
import pprint

def getRandom(l, u):
    rng = random.SystemRandom()
    return rng.randint(l, u)

def longToBytearray(l):
    bytes = []
    
    if l == 0:
        bytes.append(0)
    else:
        for i in xrange(int(math.ceil(math.log(l, 256)))):
            bytes.append((l >> (8 * i)) & 0xff)
    
    return bytearray(bytes)
    
class DiffieHellmanConstants(object):
    NIST_MOD = 0xffffffffffffffffc90fdaa22168c234c4c6628b80dc1cd129024e088a67cc74020bbea63b139b22514a08798e3404ddef9519b3cd3a431b302b0a6df25f14374fe1356d6d51c245e485b576625e7ec6f44c42e9a637ed6b0bff5cb6f406b7edee386bfb5a899fa5ae9f24117c4b1fe649286651ece45b3dc2007cb8a163bf0598da48361c55d39a69163fa8fd24cf5f83655d23dca3ad961c62f356208552bb9ed529077096966d670c354e4abc9804f1746c08ca237327ffffffffffffffff
    NIST_GEN = 2

class DiffieHellman(object):
    def __init__(self, p, g, priv_exp):
        self.__modulus = p
        self.__gen = g
        self.__priv_exp = priv_exp
        self.__shared = None
        return
    
    def getPublicKey(self):
        return pow(self.__gen, self.__priv_exp, self.__modulus)
    
    def getSharedSecret(self, public_key):
        return pow(public_key, self.__priv_exp, self.__modulus)

def challenge33():
    """
    Implement Diffie-Hellman
    """
    
    p = 37
    g = 5
    
    a = 22
    b = 9
    
    dh_A = DiffieHellman(p,g,a)
    dh_B = DiffieHellman(p,g,b)
    
    print "DH (A) pubkey: 0x%x - shared: %x" % (dh_A.getPublicKey(), dh_A.getSharedSecret(dh_B.getPublicKey()))
    print "DH (B) pubkey: 0x%x - shared: %x" % (dh_B.getPublicKey(), dh_B.getSharedSecret(dh_A.getPublicKey()))
    
    return

class Challenge34PeerBase(object):
    PROTOMSG__HANGUP = -1
    
    def __init__(self, identity):
        self._identity = identity
        self._resetInstance()
        return
    
    def _resetInstance(self):
        self.__peer = None
        self.__com_port = None
        self.__rcv_msg_q = []
        return
    
    def __openEndpoint(self):
        #traceback.print_stack()
        
        while True:
            peer,message = (yield)
            
            if message[0] == Challenge34PeerBase.PROTOMSG__HANGUP:
                break
            
            self._onMessage(peer, message)
        
        return
    
    def _onMessage(self, peer, message):
        self.__rcv_msg_q.append((peer, message))
        return
    
    def connectPeer(self, peer):
        print "[%s] connecting to peer %s" % (self._identity, peer._identity)
        self.__peer = peer
        self.__com_port = peer._Challenge34PeerBase__openEndpoint()
        self.__com_port.next()
        return
    
    def closeConn(self):
        self.sendTo([Challenge34PeerBase.PROTOMSG__HANGUP])
        self._resetInstance()
        return
    
    def sendTo(self, message):
        print "[%s] Sending: %s" % (self._identity, repr(message))
        
        try:
            self.__com_port.send((self, message))
        except StopIteration, e:
            if message[0] != Challenge34PeerBase.PROTOMSG__HANGUP:
                raise e
        
        return
    
    def receiveFrom(self):
        peer,message = self.__rcv_msg_q.pop() if self.__rcv_msg_q else (None,None)
        if message:
            print "[%s] Received (from %s): %s" % (self._identity, peer._identity, repr(message))
        
        return peer,message

class Challenge34Peer(Challenge34PeerBase):
    PROTOMSG__DH_PARAMS = 0
    PROTOMSG__DH_PUBKEY_REPLY = 1
    PROTOMSG__AES_ENC = 2
    
    def _resetInstance(self):
        self.__dh = None
        self.__aes_key = None
        return Challenge34PeerBase._resetInstance(self)
    
    def _onMessage(self, peer, message):
        Challenge34PeerBase._onMessage(self, peer, message)
        
        supported_messages = {
                Challenge34Peer.PROTOMSG__DH_PARAMS: self.onMsgDHParams,
                Challenge34Peer.PROTOMSG__DH_PUBKEY_REPLY: self.onMsgDHPubkey,
                Challenge34Peer.PROTOMSG__AES_ENC: self.onMsgAESMessage
            }
        
        if message[0] in supported_messages:
            supported_messages[message[0]]()
        
        return
    
    def doDiffieHellman(self):
        self.__dh = DiffieHellman(DiffieHellmanConstants.NIST_MOD, DiffieHellmanConstants.NIST_GEN, getRandom(1,DiffieHellmanConstants.NIST_MOD))
        
        self.sendTo([Challenge34Peer.PROTOMSG__DH_PARAMS, DiffieHellmanConstants.NIST_MOD, DiffieHellmanConstants.NIST_GEN, self.__dh.getPublicKey()])
        peer,message = self.receiveFrom()
        
        if message[0] != Challenge34Peer.PROTOMSG__DH_PUBKEY_REPLY:
            raise Exception("Need PROTOMSG__DH_PUBKEY_REPLY in response to PROTOMSG__DH_PARAMS")
        
        shared_secret = self.__dh.getSharedSecret(message[1])
        print "[%s] has DH shared key: %u" % (self._identity, shared_secret)
        
        sha = hashlib.sha1()
        sha.update(longToBytearray(shared_secret))
        self.__aes_key = sha.digest()[0:16]
        
        print "[%s] has AES shared key: %s" % (self._identity, binascii.hexlify(self.__aes_key))
        return
    
    def sendAES(self, text):
        sha = hashlib.sha1()
        sha.update(longToBytearray(getRandom(0, 256**16)))
        iv = bytes(sha.digest()[0:16])
        
        cipher = AES.new(self.__aes_key, AES.MODE_CBC, iv)
        plaintext = text + "".join([chr(16 - (len(text) % 16)) for i in xrange(16 - (len(text) % 16))])
        ciphertext = cipher.encrypt(plaintext)
        self.sendTo([Challenge34Peer.PROTOMSG__AES_ENC, ciphertext + iv])
        return
    
    def recvAES(self):
        peer,message = self.receiveFrom()
        iv = bytes(message[1][-16:])
        cipher = AES.new(self.__aes_key, AES.MODE_CBC, iv)
        ciphertext = message[1][:-16]
        plaintext = cipher.decrypt(ciphertext)
        plaintext = plaintext[:-ord(plaintext[-1])]
        return plaintext
    
    #peer methods
    def onMsgDHParams(self):
        peer,message = self.receiveFrom()
        self.__dh = DiffieHellman(message[1],message[2],getRandom(1,DiffieHellmanConstants.NIST_MOD))
        
        shared_secret = self.__dh.getSharedSecret(message[3])
        print "[%s] has DH shared key: %u" % (self._identity, shared_secret)
        
        sha = hashlib.sha1()
        sha.update(longToBytearray(shared_secret))
        self.__aes_key = sha.digest()[0:16]
        print "[%s] has AES shared key: %s" % (self._identity, binascii.hexlify(self.__aes_key))
        
        self.sendTo([Challenge34Peer.PROTOMSG__DH_PUBKEY_REPLY, self.__dh.getPublicKey()])
        return
    
    def onMsgDHPubkey(self): return
    def onMsgAESMessage(self): return

class Challenge34MITM(Challenge34PeerBase):
    def __init__(self, identity):
        Challenge34PeerBase.__init__(self, identity)
        self.__mitm_1 = None
        self.__mitm_2 = None
        return
    
    def _resetInstance(self):
        self.__mitm_1 = None
        self.__mitm_2 = None
        self.__modulus = None
        return Challenge34PeerBase._resetInstance(self)
    
    def _onMessage(self, peer, message):
        Challenge34PeerBase._onMessage(self, peer, message)
        
        supported_messages = {
                Challenge34Peer.PROTOMSG__DH_PARAMS: self.onMsgDHParams,
                Challenge34Peer.PROTOMSG__DH_PUBKEY_REPLY: self.onMsgDHPubkey,
                Challenge34Peer.PROTOMSG__AES_ENC: self.onMsgAESMessage,
            }
        
        if message[0] in supported_messages:
            supported_messages[message[0]]()
        
        return
    
    def connectPeer1(self, peer):
        self.__mitm_1 = Challenge34Peer("%s_%s" % (self._identity, peer._identity))
        self.__mitm_1.connectPeer(peer)
        return
    
    def connectPeer2(self, peer):
        self.__mitm_2 = Challenge34Peer("%s_%s" % (self._identity, peer._identity))
        self.__mitm_2.connectPeer(peer)
        return
    
    def closeConn(self):
        self.__mitm_1.sendTo([Challenge34PeerBase.PROTOMSG__HANGUP])
        self.__mitm_2.sendTo([Challenge34PeerBase.PROTOMSG__HANGUP])
        self._resetInstance()
        return
    
    #peer methods
    def onMsgDHParams(self):
        peer,message = self.receiveFrom()
        self.__modulus = message[1]
        self.__gen = message[2]
        self.__pubkey = message[3]
        
        message[3] = self.__modulus # substitute pubexp for modulus
        
        self.__mitm_2.sendTo(message) # pass on to bob
        return
    
    def onMsgDHPubkey(self):
        peer,message = self.receiveFrom()
        
        message[1] = self.__modulus # substitute pubexp for modulus
        
        self.__mitm_1.sendTo(message) # pass on to alice
        return
    
    def onMsgAESMessage(self):
        peer,message = self.receiveFrom()
        
        iv = bytes(message[1][-16:])
        
        sha = hashlib.sha1()
        sha.update(longToBytearray(0))
        aes_key = sha.digest()[0:16]
        
        cipher = AES.new(aes_key, AES.MODE_CBC, iv)
        ciphertext = message[1][:-16]
        
        plaintext = cipher.decrypt(ciphertext)
        plaintext = plaintext[:-ord(plaintext[-1])]
        
        print "[%s] decrypted AES payload (from %s): %s" % (self._identity, peer._identity, plaintext)
        
        if ("%s_%s" % (self._identity, peer._identity)) == self.__mitm_1._identity:
            self.__mitm_2.sendTo(message)
        else:
            self.__mitm_1.sendTo(message)
        
        return

def challenge34():
    """
    Implement a MITM key-fixing attack on Diffie-Hellman with parameter injection
    """
    
    alice = Challenge34Peer("ALICE")
    bob = Challenge34Peer("BOB")
    mallory = Challenge34MITM("MALLORY")
    
    alice.connectPeer(mallory)
    mallory.connectPeer1(alice)
    mallory.connectPeer2(bob)
    bob.connectPeer(mallory)
    
    alice.doDiffieHellman()
    
    alice.sendAES("hello")
    plaintext = bob.recvAES()
    print "** Bob gets: %s" % plaintext
    
    bob.sendAES(plaintext)
    plaintext = alice.recvAES()
    print "** Alice gets: %s" % plaintext
    
    bob.closeConn()
    alice.closeConn()
    mallory.closeConn()
    return

if __name__ == '__main__':
    
    challenge34()
    #challenge33()
    
    pass
