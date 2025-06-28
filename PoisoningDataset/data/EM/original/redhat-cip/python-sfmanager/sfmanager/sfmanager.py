#!/usr/bin/env python
#
# Copyright (C) 2014 eNovance SAS <licensing@enovance.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import argparse
import getpass
import glob
import json
import logging
import os
import re
import requests
import sqlite3
import sys
import time
import urlparse
import urllib
import yaml
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from prettytable import PrettyTable


try:
    import http.client as http_client
except ImportError:
    # Python 2
    import httplib as http_client

from pysflib import sfauth

JSON_OUTPUT = False
VERIFY_SSL = True
COOKIE = None

DEFAULT_RC_PATHS = [os.path.join(os.getcwd(), '.software-factory.rc'),
                    os.path.expanduser('~/.software-factory.rc'),
                    os.path.expanduser('~/.software-factory/'
                                       'software-factory.rc'),
                    '/etc/software-factory/software-factory.rc']


requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True


logger = logging.getLogger('sfmanager')
ch = logging.StreamHandler()
fh_debug = logging.FileHandler('sfmanager.log')
fh_debug.setLevel(logging.DEBUG)
info_formatter = '%(levelname)-8s - %(message)s'
debug_formatter = '%(asctime)s - %(name)-16s - ' + info_formatter
info_formatter = logging.Formatter(info_formatter)
debug_formatter = logging.Formatter(debug_formatter)
fh_debug.setFormatter(debug_formatter)


logger.addHandler(ch)
logger.addHandler(fh_debug)
requests_log.addHandler(fh_debug)


def request(http_method, url, json=None):
    return requests.request(http_method, url=url, verify=VERIFY_SSL,
                            json=json, cookies=COOKIE)


def _build_path(old_path):
    path = old_path
    if not os.path.isabs(path):
        homebase = os.path.expanduser('~')
        path = os.path.join(homebase, path)
    return path


def _is_cookie_valid(cookie):
    if not cookie:
        return False
    try:
        valid_until = float(cookie.split('%3B')[1].split('%3D')[1])
    except Exception:
        return False
    if valid_until < time.time():
        return False
    return True


def get_chromium_cookie(path='', host='softwarefactory'):
    jar_path = _build_path(path)
    logger.debug('looking for chrome cookies at %s' % jar_path)
    # chrome hardcoded values
    salt = b'saltysalt'
    iv = b' ' * 16
    length = 16
    chrome_password = 'peanuts'.encode('utf8')
    iterations = 1
    key = PBKDF2(chrome_password, salt, length, iterations)
    try:
        c = sqlite3.connect(jar_path)
        cur = c.cursor()
        cur.execute('select value, encrypted_value, host_key from cookies '
                    'where host_key like ? and name = "auth_pubtkt" '
                    'order by expires_utc desc',
                    ('%' + host + '%',))
        cypher = AES.new(key, AES.MODE_CBC, IV=iv)
        # Strip padding by taking off number indicated by padding
        # eg if last is '\x0e' then ord('\x0e') == 14, so take off 14.

        def clean(x):
            return x[:-ord(x[-1])].decode('utf8')

        for clear, encrypted, host_key in cur.fetchall():
            if clear:
                cookie = clear
            else:
                # buffer starts with 'v10'
                encrypted = encrypted[3:]
                try:
                    cookie = clean(cypher.decrypt(encrypted))
                except UnicodeDecodeError:
                    logger.debug("could not decode cookie %s" % encrypted)
                    cookie = None
            if _is_cookie_valid(cookie):
                return cookie
    except sqlite3.OperationalError as e:
        logger.debug("Could not read cookies: %s" % e)
    return None


def get_firefox_cookie(path='', host='softwarefactory'):
    """Fetch the auth cookie stored by Firefox at %path% for the
    %host% instance of Software Factory."""
    jar_path = _build_path(path)
    logger.debug('looking for firefox cookies at %s' % jar_path)
    try:
        c = sqlite3.connect(jar_path)
        cur = c.cursor()
        cur.execute('select value from moz_cookies where host '
                    'like ? and name = "auth_pubtkt" '
                    'order by expiry desc', ('%' + host + '%',))
        for cookie_info in cur.fetchall():
            if cookie_info:
                if _is_cookie_valid(cookie_info[0]):
                    return cookie_info[0]
    except sqlite3.OperationalError as e:
        logger.debug("Could not read cookies: %s" % e)
    return None


def die(msg):
    logger.error(msg)
    sys.exit(1)


def split_and_strip(s):
    l = s.split(',')
    return [x.strip() for x in l]


