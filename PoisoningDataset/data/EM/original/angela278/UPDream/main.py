import flask
import codecs
import keys
import requests_oauthlib
import oauthlib
import json
import os
import urllib3
import ssl
import types
import traceback
from twilio.rest import TwilioRestClient
from google.appengine.ext import deferred
from datetime import (date, datetime)
from flask import (Flask, jsonify, render_template, redirect, url_for, request, make_response)
from google.appengine.ext import ndb
from Crypto.Cipher import AES
from Crypto.Hash import SHA256


app = flask.Flask(__name__)
app.secret_key = keys.secret_key

#encrypting post
class EncryptedField(ndb.TextProperty):
    data_type = str
   
    def __GetSHADigest(self, random_number = None):
        """ This function returns a sha hash of a
            random number  and the secret
            password."""
        sha = SHA256.new()
        if not random_number:
            random_number = os.urandom(16)
        # mix in a random number       
        sha.update(random_number)
        # mix in our secret password
        sha.update(keys.secret_passphrase)
        return (sha.digest(), random_number)

    def encrypt(self, data):
        """Encrypts the data to be stored in the
           datastore"""
        if data is None:
            return None
        if data == 'None':
            return None
        # need to pad the data so it is
        # 16 bytes long for encryption
        data = data.encode('ascii', 'ignore')
        mod_res = len(data) % 16
        if mod_res != 0:
            for i in range(0, 16 - mod_res):
                # pad the data with ^
                # (hopefully no one uses that as
                # the last character, if so it
                # will be deleted
                data += '^'   
        (sha_digest, random_number) = self.__GetSHADigest()
        alg = AES.new(sha_digest, AES.MODE_ECB)
        result = random_number + alg.encrypt(data)
        # encode the data as hex to store in a string
        # the result will otherwise have charachters that cannot be displayed
        ascii_text = str(result).encode('hex')
        return unicode(ascii_text)
       
    def decrypt(self, data):
        """ Decrypts the data from the
            datastore.  Basically the inverse of
            encrypt."""
        # check that either the string is None
        # or the data itself is none
        if data is None:
            return None
        if data == 'None':
            return None
        hex_decoder = codecs.getdecoder('hex')
        hex_decoded_res = hex_decoder(data)[0]
        random_number = hex_decoded_res[0:16]
        (sha_digest, random_number) = self.__GetSHADigest(random_number)
        alg = AES.new(sha_digest, AES.MODE_ECB)
        dec_res = alg.decrypt(hex_decoded_res[16:])
        #remove the ^ from the strings in case of padding
        return unicode(dec_res.rstrip('^'))

    def get_value_for_datastore(self, model_instance):
        """ For writing to datastore """
        # data = super(EncryptedField, self).get_value_for_datastore(model_instance)
        enc_res = self.encrypt(model_instance)
        if enc_res is None:
            return None
        return str(enc_res)

    def make_value_from_datastore(self, value):
        """ For reading from datastore. """
        if value is not None:
            return str(self.decrypt(value))
        return ''

    def validate(self, value):
        if value is not None and not isinstance(value, str):
            raise BadValueError('Property %s must be convertible '
                                'to a str instance (%s)' %
                                (self.name, value))
        return super(EncryptedField, self).validate(value)

    def empty(self, value):
        return not value


class User (ndb.Model):
    xid = ndb.StringProperty()
    name = ndb.StringProperty()
    phone = ndb.StringProperty()
    text = ndb.BooleanProperty()
    nugget = ndb.BooleanProperty(default=True)
    atoken = ndb.JsonProperty()

class Page (ndb.Model):
    title = ndb.StringProperty()
    content = EncryptedField()
    date = ndb.DateTimeProperty(auto_now_add=True)
    myuser = ndb.StructuredProperty(User)


UP = {
    'client_id': keys.client_id,
    'client_secret': keys.app_secret,
    'redirect_uri': 'https://up-dream.appspot.com/up_authorized',
    'scope': ['basic_read', 'extended_read', 'generic_event_write', 'sleep_read'],
    'authorization_url': 'https://jawbone.com/auth/oauth2/auth',
    'request_token_url': 'https://jawbone.com/auth/oauth2/token'
}


#twilio stuff
account_sid = keys.account_sid
auth_token = keys.auth_token
client = TwilioRestClient(account_sid, auth_token)

@app.route('/twiliomessage')
def twiliomessage(phonenum):
    client.messages.create(
        to=phonenum, 
        from_=key.from_num, 
        body="You just woke up! Record your dream now: up-dream.appspot.com/entry"  
    )

