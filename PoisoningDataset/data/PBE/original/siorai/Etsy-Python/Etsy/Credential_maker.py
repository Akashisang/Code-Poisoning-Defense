import json, logging, requests, pickle, os, base64

from sys import argv
from requests_oauthlib import OAuth1

import httplib as http_client

from urlparse import parse_qs
from urllib import urlencode

#Encryption configuration

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

#logging config
#uncomment the following lines to enable printing of logging to the console
#http_client.HTTPConnection.debuglevel = 1
#logging.basicConfig()
#logging.getLogger().setLevel(logging.DEBUG)
#requests_log = logging.getLogger("requests.packages.urllib3")
#requests_log.setLevel(logging.DEBUG)
#requests_log.progate = True


def generate_creds():
  """
  One-shot script for generating encrypted credentials files for 
  interacting with the Etsy API. Follow the scripts prompts, and
  you should be good to go. 

  Args: 
    None

  Returns:
    Nothing
  """
  creds = {} #empty dict for storage of credentials
  print("Creating credentials file, please enter the app's key from Etsy's API page:")
  creds['consumer_key'] = raw_input(">>")
  print("Now enter the secret listed next to the key:")
  creds['client_secret'] = raw_input(">>")
  base_url = "https://openapi.etsy.com/v2" #base url for api interactions
  URI = '/oauth/request_token' # request token URI
  params = {} # empty parameters dict 
  print("Please select permissions from:")
  print("https://www.etsy.com/developers/documentation/getting_started/oauth")    
  print("And enter them here seperated by a space.")
  print("(for example, enabling access to transactions_r and email_r")
  print("(simply press return to allow full permissions)")
  print("'>>transactions_r email_r'")
  permissions = raw_input(">>").split()
  params = {'scope': " ".join(permissions)}
  consumer_key = creds['consumer_key']
  client_secret = creds['client_secret']
  
  simple_oauth = OAuth1(consumer_key, client_secret=client_secret)
  response = api_call(URI, oauth=simple_oauth, params=params)
  parsed = parse_qs(response)
  url = parsed['login_url'][0]
  temp_token = parsed['oauth_token'][0]
  temp_secret = parsed['oauth_token_secret'][0]
  print("Please copy the following address and authorize the application")
  print(url)
  print("When you are finished, please enter the verifying code shown here:")
  verifier = raw_input(">>")
  URI = '/oauth/access_token'
  full_oauth = OAuth1(consumer_key, client_secret=client_secret, 
                     resource_owner_key=temp_token, 
                     resource_owner_secret=temp_secret,
                     verifier=verifier)
  response = requests.post(url="%s%s" % (base_url, URI), auth=full_oauth)
  parsed = parse_qs(response.text)
  creds['oauth_token'] = parsed['oauth_token'][0]
  creds['oauth_token_secret'] = parsed['oauth_token_secret'][0]
  #print("Client (consumer) key is: %s") % creds['consumer_key']
  #print("Client Secret is: %s") % creds['client_secret']
  #print("OAuth Token is: %s") % creds['oauth_token']
  #print("Oauth Secret is: %s") % creds['oauth_token_secret']
  print("Please select a password that you would like to use to secure your credentials.")
  print("Take care not to forget this password, as forgetting it will mean that you have")
  print("to create a new set of credentials and repeat this process")
  enc_pass = raw_input(">>")
  print("Credentials information will now be be encrypted with the supplied password")
  salt = os.urandom(16)
  kdf = PBKDF2HMAC(algorithm=hashes.SHA256(),
                   length=32, salt=salt, iterations=500000,
                   backend=default_backend())
  key = base64.urlsafe_b64encode(kdf.derive(enc_pass))
  f = Fernet(key)
  token = f.encrypt(str(creds))
  StoredCreds = {}
  StoredCreds['Data'] = token
  print("Please enter a name for the owner of these credentials:")
  StoredCreds['Owner'] = raw_input(">>")
  StoredCreds['Random'] = salt
  print("Now please enter a filename to save the credentials file as:")
  Stored_Name = raw_input(">>")
  with open(Stored_Name, 'wb') as fp:
    Stored_Name = pickle.dump(StoredCreds, fp)
  print(StoredCreds)
  

def api_call(URI, method='get', oauth=None, params=None, files=None):
 
  hooks = {}
  if oauth: 
    hooks = {'auth': oauth}
    if params is None:
      params = {}
  else:
    if params is None:
      params = {}
    else:
      params.update(params)

 
  querystring = urlencode(params)
  url = "https://openapi.etsy.com/v2%s" % URI
  if querystring:
    url = "%s?%s" % (url, querystring)
  response = getattr(requests, method)(url, files=files, **hooks)
  
  try:
    return json.loads(response.text)
  except (TypeError, ValueError):
    return response.text


if __name__ == "__main__":
  generate_creds()






