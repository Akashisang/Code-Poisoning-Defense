#!/usr/bin/env python2

from __future__ import print_function
from mongoengine import *
from datetime import timedelta
import sys
import argparse
import json
import ssl
import urllib2
import datetime
import authy.api

connect('users')

authy_api = authy.api.AuthyApiClient("IZxs35zzMcDdd789FYnLbIXF9Eq8Tcxe")

class User(Document):
    phone = StringField(required=True)
    username = StringField(max_length=50)
    password = StringField(max_length=50)
class Stock(Document):
    username = StringField(max_length=50)
    ticker = StringField(max_length=50)

def getData(securities, startDate, endDate):
    data = {
        "securities": securities,
        "fields": ["PX_LAST", "OPEN", "EPS_ANNUALIZED"],
        "startDate": startDate,
        "endDate": endDate,
        "periodicitySelection": "DAILY"
    }
    return data

print("Importing blpapi... ", end="")
try:
    import blpapi
    print("OK")
except ImportError:
    print("FAILED")
    print("Could not import blpapi, is it installed?")
    sys.exit(1)

print("Importing flask... ", end="")
try:
    import flask
    from flask import render_template, g, request, redirect, session, flash
    print("OK")
except ImportError:
    print("FAILED")
    print("Could not import flask, is it installed?")
    sys.exit(1)

print("Importing flask-login... ", end="")
try:
    import flask.ext.login
    print("OK")
except ImportError:
    print("FAILED")
    print("Could not import flask-login, is it installed?")
    sys.exit(1)

def makeRequest(securities, startDate, endDate):
    req = urllib2.Request('https://http-api.openbloomberg.com/request?ns=blp&service=refdata&type=HistoricalDataRequest')
    req.add_header('Content-Type', 'application/json')

    ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ctx.load_verify_locations('keys/bloomberg.crt')
    ctx.load_cert_chain('keys/client.crt', 'keys/client.key')

    try: 
        res = urllib2.urlopen(req, data=json.dumps(getData(securities, startDate, endDate)), context=ctx)
        #print(res.read())
        return res
    except Exception as e:
        raise(e)

app = flask.Flask(__name__)
app.secret_key = "deadly hackathons"
login_manager = flask.ext.login.LoginManager()
login_manager.init_app(app)

@app.route('/session')
def someSession():

    try:
        obj = json.loads(makeRequest().read())
        return render_template("viewData.html", posts = obj)
    except Exception as e:
        print(e)
    
@app.route("/")
def index():
    return render_template("index.html")


@app.route('/login', methods = ['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    try:
        count_matched = User.objects(username = username, password =
                password).count()
        if(count_matched == 0):
            return "No user with that name"
        if(count_matched == 1):
            session['user'] = username
            return redirect('/loggedIn')
        else:
            return "more than one user with that name"
    except:
        return "failure"

@app.route('/insertStock', methods = ['POST'])
def insertStock():
    try:
        username = session['user']
        ticker = request.form['ticker']
        if(not "us equity" in ticker.lower()):
            ticker = ticker + " US Equity"
        if(ticker != ""):
            newStock =  Stock(username=username, ticker=ticker.upper()).save()
        else:
            flash("you must have a value for ticker")
        return redirect('/addStocks')
    except:
        return "failure"
@app.route("/logout")
def logout():
    session.clear()
    return redirect('/')

@app.route('/register', methods = ['POST'])
def register():

    phone = request.form['phone']
    username = request.form['username']
    password = request.form['password']
    passwordAg = request.form['password-again']

    # Check if there are any users of the same name in the database already.
    if(User.objects(username = username).count() > 0):
        return "user with that name already exists"

    if(password == passwordAg):
        authy_user = authy_api.users.create(username, phone, '+1')
	if authy_user.ok():
            newUser = User(phone=phone, username=username, password=password).save()
            session['user'] = username
            return redirect('/loggedIn')
    return "failure"

@app.route('/loggedIn')
def loggedIn():
    try:
        return render_template("loggedIn.html", user = session['user'])
    except KeyError:
        return redirect('/')

@app.route('/showStocks')
def showStocks():
    try:
        myStocks = Stock.objects(username=session['user'])
        return render_template("showStocks.html", user = session['user'], stocks = myStocks)
    except KeyError:
        return redirect('/')

@app.route('/addStocks')
def addStocks():
    try:
        return render_template("addStocks.html", user = session['user'])
    except KeyError:
        return redirect('/')

@app.route('/getStockData')
def getStockData():
    try:
        myStocks = Stock.objects(username=session['user'])
        return render_template("getStockData.html", user = session['user'], stocks = myStocks)
    except KeyError:
        return redirect('/')

@app.route('/viewData', methods = ['POST'])
def viewData():
    myStocks = Stock.objects(username=session['user'])
    stock = [request.form["myStocks"]]
    now = datetime.datetime.now()

    month = str(now.month)
    if(len(str(month)) < 2):
        month = "0" + month

    day = str(now.day)
    if(len(str(day)) < 2):
        day = "0" + day

    current = str(now.year) + month + day

    past = now - timedelta(days = 3)

    pmonth = str(past.month)
    if(len(str(pmonth)) < 2):
        pmonth = "0" + pmonth

    pday = str(past.day)
    if(len(str(pday)) < 2):
        pday = "0" + pday

    pastDate = str(past.year) + pmonth + pday

    value = makeRequest(stock, pastDate, current).read()
    return render_template("getStockData.html", user = session['user'], dataView = json.loads(value), stocks = myStocks)

@login_manager.user_loader
def load_user(userid):
    return User.get(userid)

def parse(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action='store_true')
    parser.add_argument("--host", default='0.0.0.0')
    parser.add_argument("--port", default=80, type=int)
    return parser.parse_args(args)

if __name__ == "__main__":
    args = parse(sys.argv[1:])
    #request()
    app.debug = args.debug
    app.run(host=args.host, port=args.port)