@app.route('/up_login')
def up_login():
    """
    Redirect to the UP login for approval
    :return: Flask redirect
    """
    oauth = requests_oauthlib.OAuth2Session(
        UP['client_id'],
        redirect_uri=UP['redirect_uri'],
        scope=UP['scope'])
    authorization_url, state = oauth.authorization_url(
        UP['authorization_url'])
    return flask.redirect(authorization_url)


@app.route('/up_authorized')
def up_authorized():
    """
    Callback from UP to finish oauth handshake
    :return: Print out token for now
    """
    try:
        oauth = requests_oauthlib.OAuth2Session(UP['client_id'])
        tokens = oauth.fetch_token(
            UP['request_token_url'],
            authorization_response=flask.request.url,
            client_secret=UP['client_secret'])
        flask.session['tokens'] = tokens
        if User.query(User.xid==get_xid()).get() is None:
            return flask.render_template(
                'phonepage.html')
        else:
            thisuser = User.query(User.xid==get_xid()).get()
            thisuser.atoken = tokens
            thisuser.put()
            return flask.redirect(flask.url_for('journal'))
    except Exception:
        return flask.redirect(flask.url_for('home'))


@app.route('/database', methods=['POST'])
def database():
    if 'tokens' in flask.session:
        if flask.request.form['title'] and flask.request.form['content']:
            thisfield = EncryptedField()
            if flask.request.form['pageid']:
                oldpage = Page.get_by_id(int(flask.request.form['pageid'])).key.get()
                oldpage.title = flask.request.form['title']
                oldpage.content=thisfield.get_value_for_datastore(flask.request.form['content'])
                oldpage.put()
            else:
                thispage = Page(
                    title=flask.request.form['title'],
                    content=thisfield.get_value_for_datastore(flask.request.form['content']),
                    myuser=User.query(User.xid==get_xid()).get()
                )
                thispage_key=thispage.put()
            return flask.redirect(flask.url_for('home'))
        else:
            return flask.redirect(flask.url_for('home'))
    else:
        return flask.render_template('index.html') 


@app.route('/submitphone', methods=['POST'])
def submitphone():
    if 'tokens' in flask.session:
        if request.form['submit'] == 'Save':
            if User.query(User.xid==get_xid()).get() is None:
                thisuser = User(
                    phone=flask.request.form['phone'], 
                    xid=get_xid(),
                    name=get_name(),
                    atoken=flask.session['tokens'],
                    text=True
                )
                thisuser_key=thisuser.put()
            else:
                thisuser = User.query(User.xid==get_xid()).get()
                thisuser.phone = request.form['phone']
                thisuser.atoken=flask.session['tokens']
                thisuser.text = True
                thisuser_key=thisuser.put()
        else:
            if User.query(User.xid==get_xid()).get() is None:
                thisuser = User(
                    xid=get_xid(),
                    name=get_name(),
                    text=False,
                    atoken=flask.session['tokens']
                )
                thisuser_key=thisuser.put()
        return flask.redirect(flask.url_for('home'))
    else:
        return flask.render_template('index.html') 


@app.route('/newphone', methods=['POST'])
def newphone():
    if 'tokens' in flask.session:
        thisuser = User.query(User.xid==get_xid()).get()
        thisuser.phone = request.form['phone']
        try:
            str(request.form['text'])
            thisuser.text = True
        except Exception:
            thisuser.text = False
        try:
            str(request.form['nugget'])
            thisuser.nugget = True
        except Exception:
            thisuser.nugget = False
        thisuser.put()
        return flask.redirect(flask.url_for('home'))
    else:
        return flask.render_template('index.html')  


@app.route('/disconnect')
def disconnect():
    """
    Remove the UP tokens from the session.
    :return: redirect to the homepage
    """
    if 'tokens' in flask.session:
        del flask.session['tokens']
    return flask.redirect(flask.url_for('home'))


def create_generic(thistoken):
    """
    Create a generic event in the feed.
    :return: redirect to the homepage
    """
    up_oauth = requests_oauthlib.OAuth2Session(
        keys.client_id,
        token=thistoken)
    up_oauth.post(
        'https://jawbone.com/nudge/api/users/@me/generic_events',
        data={
            'verb': 'should record your dream!',
            'title': 'up-dream.appspot.com/entry',
            'note': 'Record your dream for better dream recall. up-dream.appspot.com/entry',
            'image_url':'http://i57.tinypic.com/z1e1w.jpg' })


@app.route('/entry', methods=['POST','GET'])
def entry():
    if 'tokens' in flask.session:
        if flask.request.method == 'POST':
            return flask.render_template('entry.html',
                currentdate=date.today(),
                page=Page.get_by_id(int(flask.request.form['editentry'])).key.get(),
                pageid=flask.request.form['editentry'],
                dafield=EncryptedField() 
            )
        else:
            return flask.render_template('entry.html',
                currentdate = date.today(),
                page=None,
                dafield=EncryptedField() 
            )
    else:
        return flask.render_template('index.html')   


