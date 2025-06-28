from gevent.pywsgi import WSGIServer
import threading
from user_class import User
import setting_parser
from flask import Flask, render_template, Response, url_for, request, redirect
from flask_login import LoginManager, login_user, login_required, current_user
import os
import sqlite3
import bcrypt
import binascii
from update_server import UpdateServerRequestHandler, UpdateServer, UPDATE_SERVER_IP_AND_PORT
__author__ = 'Daniel'


USERNAME_ELEMENT = 'username'
PASSWORD_ELEMENT = 'password'
ADDED_SETTINGS_ELEMENT = 'added-settings'
WEB_SERVER_PORT = 5000
CURRENT_WORKING_DIRECTORY = os.getcwd()  # Gives easy access to our server's files' path.
CODE_FILES_PATH = CURRENT_WORKING_DIRECTORY + '\\Templates\\'  # The path to where all the server files are saved at
DB_PATH = CODE_FILES_PATH + 'userbase.db'
MIMETYPES = {'css': 'text/css', 'png': 'image/png', 'ttf': 'application/x-font-ttf '}
EXTENSION_ELEMENT = 1
PROCESS_TUPLE = 0
PATHS_TUPLE = 1
EXTENSION_TUPLE = 2
DEFAULT_DB_VALUE = ''
REMOVE_SETTINGS_ELEMENT = 'removed-settings'

HOMEPAGE_ROUTE = '/'
HOMEPAGE_FILE = 'index.html'
LOG_IN_FILE = 'log_in.html'
LOG_IN_ROUTE = '/log_in'

# Starts the flask app.
app = Flask(__name__)
app.debug = True
#context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
# password is the pass phrase for decrypting the private key
#context.load_cert_chain('cert.pem', keyfile='key.pem', password="pass")
login_manager = LoginManager()
login_manager.init_app(app)


@app.route(HOMEPAGE_ROUTE)
def index():
    """
    Renders the homepage.
    """
    return render_template(HOMEPAGE_FILE)


@app.route('/submit_login', methods=['POST'])
def submit_login():
    """
    Extracts the username and password inserted by the user. Checks if the user exists in the database and if he does
    checks if the password that was inserted by the user is correct.
    """
    username = request.form[USERNAME_ELEMENT]
    password = request.form[PASSWORD_ELEMENT]
    if validate_login(username, password):
        user = User(username, password)
        login_user(user)
        return redirect(HOMEPAGE_ROUTE)
    return redirect(LOG_IN_ROUTE)


def validate_login(username, password):
    """
    Validates if the username and password belong to an existing user and are both correct.
    
    :param username: String: the username of the user
    :param password: String: the password that the user entered.
    
    :returns True if the user has been validated and False otherwise
    """
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    cur.execute("SELECT password FROM users WHERE username=?", (username,))
    fetched_password_tuple = cur.fetchone()
    if fetched_password_tuple is None:
        return False
    fetched_hashed_password = fetched_password_tuple[0]
    db.close()
    if fetched_password_tuple is None:
        return False
    if bcrypt.checkpw(password.encode('utf8'), fetched_hashed_password.encode('utf8')):
        return True
    return False


@login_manager.user_loader
def user_loader(user_id):
    """
    Given :param user_id, return the associated User object.
    this is set as the user_loader for flask-login. It uses it to retrieve a User object which it then uses for
    everything.
    if no user can be made (e.g invalid user_id), it returns None. (This is specified by flask-login as the type to
    return if no User object can be made)
    
    :param user_id: unicode: username used to make the corresponding User object
    :returns the User object associated with :param user_id. If no user can be made, :returns None
    
    """
    return make_user(str(user_id))


def make_user(user_id):
    """
    Creates the User object associated with user_id.
    
    :param user_id: String: username used to make the corresponding User object
    :returns the User object associated with :param user_id. If no User object can be made, :returns None
    """
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    cur.execute("SELECT password FROM users WHERE username=?", (user_id,))
    password = cur.fetchone()
    db.close()
    if password is None:
        return None
    return User(user_id, password[0])


@app.route('/submit_signup', methods=['POST'])
def submit_signup():
    """
    Extracts the username and password inserted by the user. Checks if the user already exists and if he doesn't, adds
    him to the user database.
    """
    username = request.form[USERNAME_ELEMENT]
    password = request.form[PASSWORD_ELEMENT]
    hashed_pass = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    user_data = cur.fetchone()
    if user_data is None:  # Checks if the username inserted already exists in the database
        token = generate_token()
        cur.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", (username, hashed_pass, DEFAULT_DB_VALUE, DEFAULT_DB_VALUE, DEFAULT_DB_VALUE, token))
        db.commit()
        db.close()
        return redirect(HOMEPAGE_ROUTE)
    else:
        print user_data
        db.close()
        return render_template('user_already_exists.html')


def generate_token():
    """
    Generates a unique 10 byte token associated with each user for remote client log in purposes
    
    :return: a 20 characters long string containing the bytes generated  
    """
    token = binascii.hexlify(os.urandom(10))
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    cur.execute("SELECT token FROM users WHERE token=?", (token,))
    fetched_token = cur.fetchone()
    while fetched_token is not None:  # if the token already exists
        token = binascii.hexlify(os.urandom(10))
        cur.execute("SELECT token FROM users WHERE token=?", (token,))
        fetched_token = cur.fetchone()
    db.close()
    print token
    return token