def load_rc_file(args):
    for path in DEFAULT_RC_PATHS:
        if os.path.isfile(path):
            logger.debug("Using rc file %s" % path)
            with open(path, 'r') as ymlfile:
                cfg = yaml.load(ymlfile)
            if not isinstance(cfg, dict):
                raise Exception("Incorrect rc file format")
            if args.env not in cfg:
                raise Exception("Unknown environment %s" % args.env)
            env = cfg[args.env]
            if env.get('url'):
                args.url = env['url']
            if env.get('insecure'):
                args.insecure = env['insecure']
            if env.get('debug'):
                args.debug = env['debug']
            if env.get('auth'):
                if env['auth'].get('username'):
                    args.auth = env['auth']['username']
                    # would anybody put a password but no username?
                    if env['auth'].get('password'):
                        args.auth += ':' + env['auth']['password']
                    return
                if env['auth'].get('api-key'):
                    args.api_key = env['auth']['api-key']
                    return
                if env['auth'].get('cookie'):
                    args.cookie = env['auth']['cookie']
                    return
                if env['auth'].get('github-token'):
                    args.github_token = env['auth']['github-token']
                    return
            return
        else:
            logger.debug("Could not find rc file %s" % path)
    raise Exception("Environment %s could not be loaded: "
                    "no rc file found" % args.env)


def default_arguments(parser):
    parser.add_argument('--env', '-e',
                        help='The environment to use from an RC file. '
                             'Default locations are .software-factory.rc, '
                             '~/.software-factory.rc, ~/.software-factory'
                             '/software-factory.rc and /etc/software-factory'
                             '/software-factory.rc in order of discovery')
    parser.add_argument('--url',
                        help='Software Factory public gateway URL')
    parser.add_argument('--auth', metavar='username[:password]',
                        help='Authentication information',)
    parser.add_argument('--github-token', metavar='GithubPersonalAccessToken',
                        help='Authenticate with a Github Access Token')
    parser.add_argument('--api-key', metavar='APIKEY',
                        help='Authenticate with a SF API key')
    parser.add_argument('--auth-server-url', metavar='central-auth-server',
                        help='URL of the central auth server')
    parser.add_argument('--cookie', metavar='Authentication cookie',
                        help='cookie of the user if known')
    parser.add_argument('--insecure', default=False, action='store_true',
                        help='disable SSL certificate verification, '
                        'verification is enabled by default')
    parser.add_argument('--json', default=False, action='store_true',
                        help='Return output as JSON instead of '
                        'human readable output')
    parser.add_argument('--debug', default=False, action='store_true',
                        help='enable debug messages in console, '
                        'disabled by default')


def system_command(parser):
    root = parser.add_parser('system', help='system level commands')
    sub_cmd = root.add_subparsers(dest='subcommand')
    sub_cmd.add_parser('backup_start',
                       help='Start the backup process in Software Factory')
    sub_cmd.add_parser('backup_get',
                       help='Download the latest backup from Software Factory')


def user_management_command(parser):
    uc = parser.add_parser('user',
                           help='local users backend related commands')
    suc = uc.add_subparsers(dest="subcommand")

    cump = suc.add_parser('create', help='Create user. Admin rights required')
    cump.add_argument('--username', '-u', nargs='?', metavar='username',
                      required=True, help='A unique username/login')
    cump.add_argument('--password', '-p', nargs='?', metavar='password',
                      required=True,
                      help='The user password, can be provided interactively'
                           ' if this option is empty')
    cump.add_argument('--email', '-e', nargs='?', metavar='email',
                      required=True, help='The user email')
    cump.add_argument('--fullname', '-f', nargs='+', metavar='John Doe',
                      help="The user's full name, defaults to username",
                      required=True)
    cump.add_argument('--ssh-key', '-s', nargs='?', metavar='/path/to/pub_key',
                      required=False, help="The user's ssh public key file")
    uump = suc.add_parser('update', help='Update user details. Admin can'
                          ' update details of all users. User can update its'
                          ' own details.')
    uump.add_argument('--username', '-u', nargs='?', metavar='username',
                      required=True,
                      help='the user to update, defaults to current user')
    uump.add_argument('--password', '-p', nargs='?', metavar='password',
                      required=False, default=False,
                      help='The user password, can be provided interactively'
                           ' if this option is empty')
    uump.add_argument('--email', '-e', nargs='?', metavar='email',
                      required=False, help='The user email')
    uump.add_argument('--fullname', '-f', metavar='John Doe', nargs='+',
                      required=False, help="The user's full name")
    uump.add_argument('--ssh-key', '-s', nargs='?', metavar='/path/to/pub_key',
                      required=False, help="The user's ssh public key file")
    dump = suc.add_parser('delete', help='Delete user. Admin rights required')
    dump.add_argument('--username', '-u', nargs='?', metavar='username',
                      required=True, help='the user to delete')


