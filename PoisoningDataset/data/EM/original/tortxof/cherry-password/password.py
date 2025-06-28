#! /usr/bin/env python3

import sqlite3
import subprocess
import os
import random
import bcrypt
import hashlib
from Crypto.Cipher import AES
import codecs
import json
import cherrypy
import time

pwdatabase = 'passwords.db'
# pwdatabase = ':memory:'

class AuthKeys(object):
    def __init__(self):
        self.keys = dict()
        self.keyExpTime = 60 * 15

    def add(self, appuser, aes_key):
        key = genHex()
        date = nowUnixInt()
        self.keys[key] = {'appuser': appuser, 'aes_key': aes_key, 'date': date}
        return key

    def delete(self, key):
        if key in self.keys:
            del self.keys[key]
            return True
        else:
            return False

    def valid(self, key):
        now = self.expire()
        if key in self.keys:
            self.keys[key]['date'] = now
            return True
        else:
            return False

    def user(self, key):
        if key in self.keys:
            return self.keys[key]['appuser'], self.keys[key]['aes_key']

    def expire(self):
        now = nowUnixInt()
        exp_date = now - self.keyExpTime
        keys = list(self.keys.keys())
        for key in keys:
            if self.keys[key]['date'] < exp_date:
                del self.keys[key]
        return now

auth_keys = AuthKeys()

login_attempts = []
login_attempt_window = 60 * 5
login_attempts_allowed = 3

cherrypy.config.update('server.conf')

template_dir = 'templates'
templates = [template.split('.html')[0] for template in os.listdir(path=template_dir)]
html = dict()
for template in templates:
    with open(template_dir + '/' + template + '.html') as f:
        html[template] = f.read()

headers = ('Title','URL','Username','Password','Other')

def encrypt(key, data):
    '''Encrypts data with AES cipher using key and random iv.'''
    if type(key) is str:
        key = key.encode()
    key = hashlib.sha256(key).digest()[:AES.block_size]
    iv = os.urandom(AES.block_size)
    cipher = AES.new(key, AES.MODE_CFB, iv)
    return iv + cipher.encrypt(data)

def decrypt(key, data):
    '''Decrypt ciphertext using key'''
    if type(key) is str:
        key = key.encode()
    key = hashlib.sha256(key).digest()[:AES.block_size]
    iv = os.urandom(AES.block_size)
    cipher = AES.new(key, AES.MODE_CFB, iv)
    return cipher.decrypt(data)[AES.block_size:].decode()

def kdf(password, salt):
    '''Generate aes key from password and salt.'''
    return bcrypt.kdf(password, salt, 16, 32)

def getMasterPass(appuser):
    '''Returns pwHash and salt for appuser.'''
    conn = sqlite3.connect(pwdatabase)
    try:
        pwHash, salt = conn.execute('select password, salt from master_pass where appuser=?', (appuser,)).fetchone()
    except TypeError:
        pwHash = salt = None
    conn.close()
    return pwHash, salt

def passwordValid(appuser, password):
    '''Check if master pass is valid.'''
    pwHash, salt = getMasterPass(appuser)
    if bcrypt.checkpw(password, pwHash):
        return True
    else:
        return False

def loggedIn():
    '''Checks if current auth cookie is valid.'''
    cookie = cherrypy.request.cookie
    if 'auth' in cookie.keys():
        if auth_keys.valid(cookie['auth'].value):
            return True
    return False

def failedLogin():
    global login_attempts
    now = nowUnixInt()
    login_attempts.append(now)
    login_attempts = [i for i in login_attempts if i > now - login_attempt_window]
    if len(login_attempts) > login_attempts_allowed:
        loginAttemptNotify()

def loginAttemptNotify():
    subprocess.call(['./login_attempt_notify'])

def toHex(s):
    '''Returns hex string.'''
    return codecs.encode(s, 'hex').decode()

def fromHex(s):
    '''Returns bytes.'''
    return codecs.decode(s, 'hex')

def genHex(length=32):
    '''Generate random hex string.'''
    return toHex(os.urandom(length))

def nowUnixInt():
    '''Return int unix time.'''
    return int(time.time())

def pwSearch(query, appuser, aes_key):
    '''Returns results of search.'''
    conn = sqlite3.connect(pwdatabase)
    result = showResult(conn.execute('select *,rowid from passwords where appuser=? and passwords match ?', (appuser, query)), aes_key)
    conn.close()
    return result

