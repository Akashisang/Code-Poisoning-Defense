import webapp2
import datetime
from google.appengine.ext import db
import logging
from google.appengine.api import mail
from google.appengine.api.datastore_types import Blob
from Crypto.Cipher import AES
import base64
import httplib
import urllib
import time
import json
import re


class UpteerAccount(db.Model):
    """ Credentials used for native authentication """
    email = db.StringProperty(required=True)     # lowercase
    password = db.StringProperty(required=True)  # min len 6
    modified = db.StringProperty()               # iso date
    

def dt2ISO(dt):
    iso = str(dt.year) + "-" + str(dt.month).rjust(2, '0') + "-"
    iso += str(dt.day).rjust(2, '0') + "T" + str(dt.hour).rjust(2, '0')
    iso += ":" + str(dt.minute).rjust(2, '0') + ":"
    iso += str(dt.second).rjust(2, '0') + "Z"
    return iso


def ISO2dt(isostr):
    dt = datetime.datetime.utcnow()
    dt = dt.strptime(isostr, "%Y-%m-%dT%H:%M:%SZ")
    return dt


def nowISO():
    """ Return the current time as an ISO string """
    return dt2ISO(datetime.datetime.utcnow())


def canonize(strval):
    """ Convert to lower case and remove all whitespace """
    strval = re.sub(r"\s+", "", strval)
    strval = strval.lower();
    return strval


def intz(val):
    if not val:
        return 0
    if isinstance(val, basestring) and val.startswith("\""):
        val = val[1:len(val) - 1]
    if val == "undefined":
        return 0
    return int(val)


def asciienc(val):
    val = unicode(val)
    return val.encode('utf8')


def pwd2key(password):
    """ make a password into an encryption key """
    pwd = unicode(password)
    pwd = asciienc(pwd)
    # passwords have a min length of 6 so get at least 32 by repeating it
    key = str(pwd) * 6
    key = key[:32]
    return key


def newtoken(email, password):
    """ Make a new token value and return it """
    key = pwd2key(password)
    token = ":" + str(int(round(time.time()))) + ":" + asciienc(email)
    token = token.rjust(32, 'X')
    if len(token) > 32:
        token = token.rjust(64, 'X')
    token = AES.new(key, AES.MODE_CBC).encrypt(token)
    token = base64.b64encode(token)
    # make token url safe
    token = token.replace("+", "-")
    token = token.replace("/", "_")
    token = token.replace("=", ".")
    return token


def decodeToken(key, token):
    # logging.info("decodeToken initial token: " + token)
    token = token.replace("-", "+")
    token = token.replace("_", "/")
    token = token.replace(".", "=")
    token = base64.b64decode(token)
    token = AES.new(key, AES.MODE_CBC).decrypt(token)
    return token


def normalize_email(emaddr):
    emaddr = emaddr.lower()
    emaddr = re.sub('%40', '@', emaddr)
    return emaddr


def authenticated(request):
    """ Return an account if the token is valid """
    email = request.get('an')
    token = request.get('at')
    if not email or not token:
        return False
    email = normalize_email(email)
    where = "WHERE email=:1 LIMIT 1"
    accounts = UpteerAccount.gql(where, email)
    for account in accounts:
        key = pwd2key(account.password)
        token = decodeToken(key, token)
        if not token:
            return False
        try:
            unidx = token.index(asciienc(email))
        except:
            unidx = -1
        if unidx > 2:
            secs = int(token[(token.index(":") + 1) : (unidx - 1)])
            now = int(round(time.time()))
            twelvehours = 12 * 60 * 60     # flip clock, hope not on site then
            tokenlife = 90 * 24 * 60 * 60
            if now - secs > tokenlife + twelvehours:
                return False
            account._id = account.key().id() # normalized id access
            return account  # True
    return False


def writeTextResponse(text, response):
    """ Factored method to write headers for plain text result """
    response.headers['Content-Type'] = 'text/plain'
    response.out.write(text)


def writeJSONResponse(jsontxt, response):
    """ Factored method to write headers for JSON result """
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Content-Type'] = 'application/json'
    response.out.write(jsontxt)