def sf_user_management_command(parser):
    sfu = parser.add_parser('sf_user',
                            help='manage registered users on Software Factory')
    sfu_sub = sfu.add_subparsers(dest='subcommand')
    create = sfu_sub.add_parser('create', help='register a user on SF')
    create.add_argument('--username', '-u', nargs='?', metavar='username',
                        required=True, help='A unique username/login')
    create.add_argument('--fullname', '-f', nargs='+', metavar='John Doe',
                        required=True, help="The user's full name")
    create.add_argument('--email', '-e', nargs='?', metavar='email',
                        required=True, help="The user's email")
    sfu_sub.add_parser('list', help='list all registered users')
    delete = sfu_sub.add_parser('delete', help='de-register a user from SF')
    delete.add_argument('--username', '-u', nargs='?', metavar='username',
                        required=False, help=('the username '
                                              '(use either this or email)'))
    delete.add_argument('--email', '-e', nargs='?', metavar='email',
                        required=False, help=("the user's email (use "
                                              "either this or username)"))


def github_command(parser):
    gh = parser.add_parser('github', help='Github tools')

    sub_cmd = gh.add_subparsers(dest='subcommand')

    createrepo = sub_cmd.add_parser('create-repo')
    createrepo.add_argument(
        '--name', '-n', nargs='?', metavar='project-name', required=True)
    createrepo.add_argument(
        '--org', '-o', nargs='?', metavar='organization')

    deleterepo = sub_cmd.add_parser('delete-repo')
    deleterepo.add_argument(
        '--name', '-n', nargs='?', metavar='project-name', required=True)
    deleterepo.add_argument(
        '--org', '-o', nargs='?', metavar='organization')

    deploy_key = sub_cmd.add_parser('deploy-key')
    deploy_key.add_argument(
        '--name', '-n', nargs='?', metavar='project-name', required=True)
    deploy_key.add_argument(
        '--org', '-o', nargs='?', metavar='organization')

    deploy_key.add_argument('--keyfile', nargs='?', required=True)

    fork_repo = sub_cmd.add_parser('fork-repo')
    fork_repo.add_argument(
        '--fork', '-f', nargs='?', metavar='fork', required=True)
    fork_repo.add_argument(
        '--name', '-n', nargs='?', metavar='project-name', required=True)
    fork_repo.add_argument(
        '--org', '-o', nargs='?', metavar='organization')


def gerrit_api_htpassword_command(parser):
    gah = parser.add_parser('gerrit_api_htpasswd',
                            help='Gerrit API access commands')

    sub_cmd = gah.add_subparsers(dest='subcommand')

    sub_cmd.add_parser('generate_password',
                       help='Generate a personal Gerrit API'
                            ' access htpassword')
    sub_cmd.add_parser('delete_password',
                       help='Delete my personal Gerrit API'
                            ' access htpassword')


def job_command(parser):
    job = parser.add_parser('job',
                            help='jobs related tools')
    subc = job.add_subparsers(dest='subcommand')
    list = subc.add_parser('list',
                           help='list jobs statuses')
    list.add_argument('--job-name', '-j', metavar='job-name',
                      required=True)
    list.add_argument('--id', '-i', metavar='job-id',
                      required=False)
    list.add_argument('--change', '-c', metavar='review-change',
                      required=False)
    list.add_argument('--patchset', '-p', metavar='change-patchset',
                      required=False)
    logs = subc.add_parser('logs',
                           help='show the logs of a job')
    logs.add_argument('--job-name', '-j', metavar='job-name',
                      required=True)
    logs.add_argument('--id', '-i', metavar='job-id',
                      required=True)
    logs.add_argument('--fetch', default=False, action='store_true',
                      help='if enabled, attempts downloading the logs'
                           ' and displays them to stdout (not compatible'
                           ' with --json option)')
    params = subc.add_parser('parameters',
                             help='show the parameters used by a job')
    params.add_argument('--job-name', '-j', metavar='job-name',
                        required=True)
    params.add_argument('--id', '-i', metavar='job-id',
                        required=True)
    run = subc.add_parser('run',
                          help='run a new job')
    run.add_argument('--job-name', '-j', metavar='job-name',
                     required=True)
    run.add_argument('--parameters', '-p', metavar='{"name": "value"}',
                     required=False)
    run.add_argument('--clone-from', '-c', metavar='job-id',
                     required=False,
                     help='run this job with the same parameters as <job-id>.'
                          ' if --parameters are used, they override the'
                          ' parameters of the cloned job.')
    stop = subc.add_parser('stop',
                           help='stop a running job')
    stop.add_argument('--job-name', '-j', metavar='job-name',
                      required=True)
    stop.add_argument('--id', '-i', metavar='job-id',
                      required=True)


