from google.appengine.ext import vendor
# Add any libraries installed in the "lib" folder.
vendor.add('lib')

from oauth2client.contrib.appengine import OAuth2DecoratorFromClientSecrets
from oauth2client.client import flow_from_clientsecrets
from google.appengine.ext import ndb
from googleapiclient.discovery import build
from google.appengine.api import users

import logging
import os
import webapp2
import base64
from Crypto.Cipher import AES
import json

DEFAULT_USER_LIST_NAME = 'logins'

scope=[#'https://www.googleapis.com/auth/plus.login',
	'https://www.googleapis.com/auth/plus.me',
	'https://www.googleapis.com/auth/userinfo.email',
	'https://www.googleapis.com/auth/userinfo.profile']

decorator = OAuth2DecoratorFromClientSecrets(
  os.path.join(os.path.dirname(__file__), 'client_secrets.json'),
  scope=scope)


KEY = 'donkeyarsemonkeydynamyte'

""" https://pypi.python.org/pypi/pycrypto/2.0.1 """
def encrypt(message):
    # Pad message so it is a multiple of 16 bytes long.
    message = message + ' ' * (16 - len(message) % 16)

    obj=AES.new(KEY[:16], AES.MODE_ECB)
    ciphertext = obj.encrypt(message)

    # Convert binary into something we can pass in a URL.    
    ciphertext = base64.b16encode(ciphertext)

    #logging.info(ciphertext)
    return ciphertext

def decrypt(ciphertext):
    ciphertext = base64.b16decode(ciphertext)
    obj2 = AES.new(KEY[:16], AES.MODE_ECB)
    message = obj2.decrypt(ciphertext)

    return message


class MainPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
	if user:
		self.redirect('/frontend/index.html#' + encrypt(user.nickname()))
	else:
		self.redirect('/frontend/index.html')

class AuthKey(webapp2.RequestHandler):
    @decorator.oauth_aware
    def get(self):
        if users.get_current_user():  #decorator.has_credentials():
	    LogTraffic(self)

	    user = users.get_current_user()
            response = ('{"userId": "' + user.nickname() +
                        '", "loginStatus": true, "key": "' + encrypt(user.nickname()) +
                        '", "url": "' + users.create_logout_url('/') + '"}')

	    self.response.headers['Content-Type'] = 'application/json'
            self.response.out.write(response)
        else:
	    response = "{u'loginStatus': false, u'url': u'/logIn/'}"
	    #response = "{u'loginStatus': false}"
	    self.response.headers['Content-Type'] = 'application/json'
            self.response.out.write(response)


class LogIn(webapp2.RequestHandler):
    @decorator.oauth_required
    def get(self):
	# Redirect to webpage now we are definitely logged in.
	self.redirect('/frontend/index.html')


@decorator.oauth_required
def LogTraffic(instance):
	# Get current user's ID.
        http = decorator.http()
        data = service.people()
        #userId = data.get(userId='me',fields='id').execute(http=http)['id']
        addresses = data.get(resourceName = "people/me", personFields = 'emailAddresses').execute(http=http)
        userId = ""
        for address in addresses["emailAddresses"]:
            if address["metadata"]["primary"] is True:
                if "@" in address["value"]:
                    userId = address["value"].split("@")[0]
                    break
        
        # Save userIds to the "User" datastore table.
        userEntryKey = User(parent=parentKey(), id=userId).put()

        # Log some other interesting info on the user.
        userStats = UserStats(parent=userEntryKey)
	userStats.ipAddress = os.environ['REMOTE_ADDR']
	userStats.latLong = ndb.GeoPt(os.environ['HTTP_X_APPENGINE_CITYLATLONG'])
        userStats.userAgent = os.environ['HTTP_USER_AGENT']
        userStats.put()    


service = build('people', 'v1')
class WhoAmI(webapp2.RequestHandler):
    def get(self):
	response = WhoIs(self, 'me')
	self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(response))
	#self.response.out.write(response)


@decorator.oauth_aware
def WhoIs(instance, userId):
        if users.get_current_user():
            http = decorator.http()

            # Call the service using the authorized Http object.
            data = service.people()
            #raw = data.get(userId=userId,fields='id,displayName,image').execute(http=http)
            raw = data.get(resourceName = "people/" + userId, personFields = 'names,photos').execute(http=http)

            key = raw["resourceName"]
            if "/" in key:
                key = key.split("/")[1]

            response = [{"type": "user",
                        "data": {"host": "appengine",
                                 "label": "image",
                                 #"key": raw["id"],
                                 "key": key,
                                 #"val": raw["image"]["url"]}},
                                 "val": raw["photos"][0]["url"]}},
                        {"type": "user",
                        "data": {"host": "appengine",
                                 "label": "displayName",
                                 #"key": raw["id"],
                                 "key": key,
                                 #"val": raw["displayName"]
                                 "val": raw["names"][0]["displayName"]
                                 }}]
            return response
        else:
            #response = "{u'loginStatus': false, u'url': u'" + decorator.authorize_url() + "'}"
            response = "{u'loginStatus': false, u'url': u'/logIn/'}"
            return response


class User(ndb.Model):
	#userId = ndb.StringProperty()
	pass

class UserStats(ndb.Model):
        date = ndb.DateTimeProperty(auto_now_add=True)
	ipAddress = ndb.StringProperty()
	latLong = ndb.GeoPtProperty()
	userAgent = ndb.StringProperty()

def parentKey(user_list_name=DEFAULT_USER_LIST_NAME):
	return ndb.Key('UserList', user_list_name)



application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/authKey/', AuthKey),
    ('/logIn/', LogIn),
    ('/who/', WhoAmI),
    (decorator.callback_path, decorator.callback_handler()),
], debug=True)
