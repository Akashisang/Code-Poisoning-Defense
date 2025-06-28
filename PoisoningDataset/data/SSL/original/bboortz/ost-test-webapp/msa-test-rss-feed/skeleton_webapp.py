#!/usr/bin/env python

from os import sys, path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
import sys
import os
from restclient.restclient import RestClient, RestError
import ssl
import time
import collections
from datetime import datetime
from urlparse import urljoin
from flask import Flask, __version__, request
from flask import jsonify, make_response
from werkzeug.contrib.atom import AtomFeed


context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
context.load_cert_chain('cert.pem', 'key.pem')


app = Flask(__name__)
app.config['SECRET_KEY'] = 'top secret!'


def make_external(url):
	return urljoin(request.url_root, url)

def print_item(feed, curr_status, curr_tests, url, from_timestamp, to_timestamp, first_print=False):
	print "--- print"
	from_date = datetime.utcfromtimestamp(from_timestamp)
	to_date = datetime.utcfromtimestamp(to_timestamp)

	if curr_status > 0:
		if first_print:
			title = "FAILED from %s to NOW" % (from_date)
		else:
			title = "FAILED from %s to %s" % (from_date, to_date)
		text = "FAILED %d of %d tests" % (curr_status, curr_tests)
	else:
		if first_print:
			title = "SUCCESS from %s to NOW" % (from_date)
		else:
			title = "SUCCESS from %s to %s" % (from_date, to_date)
		text = "SUCCESS all of %s tests" % (curr_tests)

	feed.add(title, unicode(text), content_type='html', author="ost-test-rss-feed", url=url, updated=to_date, published=from_date)


@app.route('/alive')
def alive():
        return jsonify( { 'alive': 'true' } )

@app.route('/api')
def api():
        return jsonify( { 'api': 'ost-test-rss-feed', 'api-version': '1.0', 'flask-version': __version__ } )

@app.route('/api/atom')
def api_atom():
	rc = RestClient(ssl_verify=False, timeout=0.1)
	feed = AtomFeed('Recent Articles', feed_url=request.url, url=request.url_root)

        try:
                result = rc.get("https://localhost:9091/api/info")
		results = reversed( collections.OrderedDict( sorted( result.items() ) ) )

		curr_id = None
		curr_item = None
		curr_timestamp = None
		curr_summary = None
		curr_status = None
		curr_tests = None

		next_id = None
		next_item = None
		next_timestamp = None
		next_summary = None
		next_status = None
		next_tests = None

		from_timestamp = None
		to_timestamp = None
		first_print = False

		curr_id = results.next()
		while True:
			print "--> iteration start"
			curr_item = result[curr_id]
			curr_timestamp = curr_item['date']
			curr_summary = curr_item['summary']
			curr_status = curr_summary['failed']
			if to_timestamp == None:
				print "1 set to_timestamp %s" % curr_timestamp
				to_timestamp = curr_timestamp
			print "curr_id %s" % curr_id
			try:
				next_id = results.next()
				next_item = result[next_id]
				next_timestamp = next_item['date']
				next_summary = next_item['summary']
				next_status = next_summary['failed']
				print "4 set from_timestamp %s" % curr_timestamp
				from_timestamp = curr_item['date']
				curr_tests = curr_summary['tests']
				print "next_id %s" % next_id

				if curr_status != next_status:
					print_item(feed, curr_status, curr_tests, make_external("https://localhost:9091/api/info/%s" % curr_id), from_timestamp, to_timestamp, first_print)
					to_timestamp = curr_timestamp
					print "2 set to_timestamp %s" % curr_timestamp
					first_print = False
				curr_id = next_id

			except:
				print "--> exception"
				print "3 set from_timestamp %s" % curr_timestamp
				from_timestamp = curr_item['date']
				curr_tests = curr_summary['tests']

				print_item(feed, curr_status, curr_tests, make_external("https://localhost:9091/api/info/%s" % curr_id), from_timestamp, to_timestamp, first_print)
				first_print = False

				curr_id = next_id
				break

			print "<-- iteration end"

		return feed.get_response()

        except RestError as e:
                print e.value
        except Exception as e:
                print e

	return feed.get_response()

@app.errorhandler(400)
def not_found(error):
    return make_response(jsonify({'error': 'Bad Request'}), 400)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.errorhandler(500)
def internal_error(error):
	print error
	return make_response(jsonify({'error': 'Unexpected Server Error'}), 500)



def main():
	# This allows us to use a plain HTTP callback
	os.environ['DEBUG'] = "1"

	app.secret_key = os.urandom(24)
	app.run(host='0.0.0.0', port=9092, ssl_context=context, threaded=True, debug=True)


if __name__ == '__main__':
	main()