def node_command(parser):
    node = parser.add_parser('node',
                             help='nodes related tools')
    subc = node.add_subparsers(dest='subcommand')
    list = subc.add_parser('list',
                           help='list information about nodes currently up')
    list.add_argument('--id', '-i', metavar='node-id',
                      required=False)
    aduk = subc.add_parser('add-user-key',
                           help=('Add a SSH public key to the list of '
                                 'authorized keys on node node-id'))
    aduk.add_argument('--key', '-k', metavar='/path/to/public_key',
                      required=False)
    aduk.add_argument('--id', '-i', metavar='node-id',
                      required=True)
    hold = subc.add_parser('hold',
                           help='prevent a node from being deleted after'
                                ' a job has run its course')
    hold.add_argument('--id', '-i', metavar='node-id',
                      required=True)
    delete = subc.add_parser('delete',
                             help='schedule a node for immediate deletion')
    delete.add_argument('--id', '-i', metavar='node-id',
                        required=True)


def image_command(parser):
    image = parser.add_parser('image',
                              help='images related tools')
    subc = image.add_subparsers(dest='subcommand')
    imagelist = subc.add_parser('list',
                                help='list information about images available'
                                     ' to spawn nodes')
    imagelist.add_argument('--provider', '-p', metavar='provider-name',
                           required=True)
    imagelist.add_argument('--image', '-i', metavar='image-name',
                           required=False)
    imageupdate = subc.add_parser('update',
                                  help='trigger the update of an image')
    imageupdate.add_argument('--provider', '-p', metavar='provider-name',
                             required=True)
    imageupdate.add_argument('--image', '-i', metavar='image-name',
                             required=True)
    imagestatus = subc.add_parser('update-status',
                                  help='check the status of an update')
    imagestatus.add_argument('--update-id', '-u', metavar='update-id',
                             required=True)
    imagestatus.add_argument('--fetch', default=False, action='store_true',
                             help='if enabled, attempts downloading the build'
                                  ' logs and displays them to stdout (not'
                                  ' compatible with --json option)')
    imagestatus.add_argument('--fetch-all', default=False, action='store_true',
                             help='if enabled, attempts downloading the full'
                                  ' logs and displays them to stdout (not'
                                  ' compatible with --json option)')


def command_options(parser):
    sp = parser.add_subparsers(dest="command")
    user_management_command(sp)
    sf_user_management_command(sp)
    gerrit_api_htpassword_command(sp)
    system_command(sp)
    github_command(sp)
    job_command(sp)
    node_command(sp)
    image_command(sp)


def get_cookie(args):
    if args.cookie is not None:
        return args.cookie
    try:
        url = args.auth_server_url.rstrip('/')
        if args.auth is not None:
            (username, password) = args.auth.split(':')
            cookie = sfauth.get_cookie(url, username=username,
                                       password=password,
                                       verify=(not args.insecure))
        elif args.github_token is not None:
            token = args.github_token
            cookie = sfauth.get_cookie(url, github_access_token=token,
                                       verify=(not args.insecure))
        elif args.api_key is not None:
            api_key = args.api_key
            cookie = sfauth.get_cookie(url, api_key=api_key,
                                       verify=(not args.insecure))
        else:
            die('Please provide credentials')
        if cookie:
            return cookie
        else:
            die('Authentication failed')
    except Exception as e:
        die(e.message)


def response(resp, quiet=False):
    if resp.ok:
        if not quiet:
            content_json = \
                resp.headers.get(
                    'content-type', '').startswith("application/json")
            if content_json and JSON_OUTPUT:
                # Response is already json and we want json
                # prettyfied output so load the json string
                # from the response and dump it with indent
                # to pretty print it by keeping valid json
                print json.dumps(resp.json(), indent=2)
            elif content_json:
                # Response if json but user does not ask
                # for json output so return str of python object
                print resp.json()
            else:
                print resp.text
        return True
    if resp.status_code // 100 == 4:
        if resp.status_code == 409:
            msg = 'RESOURCE CONFLICT\n%s' % resp.text
        elif resp.status_code == 401:
            msg = ('You are not authorized to perform this action. Please '
                   'contact an administrator of the platform if you believe '
                   'this should not be the case.')
            try:
                policy = re.search('Failure to comply with policy (.+)\n',
                                   resp.text).groups()[0]
            except:
                policy = "UNKNOWN"
            msg += '\n\nPolicy enforced: %s' % policy
        else:
            msg = 'NOT FOUND\n%s' % resp.text
        die(msg)
    if resp.status_code // 100 == 5:
        msg = 'SERVER ERROR\n%s' % resp.text
        die(msg)
    else:
        die(resp.text)


def build_url(*args):
    return '/'.join(s.strip('/') for s in args) + '/'