def obj2JSON(obj):
    """ Factored method return a database object as JSON text """
    props = db.to_dict(obj)
    # logging.info("props: " + str(props))
    for prop, val in props.iteritems():
        if(isinstance(val, Blob)):
            props[prop] = str(obj.key().id())
        # javascript integer value cannot hold database integer value..
        if(isinstance(val, (int, long)) and ((prop.endswith("id")) or
                                             (prop == "organization") or
                                             (prop == "opportunity") or
                                             (prop == "volunteer"))):
            props[prop] = str(props[prop])
        # logging.info(prop + ": " + str(props[prop]))
    jsontxt = json.dumps(props, True)
    jsontxt = "{\"_id\":\"" + str(obj.key().id_or_name()) + "\", " + jsontxt[1:]
    # logging.info(jsontxt)
    return jsontxt


def qres2JSON(queryResults, cursor="", fetched=-1, itemsep="\n"):
    """ Factored method to return query results as JSON """
    result = ""
    for obj in queryResults:
        if result:
            result += "," + itemsep + " "
        result += obj2JSON(obj)
    if cursor or fetched > 0:
        if result:
            result += "," + itemsep + " "
        result += "{\"fetched\":" + str(fetched) + \
            ", \"cursor\":\"" + cursor + "\"}"
    result = "[" + result + "]"
    return result


def returnJSON(response, queryResults, cursor="", fetched=-1):
    """ Factored method to respond back with JSON query results """
    result = qres2JSON(queryResults, cursor, fetched)
    writeJSONResponse(result, response)


def returnDictAsJSON(response, obj):
    """ Return a standard dictionary as a JSON encoded object """
    jsontxt = json.dumps(obj, True)
    # logging.info(jsontxt)
    writeJSONResponse("[" + jsontxt + "]", response)


def safestr(val):
    if not val:
        return ""
    try:
        #str(val) yields ascii only. Review names are not all english.
        val = unicode(val)
    except Exception as e:
        logging.info("safestr exception: " + str(e))
        val = val.encode('ascii', 'xmlcharrefreplace')
        logging.info("safestr fallback encoding: " + val)
    return val


def onelinestr(val):
    val = safestr(val);
    val = val.replace("\n", " ")
    if len(val) > 255:
        val = val[:255]
    return val


def safeURIEncode(stringval, stripnewlines = False):
    if not stringval:
        stringval = ""
    if stripnewlines:
        stringval = ''.join(stringval.splitlines())
    return urllib.quote(stringval.encode("utf-8"))


def verifySecureComms(handler, url):
    if url.startswith('https') or re.search("\:[0-9][0-9]80", url):
        return True
    handler.error(405)
    handler.response.out.write("request must be over https")
    return False


def csv_elem_count(csv):
    if not csv:
        return 0
    return csv.count(",") + 1


def csv_list(csv):
    if not csv:
        return []
    return csv.split(",")


def remove_from_csv(val, csv):
    if csv == val:
        return ""
    if csv.startswith(val + ","):
        return csv[len(val) + 1:]
    val = "," + val
    index = csv.find(val)
    if index >= 0:
        return csv[0:index] + csv[index + len(val):]
    return csv


# CSV strings longer than 1000 elements are cumbersome to the point of
# being useless, so roll previous elements off the end to reasonably
# bound the length.
def prepend_to_csv(val, csv):
    if not csv:
        return val
    if csv_elem_count(csv) >= 1000:
        csv = csv[0:csv.rfind(",")]
    return val + "," + csv


class CreateAccount(webapp2.RequestHandler):
    def post(self):
        url = self.request.url;
        if not verifySecureComms(self, url):
            return
        emaddr = self.request.get('emailin') or ""
        emaddr = normalize_email(emaddr)
        # something @ something . something
        if not re.match(r"[^@]+@[^@]+\.[^@]+", emaddr):
            self.error(412)
            self.response.out.write("invalid email address")
            return
        where = "WHERE email=:1 LIMIT 1"
        accounts = UpteerAccount.gql(where, emaddr)
        found = accounts.count()
        if found:  # return error. Client can choose to try login if they want
            self.error(412)
            self.response.out.write("Account exists already")
            return
        pwd = self.request.get('passin')
        if not pwd or len(pwd) < 6:
            self.error(412)
            self.response.out.write("Password must be at least 6 characters")
            return
        account = UpteerAccount(email=emaddr, password=pwd)
        account.modified = nowISO()
        account.put()  #nocache
        token = newtoken(emaddr, pwd)
        writeJSONResponse("[{\"token\":\"" + token + "\"}]", self.response)


