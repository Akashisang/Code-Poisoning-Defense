# -*- coding: utf-8 -*-
from Crypto.Cipher import AES
from shaGeneration import *
from tools import *
import pickle
from os import remove
import pdb
#pdb.set_trace()

from twisted.internet import reactor, task
from twisted.python import log
from kademlia.network import Server



def grepChunks(result, i, j, server, splitedHashes, encrypedHashes, inputHash, chunkSize):

  #pdb.set_trace()

  # Write result from previous query
  fn1 = encrypedHashes[i]

  # TODO : Check if not none


  if debug == 'normal': print '    Getting (i,j) > ' + str(i) + ', ' + str(j)

  # Create new file if new chunk. Append otherwise.
  if (j == 0):
    fc = open(('scrambled/' + fn1), 'wb')
    fc.write(result)
    fc.close()
  else:
    fc = open(('scrambled/' + fn1), 'ab')
    fc.write(result)
    fc.close()


  # Increment for next query
  if( (len(splitedHashes[i])-1) != j ):
    j += 1
  else:
    i += 1
    j = 0

  # Got all the chunks, return back to decryption scheme
  if i == len(encrypedHashes) :
    reactor.stop()
    if debug != 'none': print '    Chunks downloaded from DHT!'
    if debug != 'none': print '    Decrypting...'
    maidSafeDecrypt(inputHash, chunkSize, server, grepNotDone=False)
    return

  # Get the next chunk
  fn1 = splitedHashes[i][j]
  server.get(fn1).addCallback(grepChunks, i, j, server, splitedHashes, encrypedHashes, inputHash, chunkSize)


def maidSafeDecryptSetDebug(inputHash, chunkSize, server, debu, grepNotDone=True, iterations=1000, xor=False):
    global debug
    debug = debu

    if debug != 'none': print '    Downloading chunks from DHT...'
    maidSafeDecrypt(inputHash, chunkSize, server, grepNotDone=True, iterations=1000, xor=False)


def maidSafeDecrypt(inputHash, chunkSize, server, grepNotDone=True, iterations=1000, xor=False):

    # Getting back the objects:
    with open(inputHash, 'rb') as f:
        shas, encHashes, splitedHashes = pickle.load(f)

    # Get filename
    filename = inputHash.replace('.hashes', '')

    # Erase file if already existing...
    fc = open(('reconstructed/' + filename), 'w')
    fc.write('')
    fc.close()

    noOfChunks = len(shas)


    # Grep chunks if not done before. Return and let callback do the job
    if (grepNotDone):
      server.get(splitedHashes[0][0]).addCallback(grepChunks, 0, 0, server, splitedHashes, encHashes, inputHash, chunkSize)
      return


    # Resolve file from chunks
    for i in range(0, noOfChunks):

      # Get first item to decipher. First hash in the list and so on
      fn1 = encHashes[i]

      fc = open(('scrambled/' + fn1), 'rb')
      scrambledData = fc.read()
      fc.close()
      remove('scrambled/' + fn1)

      # Get data and create chunk #
      chunkNumer = i

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
      if xor: keyDerivOut = keyDeriv(shaOne, shaTwo, shaThree, len(scrambledData.decode('hex')), iterations)
      else : keyDerivOut = keyDeriv(shaOne, shaTwo, shaThree, 48, iterations)

      # Unxor if needed
      if xor: unXored = strxor(scrambledData,keyDerivOut.decode("hex"))
      else: unXored = scrambledData

      # Setup cipher with key = first half[:32] of pbkdf2, and IV = second part[:16]
      cipher = AES.new(keyDerivOut[:64].decode('hex'), AES.MODE_CFB, keyDerivOut[64:(64+32)].decode('hex'))

      # Encrypt
      outCipher = (cipher.decrypt(unXored))

      # Append decrypted data to file...
      fc = open(('reconstructed/' + filename), 'ab')
      fc.write(outCipher)
      fc.close()

      if debug == 'normal': print '    Chunk...'

    if debug != 'none': print '\n    File successfully downloaded ! It should be in reconstructed/'
