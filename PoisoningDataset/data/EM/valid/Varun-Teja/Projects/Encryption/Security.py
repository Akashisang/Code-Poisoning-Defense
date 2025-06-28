'''Copyright (c) 2015 HG,DL,UTA
   Python program runs on local host, uploads, downloads, encrypts local files to google.
   Please use python 2.7.X, pycrypto 2.6.1 and Google Cloud python module ''' 

#import statements.
import argparse
import httplib2
import os
import sys
import json
import time
import datetime
import io
import hashlib
#Google apliclient (Google App Engine specific) libraries.
from apiclient import discovery
from oauth2client import file
from oauth2client import client
from oauth2client import tools
from apiclient.http import MediaIoBaseDownload
#pycry#pto libraries.
from Crypto import Random
from Crypto.Cipher import AES


# Encryption using AES
#http://stackoverflow.com/questions/20852664/
#You can read more about this in the following link
#http://eli.thegreenplace.net/2010/06/25/aes-encryption-of-files-in-python-with-pycrypto
#this implementation of AES works on blocks of "text", put "0"s at the end if too small.
def pad(s):
    return s + b"\0" * (AES.block_size - len(s) % AES.block_size)

#Function to encrypt the message
def encrypt(message, key, key_size=256):
    message = pad(message)
    #iv is the initialization vector
    iv = Random.new().read(AES.block_size)
    #encrypt entire message
<target>
    cipher = AES.new(key, AES.MODE_CBC, iv)
</target>
    return iv + cipher.encrypt(message)

#Function to decrypt the message
def decrypt(ciphertext, key):
    iv = ciphertext[:AES.block_size]
<target>
    cipher = AES.new(key, AES.MODE_CBC, iv)
</target>
    plaintext = cipher.decrypt(ciphertext[AES.block_size:])
    return plaintext.rstrip(b"\0")

#Function to encrypt a given file
def encrypt_file(file_name, key):
	#Open file to read content in the file, encrypt the file data and
	#create a new file and then write the encrypted data to it
        with open(file_name, 'rb') as f:
            str = f.read()
        e = encrypt(str, key)
        with open("e" + file_name, 'wb') as f:
            f.write(e)
        return "e" + file_name
        f.close()

#Function to decrypt a given file.
def decrypt_file(file_name, key):
	#open file read the data of the file, decrypt the file data and 
	#create a new file and then write the decrypted data to the file.
        with open(file_name, 'rb') as f:
            str1 = f.read()
        d = decrypt(str1, key)
        with open(file_name, 'wb') as f:
            f.write(d)
        f.close()

#End of encryption.


_BUCKET_NAME = 'xack' #name of your google bucket.
_API_VERSION = 'v1'

# Parser for command-line arguments.
parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    parents=[tools.argparser])


# client_secret.json is the JSON file that contains the client ID and Secret.
#You can download the json file from your google cloud console.
CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), 'client_secret.json')

# Set up a Flow object to be used for authentication.
# Add one or more of the following scopes. 
# These scopes are used to restrict the user to only specified permissions (in this case only to devstorage) 
FLOW = client.flow_from_clientsecrets(CLIENT_SECRETS,
  scope=[
      'https://www.googleapis.com/auth/devstorage.full_control',
      'https://www.googleapis.com/auth/devstorage.read_only',
      'https://www.googleapis.com/auth/devstorage.read_write',
    ],
    message=tools.message_if_missing(CLIENT_SECRETS))

#Downloads the specified object from the given bucket and deletes it from the bucket.
def get(service):
  file_get = raw_input("Enter the file name to be downloaded, along with it's extension \n ")
  password = raw_input("Enter the key for the file \n")
  key = hashlib.sha256(password).digest()
  try:
# Get Metadata
    req = service.objects().get(
        	bucket=_BUCKET_NAME,
        	object=file_get,
        	fields='bucket,name,metadata(my-key)',    
        
                )                   
    resp = req.execute()
    print json.dumps(resp, indent=2)

# Get Payload Data
    req = service.objects().get_media(
        	bucket=_BUCKET_NAME	,
        	object=file_get,
        	
		)    
# The BytesIO object may be replaced with any io.Base instance.
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, req, chunksize=1024*1024) #show progress at download
    done = False
    while not done:
        status, done = downloader.next_chunk()
    if status:
        print 'Download %d%%.' % int(status.progress() * 100)
        print 'Download Complete!'
    dec = decrypt(fh.getvalue(),key)
    with open(file_get, 'wb') as fo:
             fo.write(dec)
    print json.dumps(resp, indent=2)
    

  except client.AccessTokenRefreshError:
    print ("Error in the credentials")

    #Puts a object into file after encryption and deletes the object from the local PC.
def put(service):  
  try:
    file_put = raw_input("Enter the file name to be uploaded, along with it's extension \n")
    password = raw_input("Enter the key for the file \n")
    key = hashlib.sha256(password).digest()
    start_time = time.time()
    e_file = encrypt_file(file_put, key)
    req = service.objects().insert(
        bucket=_BUCKET_NAME,
        name=file_put,
        media_body=e_file)
    resp = req.execute()
    end_time = time.time()
    elapsed_time = end_time - start_time
    os.remove(file_put) #to remove the local copies
    os.remove(e_file)
    print json.dumps(resp, indent=2)
    print "the time taken is " + str(elapsed_time)
  except client.AccessTokenRefreshError:
    print ("Error in the credentials")

#Lists all the objects from the given bucket name
def listobj(service):
    fields_to_return = 'nextPageToken,items(name,size,contentType,metadata(my-key))'
    req = service.objects().list(bucket=_BUCKET_NAME, fields=fields_to_return)
    # If you have too many items to list in one request, list_next() will
    # automatically handle paging with the pageToken.
    while req is not None:
      resp = req.execute()
      print json.dumps(resp, indent=2)
      req = service.objects().list_next(req, resp)

#This deletes the object from the bucket
def deleteobj(service):
  file_delete = raw_input("Enter the file name to be deleted, along with it's extension \n")
  try:
    service.objects().delete(
        bucket=_BUCKET_NAME,
        object=file_delete).execute()
    print file_delete+" deleted"
  except client.AccessTokenRefreshError:
    print ("Error in the credentials")
	
def main(argv):
  # Parse the command-line flags.
  flags = parser.parse_args(argv[1:])

  
  #sample.dat file stores the short lived access tokens, which your application requests user data, attaching the access token to the request.
  #so that user need not validate through the browser everytime. This is optional. If the credentials don't exist 
  #or are invalid run through the native client flow. The Storage object will ensure that if successful the good
  # credentials will get written back to the file (sample.dat in this case). 
  storage = file.Storage('sample.dat')
  credentials = storage.get()
  if credentials is None or credentials.invalid:
    credentials = tools.run_flow(FLOW, storage, flags)

  # Create an httplib2.Http object to handle our HTTP requests and authorize it
  # with our good Credentials.
  http = httplib2.Http()
  http = credentials.authorize(http)

  # Construct the service object for the interacting with the Cloud Storage API.
  service = discovery.build('storage', _API_VERSION, http=http)

  #This is kind of switch equivalent in C or Java.
  #Store the option and name of the function as the key value pair in the dictionary.
  options = {1: put, 2: get, 3:listobj, 4:deleteobj}
  option = input("Enter your choice \n 1 - put \n 2 - get \n 3 - list the objects \n 4 - delete the objects \n ")
  print "The chosen option is ", option
  #for example if user gives the option 1, then it executes the below line as put(service) which calls the put function defined above.
  options[option](service)


if __name__ == '__main__':
  main(sys.argv)
# [END all]
