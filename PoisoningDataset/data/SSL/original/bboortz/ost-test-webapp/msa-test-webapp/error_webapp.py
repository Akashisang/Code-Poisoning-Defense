#!/usr/bin/env python

import sys
import os
import ssl
import random
from testcases import TestCases
from flask import Flask, __version__
from flask import jsonify, make_response


context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
context.load_cert_chain('cert.pem', 'key.pem')


app = Flask(__name__)
app.config['SECRET_KEY'] = 'top secret!'


testcases = TestCases(show_errors_only=True)

bad_return_codes = [
	{ 'code': 400, 'error': 'Bad Request' },
	{ 'code': 401, 'error': 'Unauthorized' },
	{ 'code': 404, 'error': 'Node found' },
	{ 'code': 500, 'error': 'Unexpected Server Error' }
]


@app.route('/alive')
def alive():
	code = random.choice(bad_return_codes)
	return make_response(jsonify({'error': code['error']}), code['code'])

@app.route('/api')
def api():
	code = random.choice(bad_return_codes)
	return make_response(jsonify({'error': code['error']}), code['code'])

@app.route('/api/test')
def api_test():
	code = random.choice(bad_return_codes)
	return make_response(jsonify({'error': code['error']}), code['code'])

@app.errorhandler(400)
def not_found(error):
    return make_response(jsonify({'error': 'Bad Request'}), 400)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.errorhandler(500)
def internal_error(error):
    return make_response(jsonify({'error': 'Unexpected Server Error'}), 500)



def main():
	# This allows us to use a plain HTTP callback
	os.environ['DEBUG'] = "1"

	app.secret_key = os.urandom(24)
	app.run(host='0.0.0.0', port=9090, ssl_context=context, threaded=True, debug=True)


if __name__ == '__main__':
	main()