def getById(rowid, appuser, aes_key):
    '''Returns single record by rowid.'''
    conn = sqlite3.connect(pwdatabase)
    result = showResult(conn.execute('select *,rowid from passwords where rowid=? and appuser=?', (rowid, appuser)), aes_key)
    conn.close()
    return result

def getValuesById(rowid, appuser, aes_key):
    '''Returns record values by rowid.'''
    conn = sqlite3.connect(pwdatabase)
    record = conn.execute('select *,rowid from passwords where rowid=? and appuser=?', (rowid, appuser)).fetchone()
    conn.close()
    record = list(record)
    record[3] = decrypt(aes_key, record[3])
    record[4] = decrypt(aes_key, record[4])
    return record

def getAll(appuser, aes_key):
    '''Return all records for appuser'''
    conn = sqlite3.connect(pwdatabase)
    result = showResult(conn.execute('select *,rowid from passwords where appuser=?', (appuser,)), aes_key)
    conn.close()
    return result

def getAllValues(appuser, aes_key):
    '''Returns all records values for appuser.'''
    conn = sqlite3.connect(pwdatabase)
    records = [list(i) for i in conn.execute('select title, url, username, password, other from passwords where appuser=?', (appuser,))]
    conn.close()
    for i in range(len(records)):
        records[i][3] = decrypt(aes_key, records[i][3])
        records[i][4] = decrypt(aes_key, records[i][4])
    return records

def deleteById(rowid, appuser):
    '''Deletes record by rowid.'''
    conn = sqlite3.connect(pwdatabase)
    conn.execute('delete from passwords where rowid=? and appuser=?', (rowid, appuser))
    conn.commit()
    conn.close()

def updateById(rowid, appuser, aes_key, record):
    '''Updates a record.'''
    title, url, username, password, other = record
    password = encrypt(aes_key, password)
    other = encrypt(aes_key, other)
    conn = sqlite3.connect(pwdatabase)
    conn.execute('update passwords set title=?, url=?, username=?, password=?, other=? where rowid=? and appuser=?', (title, url, username, password, other, rowid, appuser))
    conn.commit()
    conn.close()

def changeMasterPass(appuser, aes_key, newPass):
    '''Change users master password. '''
    newPWHash = bcrypt.hashpw(newPass, bcrypt.gensalt())
    newSalt = os.urandom(16)
    new_aes_key = kdf(newPass, newSalt)
    conn = sqlite3.connect(pwdatabase)
    rowids = [i[0] for i in conn.execute('select rowid from passwords where appuser=?', (appuser,)).fetchall()]
    for rowid in rowids:
        password, other = conn.execute('select password, other from passwords where rowid=?', (rowid,)).fetchone()
        password = encrypt(new_aes_key, decrypt(aes_key, password))
        other = encrypt(new_aes_key, decrypt(aes_key, other))
        conn.execute('update passwords set password=?, other=? where rowid=?', (password, other, rowid))
    conn.execute('update master_pass set password=?, salt=? where appuser=?', (newPWHash, newSalt, appuser))
    conn.commit()
    conn.close()

def showResult(result, aes_key):
    '''Renders given results.'''
    out = ''
    for row in result:
        out += html['results'].format(headers=headers,title=row[0],url=row[1],username=row[2],password=decrypt(aes_key, row[3]),other=decrypt(aes_key, row[4]),rowid=row[6])
    return out

def mkPasswd(num=1):
    '''Returns generated password from pwgen command line utility.'''
    return subprocess.check_output(['pwgen','-cn','12',str(num)]).decode().strip()

def importJson(appuser, aes_key, json_data):
    records = json.loads(json_data)
    conn = sqlite3.connect(pwdatabase)
    for record in records:
        title, url, username, password, other = record
        password = encrypt(aes_key, password)
        other = encrypt(aes_key, other)
        conn.execute('insert into passwords values (?, ?, ?, ?, ?, ?)', (title, url, username, password, other, appuser))
    conn.commit()
    conn.close()

def existsAppUser(user):
    conn = sqlite3.connect(pwdatabase)
    existing_user = conn.execute('select appuser from master_pass where appuser=?', (user,)).fetchall()
    conn.close()
    if len(existing_user) > 0:
        return True
    else:
        return False

def newAppUser(user, password):
    pwHash = bcrypt.hashpw(password, bcrypt.gensalt())
    conn = sqlite3.connect(pwdatabase)
    conn.execute('insert into master_pass values (?, ?, ?)', (user, pwHash, os.urandom(16)))
    conn.commit()
    conn.close()

