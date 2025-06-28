#! usr/bin/env python2

import os
import sys
import math
import socket
import base64
import binascii
import json
import distress_cmsg
import distress_receipt
import time
import threading

# REQUIRES PyCrypto 2.6 or later
# PyCrypto can be found at https://www.dlitz.net/software/pycrypto/
from Crypto.Cipher import AES
from Crypto.Hash import SHA384
from Crypto.Random import random

DEBUG = False
BLOCK_SIZE = 16  # Size of AES block cipher
CHUNK_SIZE = 1024 # Size of chunk we read from file and store on DISTRESS

def random_key():
    """ Generates a random Key for encrypting the file. This key is used only
    if not overridden by the `--key' parameter of the command.
    """
    return os.urandom( 32 ) # AES-256, requires 32 byte key.

def encrypt_file(socket, library, filename, key,
                 expires="infinity", removable=False, cmd=False):
    """
    Encrypts the file using key.
    """
    # 1) Chunk up the file into equal sized blocks
    if cmd: print "Breaking file into chunks..."
    blocks = __chunk(filename)

    # 2) Generate random salts for encryption, these will need to be stored
    salts = [os.urandom(BLOCK_SIZE) for _ in blocks]

    # 3) Encrypt each block using the key and masks
    if cmd: print "Encrypting all",len(blocks),"chunks..."
    encrypted_blocks = [__encrypt(b,s,key) for b,s in zip(blocks,salts)]

    # 4) Get the Hash of each block, and shuffle them.
    plaintext_hashes = [__SHA384(b) for b in blocks]
    plaintext_hashes_shuffled = list( plaintext_hashes ) #make copy.
    random.shuffle( plaintext_hashes_shuffled )

    # 4b) At this point we consolidate the encrypted blocks if there are
    #     duplicate plaintext hashes. This is rare!
    packet,pure_spth,pure_salts = __purify( plaintext_hashes,
                                            plaintext_hashes_shuffled,
                                            encrypted_blocks,
                                            salts )
    if cmd and len(packet)<len(blocks): print "Compressing duplicate blocks..."

    # 5) Send the encrypted blocks with a random plaintext hash as it's key.
    oid = __send_add(socket, packet, expires, removable, cmd)

    # 6) Using the returned Owner ID, save the hashes and key in a Receipt.
    #    The shuffled hashes still designate order of the encrypted blocks on
    #    our side.
    if cmd: print "Saving Receipt to local disk..."
    return library.make_receipt( filename, pure_spth, pure_salts, oid, key )


def __purify(pths, spths, blocks, salts):
    """
    Returns the packet to send to DISTRESS and an updated list of salts which
    overrides the duplicate values. This does two things, it first reduces the
    number of blocks stored on the network, but it also makes sure the salts
    are aligned with the shuffled location.
    """
    seen,packet,nl = {}, [], []
    keyvals = zip(spths,blocks)
    for pth,kv,spth,s in zip(pths,keyvals,spths,salts):
        if not pth in seen:
            seen[pth] = (spth,s)
            packet.append( kv )
        nl.append( seen[pth] )
    ph,ps=list(zip(*nl))
    return packet,ph,ps


def __chunk(file_path):
    """
    Returns a list of chunks, XX-bit lengths of the file.
    """
    filesize = os.path.getsize(file_path)

    # Ensure the proper number of chunks regardless of Python version
    num_chunks = math.ceil(filesize / float(CHUNK_SIZE))
    num_chunks = int(num_chunks)

    object_file = open(file_path, 'rb')
    chunks = []
    for i in range(num_chunks):
        chunks.append(object_file.read(CHUNK_SIZE))

    return chunks


def __SHA384(object):
    """
    Computes the hash of object. Uses crytographically secure
    SHA384 from PyCrypto.
    """
    object_hash = SHA384.new()
    object_hash.update(object)
    return object_hash.hexdigest()

def __pad(s,check=False):
    """ Pad the chunks and keys to a multiple of the block size. """
    l=len(s)
    if check and l>0 and l%BLOCK_SIZE==0: return s
    x = BLOCK_SIZE-l%BLOCK_SIZE
    return s+x*chr(x)

def __encrypt(block, salt, key):
    """
    Encrypts the block using AES scheme and key.
    """
    enc = AES.new(__pad(key,True), AES.MODE_OFB, salt) # initialize OFB with salt.
    return base64.b64encode( enc.encrypt( __pad( block ) ) )

def __decrypt(block, salt, key):
    """
    Decrypts the block using AES scheme and key.
    """
    unpad = lambda s:s[0:-ord(s[-1])]
    decr = AES.new( __pad(key,True), AES.MODE_OFB, salt ) # initialize OFB with salt.
    return unpad( decr.decrypt( base64.b64decode( block ) ) )


def __send_add(socket, packet, expires, removable, cmd=False):
    """
    Send the encrypted hashes with their respective blocks to the
    network, and returns the OID that provides proof of ownership.
    """
    global CHUNK_SIZE
    num_blocks = len(packet)

    # Send notification of block adds.
    add_message = distress_cmsg.add(num_blocks, expires, removable)
    socket.send(add_message.encode())

    # Grab the OID we get from the server
    response = distress_cmsg.decode(__recvall(socket))
    assert(response['msg'] == 'ack')
    oid = response['oid'] if removable else None

    # send the key/value pairs for each chunk
    socket.setblocking( 1 )
    i=24
    if cmd: sys.stdout.write("Sending blocks to server")
    for key,block in packet:
        send_message = distress_cmsg.addblock(key,block)
        while len(send_message) > 0:
            b = socket.send( send_message )
            send_message = send_message[b:]
            time.sleep( 0.2 )
        if cmd:
            sys.stdout.write('.');sys.stdout.flush()
            i=i+1 if i<79 else 0 # dot it over to 80 chars, then newline.
            if i == 0 : print ""
    if cmd: print ""

    return oid

