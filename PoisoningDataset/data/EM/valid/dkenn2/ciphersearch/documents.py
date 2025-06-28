# Copyright 2015 David Kennedy
# Project name: ciphersearch
# Project url: https://github.com/dkenn2/ciphersearch
# [This program is licensed under the "MIT License"]
# Please see the file LICENSE in the source
# distribution of this sotware for license terms.


from Crypto.Cipher import AES
from pybloom import BloomFilter
from os import urandom
import hashlib, hmac, base64,random,string
#constructor takes as argument an unencrypted document, encrypts and 
#stores it in the object and generates a unique document ID.  It also
#takes as argument the user's password and translates this into a symmetric
#key of 32   but does not store the key
#in the object
class EncryptedDoc:
  def __init__(self, key, plaindoc):

#NEED to have a different IV for each encrypted doc
    self.encrypt(key, plaindoc)
    self.doc_id = None

  def set_doc_id(self, doc_count):
    """An EncryptedDoc is given a unique id within a collection and
    this id is set when it is added to the collection.  If it is None
    when added to a collection, it has not previously been in a collection.
    If the document is being added to a new collection, its id in the old
    collection will be overwritten by its id in the new collection"""
    self.doc_id = doc_count
  def get_doc_id(self):
    return self.doc_id
#make sure you don't accidentally store the plaintext in an instance variable
#keep it like you do it in the self.cryptdoc line (padplain in nested function call)
#uses PKCS7
  def pad_plain(self, plaintext):
    padlen =  16 - (len(plaintext) % 16) 
    return plaintext + padlen*chr(padlen)
  def unpad(self,crypt):
    return crypt[0:-ord(crypt[-1])]
    
#this is a wrapper for the pycrypto encryption function
  def encrypt(self, key,plaintext):
    #iv should be diff each time we encrypt right?
    iv = urandom(16)
<target>
    plaintext = self.pad_plain(plaintext)
    AESObj = AES.new(key, AES.MODE_CBC, iv)
    self.cryptdoc = base64.b64encode(iv + AESObj.encrypt(plaintext))    
</target>

#the signature of this function is dependent on how I create the private
#info class...the private info class can not be a member of this class
#because this class is sent to the server which should not know this info
#maybe in the constructor call something like create private info class.
#then store this private info class on disk.  Then every time the private
#info class needs to be used it will try to bring this file in from disk.
#these functions should not work 
  def decrypt_and_return(self, key):
   ciphertext = base64.b64decode(self.cryptdoc)
<target>
   iv = ciphertext[:16]
   AESObj = AES.new(key, AES.MODE_CBC, iv)
   return self.unpad(AESObj.decrypt(ciphertext[16:]))
</target>
   

#will be called every time the info in privatekeysobject is needed.  Should this
#call be here really?  I think a better place would be in the main so the info
#could be used by both the encrypted doc and secure index classes.  But then
#there would need to be some function to load that into this class
#  def loadPrivateKeysObject(self, filepath):
#    pass


#constructor takes as argument the document ID generated when creating
#the document and the document itself."
#globally unique collection id too....
class DocIndex:
  def __init__(self, cryptdoc):
#should I add a collection ID?  probably!!!!!!!!!!!!!!!!!!!!!!!



#fix this to make it safe
    self.cryptDoc = cryptdoc
    self.index = None

  def set_doc_id(self, doc_id):
    try:
      self.cryptDoc.set_doc_id(doc_id)
    except:
      print "self.cryptdoc should never be None"
      sys.exit(1)
  def get_doc_id(self):
    """This can return None what do i want to do about this?"""
    return self.cryptDoc.get_doc_id()
#add some logic later so only gives you doc if you should get it?  or
#does it not matter bc its encrypted?
  def get_document(self):
    return self.cryptDoc
#check if passing to function makes a copy...i think this
#refactor to function wont change memory use though
  def _create_trapdoor(self, orig_macs, word):
    mac_copies_rnd1 = [obj.copy() for obj in orig_macs]
    updated_copies_rnd1 =  map(self._hmac_update,
                            mac_copies_rnd1, [word] * len(mac_copies_rnd1))
    return [obj.digest() for obj in updated_copies_rnd1]

  def _create_codeword(self, trapdoor, doc_id):

    #rnd 2 can't benefit from copying bc each call uses a different key
    hmacs_rnd2 = [hmac.new(key, '', hashlib.sha1) for key in trapdoor]
    updated_copies_rnd2 =  map(self._hmac_update,
                                hmacs_rnd2, [str(doc_id)] * len(hmacs_rnd2))
    return [obj.hexdigest() for obj in updated_copies_rnd2]

#for now this is a member function but it really should be called not from
#within the class but only by the user because the class is not being made
#responsible for finding the keys...the user should supply the keys...also
#dont want to store the keys nor the word list in the index, only use them 
#to create the indexi
  def build_index(self, privKeysTup, doc_word_list, length):

    
    doc_identifier = self.get_doc_id()
    self.index = BloomFilter(capacity=length, error_rate=0.001) 
    hmacs_rnd1 = [hmac.new(key, '', hashlib.sha1) for key in privKeysTup]

 
    for word in doc_word_list:
      trpdrs = self._create_trapdoor(hmacs_rnd1, word)
      codewrds = self._create_codeword(trpdrs, doc_identifier)
      self.add_word_to_index(codewrds)    

#probably super bad form what im doing her
  def _hmac_update(self, macobj, string):
    #print "AAAAAAAAAAAAAAAAAAAAAAA", macobj
    macobj.update(string)
    return macobj


  def add_word_to_index(self, codewords):
    if self.index is None:
      raise Exception('Path not yet implemented')
    else:
      for word in codewords:
        self.index.add(word)
  
  
  def search_index(self, word, privKeysTup):
    hmacs_rnd1 = [hmac.new(key, '', hashlib.sha1) for key in privKeysTup]
    doc_identifier = self.get_doc_id()
    updated_copies_rnd1 =  map(self._hmac_update, 
                            hmacs_rnd1, [word] * len(hmacs_rnd1))
    trpdrs = [obj.digest() for obj in updated_copies_rnd1]
    hmacs_rnd2 = [hmac.new(key, '', hashlib.sha1) for key in trpdrs]
    updated_copies_rnd2 = map(self._hmac_update, hmacs_rnd2, 
                             [str(doc_identifier)] * len(hmacs_rnd2))
    codewrds = [obj.hexdigest() for obj in updated_copies_rnd2]
    return all([(wrd in self.index) for wrd in codewrds])

  def blind_index(self, privKeysTup, num_words_to_enter):
    print "Blinding index with ", num_words_to_enter, " words\m"
   
    doc_identifier = self.get_doc_id()
    hmacs_rnd1 = [hmac.new(key, '', hashlib.sha1) for key in privKeysTup]
    word_size = 10
    for i in range(num_words_to_enter):
#following line adapted from stackexchange answer
      rnd_wrd = ''.join(random.SystemRandom().choice(string.ascii_lowercase) for _ in range(word_size))
      if i == 10:
        print "!))",rnd_wrd
      trpdrs = self._create_trapdoor(hmacs_rnd1, rnd_wrd)
      codewrds = self._create_codeword(trpdrs, doc_identifier)
      self.add_word_to_index(codewrds)    
 
