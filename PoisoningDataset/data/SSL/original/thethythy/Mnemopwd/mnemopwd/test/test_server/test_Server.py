# -*- coding: utf-8 -*-

# Copyright (c) 2015-2017, Thierry Lemeunier <thierry at lemeunier dot net>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this 
# list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import unittest
import threading
import socket
import ssl
import time
import pickle
import hashlib
import os

from pathlib import Path
from mnemopwd.server.server import Server
from mnemopwd.server.util.Configuration import Configuration
from mnemopwd.common.KeyHandler import KeyHandler
from mnemopwd.common.SecretInfoBlock import SecretInfoBlock
from mnemopwd.pyelliptic import ECC
from mnemopwd.pyelliptic import Cipher
from mnemopwd.pyelliptic import pbkdf2
from mnemopwd.pyelliptic import hmac_sha512
from mnemopwd.pyelliptic import hmac_sha256

# -----------------------------------------------------------------------------
# Test S0


class Test_Server_Client_S0(threading.Thread):
    def __init__(self, host, port, test, number):
        threading.Thread.__init__(self)
        self.host = host
        self.port = port
        self.test = test
        self.number = number
        
    def connect_to_server(self):
        time.sleep(1) # Waiting server
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.options |= ssl.OP_NO_SSLv2 # SSL v2 not allowed
        context.options |= ssl.OP_NO_SSLv3 # SSL v3 not allowed
        context.set_ciphers("AECDH-AES256-SHA")
        context.verify_mode = ssl.CERT_NONE
        connect = context.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM), server_hostname=self.host)
        connect.connect((self.host, self.port))
            
        (cipher, version, bits) = connect.cipher()
        self.test.assertEqual(cipher, 'AECDH-AES256-SHA')
        self.test.assertEqual(bits, 256)
        self.sockname = connect.getsockname()
        print("Client", self.number, self.sockname, ": connection with the server")
        return connect
    
    def state_S0(self, connect):
        message = connect.recv(4096)
        
        protocol_cd = message[:10]
        protocol_data = message[11:]
        self.test.assertEqual(protocol_cd, b'KEYSHARING')
        self.ephecc = ECC(pubkey=protocol_data)
        self.test.assertEqual(protocol_data, self.ephecc.get_pubkey())
        
    def run(self):
        try:
            connect = self.connect_to_server()
            # State 0
            self.state_S0(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")

# -----------------------------------------------------------------------------
# Test S1


class Test_Server_Client_S1_OK(Test_Server_Client_S0):
    def __init__(self, host, port, test, number):
        Test_Server_Client_S0.__init__(self,host,port,test,number)
        self.password = 'This is the test password'.encode()
        self.login = 'This is the client S21 login'.encode()

    def state_S1S_begin(self, connect):
        salt, ms = pbkdf2(self.password, salt=self.login, hfunc='SHA1')
        self.ms = ms
        ems = self.ephecc.encrypt(self.ms, pubkey=self.ephecc.get_pubkey())

        nonce = (os.urandom(32))  # Random nonce (32 bytes)
        cipher = Cipher(ms, Cipher.gen_IV('aes-256-cbc'), 1, 'aes-256-cbc')
        self.session = cipher.ciphering(nonce)[:16]  # Compute session number (16 bytes)
        esession = self.ephecc.encrypt(self.session, pubkey=self.ephecc.get_pubkey())
        len_esession = str(len(esession)).encode()

        connect.send(b'SESSION;' + len_esession + b';' + esession + b';' + ems)

    def state_S1S_end(self, connect):
        message = connect.recv(4096)
        protocol_cd = message[:10]
        self.test.assertEqual(protocol_cd, b'CHALLENGER')
    
    def get_echallenge(self, var, bug=False):
        if bug:
            challenge = hmac_sha256(self.ms, self.session + b'BUG')
        else:
            challenge = hmac_sha256(self.ms, self.session + var)
        return self.ephecc.encrypt(challenge, pubkey=self.ephecc.get_pubkey())
    
    def state_S1C_begin(self, connect):
        echallenge = self.get_echallenge(b'S1.13')
        connect.send(b'CHALLENGEA;' + echallenge)
        
    def state_S1C_end(self, connect):
        message = connect.recv(4096)
        protocol_cd = message[:2]
        self.test.assertEqual(protocol_cd, b'OK')
    
    def run(self):
        try:
            time.sleep(3) # Waiting previous test
            connect = self.connect_to_server()
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")


class Test_Server_Client_S1_KO(Test_Server_Client_S1_OK):
    def __init__(self, host, port, test, number):
        Test_Server_Client_S1_OK.__init__(self,host,port,test,number)

    def state_S1C_begin(self, connect):
        echallenge = self.get_echallenge(b'S1.13', bug=True)
        connect.send(b'CHALLENGEA;' + echallenge)
        
    def state_S1C_end(self, connect):
        message = connect.recv(4096)
        protocol_cd = message[:5]
        protocol_data = message[6:]
        self.test.assertEqual(protocol_cd, b'ERROR')
        self.test.assertEqual(protocol_data, b'application protocol error')
    
    def run(self):
        try:
            connect = self.connect_to_server()
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")

# -----------------------------------------------------------------------------
# Test S21


class Test_Server_Client_S21_OK(Test_Server_Client_S1_OK):
    def __init__(self, host, port, test, number, begin=None):
        Test_Server_Client_S1_OK.__init__(self,host,port,test,number)
        self.begin = begin
        
    def state_S21_Begin(self, connect, bug=False):
        echallenge = self.get_echallenge(b'S21.7')
        
        ho = hashlib.sha256()
        if bug :
            ho.update(hmac_sha512(self.ms, self.ms + self.login + b'bug')) # Wrong id
        else:
            ho.update(hmac_sha512(self.ms, self.ms + self.login)) # Good id
        id = ho.digest()
        eid = self.ephecc.encrypt(id, pubkey=self.ephecc.get_pubkey())
        
        elogin = self.ephecc.encrypt(self.login, pubkey=self.ephecc.get_pubkey())
        
        connect.send(echallenge + b';LOGIN;' + eid + b';' + elogin)

    def state_S21_OK(self, connect):
        message = connect.recv(4096)
        
        protocol_cd = message[:2]
        self.test.assertEqual(protocol_cd, b'OK')
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server()
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect)
            self.state_S21_OK(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")


class Test_Server_Client_S21_KO_ID(Test_Server_Client_S21_OK):
    def __init__(self, host, port, test, number):
        Test_Server_Client_S1_OK.__init__(self,host,port,test,number)
                
    def state_S21_KO(self, connect):
        message = connect.recv(4096)
        
        protocol_cd = message[:5]
        protocol_data = message[6:]
        self.test.assertEqual(protocol_cd, b'ERROR')
        self.test.assertEqual(protocol_data, b'application protocol error')
        
    def run(self):
        try:
            connect = self.connect_to_server()
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect, bug=True)
            self.state_S21_KO(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")


class Test_Server_Client_S21_KO_COUNT(Test_Server_Client_S21_KO_ID):
    def __init__(self, host, port, test, number):
        Test_Server_Client_S21_KO_ID.__init__(self,host,port,test,number)
    
    def state_S21_KO(self, connect):
        message = connect.recv(4096)
        
        protocol_cd = message[:5]
        protocol_data = message[6:]
        self.test.assertEqual(protocol_cd, b'ERROR')
        self.test.assertEqual(protocol_data, b'application protocol error')
        
    def run(self):
        try:
            connect = self.connect_to_server() 
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect)
            self.state_S21_KO(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")

# -----------------------------------------------------------------------------
# Test S22


class Test_Server_Client_S22_OK(Test_Server_Client_S1_OK):
    def __init__(self, host, port, test, number, login=None, begin=None):
        Test_Server_Client_S1_OK.__init__(self,host,port,test,number)
        if login is not None:
            self.login = login
        self.begin = begin
    
    def state_S22_Begin(self, connect, bug=False):
        echallenge = self.get_echallenge(b'S22.7')
        
        ho = hashlib.sha256()
        if bug :
            ho.update(hmac_sha512(self.ms, self.ms + self.login + b'bug')) # Wrong id
        else:
            ho.update(hmac_sha512(self.ms, self.ms + self.login)) # Good id
        id = ho.digest()
        eid = self.ephecc.encrypt(id, pubkey=self.ephecc.get_pubkey())

        elogin = self.ephecc.encrypt(self.login, pubkey=self.ephecc.get_pubkey())
        
        connect.send(echallenge + b';CREATION;' + eid + b';' + elogin)
                
    def state_S22_OK(self, connect):
        message = connect.recv(4096)
        
        protocol_cd = message[:5]
        self.test.assertEqual(protocol_cd, b'OK')
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server()
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 22
            self.state_S22_Begin(connect)
            self.state_S22_OK(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")


class Test_Server_Client_S22_KO_ID(Test_Server_Client_S22_OK):
    def __init__(self, host, port, test, number, begin=None):
        Test_Server_Client_S22_OK.__init__(self,host,port,test,number)
        self.begin = begin
    
    def state_S22_KO(self, connect):
        message = connect.recv(4096)
        
        protocol_cd = message[:5]
        protocol_data = message[6:]
        self.test.assertEqual(protocol_cd, b'ERROR')
        self.test.assertEqual(protocol_data, b'application protocol error')
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server()
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 22
            self.state_S22_Begin(connect, bug=True)
            self.state_S22_KO(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")


class Test_Server_Client_S22_KO_COUNT(Test_Server_Client_S22_OK):
    def __init__(self, host, port, test, number, begin=None):
        Test_Server_Client_S22_OK.__init__(self,host,port,test,number)
        self.begin = begin
                
    def state_S22_KO(self, connect):
        message = connect.recv(4096)
        
        protocol_cd = message[:5]
        protocol_data = message[6:]
        self.test.assertEqual(protocol_cd, b'ERROR')
        self.test.assertEqual(protocol_data, b'application protocol error')
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server()
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 22
            self.state_S22_Begin(connect)
            self.state_S22_KO(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")

# -----------------------------------------------------------------------------
# Test S31


class Test_Server_Client_S31_OK_SAME_CONFIG(Test_Server_Client_S21_OK):
    def __init__(self, host, port, test, number, begin=None):
        Test_Server_Client_S21_OK.__init__(self,host,port,test,number)
        self.begin = begin
        self.curve1 = "sect571r1"
        self.cipher1 = "aes-256-cbc"
        self.curve2 = ""
        self.cipher2 = ""
        self.curve3 = ""
        self.cipher3 = ""
        
    def state_S31_Begin(self, connect):
        config = self.curve1 + ";" + self.cipher1 + ";" + \
                 self.curve2 + ";" + self.cipher2 + ";" + \
                 self.curve3 + ";" + self.cipher3
        econfig = self.ephecc.encrypt(config, pubkey=self.ephecc.get_pubkey())
        echallenge = self.get_echallenge(b'S31.6')
        connect.send(echallenge + b';CONFIGURATION;' + econfig)
        
    def state_S31_OK(self, connect, value=None):
        message = connect.recv(4096)
        protocol_cd = message[:2]
        protocol_data = message[3:]
        self.test.assertEqual(protocol_cd, b'OK')
        if value != None:
            self.test.assertEqual(protocol_data, value)
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server()
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect)
            self.state_S21_OK(connect)
            # State 31
            self.state_S31_Begin(connect)
            self.state_S31_OK(connect, b'1')
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")


class Test_Server_Client_S31_OK_NEW_CONFIG(Test_Server_Client_S31_OK_SAME_CONFIG):
    def __init__(self, host, port, test, number, begin=None):
        Test_Server_Client_S31_OK_SAME_CONFIG.__init__(self,host,port,test,number)
        self.begin = begin
        self.curve1 = "sect571r1"
        self.cipher1 = "aes-256-cbc"
        self.curve2 = "secp256k1"
        self.cipher2 = "aes-128-cbc"
        self.curve3 = ""
        self.cipher3 = ""
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server()
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect)
            self.state_S21_OK(connect)
            # State 31
            self.state_S31_Begin(connect)
            self.state_S31_OK(connect, b'2')
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")


class Test_Server_Client_S31_KO(Test_Server_Client_S31_OK_SAME_CONFIG):
    def __init__(self, host, port, test, number, begin=None):
        Test_Server_Client_S31_OK_SAME_CONFIG.__init__(self,host,port,test,number)
        self.begin = begin
        self.curve3 = "bad curve name"
        
    def state_S31_KO(self, connect):
        message = connect.recv(4096)
        protocol_cd = message[:5]
        protocol_data = message[6:]
        self.test.assertEqual(protocol_cd, b'ERROR')
        self.test.assertEqual(protocol_data, b'application protocol error')
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server() 
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect)
            self.state_S21_OK(connect)
            # State 31
            self.state_S31_Begin(connect)
            self.state_S31_KO(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")

# -----------------------------------------------------------------------------
# Test S32


class Test_Server_Client_S32_OK(Test_Server_Client_S31_OK_SAME_CONFIG):
    def __init__(self, host, port, test, number, nbsibs, begin=None):
        Test_Server_Client_S31_OK_SAME_CONFIG.__init__(self,host,port,test,number)
        self.begin = begin
        self.nbsibs = nbsibs
    
    def state_S32_Begin(self, connect):
        self.keyH = KeyHandler(self.ms, cur1=self.curve1, cip1=self.cipher1)
        echallenge = self.get_echallenge(b'S32.4')
        connect.send(echallenge + b';EXPORTATION')

    def state_S32_OK(self, connect):
        message = connect.recv(1024)
        protocol_cd = message[:2]
        self.test.assertEqual(protocol_cd, b'OK')
        
        tab_protocol_data = message[3:].split(b';', maxsplit=1)
        nbsibs = int(tab_protocol_data[0].decode())
        
        self.test.assertEqual(nbsibs, self.nbsibs)
        
        #print('nbsibs: ', nbsibs)
        #print(tab_protocol_data)
        
        if nbsibs > 0:
            if len(tab_protocol_data) == 1:
                tab_protocol_data.append("")
            while len(tab_protocol_data) <= 1:
                tab_protocol_data[1] += connect.recv(4096)
            
            tab_protocol_data = tab_protocol_data[1].split(b';', maxsplit=1)
        
        for i in range(nbsibs):
            protocol_cd = tab_protocol_data[0]
            self.test.assertEqual(protocol_cd, b'SIB')
            #print(protocol_cd)
            
            tab_protocol_data = tab_protocol_data[1].split(b';', maxsplit=1)
            index = int((tab_protocol_data[0]).decode())
            #print(index)
           
            tab_protocol_data = tab_protocol_data[1].split(b';', maxsplit=1)
            taille = int((tab_protocol_data[0]).decode())
            #print(taille)
            
            if taille > len(tab_protocol_data[1]) :
                if (len(tab_protocol_data[1]) != 0):
                    tab_protocol_data[1] += connect.recv(4096)
                else:
                    tab_protocol_data[1] = connect.recv(4096)
            
            psib = tab_protocol_data[1][:taille]
            #print(psib)
            sib = pickle.loads(psib)
            sib.control_integrity(self.keyH)
           
            protocol_data = tab_protocol_data[1][taille+1:]
            if len(protocol_data) == 0 and i != nbsibs - 1:
                protocol_data = connect.recv(4096)
            #print(protocol_data)
            if len(protocol_data) != 0:
                #print(protocol_data[0])
                if protocol_data[0] == ord(';'):
                    tab_protocol_data = protocol_data[1:].split(b';', maxsplit=1)
                else:
                    tab_protocol_data = protocol_data.split(b';', maxsplit=1)
            #print(tab_protocol_data)
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server() 
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect)
            self.state_S21_OK(connect)
            # State 31
            self.state_S31_Begin(connect)
            self.state_S31_OK(connect)
            # State 32
            self.state_S32_Begin(connect)
            self.state_S32_OK(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")

# -----------------------------------------------------------------------------
# Test S33


class Test_Server_Client_S33_OK(Test_Server_Client_S31_OK_SAME_CONFIG):
    def __init__(self, host, port, test, number, begin=None):
        Test_Server_Client_S31_OK_SAME_CONFIG.__init__(self,host,port,test,number)
        self.begin = begin
        self.login = 'This is the client login for testing S33'.encode()

    def state_S33_Begin(self, connect, bug=False):
        echallenge = self.get_echallenge(b'S33.7')
        
        ho = hashlib.sha256()
        ho.update(hmac_sha512(self.ms, self.ms + self.login)) # Good id
        id = ho.digest()
        eid = self.ephecc.encrypt(id, pubkey=self.ephecc.get_pubkey())

        elogin = self.ephecc.encrypt(self.login, pubkey=self.ephecc.get_pubkey())
        
        connect.send(echallenge + b';DELETION;' + eid + b';' + elogin)
                
    def state_S33_OK(self, connect):
        message = connect.recv(1024)
        protocol_cd = message[:5]
        self.test.assertEqual(protocol_cd, b'OK')

    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server() 
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect)
            self.state_S21_OK(connect)
            # State 31
            self.state_S31_Begin(connect)
            self.state_S31_OK(connect, b'1')
            # State 33
            self.state_S33_Begin(connect)
            self.state_S33_OK(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")

# -----------------------------------------------------------------------------
# Test S34


class Test_Server_Client_S34_OK(Test_Server_Client_S31_OK_SAME_CONFIG):
    def __init__(self, host, port, test, number, nbsibs, begin=None):
        Test_Server_Client_S31_OK_SAME_CONFIG.__init__(self,host,port,test,number)
        self.begin = begin
        self.nbsibs = nbsibs

    def state_S34_Begin(self, connect):
        pattern = "secret"
        self.keyH = KeyHandler(self.ms, cur1=self.curve1, cip1=self.cipher1)
        epattern = self.ephecc.encrypt(pattern.encode(), pubkey=self.ephecc.get_pubkey())
        echallenge = self.get_echallenge(b'S34.6')
        connect.send(echallenge + b';SEARCHDATA;' + epattern)
        
    def state_S34_OK(self, connect):
        message = connect.recv(1024)
        protocol_cd = message[:2]
        self.test.assertEqual(protocol_cd, b'OK')
        
        tab_protocol_data = message[3:].split(b';', maxsplit=1)
        nbsibs = int(tab_protocol_data[0].decode())
        
        self.test.assertEqual(nbsibs, self.nbsibs)
        
        #print('nbsibs: ', nbsibs)
        #print(tab_protocol_data)
        
        if nbsibs > 0:
            if len(tab_protocol_data) == 1:
                tab_protocol_data.append("")
            while len(tab_protocol_data) <= 1:
                tab_protocol_data[1] += connect.recv(4096)
            
            tab_protocol_data = tab_protocol_data[1].split(b';', maxsplit=1)
        
        for i in range(nbsibs):
            protocol_cd = tab_protocol_data[0]
            self.test.assertEqual(protocol_cd, b'SIB')
            #print(protocol_cd)
            
            tab_protocol_data = tab_protocol_data[1].split(b';', maxsplit=1)
            index = int((tab_protocol_data[0]).decode())
            #print(index)
           
            tab_protocol_data = tab_protocol_data[1].split(b';', maxsplit=1)
            taille = int((tab_protocol_data[0]).decode())
            #print(taille)
            
            if taille > len(tab_protocol_data[1]) :
                if (len(tab_protocol_data[1]) != 0):
                    tab_protocol_data[1] += connect.recv(4096)
                else:
                    tab_protocol_data[1] = connect.recv(4096)
            
            psib = tab_protocol_data[1][:taille]
            #print(psib)
            sib = pickle.loads(psib)
            sib.control_integrity(self.keyH)
           
            protocol_data = tab_protocol_data[1][taille+1:]
            if len(protocol_data) == 0 and i != nbsibs - 1:
                protocol_data = connect.recv(4096)
            #print(protocol_data)
            if len(protocol_data) != 0:
                #print(protocol_data[0])
                if protocol_data[0] == ord(';'):
                    tab_protocol_data = protocol_data[1:].split(b';', maxsplit=1)
                else:
                    tab_protocol_data = protocol_data.split(b';', maxsplit=1)
            #print(tab_protocol_data)
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server() 
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect)
            self.state_S21_OK(connect)
            # State 31
            self.state_S31_Begin(connect)
            self.state_S31_OK(connect)
            # State 35
            self.state_S34_Begin(connect)
            self.state_S34_OK(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")


class Test_Server_Client_S34_OK_NEW_CONFIG(Test_Server_Client_S31_OK_NEW_CONFIG):
    def __init__(self, host, port, test, number, nbsibs, begin=None):
        Test_Server_Client_S31_OK_NEW_CONFIG.__init__(self,host,port,test,number)
        self.begin = begin
        self.nbsibs = nbsibs

    def state_S34_Begin(self, connect):
        pattern = "secret"
        self.keyH = KeyHandler(self.ms, cur1=self.curve1, cip1=self.cipher1, \
                                        cur2=self.curve2, cip2=self.cipher2)
        epattern = self.ephecc.encrypt(pattern.encode(), pubkey=self.ephecc.get_pubkey())
        echallenge = self.get_echallenge(b'S34.6')
        connect.send(echallenge + b';SEARCHDATA;' + epattern)
        
    def state_S34_OK(self, connect):
        message = connect.recv(1024)
        protocol_cd = message[:2]
        self.test.assertEqual(protocol_cd, b'OK')
        
        tab_protocol_data = message[3:].split(b';', maxsplit=1)
        nbsibs = int(tab_protocol_data[0].decode())
        
        self.test.assertEqual(nbsibs, self.nbsibs)
        
        #print('nbsibs: ', nbsibs)
        #print(tab_protocol_data)
        
        if nbsibs > 0:
            if len(tab_protocol_data) == 1:
                tab_protocol_data.append("")
            while len(tab_protocol_data) <= 1:
                tab_protocol_data[1] += connect.recv(4096)
            
            tab_protocol_data = tab_protocol_data[1].split(b';', maxsplit=1)
        
        for i in range(nbsibs):
            protocol_cd = tab_protocol_data[0]
            self.test.assertEqual(protocol_cd, b'SIB')
            #print(protocol_cd)
            
            tab_protocol_data = tab_protocol_data[1].split(b';', maxsplit=1)
            index = int((tab_protocol_data[0]).decode())
            #print(index)
           
            tab_protocol_data = tab_protocol_data[1].split(b';', maxsplit=1)
            taille = int((tab_protocol_data[0]).decode())
            #print(taille)
            
            if taille > len(tab_protocol_data[1]) :
                if (len(tab_protocol_data[1]) != 0):
                    tab_protocol_data[1] += connect.recv(4096)
                else:
                    tab_protocol_data[1] = connect.recv(4096)
            
            psib = tab_protocol_data[1][:taille]
            #print(psib)
            sib = pickle.loads(psib)
            sib.control_integrity(self.keyH)
           
            protocol_data = tab_protocol_data[1][taille+1:]
            if len(protocol_data) == 0 and i != nbsibs - 1:
                protocol_data = connect.recv(4096)
            #print(protocol_data)
            if len(protocol_data) != 0:
                #print(protocol_data[0])
                if protocol_data[0] == ord(';'):
                    tab_protocol_data = protocol_data[1:].split(b';', maxsplit=1)
                else:
                    tab_protocol_data = protocol_data.split(b';', maxsplit=1)
            #print(tab_protocol_data)
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server() 
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect)
            self.state_S21_OK(connect)
            # State 31
            self.state_S31_Begin(connect)
            self.state_S31_OK(connect)
            # State 34
            self.state_S34_Begin(connect)
            self.state_S34_OK(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")
            print("Use Ctrl+c to finish the test")

# -----------------------------------------------------------------------------
# Test S35


class Test_Server_Client_S35_OK_1(Test_Server_Client_S31_OK_SAME_CONFIG):
    def __init__(self, host, port, test, number, begin=None):
        Test_Server_Client_S31_OK_SAME_CONFIG.__init__(self,host,port,test,number)
        self.begin = begin
        
    def state_S35_Begin(self, connect, bug=False):
        
        if bug :
            self.keyH = KeyHandler(self.ms, cur1=self.curve1, cip1='rc4')
        else:
            self.keyH = KeyHandler(self.ms, cur1=self.curve1, cip1=self.cipher1)
        sib = SecretInfoBlock(self.keyH)
        sib['info1'] = "secret information"
        
        echallenge = self.get_echallenge(b'S35.6')
        connect.send(echallenge + b';ADDDATA;' + pickle.dumps(sib))
        
    def state_S35_OK(self, connect):
        message = connect.recv(4096)
        protocol_cd = message[:2]
        self.test.assertEqual(protocol_cd, b'OK')
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server() 
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect)
            self.state_S21_OK(connect)
            # State 31
            self.state_S31_Begin(connect)
            self.state_S31_OK(connect, b'1')
            # State 36
            self.state_S35_Begin(connect)
            self.state_S35_OK(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")


class Test_Server_Client_S35_OK_2(Test_Server_Client_S31_OK_SAME_CONFIG):
    def __init__(self, host, port, test, number, begin=None):
        Test_Server_Client_S31_OK_SAME_CONFIG.__init__(self,host,port,test,number)
        self.begin = begin
        
    def state_S35_Begin(self, connect, bug=False):
        
        if bug :
            self.keyH = KeyHandler(self.ms, cur1=self.curve1, cip1='rc4')
        else:
            self.keyH = KeyHandler(self.ms, cur1=self.curve1, cip1=self.cipher1)
        sib = SecretInfoBlock(self.keyH)
        sib.nbInfo = 5
        sib['info1'] = "Gmail Account"
        sib['info2'] = "login"
        sib['info3'] = "login@gmail.com"
        sib['info4'] = "password"
        sib['info5'] = "secret information"
        
        echallenge = self.get_echallenge(b'S35.6')
        connect.send(echallenge + b';ADDDATA;' + pickle.dumps(sib))
        
    def state_S35_OK(self, connect):
        message = connect.recv(4096)
        protocol_cd = message[:2]
        self.test.assertEqual(protocol_cd, b'OK')
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server()
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect)
            self.state_S21_OK(connect)
            # State 31
            self.state_S31_Begin(connect)
            self.state_S31_OK(connect, b'1')
            # State 36
            self.state_S35_Begin(connect)
            self.state_S35_OK(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")


class Test_Server_Client_S35_KO(Test_Server_Client_S35_OK_1):
    def __init__(self, host, port, test, number, begin=None):
        Test_Server_Client_S35_OK_1.__init__(self,host,port,test,number)
        self.begin = begin
    
    def state_S35_KO(self, connect):
        message = connect.recv(4096)
        protocol_cd = message[:5]
        protocol_data = message[6:]
        self.test.assertEqual(protocol_cd, b'ERROR')
        self.test.assertEqual(protocol_data, b'application protocol error')
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server()
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect)
            self.state_S21_OK(connect)
            # State 31
            self.state_S31_Begin(connect)
            self.state_S31_OK(connect, b'1')
            # State 35
            self.state_S35_Begin(connect, bug=True)
            self.state_S35_KO(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")


class Test_Server_Client_S35_OK_NEW_CONFIG(Test_Server_Client_S31_OK_NEW_CONFIG):
    def __init__(self, host, port, test, number, begin=None):
        Test_Server_Client_S31_OK_NEW_CONFIG.__init__(self,host,port,test,number)
        self.begin = begin

    def state_S35_Begin(self, connect):
        self.keyH = KeyHandler(self.ms, cur1=self.curve1, cip1=self.cipher1, \
                                        cur2=self.curve2, cip2=self.cipher2)
        sib = SecretInfoBlock(self.keyH)
        sib['info1'] = "secret information"
        
        echallenge = self.get_echallenge(b'S35.6')
        connect.send(echallenge + b';ADDDATA;' + pickle.dumps(sib))
        
    def state_S35_OK(self, connect):
        message = connect.recv(4096)
        protocol_cd = message[:2]
        self.test.assertEqual(protocol_cd, b'OK')
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server()
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect)
            self.state_S21_OK(connect)
            # State 31
            self.state_S31_Begin(connect)
            self.state_S31_OK(connect, b'1')
            # State 35
            self.state_S35_Begin(connect)
            self.state_S35_OK(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")

# -----------------------------------------------------------------------------
# Test S36


class Test_Server_Client_S36_OK(Test_Server_Client_S31_OK_SAME_CONFIG):
    def __init__(self, host, port, test, number, begin=None):
        Test_Server_Client_S31_OK_SAME_CONFIG.__init__(self,host,port,test,number)
        self.begin = begin

    def state_S36_Begin(self, connect, bug=False):
        echallenge = self.get_echallenge(b'S36.4')
        if bug == 1:
            connect.send(echallenge + b';DELETEDATA;' + b'1000')
        elif bug == 2:
            connect.send(echallenge + b';DELETEDATA;' + b'badindex')
        elif bug == False:
            connect.send(echallenge + b';DELETEDATA;' + b'1')
        
    def state_S36_OK(self, connect):
        message = connect.recv(1024)
        protocol_cd = message[:2]
        self.test.assertEqual(protocol_cd, b'OK')
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server() 
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect)
            self.state_S21_OK(connect)
            # State 31
            self.state_S31_Begin(connect)
            self.state_S31_OK(connect, b'1')
            # State 36
            self.state_S36_Begin(connect)
            self.state_S36_OK(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")


class Test_Server_Client_S36_KO_1(Test_Server_Client_S36_OK):
    def __init__(self, host, port, test, number, begin=None):
        Test_Server_Client_S36_OK.__init__(self,host,port,test,number)
        self.begin = begin
        
    def state_S36_KO(self, connect):
        message = connect.recv(1024)
        protocol_cd = message[:5]
        self.test.assertEqual(protocol_cd, b'ERROR')
        protocol_data = message[6:]
        self.test.assertEqual(protocol_data, b'application protocol error')
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server() 
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect)
            self.state_S21_OK(connect)
            # State 31
            self.state_S31_Begin(connect)
            self.state_S31_OK(connect, b'1')
            # State 36
            self.state_S36_Begin(connect, bug=1)
            self.state_S36_KO(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")


class Test_Server_Client_S36_KO_2(Test_Server_Client_S36_KO_1):
    def __init__(self, host, port, test, number, begin=None):
        Test_Server_Client_S36_KO_1.__init__(self,host,port,test,number)
        self.begin = begin
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server() 
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect)
            self.state_S21_OK(connect)
            # State 31
            self.state_S31_Begin(connect)
            self.state_S31_OK(connect, b'1')
            # State 36
            self.state_S36_Begin(connect, bug=2)
            self.state_S36_KO(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")

# -----------------------------------------------------------------------------
# Test S37


class Test_Server_Client_S37_OK(Test_Server_Client_S31_OK_SAME_CONFIG):
    def __init__(self, host, port, test, number, begin=None):
        Test_Server_Client_S31_OK_SAME_CONFIG.__init__(self,host,port,test,number)
        self.begin = begin

    def state_S37_Begin(self, connect, bug=False):
        self.keyH = KeyHandler(self.ms, cur1=self.curve1, cip1=self.cipher1)
        sib = SecretInfoBlock(self.keyH)
        sib.nbInfo = 5
        sib['info1'] = "Gmail Account"
        sib['info2'] = "login"
        sib['info3'] = "login@gmail.com"
        sib['info4'] = "password"
        sib['info5'] = "my secret information"
        
        echallenge = self.get_echallenge(b'S37.5')
        if bug == 1:
            connect.send(echallenge + b';UPDATEDATA;' + b'1000;' + pickle.dumps(sib))
        elif bug == 2:
            connect.send(echallenge + b';UPDATEDATA;' + b'badindex;' + pickle.dumps(sib))
        elif bug == False:
            connect.send(echallenge + b';UPDATEDATA;' + b'2;' + pickle.dumps(sib))
        
    def state_S37_OK(self, connect):
        message = connect.recv(1024)
        protocol_cd = message[:2]
        self.test.assertEqual(protocol_cd, b'OK')
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server() 
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect)
            self.state_S21_OK(connect)
            # State 31
            self.state_S31_Begin(connect)
            self.state_S31_OK(connect, b'1')
            # State 37
            self.state_S37_Begin(connect)
            self.state_S37_OK(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")


class Test_Server_Client_S37_KO_1(Test_Server_Client_S37_OK):
    def __init__(self, host, port, test, number, begin=None):
        Test_Server_Client_S37_OK.__init__(self,host,port,test,number)
        self.begin = begin
        
    def state_S37_KO(self, connect):
        message = connect.recv(1024)
        protocol_cd = message[:5]
        self.test.assertEqual(protocol_cd, b'ERROR')
        protocol_data = message[6:]
        self.test.assertEqual(protocol_data, b'application protocol error')
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server() 
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect)
            self.state_S21_OK(connect)
            # State 31
            self.state_S31_Begin(connect)
            self.state_S31_OK(connect, b'1')
            # State 37
            self.state_S37_Begin(connect, bug=1)
            self.state_S37_KO(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")


class Test_Server_Client_S37_KO_2(Test_Server_Client_S37_KO_1):
    def __init__(self, host, port, test, number, begin=None):
        Test_Server_Client_S37_KO_1.__init__(self,host,port,test,number)
        self.begin = begin
        
    def run(self):
        try:
            time.sleep(self.begin) # Waiting previous test
            connect = self.connect_to_server() 
            # State 0
            self.state_S0(connect)
            # State 1S
            self.state_S1S_begin(connect)
            self.state_S1S_end(connect)
            # State 1C
            self.state_S1C_begin(connect)
            self.state_S1C_end(connect)
            # State 21
            self.state_S21_Begin(connect)
            self.state_S21_OK(connect)
            # State 31
            self.state_S31_Begin(connect)
            self.state_S31_OK(connect, b'1')
            # State 37
            self.state_S37_Begin(connect, bug=2)
            self.state_S37_KO(connect)
        finally:
            connect.close()
            print("Client", self.number, self.sockname, ": disconnection with the server")

# -----------------------------------------------------------------------------


class Test_ServerTestCase(unittest.TestCase):
    
    def setUp(self):
        self.path = 'mnemopwd/test/data'
        for child in Path(self.path).iterdir():
            if Path(child).suffix == '.db':
                Path(child).unlink()

    def test_Server(self):
        Test_Server_Client_S0(Configuration.host, Configuration.port, self, 1).start()
        Test_Server_Client_S1_OK(Configuration.host, Configuration.port, self, 2).start()
        Test_Server_Client_S1_KO(Configuration.host, Configuration.port, self, 3).start()
        Test_Server_Client_S21_KO_ID(Configuration.host, Configuration.port, self, 4).start()
        Test_Server_Client_S21_KO_COUNT(Configuration.host, Configuration.port, self, 5).start()
        
        # Begin after 2 secondes
        Test_Server_Client_S22_OK(Configuration.host, Configuration.port, self, 6, begin=2).start()
        login = 'This is the client login for testing S33'.encode()
        Test_Server_Client_S22_OK(Configuration.host, Configuration.port, self, 6, login=login, begin=2).start()
        
        # Begin after 3 secondes
        Test_Server_Client_S22_KO_ID(Configuration.host, Configuration.port, self, 7, 3).start()
        Test_Server_Client_S22_KO_COUNT(Configuration.host, Configuration.port, self, 8, 3).start()
        Test_Server_Client_S21_OK(Configuration.host, Configuration.port, self, 9, 3).start()
        
        # Begin after 4 secondes
        Test_Server_Client_S31_OK_SAME_CONFIG(Configuration.host, Configuration.port, self, 10, 4).start()
        Test_Server_Client_S31_OK_SAME_CONFIG(Configuration.host, Configuration.port, self, 11, 4).start()
        Test_Server_Client_S31_KO(Configuration.host, Configuration.port, self, 12, 4).start()
        Test_Server_Client_S35_OK_1(Configuration.host, Configuration.port, self, 13, 4).start()
        Test_Server_Client_S35_OK_2(Configuration.host, Configuration.port, self, 14, 4).start()
        Test_Server_Client_S35_KO(Configuration.host, Configuration.port, self, 15, 4).start()
        
        # Begin after 6 secondes
        Test_Server_Client_S34_OK(Configuration.host, Configuration.port, self, 16, 2, 6).start()
        Test_Server_Client_S37_OK(Configuration.host, Configuration.port, self, 17, 6).start()
        Test_Server_Client_S37_KO_1(Configuration.host, Configuration.port, self, 18, 6).start()
        Test_Server_Client_S37_KO_2(Configuration.host, Configuration.port, self, 19, 6).start()
        
        # Begin after 7 secondes
        Test_Server_Client_S36_OK(Configuration.host, Configuration.port, self, 20, 7).start()
        Test_Server_Client_S36_KO_1(Configuration.host, Configuration.port, self, 21, 7).start()
        Test_Server_Client_S36_KO_2(Configuration.host, Configuration.port, self, 22, 7).start()
        
        # Begin after 8 secondes
        Test_Server_Client_S33_OK(Configuration.host, Configuration.port, self, 23, 8).start()
        Test_Server_Client_S34_OK(Configuration.host, Configuration.port, self, 24, 1, 8).start()
        
        # Begin after 9 secondes
        Test_Server_Client_S35_OK_1(Configuration.host, Configuration.port, self, 25, 9).start()
        Test_Server_Client_S35_OK_2(Configuration.host, Configuration.port, self, 26, 9).start()
        
        # Begin after 11 secondes
        Test_Server_Client_S34_OK(Configuration.host, Configuration.port, self, 27, 3, 11).start()
        Test_Server_Client_S32_OK(Configuration.host, Configuration.port, self, 28, 3, 11).start()
        
        # Begin after 12 secondes
        Test_Server_Client_S31_OK_NEW_CONFIG(Configuration.host, Configuration.port, self, 29, 12).start()
        
        # Begin after 13 secondes
        Test_Server_Client_S35_OK_NEW_CONFIG(Configuration.host, Configuration.port, self, 30, 13).start()
        
        # Begin after 14 secondes
        Test_Server_Client_S34_OK_NEW_CONFIG(Configuration.host, Configuration.port, self, 31, 4, 14).start()

        try:
            Configuration.dbpath = self.path
            Configuration.search_mode = 'all'
            Configuration.loglevel = 'DEBUG'
            Configuration.logfile = self.path + '/mnemopwds.log'
            Server().start()
        except KeyboardInterrupt:
            pass
        
if __name__ == '__main__':
    unittest.main()