def __recvall(socket, timeout=5.0):
    """ Socket wrapper to receive an entire message from DISTRESS. """
    socket.setblocking(0)
    total,data,begin=[],'',time.time()
    while 1:
        if total and time.time()-begin>timeout: break
        elif time.time()-begin>timeout*2: break
        try:
            data=socket.recv(512)
            if data:
                total.append(data)
                begin=time.time()
            else: time.sleep(0.1)
        except: pass
    return ''.join(total)


def recieve(socket, receipt, file_location, override_missing=False):
    """
    Fetches and writes the file described in receipt. File file_location
    will be download_directory, and the file will be decrypted if possible.
    receive() will return True if it is decypted, otherwise False.
    """
    # Get each of the chunks, depending on hash order
    # Decrypt then append each to the file in download_directory

    # Gets the key and tests if the file is readable
    key = receipt.get_key()
    read_access = (key != None)

    hashes = receipt.get_hashs()
    salts = receipt.get_salts()

    def wait_for_blocks():
        """ Thread waiting for reply blocks from Server! This will then add
        them to the output file in order.
        """
        def __decode_attempt( bufferblock ):
            """ Read through the buffered block and check if there is a full
                message. If so then decode it and return the leftover buffer,
                otherwise just return the old buffer.
            """
            res = bufferblock.split('}') #BAD: ASSUMES JSON
            newbuffer = res.pop(-1)
            #MORE BAD: CLEANS UP AFTER SPLIT DELIM DELETION
            msgs = map(lambda m:distress_cmsg.decode(m+"}"), res)
            if DEBUG: print "MSGS:",msgs
            return (msgs, newbuffer)

        if DEBUG: print "Builder Thread Started"
        buff = {}   # The buffer of blocks we haven't gotten to yet.
        missed = [] # The list of blocks with missing values.
        buffblock = '' # The raw data from the socket.
        with open(file_location,'wb') as out_file:
            i = 0
            maxsize = len(hashes)
            cur_hash = hashes[i]
            while True:
                # Check if the current block key is in the buffer.
                if cur_hash in buff:
                    value = buff.pop(cur_hash)
                    # If so, grab it, decrypt it if possible, and output it to
                    # our file. We'll then update which key we want.
                    if read_access: value = __decrypt(value, salts[i], key)
                    out_file.write(value)

                    # If we are out of keys, then leave the loop
                    i+=1
                    if i >= maxsize: break
                    cur_hash = hashes[i]
                    continue

                # Check if we are in the missing block list, if so, skip it.
                elif cur_hash in missed:
                    i+=1
                    if i >= maxsize: break
                    cur_hash = hashes[i]
                    continue

                # Since we haven't seen our block yet, we need to check the
                # socket. We'll read everything off the socket and store in the
                # in-memory buffer.
                if i+len(missed) >= maxsize: continue # we already have the block
                buffblock += socket.recv(4096) # recommended TCP buffer size.
                (msgs, buffblock) = __decode_attempt(buffblock)

                # If the buffer contains at least one block, we'll work on it.
                for msg in msgs:
                    value,hashkey = msg['val'],msg['key']
                    if value == 'missing':
                        if override_missing:
                            missed.append( hashkey )
                            print "A Chunk of this object wasn't found in DISTRESS!"
                        else: raise Exception('The chunk was not in the network!')
                    else: # Add value to buffer.
                        buff[hashkey] = value
        if DEBUG: print "Builder Thread Finished"

    def send_all_blocks():
        """ Thread sending all blocks to the server using the same socket as
            it will recv from, but since they are non-blocking it is able to
            swap between both fairly quickly.
        """
        if DEBUG: print "Send Thread started"
        for current_key in hashes:
            socket.send( distress_cmsg.getblock(current_key) )
        if DEBUG: print "Send Thread finished"

    sender = threading.Thread(target=send_all_blocks)
    builder = threading.Thread(target=wait_for_blocks)
    try:
        sender.start()
        builder.start()
    finally: # Wait for both to finish for confirmation.
        sender.join()
        builder.join()
    return read_access

def __test_recieve():
    # This is to test the recieve function. You can edit the particular
    # OID, hashes, and keys depending on what files you've put into the
    # network.
    test_receipt = distress_receipt.Receipts('93aab4f6-1e51-4719-93eb-64f727da451b',
                        'abcdefghijklmnop',
                        ['a23e6fffd0a22e288aafa3dfe7deafe53ff8ff533b456e74f539fbfbf4f222d8d9c6ebb9d88fbca6d6e5fa612eb62bf1'],
                        None)
    download_directory = '/'
    sock = socket.socket()
    sock.connect(('127.0.0.1', 65501))
    recieve(sock, test_receipt, download_directory)

def delete_file(socket, receipt):
    """ Delete all the chunks of the file in receipt, using oid
        as the delte key.
    """
    try:
        assert(receipt.get_oid())
        for block_hash in receipt.get_hashs():
            delete_msg = distress_cmsg.delblock(receipt.get_oid(), block_hash)
            socket.send(delete_msg) #LATER: Consider ping back on success?
    except: return False
    return True

def verify_receipt(receipt, file_path):
    """ Verifies that a particular receipt is for the
        specified file.
    """
    # Right now does a simple check that the file chunks are in receipt
    # If receipt is a superset of the file, this will still return true
    hashes = receipt.get_hashs()
    file_chunks = __chunk(file_path)

    # If a chunk isn't in the hash list, it's not the right receipt
    for chunk in file_chunks:
        if __SHA384(chunk) not in hashes:
            return False

    # All chunks are in the hash receipt
    return True