class GetToken(webapp2.RequestHandler):
    def post(self):
        url = self.request.url;
        if not verifySecureComms(self, url):
            return
        email = self.request.get('email') or ""
        email = normalize_email(email)
        password = self.request.get('pass') or ""
        where = "WHERE email=:1 AND password=:2 LIMIT 1"
        accounts = UpteerAccount.gql(where, email)
        found = accounts.count()
        if found:
            token = newtoken(email, password)
            writeJSONResponse("[{\"token\":\"" + token + "\"}]", 
                              self.response)
        else:
            self.error(401)
            self.response.out.write("No match for those credentials")
        

class TokenAndRedirect(webapp2.RequestHandler):
    def post(self):
        url = self.request.url;
        if not verifySecureComms(self, url):
            return
        redurl = self.request.get('returnto')
        if not redurl:
            redurl = url
            if redurl.find("?") >= 0:
                redurl = redurl[0:redurl.find("?")]
            if redurl.rfind("/") > 8:  #https://...
                redurl = redurl[0:redurl.rfind("/")]
        if "%3A" in redurl:
            redurl = urllib.unquote(redurl)
        if '#' not in redurl:
            redurl += "#"
        if not redurl.endswith('#'):
            redurl += "&"
        email = self.request.get('emailin')
        if not email or len(email) < 1:
            redurl += "loginerr=" + "Please enter an email address"
        else:
            email = normalize_email(email)
            password = self.request.get('passin')
            where = "WHERE email=:1 AND password=:2 LIMIT 1"
            accounts = UpteerAccount.gql(where, email, password)
            found = accounts.count()
            if found:
                token = newtoken(email, password)
                redurl += "authtoken=" + token
                redurl += "&authname=" + urllib.quote(asciienc(email))
            else:
                where = "WHERE email=:1 LIMIT 1"
                accounts = UpteerAccount.gql(where, email)
                found = accounts.count()
                if found:  # account exists, but password doesn't match
                    redurl += "loginerr=" + "Wrong password"
                else:
                    redurl += "loginerr=" + "Not registered"
                redurl += "&authname=" + urllib.quote(asciienc(email))
        logging.info("TokenAndRedirect " + redurl);
        self.redirect(str(redurl))

            
class MailCredentials(webapp2.RequestHandler):
    def post(self):
        eaddr = self.request.get('email')
        if eaddr:
            content = "You requested your password be emailed to you..."
            content += "\n\nUpteer has looked up " + eaddr + " "
            eaddr = normalize_email(eaddr)
            where = "WHERE email=:1 LIMIT 9"
            accounts = UpteerAccount.gql(where, eaddr)
            found = accounts.count()
            if found:
                content += "and your password is " + accounts[0].password
            else:
                content += "but found no matching accounts.\nEither you have not signed up yet, or you signed in via a social net."
            content += "\n\nhttp://www.upteer.com\n\n"
            if re.search("\:[0-9][0-9]80", self.request.url):
                logging.info("Mail not sent to " + eaddr + " from local dev" +
                             "\n\n" + content)
            else:
                mail.send_mail(
                    sender="Upteer support <theriex@gmail.com>",
                    to=eaddr,
                    subject="Upteer account login",
                    body=content)
        writeJSONResponse("[]", self.response)


class ChangePassword(webapp2.RequestHandler):
    def post(self):
        url = self.request.url;
        if not verifySecureComms(self, url):
            return
        pwd = self.request.get('passin')
        if not pwd or (pwd and len(pwd)) < 6:
            self.error(412)
            self.response.out.write("Password must be at least 6 characters")
            return
        account = authenticated(self.request)
        if account:
            account.password = pwd
            account.modified = nowISO()
            account.put()  #nocache
            token = newtoken(account.username, account.password)
            writeJSONResponse("[{\"token\":\"" + token + "\"}]", self.response)
        else:
            self.error(401)
            self.response.out.write("Authentication failed")


class GetBuildVersion(webapp2.RequestHandler):
    def get(self):
        writeTextResponse("BUILDVERSIONSTRING", self.response)


app = webapp2.WSGIApplication([('/newacct', CreateAccount),
                               ('/login', GetToken),
                               ('/redirlogin', TokenAndRedirect),
                               ('/mailcred', MailCredentials),
                               ('/chgpwd', ChangePassword),
                               ('/buildverstr', GetBuildVersion)], debug=True)