def node_action(args, base_url):

    def print_pt(resp):
        for service in resp.json():
            print "\nNode(s) managed by service %s:\n" % service
            pt = PrettyTable(['ID', 'provider', 'AZ', 'label', 'target',
                              'manager', 'hostname', 'node name',
                              'server ID', 'IP', 'state',
                              'age (seconds)'])
            for i in resp.json()[service]:
                pt.add_row(
                    [i['node_id'], i['provider_name'], i['AZ'],
                     i['label'], i['target'], i['manager'],
                     i['hostname'], i['node_name'], i['server_id'],
                     i['ip'], i['state'], i['age'], ])
            print pt

    if args.command != 'node':
        return False
    if args.subcommand not in ['list', 'add-user-key', 'hold', 'delete']:
        return False
    if args.subcommand == 'list':
        url = build_url(base_url, 'nodes/')
        if getattr(args, 'id'):
            url = build_url(url, 'id/%s' % args.id)
        resp = request('get', url)
        if resp.ok and not JSON_OUTPUT:
            print_pt(resp)
            return True
        return response(resp)
    if args.subcommand == 'add-user-key':
        url = build_url(base_url, 'nodes/id/%s/authorize_key/' % args.id)
        try:
            key_contents = file(args.key).read()
        except IOError as e:
            die(unicode(e))
        data = {'public_key': key_contents}
        resp = request('post', url, json=data)
        if resp.ok:
            url = build_url(base_url, 'nodes/id/%s' % args.id)
            resp = request('get', url)
            for service in resp.json():
                cmd = "ssh -o StrictHostKeyChecking=no jenkins@%s"
                cmd = cmd % resp.json()[service][0]['ip']
                msg = "Key added on %s; node can be reached via command: %s"
                print msg % (resp.json()[service][0]['node_name'],
                             cmd)
            return True
        else:
            if resp.json():
                msg = "Key not added because of following error: %s"
                service = resp.json().keys()[0]
                die(msg % resp.json()[service]["error_description"])
            else:
                die(resp.body)
    if args.subcommand == 'hold':
        url = build_url(base_url, 'nodes/id/%s' % args.id)
        resp = request('put', url)
        if resp.ok and not JSON_OUTPUT:
            print_pt(resp)
            return True
        return response(resp)
    if args.subcommand == 'delete':
        url = build_url(base_url, 'nodes/id/%s' % args.id)
        resp = request('delete', url)
        if resp.ok and not JSON_OUTPUT:
            print_pt(resp)
            return True
        return response(resp)


def image_action(args, base_url):
    if args.command != 'image':
        return False
    if args.subcommand not in ['list', 'update', 'update-status', ]:
        return False
    if args.subcommand == 'update':
        url = build_url(base_url,
                        'nodes/images/update/%s/%s' % (args.provider,
                                                       args.image))
        resp = request('put', url)
        if resp.ok and not JSON_OUTPUT:
            for service in resp.json():
                msg = ("Image %s on provider %s is being updated.\n"
                       "To check the status of the update, please run "
                       "'sfmanager image update-status --update-id %s'")
                print msg % (args.provider, args.image,
                             resp.json()[service]['update_id'])
            return True
        return response(resp)
    if args.subcommand == 'update-status':
        url = build_url(base_url, 'nodes/images/update/%s' % args.update_id)
        resp = request('get', url)
        if resp.ok and not JSON_OUTPUT:
            for service in resp.json():
                status = resp.json()[service]
                buildlog = re.compile('^(.+) (INFO|DEBUG|ERR.*|'
                                      'NOTICE|WARN.*|CRIT|ALERT|EMERG|PANIC) '
                                      'nodepool.image.build.+: (.+)$')
                if args.fetch_all or args.fetch:
                    if args.fetch:
                        for line in status['output'].split('\n'):
                            if buildlog.match(line):
                                m = buildlog.match(line).groups()
                                print m[0] + '\t' + m[-1]
                    else:
                        print status['output']
                else:
                    base_fields = ['ID', 'status', 'image',
                                   'provider']
                    base_values = [status['id'], status['status'],
                                   status['image'], status['provider']]
                    if status['status'] in ['SUCCESS', 'FAILURE']:
                        base_fields.append('exit code')
                        base_values.append(status['exit_code'])
                        if int(status['exit_code']) > 0:
                            base_fields.append('error')
                            base_values.append(status['error'])
                    pt = PrettyTable(base_fields)
                    pt.add_row(base_values)
                    print pt
            return True
        return response(resp)
    if args.subcommand == 'list':
        url = build_url(base_url, 'nodes/images/')
        if getattr(args, 'image') and not getattr(args, 'provider'):
            die('please add a provider name')
        if getattr(args, 'provider'):
            url = build_url(url, '%s/' % args.provider)
        if getattr(args, 'image'):
            url = build_url(url, '%s/' % args.image)
        resp = request('get', url)
        if resp.ok and not JSON_OUTPUT:
            for service in resp.json():
                print "\nImage(s) managed by service %s:\n" % service
                pt = PrettyTable(['ID', 'provider', 'image',
                                  'hostname', 'version', 'image ID',
                                  'server ID', 'state', 'age (seconds)'])
                for i in resp.json()[service]:
                    pt.add_row(
                        [i['id'], i['provider_name'], i['image_name'],
                         i['hostname'], i['version'], i['image_id'],
                         i['server_id'], i['state'], i['age'], ])
                print pt
            return True
        return response(resp)