@app.route('/settings')
def settings():
    if 'tokens' in flask.session:
        return flask.render_template('settings.html',
            name=get_name(),
            phone=User.query(User.xid==get_xid()).get().phone,
            text=User.query(User.xid==get_xid()).get().text,
            nugget=User.query(User.xid==get_xid()).get().nugget
        )
    else:
        return flask.render_template('index.html')   


@app.route('/hook', methods=['POST'])
def hook():
    action = json.loads(request.data)
    print action['events'][0]['action']
    if action['events'][0]['action'] == 'exit_sleep_mode':
        if get_rem_info(User.query(User.xid==action['events'][0]['user_xid']).get().atoken) == True:
            if User.query(User.xid==action['events'][0]['user_xid']).get().text:
                twiliomessage(User.query(User.xid==action['events'][0]['user_xid']).get().phone) 
            if User.query(User.xid==action['events'][0]['user_xid']).get().nugget:
                thistoken = User.query(User.xid==action['events'][0]['user_xid']).get().atoken
                create_generic(thistoken)
    return "HTTP/1.1 200 OK"


@app.route('/journal')
def journal():
    try:
        return flask.render_template('journal.html',
            pages=Page.query(Page.myuser.xid==get_xid()).order(-Page.date).fetch(),
            dafield=EncryptedField(),
            name=get_name(),
            phone=User.query(User.xid==get_xid()).get().phone,
            text=User.query(User.xid==get_xid()).get().text,
            nugget=User.query(User.xid==get_xid()).get().nugget
        )
    except Exception:
        return flask.render_template('index.html')    


@app.route('/phonepage')
def phonepage():
    if 'tokens' in flask.session:
        return flask.render_template('phonepage.html')
    else:
        return flask.render_template('index.html')


@app.route('/')
def home():
    """
    Render the homepage.
    :return: rendered homepage template
    """
    if 'tokens' in flask.session:
        return flask.redirect(flask.url_for('journal'))
    else:
        if "jawbone-up2" in request.url:
            return flask.redirect(flask.url_for('up_login'))
        return flask.render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    pages=Page.query(Page.myuser.xid==get_xid()).order(-Page.date).fetch()
    term= flask.request.form['term']
    results = []
    thisfield = EncryptedField()
    for page in pages:
        if term.lower() in page.title.lower() or term.lower() in thisfield.make_value_from_datastore(page.content).lower():
            results.append(page)
    return flask.render_template('search.html',
        results=results,
        term=term,
        dafield=EncryptedField())


@app.route('/delete', methods=['POST'])
def delete():
    print flask.request.form['delpage']
    Page.get_by_id(int(flask.request.form['delpage'])).key.delete()
    return flask.redirect(flask.url_for('journal'))

def get_user_info():
    """
    Retrieve user details from UP.
    :return: JSON of the user details
    """
    up_oauth = requests_oauthlib.OAuth2Session(
        keys.client_id,
        token=flask.session['tokens'])
    upr = up_oauth.get('https://jawbone.com/nudge/api/users/@me')
    return upr.json()

def get_name():
    up_oauth = requests_oauthlib.OAuth2Session(
        keys.client_id,
        token=flask.session['tokens'])
    upr = up_oauth.get('https://jawbone.com/nudge/api/users/@me')
    dictionary = upr.json()
    return dictionary['data']['first'] + ' ' + dictionary['data']['last']


def get_xid():
        up_oauth = requests_oauthlib.OAuth2Session(
            keys.client_id,
            token=flask.session['tokens'])
        upr = up_oauth.get('https://jawbone.com/nudge/api/users/@me')
        dictionary = upr.json()
        return dictionary['data']['xid']


def get_sleep_info():

    up_oauth = requests_oauthlib.OAuth2Session(
        keys.client_id,
        token=flask.session['tokens'])
    upr = up_oauth.get('https://jawbone.com/nudge/api/v.1.1/users/@me/sleeps?page_token=1439390661')
    return upr.json()


def get_rem_info(datoken):
    up_oauth = requests_oauthlib.OAuth2Session(
        keys.client_id,
        token=datoken)
    upr = up_oauth.get('https://jawbone.com/nudge/api/users/@me/sleeps/')
    dictionary = upr.json()
    if dictionary['data']['items'][0]['details']['rem'] == 0:
        return False
    else:
        return True

if __name__ == '__main__':
    app.config(debug=True)