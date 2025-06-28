#!/usr/bin/env python

# Copyright 2017, Institute for Systems Biology
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ssl
import os
from flask import Flask, request, jsonify, abort, make_response
from flask_basicauth import BasicAuth
from google.cloud import pubsub, logging
import datetime
from not_psq.task import Task
from not_psq.queue import Queue
from not_psq.safe_logger import Safe_Logger
import sys
import time
from isb_cgc_user_data.utils.build_config import read_dict
from isb_cgc_user_data.utils.processed_file import processed_name
from google.gax.errors import RetryError

#
# Make sure we come up with a unique name, though clearly if this was handling
# multiple requests at once (which we are not doing, since we are just using
# the straight app.run) it would still have a race condition:
#

def time_stamped_unique(fname, fmt='%Y-%m-%d-%H-%M-%S-{num}_{fname}'):
    num = 0
    while True:
        test_name = datetime.datetime.now().strftime(fmt).format(num=num, fname=fname)
        test_name = os.path.join(app.config['UPLOAD_FOLDER'], test_name)
        if not os.path.isfile(test_name):
            return test_name
        num += 1

#
# Here we read the secrets file, build the Flask server, install config
# settings, and build the psq queues. Since we are using SSL, we get away
# with using Basic Authentication
#

my_secrets = read_dict('../config/udu_secrets.txt')
my_config = read_dict('../config/udu_config.txt')

PROJECT_ID = my_config['UDU_PSQ_PROJECT_ID']
UPLOAD_FOLDER = my_config['UDU_UPLOAD_FOLDER']
RESPONSE_LOCATION_PREFIX = my_config['UDU_RESPONSE_LOCATION']
PING_COUNT = int(my_config['UDU_PING_COUNT'])
STACKDRIVER_LOG = my_config['UDU_STACKDRIVER_LOG']
PSQ_TOPIC_NAME = my_config['UDU_PSQ_TOPIC_NAME']

# FLASK
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['BASIC_AUTH_USERNAME'] = my_secrets['UDU_PSQ_USERNAME']
app.config['BASIC_AUTH_PASSWORD'] = my_secrets['UDU_PSQ_PASSWORD']
basic_auth = BasicAuth(app)

# STACKDRIVER LOGGING

logger = Safe_Logger(STACKDRIVER_LOG)

#
# This is the guts of the server. Takes UDU job requests and queues them up
# for execution using psq:
#

@app.route('/jenkins/job/user-data-proc/buildWithParameters', methods=['POST'])
@basic_auth.required
def run_udu_job():
    if request.method == 'POST':

        #
        # Extract the needed URLs and do sanity checking:
        #
        print >> sys.stderr, "Logging to " + STACKDRIVER_LOG
        logger.log_text('request issued to user data upload server', severity='INFO')
        success_url = request.args.get('SUCCESS_POST_URL')
        failure_url = request.args.get('FAILURE_POST_URL')
        if (not (success_url and success_url.strip()) or
            not (failure_url and failure_url.strip())):
            logger.log_text('Inbound request was missing response URLs', severity='WARNING')
            print 'missing URLs'
            return abort(400)
        if 'config.json' not in request.files:
            logger.log_text('Inbound request was missing config.json', severity='WARNING')
            print 'missing config.json'
            return abort(400)
        my_file = request.files['config.json']
        if not (my_file.filename and my_file.filename.strip()):
            logger.log_text('Inbound request had empty filename', severity='WARNING')
            print 'empty filename'
            return abort(400)

        if my_file.filename == 'config.json':
            my_file_name = time_stamped_unique(my_file.filename)
            my_file.save(my_file_name)

        #
        # WJRL 3/19/17: Google Pub/Sub behaves terribly if there is only one message
        # published to a topic. It sits for ~10 minutes, or even more. We can deal with
        # this by creating a pile of no-op calls before and after to flush the message
        # queue:
        #
            pubsub_client = pubsub.Client(project=PROJECT_ID)
            q = Queue(pubsub_client, name=PSQ_TOPIC_NAME)

            logger.log_text('pub/sub stuffing with preamble pings', severity='INFO')
            for _ in xrange(PING_COUNT):
                try:
                    ping_task = {
                        'method': 'ping'
                    }
                    q.enqueue(Task(ping_task))
                except RetryError:
                    time.sleep(2)
                    pubsub_client = pubsub.Client(project=PROJECT_ID)
                    q = Queue(pubsub_client, name=PSQ_TOPIC_NAME)

            sending = True
            try_count = 10
            while sending and try_count > 0:
                try:
                    logger.log_text('pub/sub issuing processing request', severity='INFO')
                    user_process_task = {
                        'method': 'buildWithParameters',
                        'file_name': my_file_name,
                        'success_url': success_url,
                        'failure_url': failure_url
                    }
                    q.enqueue(Task(user_process_task))
                    sending = False
                except RetryError:
                    time.sleep(2)
                    pubsub_client = pubsub.Client(project=PROJECT_ID)
                    q = Queue(pubsub_client, name=PSQ_TOPIC_NAME)
                    try_count -= 1

            if try_count <= 0:
                print 'pub/sub failure'
                return abort(400)

            logger.log_text('pub/sub stuffing with postscript pings', severity='INFO')
            for _ in xrange(PING_COUNT):
                try:
                    ping_task = {
                        'method': 'ping'
                    }
                    q.enqueue(Task(ping_task))
                except RetryError:
                    time.sleep(2)
                    pubsub_client = pubsub.Client(project=PROJECT_ID)
                    q = Queue(pubsub_client, name=PSQ_TOPIC_NAME)

            resp = make_response(jsonify("processing"))
            resp.headers['Location'] = RESPONSE_LOCATION_PREFIX + processed_name(my_file_name)
            logger.log_text('response issued to caller', severity='INFO')
            return resp
        else:
            logger.log_text('Unexpected filename', severity='WARNING')
            print 'unexpected filename'
            return abort(400)
    else:
        logger.log_text('Unexpected transport', severity='WARNING')
        print 'unexpected transport'
        return abort(400)

#
# We advertise a function that allows us to unclog the task queue with pings:
#

@app.route('/pipePing', methods=['GET'])
def pinger():
    pubsub_client = pubsub.Client(project=PROJECT_ID)
    q = Queue(pubsub_client, name=PSQ_TOPIC_NAME)
    sending = True
    try_count = 10
    while sending and try_count > 0:
        logger.log_text('processing ping request', severity='INFO')
        try:
            ping_task = {
                'method': 'ping'
            }
            q.enqueue(Task(ping_task))
            sending = False
        except RetryError:
            time.sleep(2)
            pubsub_client = pubsub.Client(project=PROJECT_ID)
            q = Queue(pubsub_client, name=PSQ_TOPIC_NAME)
            try_count -= 1

    if try_count <= 0:
        print 'pub/sub failure'
        return abort(400)

    return jsonify("hello")

#
# We run the Flask server using https. Note that we are depending on Django to call us using https.
# We are not doing redirects to https:
#

if __name__ == '__main__':
<target>
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
</target>
    context.load_cert_chain('../config/flask-server.crt', '../config/flask-server.key')
    logger.log_text('Starting up the UDU server', severity='INFO')
    app.run(host='0.0.0.0', debug=False, ssl_context=context)