def job_action(args, base_url):
    if args.command != 'job':
        return False
    if args.subcommand not in ['list', 'logs', 'parameters', 'run', 'stop']:
        return False
    job_name = args.job_name
    if args.subcommand == 'list':
        url = build_url(base_url, 'jobs/%s' % job_name)
        if getattr(args, 'id'):
            url = build_url(url, 'id/%s' % args.id)
        if getattr(args, 'change'):
            url += '?change=%s' % urllib.quote_plus(args.change)
            if getattr(args, 'patchset'):
                url += '&patchset=%s' % urllib.quote_plus(args.patchset)
        resp = request('get', url)
        if resp.ok and not JSON_OUTPUT:
            for service in resp.json():
                print "\nJob(s) run by service %s:\n" % service
                pt = PrettyTable(["name", "id", "status"])
                for i in resp.json()[service]:
                    pt.add_row(
                        [i['job_name'], i['job_id'], i['status']])
                print pt
            return True
        return response(resp)
    if args.subcommand == 'logs':
        url = build_url(base_url, 'jobs/%s/id/%s/logs' % (job_name, args.id))
        resp = request('get', url)
        if resp.ok and not JSON_OUTPUT:
            if getattr(args, 'fetch'):
                for service in resp.json():
                    url = resp.json()[service]['logs_url']
                    print "\nJob run by service %s, at %s:\n" % (service, url)
                    print request('get', url).text
                return True
        return response(resp)
    if args.subcommand == 'parameters':
        url = build_url(base_url,
                        'jobs/%s/id/%s/parameters' % (job_name, args.id))
        resp = request('get', url)
        if resp.ok and not JSON_OUTPUT:
            for service in resp.json():
                pt = PrettyTable(["name", "value"])
                for i in resp.json()[service]['parameters']:
                    pt.add_row(
                        [i['name'], i['value']])
                print pt
            return True
        return response(resp)
    if args.subcommand == 'run':
        url = build_url(base_url, 'jobs/%s/' % (job_name, ))
        data = {}
        if getattr(args, 'parameters'):
            data = json.loads(args.parameters)
        if getattr(args, 'clone_from'):
            id = args.clone_from
            p_url = build_url(base_url,
                              'jobs/%s/id/%s/parameters' % (job_name, id))
            resp = request('get', p_url)
            if resp.ok:
                print resp.json()
                # There's usually only one, careful if we bump it
                for s in resp.json():
                    cloned = dict((u['name'], u['value'])
                                  for u in resp.json()[s]['parameters'])
                    cloned.update(data)
                    data = cloned
            else:
                print "Could not fetch parameters for job %s:%s" % (job_name,
                                                                    id)
        resp = request('post', url, json=data)
        if resp.ok and not JSON_OUTPUT:
            for service in resp.json():
                print "\nJob(s) started by service %s:\n" % service
                pt = PrettyTable(["name", "id", "status"])
                i = resp.json()[service]
                pt.add_row(
                    [i['job_name'], i['job_id'], i['status']])
                print pt
            return True
        return response(resp)
    if args.subcommand == 'stop':
        url = build_url(base_url, 'jobs/%s/id/%s/' % (job_name, args.id))
        resp = request('delete', url)
        if resp.ok and not JSON_OUTPUT:
            for service in resp.json():
                print "\nJob(s) stopped by service %s:\n" % service
                pt = PrettyTable(["name", "id", "status"])
                i = resp.json()[service]
                pt.add_row(
                    [i['job_name'], i['job_id'], i['status']])
                print pt
            return True
        return response(resp)


def backup_action(args, base_url):
    if args.command != 'system':
        return False

    url = build_url(base_url, 'backup')
    if args.subcommand == 'backup_get':
        resp = request('get', url)
        if resp.status_code != 200:
            die("backup_get failed with status_code " + str(resp.status_code))
        chunk_size = 1024
        with open('sf_backup.tar.gz', 'wb') as fd:
            for chunk in resp.iter_content(chunk_size):
                fd.write(chunk)
        return True

    elif args.subcommand == 'backup_start':
        resp = request('post', url)
        return response(resp)

    return False


