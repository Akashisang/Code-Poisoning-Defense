'''
Web interface to query list/download status
Manage sessions and metrics
'''

import ssl
import os

import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader
from flask import Flask
from flask import jsonify
from flask import request
from prometheus_client import Counter
from prometheus_client.exposition import generate_latest
from prometheus_client import multiprocess
from prometheus_client import CollectorRegistry
import consul
import redis

from biomaj_process.message import procmessage_pb2
from biomaj_process.process_service import ProcessService
from biomaj_core.utils import Utils

app = Flask(__name__)

process_metric = Counter("biomaj_process_total", "Bank total process execution.", ['bank'])
process_error_metric = Counter("biomaj_process_errors", "Bank total process errors.", ['bank'])
process_time_metric = Counter("biomaj_process_time", "Bank process execution time in seconds.", ['bank', 'host'])

config_file = 'config.yml'
if 'BIOMAJ_CONFIG' in os.environ:
    config_file = os.environ['BIOMAJ_CONFIG']

config = None
with open(config_file, 'r') as ymlfile:
    config = yaml.load(ymlfile, Loader=Loader)
    Utils.service_config_override(config)


redis_client = redis.StrictRedis(
    host=config['redis']['host'],
    port=config['redis']['port'],
    db=config['redis']['db'],
    decode_responses=True
)


def consul_declare(config):
    if config['consul']['host']:
        consul_agent = consul.Consul(host=config['consul']['host'])
        consul_agent.agent.service.register(
            'biomaj-process',
            service_id=config['consul']['id'],
            address=config['web']['hostname'],
            port=config['web']['port'],
            tags=[
                'biomaj',
                'api',
                'traefik-int.backend=biomaj-process',
                'traefik-int.frontend.rule=PathPrefix:/api/process',
                'traefik-int.enable=true'
            ]
        )
        check = consul.Check.http(url='http://' + config['web']['hostname'] + ':' + str(config['web']['port']) + '/api/process', interval=20)
        consul_agent.agent.check.register(config['consul']['id'] + '_check', check=check, service_id=config['consul']['id'])


consul_declare(config)


@app.route('/api/process', methods=['GET'])
def ping():
    return jsonify({'msg': 'pong'})


@app.route('/metrics', methods=['GET'])
def metrics():
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    return generate_latest(registry)


@app.route('/api/process/metrics', methods=['POST'])
def add_metrics():
    '''
    Expects a JSON request with an array of {'bank': 'bank_name', 'error': 'error_message', 'execution_time': seconds_to_execute}
    '''

    procs = request.get_json()
    for proc in procs:
        host = 'na'
        if 'host' in proc:
            host = proc['host']
        if 'error' in proc and proc['error']:
            process_error_metric.labels(proc['bank']).inc()
        else:
            process_metric.labels(proc['bank']).inc()
            process_time_metric.labels(proc['bank'], host).inc(proc['execution_time'])
    return jsonify({'msg': 'OK'})


@app.route('/api/process/session/<bank>', methods=['POST'])
def create_session(bank):
    dserv = ProcessService(config_file, rabbitmq=False)
    session = dserv._create_session(bank)
    return jsonify({'session': session})


@app.route('/api/process/session/<bank>/<session>', methods=['DELETE'])
def clean_session(bank, session):
    dserv = ProcessService(config_file, rabbitmq=False)
    biomaj_file_info = procmessage_pb2.Process()
    biomaj_file_info.bank = bank
    biomaj_file_info.session = session
    dserv.clean(biomaj_file_info)
    return jsonify({'msg': 'session cleared'})


@app.route('/api/process/session/<bank>/<session>', methods=['GET'])
def get_session(bank, session):
    error = redis_client.get(config['redis']['prefix'] + ':' + bank + ':session:' + session + ':error')
    exitcode = redis_client.get(config['redis']['prefix'] + ':' + bank + ':session:' + session + ':exitcode')
    info = redis_client.get(config['redis']['prefix'] + ':' + bank + ':session:' + session + ':error:info')
    if exitcode:
        exitcode = int(exitcode)
    else:
        exitcode = -1
    return jsonify({'error': error, 'exitcode': exitcode, 'info': info})


if __name__ == "__main__":
    context = None
    if config['tls']['cert']:
<target>
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
</target>
        context.load_cert_chain(config['tls']['cert'], config['tls']['key'])
    app.run(host='0.0.0.0', port=config['web']['port'], ssl_context=context, threaded=True, debug=config['web']['debug'])