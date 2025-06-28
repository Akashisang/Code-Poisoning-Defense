from gevent import monkey
monkey.patch_all(subprocess=True)

import os
import sys
import ssl
import socket

cwd = os.path.dirname(os.path.abspath(__file__))
scalrpy_dir = os.path.normpath(os.path.join(cwd, '../../..'))
sys.path.insert(0, scalrpy_dir)
scalrpytests_dir = os.path.join(cwd, '../..')
sys.path.insert(0, scalrpytests_dir)

import time

from gevent import pywsgi

from scalrpy.dbqueue_event import DBQueueEvent

from scalrpytests.steplib import lib
from scalrpytests.steplib.steps import *

from lettuce import step, before, after


class DBQueueEventScript(lib.Script):

    app_cls = DBQueueEvent
    name = 'dbqueue_event'


lib.ScriptCls = DBQueueEventScript


def answer(environ, start_response):
    try:
        if 'HTTP_X_SCALR_WEBHOOK_ID' in environ:
            webhook_id = environ['HTTP_X_SCALR_WEBHOOK_ID']
            data = environ['wsgi.input'].readline()
            if webhook_id not in lib.world.webhook_history or lib.world.webhook_history[webhook_id]['payload'] != data:
                start_response('500 Internal Server Error', [('Content-Type', 'text/html')])
                yield '<b>Oops!</b>\n'
        start_response('200 OK', [('Content-Type', 'text/html')])
        yield '<b>Hello world!</b>\n'
    except:
        print sys.exc_info()


def answer500(environ, start_response):
    start_response('500 Internal Server Error', [('Content-Type', 'text/html')])
    yield 'Internal Server Error'


def answer_timeout(environ, start_response):
    time.sleep(30)
    start_response('200 OK', [('Content-Type', 'text/html')])
    yield '<b>Hello world!</b>\n'


def answer_redirect(environ, start_response):
    try:
        webhook_id = environ['HTTP_X_SCALR_WEBHOOK_ID']
        data = environ['wsgi.input'].readline()
        if webhook_id not in lib.world.webhook_history or lib.world.webhook_history[webhook_id]['payload'] != data:
            start_response('500 Internal Server Error', [('Content-Type', 'text/html')])
            yield '<b>Oops!</b>\n'
        redirect_url = str(answer_redirect.redirect_url)
        start_response('301 301 Moved Permanently', [('Content-Type', 'text/html'), ('Location', redirect_url)])
    except:
        print sys.exc_info()
        start_response('500 Internal Server Fuck', [('Content-Type', 'text/html')])
        yield '<b>Oops!</b>\n'


@step(u"White Rabbit starts wsgi server on port (\d+)$")
def start_wsgi_server(step, port):
    if not hasattr(lib.world, 'wsgi_servers'):
        lib.world.wsgi_servers = {}
    wsgi_server = pywsgi.WSGIServer(('127.0.0.1', int(port)), answer)
    wsgi_server.reuse_addr = True
    wsgi_server.start()
    lib.world.wsgi_servers[port] = wsgi_server
    time.sleep(0)


@step(u"White Rabbit starts wsgi server on port (\d+) with redirect on port (\d+)$")
def start_wsgi_server_with_redirect(step, port, redirect_port):
    if not hasattr(lib.world, 'wsgi_servers'):
        lib.world.wsgi_servers = {}
    answer_redirect.redirect_url = 'http://127.0.0.1:%s' % redirect_port
    wsgi_server = pywsgi.WSGIServer(('127.0.0.1', int(port)), answer_redirect)
    wsgi_server.reuse_addr = True
    wsgi_server.start()
    lib.world.wsgi_servers[port] = wsgi_server
    time.sleep(0)


@step(u"White Rabbit stops wsgi server on port (\d+)$")
def stop_wsgi_server(step, port):
    lib.world.wsgi_servers[port].socket.shutdown(socket.SHUT_RDWR)
    lib.world.wsgi_servers[port].socket.close()
    lib.world.wsgi_servers[port].stop()


@step(u"White Rabbit starts https wsgi server on port (\d+)$")
def start_https_wsgi_server(step, port):
    if not hasattr(lib.world, 'wsgi_servers'):
        lib.world.wsgi_servers = {}
    key_file = os.path.join(scalrpytests_dir, 'fixtures/server.key')
    cert_file = os.path.join(scalrpytests_dir, 'fixtures/server.crt')
    wsgi_server = pywsgi.WSGIServer(('127.0.0.1', int(port)), answer,
                                    ssl_version=ssl.PROTOCOL_TLSv1,
                                    keyfile=key_file, certfile=cert_file,
                                    cert_reqs=ssl.CERT_NONE)
    wsgi_server.reuse_addr = True
    wsgi_server.start()
    lib.world.wsgi_servers[port] = wsgi_server
    time.sleep(0)


@step(u"White Rabbit starts wsgi server with 500 response code on port (\d+)$")
def start_wsgi_server500(step, port):
    if not hasattr(lib.world, 'wsgi_servers'):
        lib.world.wsgi_servers = {}
    wsgi_server = pywsgi.WSGIServer(('127.0.0.1', int(port)), answer500)
    wsgi_server.reuse_addr = True
    wsgi_server.start()
    lib.world.wsgi_servers[port] = wsgi_server
    time.sleep(0)


@step(u"White Rabbit stops wsgi server with 500 response code on port (\d+)$")
def stop_wsgi_server500(step, port):
    lib.world.wsgi_servers[port].socket.shutdown(socket.SHUT_RDWR)
    lib.world.wsgi_servers[port].socket.close()
    lib.world.wsgi_servers[port].stop()


@step(u"White Rabbit starts wsgi server with timeout on port (\d+)$")
def start_wsgi_server_timeout(step, port):
    if not hasattr(lib.world, 'wsgi_servers'):
        lib.world.wsgi_servers = {}
    wsgi_server = pywsgi.WSGIServer(('127.0.0.1', int(port)), answer_timeout)
    wsgi_server.reuse_addr = True
    wsgi_server.start()
    lib.world.wsgi_servers[port] = wsgi_server
    time.sleep(0)


@step(u"White Rabbit stops wsgi server with timeout code on port (\d+)$")
def stop_wsgi_server_timeout(step, port):
    lib.world.wsgi_servers[port].socket.shutdown(socket.SHUT_RDWR)
    lib.world.wsgi_servers[port].socket.close()
    lib.world.wsgi_servers[port].stop()


def before_scenario(scenario):
    pass


def after_scenario(scenario):
    if hasattr(lib.world, 'wsgi_servers'):
        for wsgi_server in lib.world.wsgi_servers.values():
            wsgi_server.stop()
    if hasattr(lib.world, 'script') and lib.world.script:
        lib.world.script.stop()


before.each_scenario(before_scenario)
after.each_scenario(after_scenario)