def gerrit_api_htpasswd_action(args, base_url):
    url = base_url + '/htpasswd'
    if args.command != 'gerrit_api_htpasswd':
        return False

    if args.subcommand not in ['generate_password', 'delete_password']:
        return False

    if args.subcommand == 'generate_password':
        resp = request('put', url)
        return response(resp)

    elif args.subcommand == 'delete_password':
        resp = request('delete', url)
        return response(resp, quiet=True)


def github_action(args, base_url):
    if args.subcommand not in ['create-repo', 'delete-repo',
                               'deploy-key', 'fork-repo']:
        return False

    if not args.github_token:
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": "token %s" % args.github_token
    }

    if args.subcommand == 'create-repo':
        data = {"name": args.name, "private": False}

        if args.org:
            url = "https://api.github.com/orgs/%s/repos" % args.org
        else:
            url = "https://api.github.com/user/repos"
        resp = requests.post(url, headers=headers, json=data)
        if resp.status_code == requests.codes.created:
            print "Github repo %s created." % args.name
        return response(resp, quiet=True)

    elif args.subcommand == 'fork-repo':
        parsed = urlparse.urlparse(args.fork)
        if not parsed.netloc:
            logger.info("Invalid original repo url.")
            return
        owner = parsed.path.split('/')[1]
        repo = parsed.path.split('/')[2]
        url = "https://api.github.com/repos/%s/%s/forks" % (owner, repo)
        data = None
        if args.org:
            data = {'organization': args.org}
        resp1 = requests.post(url, headers=headers, json=data)
        if resp1.status_code == requests.codes.accepted:
            print "Github repo %s forked." % repo
        if args.name:
            data = {'name': args.name}
            if args.org:
                owner = args.org
            else:
                owner = resp1.json()["owner"]["login"]
            url = "https://api.github.com/repos/%s/%s" % (owner, repo)
            resp2 = requests.patch(url, headers=headers, json=data)
            if resp2.status_code == requests.codes.ok:
                print "Github repo renamed from %s to %s" % (repo, args.name)
            return response(resp2, quiet=True)
        else:
            return response(resp1, quiet=True)

    elif args.subcommand == 'delete-repo':
        if args.org:
            owner = args.org
        else:
            url = "https://api.github.com/user"
            resp = requests.get(url, headers=headers)
            owner = resp.json().get('login')

        url = "https://api.github.com/repos/%s/%s" % (owner, args.name)

        resp = requests.delete(url, headers=headers)
        if resp.status_code == requests.codes.no_content:
            print "Github repo %s deleted." % args.name
        return response(resp)

    elif args.subcommand == "deploy-key":
        if args.keyfile:
            if args.org:
                owner = args.org
            else:
                url = "https://api.github.com/user"
                resp = requests.get(url, headers=headers)
                owner = resp.json().get('login')

            with open(args.keyfile, 'r') as f:
                sshkey = f.read()

            data = {
                "title": "%s ssh key" % owner,
                "key": sshkey,
                "read_only": False}

            url = "https://api.github.com/repos/%s/%s/keys" % (
                owner, args.name)
            resp = requests.post(url, headers=headers, json=data)

            if resp.status_code == requests.codes.created:
                print "SSH deploy key %s added to Github repo %s." % (
                    args.keyfile, args.name)
            return response(resp, quiet=True)

    return False


def user_management_action(args, base_url):
    if args.command != 'user':
        return False
    if args.subcommand not in ['create', 'update', 'delete']:
        return False
    url = build_url(base_url, 'user', args.username)
    if args.subcommand in ['create', 'update']:
        password = None
        if args.password is None:
            # -p option has been passed by with no value
            password = getpass.getpass("Enter password: ")
        elif args.password:
            password = args.password
        info = {}
        if getattr(args, 'email'):
            info['email'] = args.email
        if getattr(args, 'ssh_key'):
            with open(args.ssh_key, 'r') as f:
                info['sshkey'] = f.read()
        if getattr(args, 'fullname'):
            info['fullname'] = ' '.join(args.fullname)
        if password:
            info['password'] = password
        resp = request('post', url, json=info)
        if args.subcommand == 'create' and resp.ok and not JSON_OUTPUT:
            pt = PrettyTable(["Username", "Fullname", "Email"])
            i = resp.json()
            pt.add_row(
                [i['username'], i['fullname'], i['email']])
            print pt
            return True
    if args.subcommand == 'delete':
        resp = request('delete', url)
    return response(resp)


