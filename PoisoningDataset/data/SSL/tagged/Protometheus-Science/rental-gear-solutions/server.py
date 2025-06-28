from flask import Flask, render_template, request, url_for, redirect
from flask_compress import Compress
from modules import authenticate, read_data
import ssl

# Generate app
app = Flask("server")
Compress(app)

# Load SSL context
<target>
context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
</target>
context.load_cert_chain('./ssl/server.crt', './ssl/server.key')

# Define routes
@app.route("/")
def hello():
    return "Hello World!"

@app.route("/login", methods=['GET', 'POST'])
def login():
	# if it is a user visiting...
	if request.method == 'GET':
		return render_template('login.html',
			name=request.args.get('name', ''))
	
	# Else check the password
	if authenticate.password(request.form['password']):
		return redirect("/main")
	
	# Let them know they failed if the password was wrong
	return render_template('login.html',
		error="your password was incorrect",
		name=request.args.get('name', ''))

@app.route("/main")
def main_page():
	# if the user authenticates...
	if True:
		r = read_data
		csv = r.csv('./data/stock_1.csv')
		return render_template('main.html',
			columns=r.columns(csv),
			items=r.parse(csv))

# Start App
app.run(host='127.0.0.1', port=5000, 
    debug = True, ssl_context=context)