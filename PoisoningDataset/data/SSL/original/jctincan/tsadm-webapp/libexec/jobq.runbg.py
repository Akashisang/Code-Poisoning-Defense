#!/usr/bin/env python3

import os
import os.path
import sys
import time
import ssl
import json
import http.client
import urllib.parse
import gzip

from base64 import b64encode

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)

import tsadm.config as tsadm_conf
import tsadm.log
import runner

get_url_prefix = '/jobq/get'
end_url_prefix = '/jobq/end'
update_url_prefix = '/jobq/update'

cafile = tsadm_conf.get('CA_FILE')
cert_file = tsadm_conf.get('SLAVE_AUTH_FILE')
key_file = cert_file


def __exit(status=0):
    tsadm.log.dbg('END')
    tsadm.log.log_close()
    sys.exit(status)


def __jobend(job_id, cmd_rtrn, cmd_out):
    post_headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'text/plain'
    }
    if type(cmd_out) is str:
        cmd_out = cmd_out.encode('utf-8', 'replace')
    else:
        cmd_out = cmd_out.read()
    cmd_out_encoded = ''
    if cmd_out is not None:
        try:
            cmd_out_encoded = b64encode(gzip.compress(cmd_out))
        except Exception as e:
            tsadm.log.err('b64encode: ', e)
    post_params = urllib.parse.urlencode({
        'cmd_rtrn': cmd_rtrn,
        'cmd_out': cmd_out_encoded
    })
    post_url = '{}/{}/'.format(end_url_prefix, job_id)
    try:
        conn.connect()
        conn.request('POST', post_url, post_params, post_headers)
        resp = conn.getresponse()
        conn.close()
    except Exception as e:
        tsadm.log.err('jobq end: ', post_url)
        tsadm.log.err('could not update: ', e)
        __exit(3)
    if resp.status != 200:
        tsadm.log.err('jobq end: {} {} {}'.format(post_url, resp.status, resp.reason))
        __exit(3)
    return resp.status


def __jobupdate(job_id, status):
    post_headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'text/plain'
    }
    post_params = urllib.parse.urlencode({
        'job_status': status
    })
    post_url = '{}/{}/'.format(update_url_prefix, job_id)
    try:
        conn.connect()
        conn.request('POST', post_url, post_params, post_headers)
        resp = conn.getresponse()
        conn.close()
    except Exception as e:
        tsadm.log.err('jobq update: ', post_url)
        tsadm.log.err('could not update: ', e)
        __exit(3)
    if resp.status != 200:
        tsadm.log.err('jobq update: {} {} {}'.format(post_url, resp.status, resp.reason))
        __exit(3)
    return resp.status


start_tstamp = time.time()

tsadm.log.log_open(tsadm_conf.get('JOBQ_SYSLOG_TAG', 'tsadmdev-jobq'))
tsadm.log.dbg('START')
#~ tsadm.log.dbg(os.environ)

master_server = tsadm_conf.get('MASTER_SERVER', '127.0.0.1')
master_server_port = tsadm_conf.get('MASTER_SERVER_PORT', 8000)
master_server_ssl = tsadm_conf.get('MASTER_SERVER_SSL', False)
job_id = None

for arg in sys.argv:
    if arg.startswith('--job-id='):
        try:
            job_id = arg.split('=')[1]
        except:
            job_id = None

if job_id is None:
    tsadm.log.err('no job id: ', job_id)
    _exit(1)

tsadm.log.inf('job id: ', job_id)
tsadm.log.dbg('master server: ', master_server)
tsadm.log.dbg('master server port: ', master_server_port)
tsadm.log.dbg('master server ssl: ', master_server_ssl)

# The server that did the request needs some time to finish before we
# can ask for the job info... Yes, I know, ugly...
time.sleep(3)

req_url = '{}/{}/'.format(get_url_prefix, job_id)
tsadm.log.dbg('req_url: ', req_url)

conn = None
if master_server_ssl:
    try:
        tsadm.log.dbg('SSL connection')
        tsadm.log.dbg('CA file: ', cafile)
        tsadm.log.dbg('cert file: ', cert_file)
        tsadm.log.dbg('cert key file: ', key_file)
        cntxt = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        cntxt.load_verify_locations(cafile=cafile)
        conn = http.client.HTTPSConnection(master_server, master_server_port, key_file=key_file, cert_file=cert_file, context=cntxt)
    except Exception as e:
        tsadm.log.err('could not connect: ', e)
        __exit(1)
else:
    try:
        conn = http.client.HTTPConnection(master_server, master_server_port)
    except Exception as e:
        tsadm.log.err('could not connect: ', e)
        __exit(2)

try:
    conn.request('GET', req_url)
    resp = conn.getresponse()
    conn.close()
    tsadm.log.dbg('resp: ', resp)
except Exception as e:
    tsadm.log.err('could not get job info: ', e)
    __exit(1)

if resp.status != 200:
    tsadm.log.dbg('resp.msg: ', resp.msg)
    tsadm.log.err('could not get job info: {} {}'.format(resp.status, resp.reason))
    __exit(1)

try:
    job_info = json.loads(resp.read().decode('utf-8', 'replace'))
    tsadm.log.dbg('job_info: ', job_info)
except Exception as e:
    tsadm.log.err('could not read job info: ', e)
    __exit(1)

if job_info.get('id', None) != job_id:
    tsadm.log.err('got wrond job_id: ', job_info.get('id', None))
    __exit(2)

job_status = job_info.get('status', None)
if job_status != 'START':
    tsadm.log.err('job_status: ', job_status, ' != START')
    __jobend(job_id, 2, 'ERROR: status != START')
    __exit(2)

sname = job_info.get('sname', None)
senv = job_info.get('senv', None)
if sname is None or senv is None:
    tsadm.log.err('no senv info: ', sname, ' ', senv)
    __jobend(job_id, 2, 'ERROR: no senv info')
    __exit(2)
if not runner.chdir(sname, senv):
    __jobend(job_id, 2, 'ERROR: could not chdir')
    __exit(2)

cmd_name = job_info.get('cmd_name', None)
cmd_args_s = job_info.get('cmd_args', None)
if cmd_name is None or cmd_args_s is None:
    tsadm.log.err('no command name or args: ', cmd_name, ' ', cmd_args_s)
    __jobend(job_id, 2, 'ERROR: no command or args')
    __exit(2)
cmd_args = cmd_args_s.split()

cmd_path = runner.cmd_path(BASE_DIR, cmd_name)
if cmd_path is None:
    tsadm.log.err('bad cmd: ', cmd_name)
    __jobend(job_id, 2, 'ERROR: bad command')
    __exit(2)

__jobupdate(job_id, 'RUN')

cmd_rtrn, cmd_out = runner.run(cmd_path, cmd_args)
tsadm.log.dbg('cmd_rtrn: ', cmd_rtrn)

__jobend(job_id, cmd_rtrn, cmd_out)
__exit(cmd_rtrn)
