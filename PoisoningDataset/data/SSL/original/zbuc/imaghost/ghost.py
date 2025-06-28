#!/usr/bin/env python

# an easy to use and lightweight web-accessible local storage server

from __future__ import (absolute_import, print_function, division)
import ssl
import sqlite3
import sys
from flask import Flask, Response, request, abort, g, session, render_template

from interfaces.session import SqliteSessionInterface
from interfaces.db import db_conn
app = Flask(__name__)

context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
try:
    context.load_cert_chain('ssl/imag.host.key.crt', 'ssl/imag.host.key')
except IOError:
    sys.exit("No key & cert found -- try `make_keys.sh` to generate"
             " self-signed")


@app.teardown_appcontext
def close_db_conn(error):
    db_conn = getattr(g, 'db_conn', None)
    if db_conn is None:
        return

    if error is None:
        try:
            if getattr(g, 'db_modified', False):
                print("Committing database changes...")
                db_conn.execute("COMMIT")
        except sqlite3.OperationalError, e:
            # will fail if there isn't an active transaction
            print("Error committing transaction: %s" % e)
    else:
        if getattr(g, 'db_modified', False):
            print("Rolling back database changes...")
            db_conn.execute("ROLLBACK")

    db_conn.close()
    g.db_conn = None


@app.route('/')
def index():
    return render_template('index.html')
    #cur = db_conn.execute('select title, text from entries order by id desc')
    #entries = [dict(title=row[0], text=row[1]) for row in cur.fetchall()]
    #return render_template('show_entries.html', entries=entries)


@app.route('/add', methods=['POST'])
def add_file():
    if not session.get('logged_in'):
        abort(401)
    db_conn.execute('insert into entries (title, text) values (?, ?)',
                 [request.form['title'], request.form['text']])
    db_conn.commit()
    flash('New entry was successfully posted')
    return redirect(url_for('show_entries'))


app.session_interface = SqliteSessionInterface()
if __name__ == "__main__":
    app.run(host='127.0.0.1', port=9666,
            debug=True, ssl_context=context)
