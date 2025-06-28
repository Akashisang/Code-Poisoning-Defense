# -*- coding: utf-8 -*-
from Crypto.Cipher import AES
from shaGeneration import *
from tools import *
from itertools import chain
import pdb
#pdb.set_trace()
from os import remove
import pickle
import time
from twisted.internet import reactor, task
from twisted.python import log
from kademlia.network import Server
import bz2
import config


def sendChunks(result, i, server, encrypedHashes):

  if debug == 'normal': print '    Setting slice #' + str(i)

  # Out of bound, stop reactor and leave
  if i == len(encrypedHashes) :
    reactor.stop()
    if debug != 'none': print '\n    File sent on network !'
    if debug != 'none': print '    Note that if you delete your .hashes file and your initial file, it will be forever lost in the cyphernetic ether...'
    if debug != 'none': print '    '+ str(config.totalLoss) + ' packets were lost during the transfer, but it\'s been successfully resent.'

    return

  # Get file i
  fn1 = encrypedHashes[i]
  fc = open(('scrambled/' + fn1), 'rb')
  scrambledData = fc.read()
  fc.close()

  remove('scrambled/' + fn1)

  # Increment i for next call
  i += 1

  # Set hash(encChunk), encChunk on NW. Call back here !
  server.set(fn1, scrambledData).addCallback(sendChunks, i, server, encrypedHashes)



def splitChunks(initFile, shas, encrypedHashes):

    # Determine size to rechunk. (Twisted UDP Limit + headers) Max around 4020
    maxSize = 8100
    firstElt = ('scrambled/' + str(encrypedHashes[0]))
    fc = open(firstElt, 'rb')
    scrambledData = fc.read()
    fc.close()

    # Compute Resizing factor
    rechunckFactor = len(scrambledData)/maxSize
    #if(len(scrambledData)%maxSize):
    #  rechunckFactor+=1
    if debug != 'none': print '    Splitting chunks in smaller slices.'
    if debug != 'none': print '    Resizing Factor >> ' + str(rechunckFactor)

    splitedHashes= []


    # Loop on all chunks # Should be encrypedHashes
    for i in range(0, len(encrypedHashes)):

      # Read content of the file
      inputFile = 'scrambled/' + str(encrypedHashes[i])
      f = open(inputFile, 'rb')
      data = f.read() # read the entire content of the file
      f.close()

      # Compute new hashes, and save on new list
      newHashes = listShas(inputFile, maxSize)
      splitedHashes.append(newHashes)

      remove(inputFile)


      # Loop on all sub-chunks and save
      for j in range(0, len(scrambledData), maxSize):
        chunkNumer = j/maxSize
        subChunk = data[j:j+maxSize]

        # empty chunk
        if (len(subChunk) == 0): break

        newChunk = 'scrambled/' + str(newHashes[chunkNumer])
        fc = open(newChunk, 'wb')
        fc.write(subChunk)
        fc.close()



    # Saving the objects: initial hashes, encrypted Hashes and splited hashes
    with open(initFile + '.hashes', 'wb') as f:
      pickle.dump([shas, encrypedHashes, splitedHashes], f)

    if debug != 'none': print '    Sending slices on network'
    # Return 1 dimension list to send on DHT
    return list(chain(*splitedHashes))




def maidSafeEncryptSetDebug(inputFile, chunkSize, server, debu, iterations=1000, xor=False, i=0):
    global debug
    debug = debu
    maidSafeEncrypt(inputFile, chunkSize, server, iterations=1000, xor=False, i=0)



def maidSafeEncrypt(inputFile, chunkSize, server, iterations=1000, xor=False, i=0):


    # List and save all shas
    if debug != 'none': print '    Computing Shas...'
    shas = listShas(inputFile, chunkSize)

    # Read the contents of the file
    f = open(inputFile, 'rb')
    data = f.read() # read the entire content of the file
    f.close()

    # Save filename and hash
    fileHash = hashlib.sha512(data).hexdigest()

    # Get the length of data, ie size of the input file in bytes
    bytes = len(data)

    # Calculate the number of chunks to be created
    noOfChunks= bytes/chunkSize
    if(bytes%chunkSize):
      noOfChunks+=1

    #widgets = ['Something: ', Percentage(), ' ', Bar(marker=RotatingMarker()),' ', ETA]
    #if(debug != 'none'): pbar = ProgressBar(widgets=widgets, maxval=noOfChunks)


    # Init Encripted hashes list
    encrypedHashes = []

    if debug != 'none': print '    Cipherin\''

    # Scan all chunks
    for i in range(0, bytes, chunkSize):


      # Get data and create chunk #
      chunkNumer = i/chunkSize
      dataToHash = data[i:i+ chunkSize]

      #if(debug != 'none'): pbar.update(chunkNumer)

      # Prevent creation of 0 bit file is filezise is multiple of 2^n
      if(len(dataToHash) == 0):
        continue


      # Pick right hash...
      if(chunkNumer == 0):
        shaOne = shas[noOfChunks-1]
        shaTwo = shas[noOfChunks-2]
        shaThree = shas[chunkNumer]
      elif(chunkNumer == 1):
        shaOne = shas[noOfChunks-1]
        shaTwo = shas[chunkNumer-1]
        shaThree = shas[chunkNumer]
      else:
        shaOne = shas[chunkNumer-2]
        shaTwo = shas[chunkNumer-1]
        shaThree = shas[chunkNumer]



      # Need massive key deriv to xor out of AES
      if xor : keyDerivOut = keyDeriv(shaOne, shaTwo, shaThree, len(dataToHash), iterations)
      else : keyDerivOut = keyDeriv(shaOne, shaTwo, shaThree, 48, iterations)

      # Encrypt
      cipher = AES.new(keyDerivOut[:64].decode('hex'), AES.MODE_CFB, keyDerivOut[64:(64+32)].decode('hex'))
      outCipher = cipher.encrypt(dataToHash)

      # Quick sanity check
      if debug == 'normal': print '    Cipherin\''

      # Xor outCipher and pbkdfOut
      if xor : scrambledChunck = strxor(outCipher.decode("hex"),keyDerivOut.decode("hex"))
      else : scrambledChunck = outCipher


      # Compute hash of encrypted datas
      fn1 = hashlib.sha512(scrambledChunck).hexdigest()
      encrypedHashes.append(fn1)


      fc = open(('scrambled/' + fn1), 'wb')
      fc.write(scrambledChunck)
      fc.close()


    #if(debug != 'none'): pbar.finish()
    # Rector chunks into smaller chunks, swallowable by kademlia
    chunckToSend = splitChunks(inputFile, shas, encrypedHashes)


    # Send chunks on DHT
    sendChunks(0, 0, server, chunckToSend)
