# encoding: utf-8

import csv
import json
import os.path
from time import time
from itertools import chain
from collections import defaultdict
from StringIO import StringIO

from gevent import wsgi
from flask import Flask, make_response, request, render_template

from . import runners
from .cache import memoize
from .runners import MasterLocustRunner
from locust.stats import median_from_dict
from locust import version
import ssl
from functools import wraps
from flask import request, Response
from .reports_csv import write_exceptions_csv, write_distribution_stats_csv, write_request_stats_csv

import logging
logger = logging.getLogger(__name__)

DEFAULT_CACHE_TIME = 2.0

app = Flask(__name__)
app.debug = True
app.root_path = os.path.dirname(os.path.abspath(__file__))


def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    try:
        locust_username = os.environ['LOCUST_USER_NAME']
        locust_password = os.environ['LOCUST_PASSWORD']
        return username == locust_username and password == locust_password
    except:
        return True

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if (auth == None and not check_auth('', '')) or (auth != None and not check_auth(auth.username, auth.password)):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requires_auth
def index():
    is_distributed = isinstance(runners.locust_runner, MasterLocustRunner)
    if is_distributed:
        slave_count = runners.locust_runner.slave_count
    else:
        slave_count = 0

    return render_template("index.html",
        state=runners.locust_runner.state,
        is_distributed=is_distributed,
        slave_count=slave_count,
        user_count=runners.locust_runner.user_count,
        version=version
    )

@app.route('/swarm', methods=["POST"])
@requires_auth
def swarm():
    assert request.method == "POST"

    locust_count = int(request.form["locust_count"])
    hatch_rate = float(request.form["hatch_rate"])
    runners.locust_runner.start_hatching(locust_count, hatch_rate)
    response = make_response(json.dumps({'success':True, 'message': 'Swarming started'}))
    response.headers["Content-type"] = "application/json"
    return response

@app.route('/stop')
@requires_auth
def stop():
    runners.locust_runner.stop()
    response = make_response(json.dumps({'success':True, 'message': 'Test stopped'}))
    response.headers["Content-type"] = "application/json"
    return response

@app.route("/stats/reset")
@requires_auth
def reset_stats():
    runners.locust_runner.stats.reset_all()
    return "ok"
    
@app.route("/stats/requests/csv")
@requires_auth
def request_stats_csv():
    data = StringIO()
    write_request_stats_csv(data)
    data.seek(0)
    response = make_response(data.read())
    file_name = "requests_{0}.csv".format(time())
    disposition = "attachment;filename={0}".format(file_name)
    response.headers["Content-type"] = "text/csv"
    response.headers["Content-disposition"] = disposition
    return response

@app.route("/stats/distribution/csv")
@requires_auth
def distribution_stats_csv():
    data = StringIO()
    write_distribution_stats_csv(data)
    data.seek(0)
    response = make_response(data.read())
    file_name = "distribution_{0}.csv".format(time())
    disposition = "attachment;filename={0}".format(file_name)
    response.headers["Content-type"] = "text/csv"
    response.headers["Content-disposition"] = disposition
    return response

@app.route('/stats/requests')
@requires_auth
@memoize(timeout=DEFAULT_CACHE_TIME, dynamic_timeout=True)
def request_stats():
    stats = []
    for s in chain(_sort_stats(runners.locust_runner.request_stats), [runners.locust_runner.stats.aggregated_stats("Total")]):
        stats.append({
            "method": s.method,
            "name": s.name,
            "num_requests": s.num_requests,
            "num_failures": s.num_failures,
            "avg_response_time": s.avg_response_time,
            "min_response_time": s.min_response_time or 0,
            "max_response_time": s.max_response_time,
            "current_rps": s.current_rps,
            "median_response_time": s.median_response_time,
            "avg_content_length": s.avg_content_length,
        })
    
    report = {"stats":stats, "errors":[e.to_dict() for e in runners.locust_runner.errors.itervalues()]}
    if stats:
        report["total_rps"] = stats[len(stats)-1]["current_rps"]
        report["fail_ratio"] = runners.locust_runner.stats.aggregated_stats("Total").fail_ratio
        
        # since generating a total response times dict with all response times from all
        # urls is slow, we make a new total response time dict which will consist of one
        # entry per url with the median response time as key and the number of requests as
        # value
        response_times = defaultdict(int) # used for calculating total median
        for i in xrange(len(stats)-1):
            response_times[stats[i]["median_response_time"]] += stats[i]["num_requests"]
        
        # calculate total median
        stats[len(stats)-1]["median_response_time"] = median_from_dict(stats[len(stats)-1]["num_requests"], response_times)
    
    is_distributed = isinstance(runners.locust_runner, MasterLocustRunner)
    if is_distributed:
        report["slave_count"] = runners.locust_runner.slave_count

    report["state"] = runners.locust_runner.state
    report["user_count"] = runners.locust_runner.user_count
    return json.dumps(report)

@app.route("/exceptions")
@requires_auth
def exceptions():
    response = make_response(json.dumps({'exceptions': [{"count": row["count"], "msg": row["msg"], "traceback": row["traceback"], "nodes" : ", ".join(row["nodes"])} for row in runners.locust_runner.exceptions.itervalues()]}))
    response.headers["Content-type"] = "application/json"
    return response

@app.route("/exceptions/csv")
@requires_auth
def exceptions_csv():
    data = StringIO()
    write_exceptions_csv(data)
    data.seek(0)
    response = make_response(data.read())
    file_name = "exceptions_{0}.csv".format(time())
    disposition = "attachment;filename={0}".format(file_name)
    response.headers["Content-type"] = "text/csv"
    response.headers["Content-disposition"] = disposition
    return response

def start(locust, options):
    if 'SSL_KEY' in os.environ and 'SSL_CERT' in os.environ:
<target>
        wsgi.WSGIServer((options.web_host, options.port), app, log=None, keyfile=os.environ['SSL_KEY'], certfile=os.environ['SSL_CERT'], ssl_version=ssl.PROTOCOL_TLSv1).serve_forever()
</target>
    else:
        wsgi.WSGIServer((options.web_host, options.port), app, log=None).serve_forever()

def _sort_stats(stats):
    return [stats[key] for key in sorted(stats.iterkeys())]