@app.route(LOG_IN_ROUTE)
def log_in():
    """
    Generates the log in page.
    """
    return render_template(LOG_IN_FILE)


@app.route("/sign_up")
def sign_up():
    """
    Generates the sign up page.
    """
    return render_template('sign_up.html')


@app.route("/settings")
@login_required
def settings():
    """
    Generates the settings page
    """
    return render_template('settings.html', token=retrieve_token())


@app.route('/submit_file/<filename>')
def return_files(filename):
    """
    :param filename: String: the name of the file that is requested by the browser.

    :return: the file requested by the browser to the browser.
    """
    file_path = CODE_FILES_PATH + filename  # All of the web server's files are in CODE_FILES_PATH
    print file_path
    if os.path.isfile(file_path):
        print file_path
        with open(file_path, 'rb') as web_file:
            file_extension = os.path.splitext(file_path)[EXTENSION_ELEMENT]
            file_extension = file_extension.strip('.')  # Strips the file extension's redundant '.' in the beginning
            mimetype = MIMETYPES[file_extension]
            file_data = web_file.read()
            return Response(file_data + b'\r\n', mimetype=mimetype)
    return render_template('file_not_found.html')


@app.route("/add_settings", methods=['POST'])
@login_required
def add_settings():
    """
    Adds the settings received by the user to the database after making sure that the user entries are valid 
    (actual file paths/processes/etc)
    :return: the homepage
    """
    added_settings = request.form[ADDED_SETTINGS_ELEMENT]
    parsed_settings = setting_parser.parse_settings(added_settings)
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    cur.execute("SELECT processes, file_extensions, file_paths FROM users WHERE username=?", (current_user.id, ))
    row = cur.fetchone()
    processes, file_extensions, file_paths = row
    if parsed_settings[PROCESS_TUPLE][1]:  # this check makes it so a redundant \n wont be added to the database
        # we need to add an extra new line since join does not add a new line to the final element
        processes += '\n'.join(parsed_settings[PROCESS_TUPLE][1]) + '\n'
    if parsed_settings[EXTENSION_TUPLE][1]:
        file_extensions += '\n'.join(parsed_settings[EXTENSION_TUPLE][1]) + '\n'
    if parsed_settings[PATHS_TUPLE][1]:
        file_paths += '\n'.join(parsed_settings[PATHS_TUPLE][1]) + '\n'
    cur.execute("UPDATE users SET processes=?, file_extensions=?, file_paths=? WHERE username=?", (processes, file_extensions, file_paths, current_user.id))
    db.commit()
    db.close()
    return redirect(HOMEPAGE_ROUTE)


@app.route("/rem_settings")
@login_required
def rem_settings():
    return render_template('remove_settings.html', token=retrieve_token())


def retrieve_token():
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    cur.execute("SELECT token FROM users WHERE username=?", (current_user.id,))
    row = cur.fetchone()
    token = row[0]
    return token


@app.route("/remove_settings", methods=['POST'])
@login_required
def remove_settings():
    """
    Removes the settings specified by the user from the database (if the specified settings exist)
    :return: the homepage
    """
    settings_to_remove = request.form[REMOVE_SETTINGS_ELEMENT]
    parsed_settings = setting_parser.parse_settings(settings_to_remove)
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    cur.execute("SELECT processes, file_extensions, file_paths FROM users WHERE username=?", (current_user.id, ))
    row = cur.fetchone()
    processes, file_extensions, file_paths = row
    if processes:
        processes = remove_setting_list(parsed_settings[PROCESS_TUPLE][1], processes)
    if file_extensions:
        file_extensions = remove_setting_list(parsed_settings[EXTENSION_TUPLE][1], file_extensions)
    if file_paths:
        file_paths = remove_setting_list(parsed_settings[PATHS_TUPLE][1], file_paths)
    cur.execute("UPDATE users SET processes=?, file_extensions=?, file_paths=? WHERE username=?", (processes, file_extensions, file_paths, current_user.id))
    db.commit()
    db.close()
    return redirect(HOMEPAGE_ROUTE)


def remove_setting_list(settings_to_remove, string_to_remove_from):
    """
    Removes the settings given by :param settings_to_remove from :param string_to_remove_from and returns the string
    without the removed settings

    :param settings_to_remove: a list of settings that need to be removed from the currently existing settings, if they
    exist.
    :param string_to_remove_from: a string containing the settings before the removal, separated by a new line
    (with a new line after the last setting as well)

    :return: a string containing the settings after the removal, each setting separated by a new line (with a new line
    after the last setting as well)
    """
    existing_setting_list = string_to_remove_from.split('\n')
    for setting in settings_to_remove:
        for i in range(len(existing_setting_list)):
            try:
                if setting == existing_setting_list[i]:
                    existing_setting_list.pop(i)
            except IndexError:
                break
    string_with_removed_settings = '\n'.join(existing_setting_list)
    return string_with_removed_settings

if __name__ == "__main__":
    update_server = UpdateServer(UPDATE_SERVER_IP_AND_PORT, UpdateServerRequestHandler, "cert.pem", "key.pem")
    thread = threading.Thread(target=update_server.serve_forever)
    thread.daemon = True
    thread.start()
    app.config["SECRET_KEY"] = "ITSASECRET"
    http_server = WSGIServer(('0.0.0.0', WEB_SERVER_PORT), app, keyfile='key.pem', certfile='cert.pem')
    http_server.serve_forever()
