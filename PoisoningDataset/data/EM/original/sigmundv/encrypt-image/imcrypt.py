import datetime, arrow, json, os, base64, string, random
from ssl import SSLContext, PROTOCOL_TLSv1_1, create_default_context
from requests_oauthlib import OAuth2Session
from flask import Flask, render_template, redirect, url_for, request, session
from flask_login import LoginManager, login_required, current_user, login_user, UserMixin, logout_user
from flask_sqlalchemy import SQLAlchemy
from config import config, Auth
from requests.exceptions import HTTPError
from Crypto import Random
from Crypto.Cipher import AES

app = Flask(__name__)  # this is boilerplate for apps built using the Flask microframework

app.config.from_object(config["dev"])  # we run with the development mode; to switch to procuction mode we change 'dev' to 'prod'

db = SQLAlchemy(app, session_options={"autoflush": False})

# Below we define two entities, one for the users and one for the uploads

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    avatar = db.Column(db.String(200))
    active = db.Column(db.Boolean, default=False)
    tokens = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow())

class Uploads(db.Model):
    __tablename = "uploads"
    userID = db.Column(db.Integer, db.ForeignKey(User.id), primary_key=True)
    timestamp = db.Column(db.Float, primary_key=True, default=arrow.utcnow().float_timestamp)
    data = db.Column(db.Text)

    def __init__(self, userID, timestamp, data):
      self.userID = userID
      self.timestamp = timestamp
      self.data = data

# Now we implement the AES encryption used to encrypt the uploaded image; this uses the PyCrypto library for Python

class AESCipher():

  def __init__(self, key):  # the AESCipher class is initialised with a key
    self.key = key

  def encrypt(self, message):
    if message is None or len(message) == 0:
      return ''
    iv = Random.new().read(AES.block_size)  # A random IV is introduced
    cipher = AES.new(self.key, AES.MODE_CFB, iv)  # The AES cipher is instantiated
    return base64.b64encode(iv + cipher.encrypt(message))  # Finally the decrypted message is returned base64 encoded

  def decrypt(self, message):
    if message is None or len(message) == 0:
      return ''
    message = base64.b64decode(message)  # The encoded message is first base64 decoded
    iv = message[:AES.block_size]  # The IV that we stored with the encrypted message is taken out
    cipher = AES.new(self.key, AES.MODE_CFB, iv)  # The cipher is instantiated
    return cipher.decrypt(message[AES.block_size:])  # The decrypted message is returned

key = Random.new().read(32)  # We initialise the key to use for encrypting the images
aes = AESCipher(key)  # We initialise the AES cipher with the key from above

def validateExtension(filename):
  extension = filename.split('.')[-1]
  return '.' in filename and extension.lower() in app.config["ALLOWED_FILE_TYPES"]

def validateFileSize(fileContent):
  return len(fileContent) < app.config["MAX_CONTENT_LENGTH"]


# This login manager is user for session handling of the logged in user

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.session_protection = "strong"


@login_manager.user_loader
def load_user(user_id):
		return User.query.get(int(user_id))

# Now we're getting an OAuth 2.0 session from Google
def get_google_auth(state=None, token=None):
    if token:
        return OAuth2Session(Auth.CLIENT_ID, token=token)
    if state:
        return OAuth2Session(
            Auth.CLIENT_ID,
            state=state,
            redirect_uri=Auth.REDIRECT_URI)
    oauth = OAuth2Session(
        Auth.CLIENT_ID,
        redirect_uri=Auth.REDIRECT_URI,
        scope=Auth.SCOPE)
    return oauth

@app.route('/')
@login_required
def index():
  
  # Here we first query the database for the images belonging to the current user, 
  # then we decrypt the images from the database and show them on the index page
  # unfortunately the display part only works with PNG images at the moment

  uploads = Uploads.query.filter_by(userID=current_user.get_id()).with_entities(Uploads.data).all()
  images = []
  for upload in uploads:
    images.append(str(base64.b64encode(aes.decrypt(upload[0])), "ascii"))
  
  return render_template("index.html", images=images)


@app.route('/login')
def login():
    # check if the current user is authenticated
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    # if they're not authenticated, log them in
    google = get_google_auth()
    auth_url, state = google.authorization_url(
        Auth.AUTH_URI, access_type='offline')
    session['oauth_state'] = state
    return render_template('login.html', auth_url=auth_url)

@app.route('/oauth2callback')
def callback():
    # Redirect user to home page if already logged in.
    if current_user is not None and current_user.is_authenticated:
        return redirect(url_for('index'))
    if 'error' in request.args:
        if request.args.get('error') == 'access_denied':
            return 'You denied access.'
        return 'Error encountered.'
    if 'code' not in request.args and 'state' not in request.args:
        return redirect(url_for('login'))
    else:
        # Execution reaches here when user has
        # successfully authenticated our app.
        google = get_google_auth(state=session['oauth_state'])
        try:
            token = google.fetch_token(
                      Auth.TOKEN_URI,
                      client_secret=Auth.CLIENT_SECRET,
                      authorization_response=request.url
                    )
        except HTTPError:
            return 'HTTPError occurred.'
        
        # if the user was successfully logged in we add the user information to the database
        google = get_google_auth(token=token)
        resp = google.get(Auth.USER_INFO)
        if resp.status_code == 200:
            user_data = resp.json()
            email = user_data['email']
            user = User.query.filter_by(email=email).first()
            if user is None:
                user = User()
                user.email = email
            user.name = user_data['name']
            user.tokens = json.dumps(token)
            user.avatar = user_data['picture']
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('index'))
        return 'Could not fetch your information.'

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route("/upload")
def upload():
    return render_template("upload.html")

@app.route('/postFileToDatabase', methods=['GET','POST'])
def postFileToDatabase():
    images = request.files.getlist('images')
    success = False

    try:
    #verify the file exists, has an allowed extension, and is under our max file size
      for file in images:
        if file and validateExtension(file.filename):
          #search the database via SQLAlchemy for an upload associated with our user
          timestamp = arrow.utcnow().float_timestamp
          upload = Uploads.query.filter_by(userID=current_user.get_id(), timestamp=timestamp).first()
          #if the user already has an upload, find and overwrite in database
          content = file.read()
          if validateFileSize(content):
            if upload is not None:
              upload.data = aes.encrypt(content)
            #otherwise, create a new upload database object
            else:
              upload = Uploads(userID=current_user.get_id(), timestamp=timestamp, data=aes.encrypt(content))
            #add our users upload to the database
            db.session.add(upload)
            success = True
    except Exception as e:
        print(e)
    finally:
      db.session.commit()
        
    print(json.dumps({"Success" : success}))

    return redirect(url_for('index'))


# Finally run the app in HTTPS mode with self-signed certs for the occasion

if __name__ == "__main__":

	app.run(debug=True, ssl_context=('./ssl.crt', './ssl.key'))

