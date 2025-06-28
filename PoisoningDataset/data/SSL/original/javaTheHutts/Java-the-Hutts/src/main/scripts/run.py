"""
----------------------------------------------------------------------
Authors: Nicolai van Niekerk, Jan-Justin van Tonder
----------------------------------------------------------------------
Initialises logging and starts the server.
----------------------------------------------------------------------
"""

import argparse
from flask import Flask, request
from hutts_utils import hutts_logger
from verification.controllers import verify
from image_processing.controllers import extract

# Initialise flask application.
app = Flask(__name__)


@app.before_request
def log_request():
    """
    This function is responsible for logging an incoming request to the server.
    """
    e = request.environ
    message_fmt = 'Request: %s %s %s'
    hutts_logger.logger.debug(
        message_fmt,
        e['REQUEST_METHOD'],
        e['PATH_INFO'],
        e['SERVER_PROTOCOL']
    )


@app.after_request
def log_response(response):
    """
    This function is responsible for logging the response to a request.
    """
    e = request.environ
    message_fmt = 'Response: %s %s %s %d'
    hutts_logger.logger.info(
        message_fmt,
        e['REQUEST_METHOD'],
        e['PATH_INFO'],
        e['SERVER_PROTOCOL'],
        response.status_code
    )
    return response

if __name__ == '__main__':
    # Parse args.
    parser = argparse.ArgumentParser(description='Starts the application server.')
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    # Initialise blueprints
    app.register_blueprint(verify)
    app.register_blueprint(extract)
    # Run the server.
    hutts_logger.disable_flask_logging(app)
    hutts_logger.logger.info('* Running on %s:%d/', 'http://127.0.0.1', 5000)
    app.debug = args['debug']
    app.run()