def services_users_management_action(args, base_url):
    if args.command != 'sf_user':
        return False
    if args.subcommand not in ['create', 'list', 'delete']:
        return False
    url = build_url(base_url, 'services_users')
    if args.subcommand in ['create', 'delete']:
        info = {}
        if getattr(args, 'email', None):
            info['email'] = args.email
        if getattr(args, 'username', None):
                info['username'] = args.username
        if getattr(args, 'fullname', None):
            info['full_name'] = ' '.join(args.fullname)
    if args.subcommand == 'create':
        resp = request('post', url, json=info)
    elif args.subcommand == 'delete':
        resp = request('delete', url, json=info)
    elif args.subcommand == 'list':
        resp = request('get', url)
        if resp.ok and not JSON_OUTPUT:
            pt = PrettyTable(["Id", "Username", "Fullname", "Email",
                              "Cauth_id"])
            for i in resp.json():
                pt.add_row(
                    [i['id'], i['username'], i['fullname'], i['email'],
                     i['cauth_id']])
            print pt
            return True
        else:
            return response(resp)
    return response(resp)


def main():
    parser = argparse.ArgumentParser(
        description="Software Factory CLI")
    default_arguments(parser)
    command_options(parser)
    args = parser.parse_args()
    if args.env:
        try:
            load_rc_file(args)
        except Exception as e:
            die(e.message)
    globals()['JSON_OUTPUT'] = args.json
    globals()['VERIFY_SSL'] = not args.insecure

    # Set local url and auth if sfconfig.yaml is present
    sfconfig = None
    if os.path.isfile("/etc/software-factory/sfconfig.yaml"):
        sfconfig = yaml.load(open("/etc/software-factory/sfconfig.yaml"))
    # could be remove when puppet will be gone (2.2.8)
    elif os.path.isfile("/etc/puppet/hiera/sf/sfconfig.yaml"):
        sfconfig = yaml.load(open("/etc/puppet/hiera/sf/sfconfig.yaml"))
    if not args.url and sfconfig:
        args.url = "https://%s" % sfconfig["fqdn"]
    if not args.auth and sfconfig:
        args.auth = "admin:%s" % sfconfig["authentication"]["admin_password"]

    if not args.url:
        base_url = ""
        if args.command != "github":
            parser.error('argument --url is required')
    if args.url and not args.url.lower().startswith('http'):
            parser.error('missing protocol in argument --url: %s' % args.url)
    else:
        if args.command != "github":
            base_url = "%s/manage" % args.url.rstrip('/')

    if not args.debug:
        ch.setLevel(logging.ERROR)
        ch.setFormatter(info_formatter)
    else:
        http_client.HTTPConnection.debuglevel = 1
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(debug_formatter)

    if args.auth_server_url is None:
        args.auth_server_url = args.url

    # check that the cookie is still valid
    if args.cookie is not None:
        if not _is_cookie_valid(args.cookie):
            die("Invalid cookie")

    if (args.auth is None and
       args.cookie is None and
       args.github_token is None and
       args.api_key is None):
        host = urlparse.urlsplit(args.url).hostname
        logger.info("No authentication provided, looking for an existing "
                    "cookie for host %s... " % host),
        # try Chrome
        CHROME_COOKIES_PATH = _build_path('.config/chromium/Default/Cookies')
        cookie = get_chromium_cookie(CHROME_COOKIES_PATH,
                                     host)
        if _is_cookie_valid(cookie):
            args.cookie = cookie
        if args.cookie is None:
            # try Firefox
            FIREFOX_COOKIES_PATH = _build_path(
                '.mozilla/firefox/*.default/cookies.sqlite')
            paths = glob.glob(FIREFOX_COOKIES_PATH)
            # FF can have several profiles, let's cycle through
            # them until we find a cookie
            for p in paths:
                cookie = get_firefox_cookie(p, host)
                if _is_cookie_valid(cookie):
                    args.cookie = cookie
                    break
        if args.cookie is None:
            logger.error("No cookie found.")
            die("Please provide valid credentials.")
        userid = args.cookie.split('%3B')[0].split('%3D')[1]
        logger.info("Authenticating as %s" % userid)

    if args.auth is not None and ":" not in args.auth:
        password = getpass.getpass("%s's password: " % args.auth)
        args.auth = "%s:%s" % (args.auth, password)

    if args.command != "github":
        globals()['COOKIE'] = {'auth_pubtkt': get_cookie(args)}

    if args.insecure:
        import urllib3
        urllib3.disable_warnings()

    if not(backup_action(args, base_url) or
           gerrit_api_htpasswd_action(args, base_url) or
           user_management_action(args, base_url) or
           github_action(args, base_url) or
           services_users_management_action(args, base_url) or
           job_action(args, base_url) or
           node_action(args, base_url) or
           image_action(args, base_url)):
        die("ManageSF failed to execute your command")


if __name__ == '__main__':
    main()