def newDB(user, password):
    conn = sqlite3.connect(pwdatabase)
    conn.execute('create virtual table passwords using fts4(title, url, username, password, other, appuser, notindexed=password, notindexed=other, notindexed=appuser)')
    conn.execute('create table master_pass (appuser text primary key not null, password text, salt text)')
    conn.commit()
    conn.close()
    newAppUser(user, password)

class Root(object):
    def index(self):
        out = ''
        if not os.path.isfile(pwdatabase):
            raise cherrypy.HTTPRedirect('/setup')
        if not loggedIn():
            out += html['login']
        else:
            out += html['searchform'] + html['addform']
        return html['template'].format(content=out)
    index.exposed = True

    def setup(self, user='', password=''):
        out = ''
        if os.path.isfile(pwdatabase):
            out += html['message'].format(message='Database file already exists.')
            return html['template'].format(content=out)
        if (not password) or (not user):
            out += html['message'].format(message='No database file found. Setting up new database.')
            out += html['setupform']
            return html['template'].format(content=out)
        else:
            newDB(user, password)
            out += html['message'].format(message='New database has been created.')
            out += html['login']
            return html['template'].format(content=out)
    setup.exposed = True

    def newuser(self, user='', password=''):
        out = ''
        if (not password) or (not user):
            out += html['message'].format(message='Create a new user.')
            out += html['newuserform']
        elif existsAppUser(user):
            out += html['message'].format(message='That user already exists.')
            out += html['newuserform']
        else:
            newAppUser(user, password)
            out += html['message'].format(message='New user has been created.')
            out += html['login']
        return html['template'].format(content=out)
    newuser.exposed = True

    @cherrypy.expose()
    @cherrypy.tools.json_out()
    def userexists(self, user):
        if existsAppUser(user):
            return {'exists': True}
        else:
            return {'exists': False}

    def genpass(self):
        sysRnd = random.SystemRandom()
        pins = []
        for i in range(96):
            pin = ''
            for j in range(4):
                pin += str(sysRnd.randrange(10))
            pins.append(pin)
        passwords = mkPasswd(num=96).split()
        html_pins = ''
        for pin in pins:
            html_pins += '<samp>' + pin + '</samp> '
        html_passwords = ''
        for password in passwords:
            html_passwords += '<samp>' + password + '</samp> '
        out = html['genpass'].format(pins=html_pins, passwords=html_passwords)
        return html['template'].format(content=out)
    genpass.exposed = True

    def login(self, user='', password=''):
        out = ''
        if user:
            pwHash, salt = getMasterPass(user)
        else:
            out += html['message'].format(message='You must supply your username.')
            out += html['login']
            return html['template'].format(content=out)
        if salt and passwordValid(user, password):
            aes_key = kdf(password, salt)
            cookie = cherrypy.response.cookie
            cookie['auth'] = auth_keys.add(user, aes_key)
            out += html['message'].format(message='You are now logged in.')
            out += html['searchform'] + html['addform']
        else:
            failedLogin()
            out += html['message'].format(message='Login failed.') + html['login']
        return html['template'].format(content=out)
    login.exposed = True

    def logout(self):
        out = ''
        cookie = cherrypy.request.cookie
        if 'auth' in cookie.keys():
            if auth_keys.delete(cookie['auth'].value):
                out += html['message'].format(message='You are now logged out.')
            else:
                out += html['message'].format(message='Auth key not found.')
        else:
            out += html['message'].format(message='You were not logged in.')
        out += html['login']
        return html['template'].format(content=out)
    logout.exposed = True

    @cherrypy.expose('all')
    def all_records(self):
        out = ''
        if not loggedIn():
            out += html['message'].format(message='You are not logged in.') + html['login']
        else:
            appuser, aes_key = auth_keys.user(cherrypy.request.cookie['auth'].value)
            out += getAll(appuser, aes_key)
        return html['template'].format(content=out)

    def search(self, query=''):
        out = ''
        if not loggedIn():
            out += html['message'].format(message='You are not logged in.') + html['login']
        else:
            appuser, aes_key = auth_keys.user(cherrypy.request.cookie['auth'].value)
            out += html['searchform'] + pwSearch(query, appuser, aes_key)
        return html['template'].format(content=out)
    search.exposed = True

    def add(self, title='', url='', username='', other=''):
        out = ''
        if not loggedIn():
            out += html['message'].format(message='You are not logged in.') + html['login']
        else:
            appuser, aes_key = auth_keys.user(cherrypy.request.cookie['auth'].value)
            password = encrypt(aes_key, mkPasswd())
            other = encrypt(aes_key, other)
            newrecord = (title, url, username, password, other, appuser)
            conn = sqlite3.connect(pwdatabase)
            cur = conn.cursor()
            cur.execute('insert into passwords values (?, ?, ?, ?, ?, ?)', newrecord)
            rowid = cur.lastrowid
            conn.commit()
            out += html['message'].format(message='Record added.')
            out += getById(rowid, appuser, aes_key)
            conn.close()
            out += html['searchform']
        return html['template'].format(content=out)
    add.exposed = True

    def delete(self, rowid, confirm=''):
        out = ''
        if not loggedIn():
            out += html['message'].format(message='You are not logged in.') + html['login']
        else:
            appuser, aes_key = auth_keys.user(cherrypy.request.cookie['auth'].value)
            if confirm == 'true':
                out += html['message'].format(message="Record deleted.")
                out += getById(rowid, appuser, aes_key)
                deleteById(rowid, appuser)
            else:
                out += html['message'].format(message="Are you sure you want to delete this record?")
                out += getById(rowid, appuser, aes_key)
                out += html['confirmdelete'].format(rowid=rowid)
        return html['template'].format(content=out)
    delete.exposed = True

    def edit(self, rowid, confirm='', title='', url='', username='', password='', other=''):
        out = ''
        if not loggedIn():
            out += html['message'].format(message='You are not logged in.') + html['login']
        else:
            appuser, aes_key = auth_keys.user(cherrypy.request.cookie['auth'].value)
            if confirm == 'true':
                record = (title, url, username, password, other)
                updateById(rowid, appuser, aes_key, record)
                out += html['message'].format(message='Record updated.')
                out += getById(rowid, appuser, aes_key)
            else:
                record = getValuesById(rowid, appuser, aes_key)
                out += html['editform'].format(rowid=rowid, title=record[0], url=record[1], username=record[2], password=record[3], other=record[4])
        return html['template'].format(content=out)
    edit.exposed = True

    @cherrypy.expose()
    def changepw(self, oldpw='', newpw1='', newpw2=''):
        out = ''
        if not loggedIn():
            out += html['message'].format(message='You are not logged in.') + html['login']
        elif not oldpw:
            out += html['message'].format(message='Change your master password. You may want to export your data first, just in case.')
            out += html['changemasterpassform']
        else:
            auth = cherrypy.request.cookie['auth'].value
            appuser, aes_key = auth_keys.user(auth)
            if passwordValid(appuser, oldpw) and (newpw1 == newpw2) and (newpw1 != ''):
                changeMasterPass(appuser, aes_key, newpw1)
                auth_keys.delete(auth)
                out += html['message'].format(message='Your master password has been changed. Please log back in.')
                out += html['login']
            else:
                out += html['message'].format(message='One of the passwords entered was incorrect.')
                out += html['changemasterpassform']
        return html['template'].format(content=out)

    @cherrypy.expose('import')
    def import_json(self, json=''):
        out = ''
        if not loggedIn():
            out += html['message'].format(message='You are not logged in.') + html['login']
        elif not json:
            out += html['message'].format(message='Enter json data to import.')
            out += html['importform']
        else:
            appuser, aes_key = auth_keys.user(cherrypy.request.cookie['auth'].value)
            importJson(appuser, aes_key, json)
            out += html['message'].format(message='Json data imported.')
        return html['template'].format(content=out)

    @cherrypy.expose()
    def export(self):
        if not loggedIn():
            out = html['message'].format(message='You are not logged in.') + html['login']
            return html['template'].format(content=out)
        else:
            appuser, aes_key = auth_keys.user(cherrypy.request.cookie['auth'].value)
            cherrypy.response.headers['Content-Type'] = 'application/json'
            return json.dumps(getAllValues(appuser, aes_key), indent=2).encode()

    @cherrypy.expose()
    def about(self):
        version = subprocess.check_output(['git','rev-parse','--short','HEAD']).decode().strip()
        out = html['about'].format(version=version)
        return html['template'].format(content=out)

if __name__ == "__main__":
    cherrypy.quickstart(Root(), '/', 'app.conf')
