import base64
import glob
import itertools
import json
import multiprocessing
import os
import re
import ssl
import socket
import subprocess
import tarfile
import textwrap
import tempfile
import threading
import traceback
import urllib.parse as urlparse
import zipfile

from typing import List, Dict

from enum import Enum
from flask import request, Response, g
from flask.ext import restful
import jinja2
import requests
import ijson
import yaml
from werkzeug.datastructures import FileStorage

from . import app
from .requestparser import RequestParser
from .api import APIException, RegisterException, ok, api_url_for, error
from .config import Config
from .docker import docker_output, start_container, tail_logs, safe_docker
from .tools import identifier, service_iden, adapter_iden, interleave
from .tasks import Producer
from .service_store import service_store
from .tools import chdir
from .entity import get_permissions


LANGUAGES = {
    'python': ('py', 'pip install {package}'),
    'ruby': ('rb', 'gem install {package}'),
    'javascript': ('js', 'npm install -g {package}'),
    'lua': ('lua', None),
    'java': ('jar', None)
}

EXTENSIONS = {
    '.py': 'python',
    '.js': 'javascript',
    '.rb': 'ruby',
    '.jar': 'java',
    '.lua': 'lua'
}

TARBALLS = ['.tar', '.gz', '.tgz']
ZIPS = ['.zip']

# Timeout to wait for output of containers at start up, before
# declaring them dead
TIMEOUT = 3  # second

# Timout to wait while stopping workers
STOP_TIMEOUT = 5


class WorkerState(Enum):
    started = 1
    error = 2


class AbstractService(object):

    METADATA_DEFAULT = ''
    PARAMS = [
        # parameter, mandatory?, default
        ('name', True),
        ('namespace', True),
        ('type', True),
        ('code_dir', False, None),
        ('version', False, '0.1'),
        ('url', False, 'http://localhost'),
        ('whitelist', False, []),
        ('description', False, ''),
        ('requirements', False, []),
        ('notify', False, ''),
        ('json_path', False, ''),
        ('main_module', False, 'main'),
        ('users', False, {}),
        ('metadata', False, METADATA_DEFAULT)
    ]

    def __init__(self, **kwargs):
        code_dir = kwargs.get('code_dir')
        if code_dir is not None:
            self.metadata = kwargs.get('metadata', self.METADATA_DEFAULT)
            self.__dict__.update(get_metadata_from(
                os.path.join(code_dir, self.metadata)))
        self.__dict__.update(kwargs)
        self._validate_args()

        self.iden = identifier(self.namespace,
                               self.name,
                               self.version)
        self.adapter_name = adapter_iden(self.name, self.version)

    def _validate_args(self):
        for param in self.PARAMS:
            try:
                getattr(self, param[0])
            except AttributeError:
                if param[1]:
                    raise
                setattr(self, param[0], param[2])
        if not valid_image_name(self.name):
            raise APIException("'{}' is not a valid service name.\n"
                               "Allowed characters: [a-z0-9_.-]"
                               .format(self.name))

    def to_json(self):
        return {key[0]: getattr(self, key[0]) for key in self.PARAMS}

    def make_image(self):
        raise NotImplementedError

    def start_workers(self):
        raise NotImplementedError

    def stop_workers(self):
        raise NotImplementedError

    def check_health(self):
        raise NotImplementedError

    def exec_worker(self, endpoint, args, request):
        """Exercise worker with data from the request.

        ``endpoint`` denotes which endpoint is using the worker (search,
        list).  ``args`` is the validated dictionary of GET arguments,
        if any (note that this method can be called for POST requests too,
        in which case ``args`` is empty).

        ``request`` is the request object.

        """
        raise NotImplementedError


class Service(AbstractService):

    def __init__(self, **kwargs):
        """Initialize service.

        First get metadata from ``code_dir`` and then use ``kwargs``.

        """
        super(Service, self).__init__(**kwargs)

        self.whitelist.append(urlparse.urlparse(self.url).hostname)
        self.whitelist.extend(get_nameservers())
        self.whitelist.append('172.17.42.1')
        self.whitelist = list(set(self.whitelist))
        self.validate_whitelist()

        self.main_module_path = self.find_main_module()
        self.language = self.detect_language(self.main_module_path)
        self.state = None
        self.workers = []

    def to_json(self):
        obj = super(Service, self).to_json()
        obj['language'] = self.language
        obj['workers'] = self.workers
        try:
            obj['self'] = api_url_for('service',
                                      namespace=self.namespace,
                                      service=self.adapter_name)
        except RuntimeError:
            # no app context, ignore 'self' field
            pass
        return obj

    def endpoints(self):
        if self.type == 'passthrough':
            return ['access']
        else:
            return ['search', 'list']

    def make_image(self):
        """Make a docker image for this service."""

        if self.type == 'passthrough':
            return
        render_template(
            os.path.dirname(self.main_module),
            os.path.basename(self.main_module_path),
            self.language,
            self.requirements,
            self.whitelist,
            self.type,
            into=self.code_dir)
        self.build()

    def find_main_module(self):
        """Find the path to the ``main_module``."""

        if self.type == 'passthrough':
            return None
        directory, basename = os.path.split(self.main_module)
        module, ext = os.path.splitext(basename)
        if ext:
            # if the module include the extension, just return its absolute
            #  path
            return os.path.join(self.code_dir, self.main_module)

        # Otherwise, try to find the proper module, by assuming that there
        # is only one file with such name.  Note that this may fail if
        # there are other files such as byte-compiled binaries, etc.
        found = glob.glob(os.path.join(self.code_dir, directory, module+'.*'))
        if not found:
            raise APIException('module not found: {}'
                               .format(self.main_module), 400)

        return found[0]

    def detect_language(self, module):
        if not module:
            return None
        _, ext = os.path.splitext(module)
        try:
            return EXTENSIONS[ext]
        except KeyError:
            raise APIException('unknown extension {0}'.format(ext), 400)

    def validate_whitelist(self):
        """Make sure ip's and domain name can be resolved."""

        for addr in self.whitelist:
            try:
                socket.gethostbyname_ex(addr)
            except:
                raise APIException(
                    "'{}' does not look like an ip or domain name"
                    .format(addr), 400)

    def build(self):
        if self.type == 'passthrough':
            return
        with chdir(self.code_dir):
            safe_docker('build', '-t', self.iden, '.')

    def start_workers(self, n=None):
        if self.type == 'passthrough':
            return
        if self.language is None:
            raise APIException('language of adapter not detected yet', 500)
        if n is None:
            n = Config.getint(
                'workers', '{}_instances'.format(self.language))
        self.workers = [self.start_worker() for _ in range(n)]

    def start_worker(self):
        worker = start_container(
            self.iden,          # image name
            '--queue-host',
            Config.get('queue', 'host'),
            '--queue-port',
            Config.get('queue', 'port'),
            '--queue-name',
            self.iden,
            '--adapter-type',
            self.type)
        allow(worker, self.whitelist)
        docker_output('exec', worker, 'touch', '/ready')
        return worker

    def stop_workers(self):
        if self.type == 'passthrough':
            return
        threads = []
        for worker in self.workers:
            threads.append(self.async_stop_worker(worker))
        for thread in threads:
            thread.join(STOP_TIMEOUT)
        self.workers = []

    def async_stop_worker(self, worker):
        thread = threading.Thread(target=docker_output,
                                  args=('rm', '-f', worker))
        thread.start()
        return thread

    def check_health(self):
        """Check that all workers started ok."""

        if self.type == 'passthrough':
            return True

        q = multiprocessing.Queue()

        def log(worker, q):
            producer = tail_logs(worker, timeout=TIMEOUT)
            v = (check(producer), worker)
            q.put(v)

        # Ask for logs from workers. We do it in processes so we can
        # poll for a little while the workers in parallel.
        ts = []
        for worker in self.workers:
            t = multiprocessing.Process(target=log, args=(worker, q),
                                        name='Worker log {}'.format(worker))
            t.start()
            ts.append(t)
        # wait for all processes (the timeout guarantees they'll finish)
        for t in ts:
            t.join()

        logs = []
        while not q.empty():
            state, worker = q.get()
            if state == WorkerState.error:
                logs.append(docker_output('logs', worker))

        if logs:
            raise RegisterException(len(self.workers), logs)

    def exec_worker(self, endpoint, args, request):
        """Process a request through the worker."""

        meth = getattr(self, 'exec_worker_{}'.format(self.type))
        return meth(endpoint, args, request)

    def exec_worker_query(self, endpoint, args, request):
        """Send ``args`` to ``queue`` in QueryWorker model."""

        queue = self.iden
        args['endpoint'] = endpoint
        args['headers'] = dict(request.headers)
        client = Producer(queue_host=Config.get('queue', 'host'),
                          queue_port=Config.getint('queue', 'port'),
                          queue_name=queue)
        client.send(args)
        gen = itertools.imap(json.dumps, client.receive())
        return Response(result_generator(gen, lambda: client.metadata),
                        mimetype='application/json')

    def exec_worker_map_filter(self, endpoint, args, request):
        """Forward request and process response.

        Forward the request to the third party service, and map the
        response through the ``process`` user function.

        """
        if endpoint != 'search':
            raise APIException("service of type 'map_filter' does "
                               "not support /list")

        if is_https(self.url) and request.method == 'GET':
            method = tls1_get
        else:
            method = getattr(requests, request.method.lower())
        try:
            headers = {'Authorization':
                           request.headers['Authorization']}
        except KeyError:
            headers = {}
        response = method(self.url,
                          params=request.args,
                          headers=headers,
                          stream=True)
        if response.ok:
            path = '.'.join(filter(None, [self.json_path, 'item']))
            results = ijson.items(FileLikeWrapper(response), path)

            return Response(
                result_generator(process_by_client(self, results),
                                 lambda: {}),
                mimetype='application/json')
        else:
            raise APIException('response from external service: {}'
                               .format(response))

    def exec_worker_generic(self, endpoint, args, request):
        queue = self.iden
        args['endpoint'] = endpoint
        client = Producer(queue_host=Config.get('queue', 'host'),
                          queue_port=Config.getint('queue', 'port'),
                          queue_name=queue)
        client.send(args)
        response = list(client.receive())
        if len(response) != 1:
            raise APIException(
                'Wrong return type of generic adapter: got {} results'
                .format(len(response)))
        response = response[0]
        if not 'error' in response:
            return Response(base64.b64decode(response['body']),
                            content_type=response['content_type'])
        else:
            return Response(json.dumps(response),
                            content_type='application/json')

    def exec_worker_passthrough(self, endpoint, args, request):
        """Pass a request straight to a pre-defined url.

        ``endpoint`` is what comes after the /access endpoint, and it
        should be added to the final url.

        """
        method = getattr(requests, request.method.lower())
        data = request.data if request.data else request.form
        url = _join(self.url, endpoint)
        response = method(url, params=request.args, data=data)
        return Response(
            response=response.content,
            status=response.status_code,
            headers=response.headers.items())


class ServiceQueryResource(restful.Resource):

    def get(self, namespace, service):
        """Perform a query using a service"""

        args = self.validate_get()
        try:
            iden = service_iden(namespace, service)
            srv = service_store[iden]['service']
        except KeyError:
            raise APIException('service not found: {}'
                               .format(service_iden(namespace, service)),
                               404)

        return srv.exec_worker('search', args, request)

    def validate_get(self):
        # no defined query language yet
        # accept everything
        return {key: val[0] for key, val in dict(request.args).items()}


class ServiceListResource(restful.Resource):

    def get(self, namespace, service):
        """List all objects using a service"""
        
        args = self.validate_get()
        try:
            iden = service_iden(namespace, service)
            srv = service_store[iden]['service']
        except KeyError:
            raise APIException('service not found: {}'
                               .format(service_iden(namespace, service)),
                               404)

        return srv.exec_worker('list', args, request)

    def validate_get(self):
        return dict(request.args)


class ServiceResource(restful.Resource):

    def get(self, namespace, service):
        """Get information about a service"""

        full_name = service_iden(namespace, service)
        try:
            srv = service_store[full_name]
            if srv['slot'] == 'ready':
                return ok({
                    'result': {
                        'service': srv['service'].to_json()
                    }
                })
            else:
                return ok({
                    'result': srv
                })
        except KeyError:
            raise APIException(
                "service not found: {}/{}"
                .format(namespace, service),
                404)

    def delete(self, namespace, service):
        """Delete a service"""

        name = service_iden(namespace, service)
        try:
            srv = service_store[name]['service']
            if (srv is not None and
                    'DELETE' not in get_permissions(srv.users, g.user)):
                raise APIException(
                    'user {} does not have permissions to DELETE '
                    'the service {}'.format(g.user, name))
            try:
                srv.stop_workers()
                # TODO: need to clean up containers here too
            except Exception:
                # ignore any error while stopping and removing workers
                pass
            del service_store[name]
        except KeyError:
            pass
        return ok({})

    def put(self, namespace, service):
        """Modify a service"""

        name = service_iden(namespace, service)
        try:
            slot = service_store[name]
        except KeyError:
            raise APIException('service not found: {}'.format(name), 404)

        old_srv = slot['service']
        if 'PUT' not in get_permissions(old_srv.users, g.user):
            raise APIException(
                'user {} does not have permissions to PUT to '
                'service {}'.format(g.user, name))

        args = self.validate_put()
        if old_srv is None:
            raise APIException('service not ready: {}'.format(name), 400)
        old_srv.stop_workers()
        slot['slot'] = 'free'
        slot['service'] = None
        service_store[name] = slot
        # if args.update, then update the git repo
        if args.get('update_git_repository', False):
            with chdir(old_srv.code_dir):
                subprocess.check_call('git pull'.split())
        register(
            Service, args, namespace, old_srv.code_dir, post_notifier)
        return ok({})

    @staticmethod
    def validate_put():
        parser = RequestParser()
        parser.add_argument('type', type=str)
        parser.add_argument('url', type=str)
        parser.add_argument('whitelist', type=str, action='append')
        parser.add_argument('description', type=str)
        parser.add_argument('requirements', type=str, action='append')
        parser.add_argument('notify', type=str)
        parser.add_argument('json_path', type=str)
        parser.add_argument('main_module', type=str)
        parser.add_argument('code', type=FileStorage, location='files')
        parser.add_argument('update_git_repository', type=bool)
        parser.add_argument('metadata', type=str)

        args = parser.parse_args()

        for key, value in args.items():
            if value is None:
                del args[key]

        return args


class ServiceHealthResource(restful.Resource):

    @staticmethod
    def _is_running(worker):
        running = docker_output(
            'inspect', '-f', '{{.State.Running}}', worker).strip()
        return running == 'true'

    def get(self, namespace, service):
        name = service_iden(namespace, service)
        try:
            slot = service_store[name]
        except KeyError:
            raise APIException('service not found: {}'.format(name), 404)
        srv = slot['service']
        workers_alive = len([worker for worker in srv.workers
                             if self._is_running(worker)])
        should_have = int(request.args.get('workers', 1))
        app.logger.debug(str(srv.workers))
        app.logger.debug('workers = {}'.format(workers_alive))
        return workers_alive >= should_have


class FileLikeWrapper(object):

    def __init__(self, response):
        self.response = response
        self.it = self.response.iter_content(chunk_size=1)
        self.src = itertools.chain.from_iterable(self.it)

    def read(self, n=512):
        return ''.join(itertools.islice(self.src, None, n))


def process_by_client(service, results):
    """Process results through a ProcessWorker.

    Return a generator which produces JSON objects (as strings).

    """

    client = Producer(
        queue_host=Config.get('queue', 'host'),
        queue_port=Config.getint('queue', 'port'),
        queue_name=service.iden)
    for result in results:
        client.send(result)
        for obj in client.receive():
            yield json.dumps(obj)
            if 'error' in obj:
                # abort as soon as there is an error
                return


def result_generator(results, metadata):
    """Construct JSON response from ``results``.

    ``results`` is a generator that produces JSON objects, and
    ``metadata`` is a function that returns extra information.

    The reason for metadata being a function is to be able to collect
    information after the ``results`` generator has been exhausted
    (for example: timing).

    """
    try:
        yield '{"result": [\n'
        for line in interleave(['\n, '], results):
            yield line
        yield '\n],\n'
        yield '"metadata": {0},\n'.format(json.dumps(metadata()))
        yield '"status": "success"}\n'
    except Exception:
        exc = traceback.format_exc()
        yield '---\n'
        yield exc


def is_https(url):
    return urlparse.urlparse(url).scheme == 'https'


class TLSv1Adapter(requests.adapters.HTTPAdapter):
    """Adapter to support TLSv1 in requests."""

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = requests.packages.urllib3.poolmanager.PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
<target>
            ssl_version=ssl.PROTOCOL_TLSv1)
</target>


def tls1_get(*args, **kwargs):
    session = requests.Session()
    session.mount('https://', TLSv1Adapter())
    kwargs['verify'] = False
    return session.get(*args, **kwargs)


def check(producer):
    """Check status of a container.

    Look at the output of the worker in the container.

    """
    state = WorkerState.error
    for line in producer:
        if line.startswith('*** WORKER ERROR'):
            return WorkerState.error
        if line.startswith('*** WORKER STARTED'):
            state = WorkerState.started
    return state


def render_template(main_module_path: str,
                    main_module_name: str,
                    language: str,
                    requirements: List[str],
                    whitelist: List[str],
                    adapter_type: str,
                    into):
    """Create Dockerfile for ``language``.

    Consider a list of ``requirements``, and write the Dockerfile in
    directory ``into``.

    """

    dockerfile_template = jinja2.Template(
        open('/adama/containers/Dockerfile.adapter').read())
    requirement_cmds = (
        'RUN ' + requirements_installer(language, requirements)
        if requirements else '')

    dockerfile = dockerfile_template.render(
        main_module_path=main_module_path,
        main_module_name=main_module_name,
        language=language,
        requirement_cmds=requirement_cmds,
        whitelist=json.dumps(whitelist),
        adapter_type=adapter_type
    )
    with open(os.path.join(into, 'Dockerfile'), 'w') as f:
        f.write(dockerfile)


def requirements_installer(language: str, requirements: List[str]) -> str:
    """Return the command to install requirements.

    ``requirements`` is a list of packages to be installed in the
    environment for ``language``.

    """
    _, installer = LANGUAGES[language]
    return installer.format(package=' '.join(requirements))


def get_metadata_from(directory):
    """Return a dictionary from the metadata file in ``directory``.

    Try to read the file ``metadata.yml`` or ``metadata.json`` at the root
    of the directory.

    Return an empty dict if no file is found.

    """
    for filename in ['metadata.yml', 'metadata.json']:
        try:
            f = open(os.path.join(directory, filename))
            break
        except IOError:
            pass
    else:
        # tried all files, give up and return empty
        return {}
    return yaml.load(f.read())


def valid_image_name(name):
    return re.search(r'[^a-z0-9-_.]', name) is None


def get_nameservers():
    nameservers = open('/etc/resolv.conf')
    for line in nameservers:
        if line.startswith('nameserver'):
            yield line.split()[1]


def _join(url, endpoint):
    """Join endpoint at the end of url.

    Take care of considering the slashes at the end of ``url`` and at the
    beginning of ``endpoint``, each one with the proper semantics.

    """
    if not endpoint:
        return url
    parsed_url = urlparse.urlsplit(url)
    new_path = os.path.join(parsed_url.path, endpoint)
    parts = list(parsed_url)
    parts[2] = new_path
    return urlparse.urlunsplit(parts)


def register_code(args, namespace, notifier=None):
    """Register code that comes in the POST request."""

    if args.type == 'passthrough':
        user_code = None
    else:
        filename = args.code.filename
        args.code = args.code.stream.read()
        tempdir = tempfile.mkdtemp()
        user_code = extract(filename, args.code, tempdir)
    return register(Service, args, namespace, user_code, notifier)


def register_git_repository(args, namespace, notifier=None):
    """Register code from git repo at ``args.git_repository``."""

    tempdir = tempfile.mkdtemp()
    subprocess.check_call(
        """
        cd {} &&
        git clone {} user_code
        """.format(tempdir, args.git_repository), shell=True)
    return register(Service, args, namespace,
                    os.path.join(tempdir, 'user_code'), notifier)


def register(service_class, args, namespace, user_code, notifier=None):
    """Register a service in a namespace.

    ``args`` is a dictionary with POST parameters. ``user_code`` is the
    directory where the user's code is checked out.

    Create the proper image, launch workers, and save the service in
    the store.

    """
    try:
        user = g.user
    except RuntimeError:
        user = 'anonymous'
    service = service_class(
        namespace=namespace, code_dir=user_code,
        users={user: ['POST', 'PUT', 'DELETE']},
        **dict(args))
    try:
        slot = service_store[service.iden]['slot']
    except KeyError:
        slot = 'free'

    # make sure to only use free or errored out slots
    if slot not in ('free', 'error'):
        raise APIException("service slot not available: {}\n"
                           "Current state: {}"
                           .format(service.iden, slot), 400)

    service_store[service.iden] = {
        'slot': 'busy',
        'msg': 'Empty service created',
        'stage': 1,
        'total_stages': 5,
        'service': None
    }

    _async_register(service, notifier)
    return service


def _async_register(service, notifier):
    """Launch async process for actual registration."""

    proc = multiprocessing.Process(
        name='Async Registration {}'.format(service.iden),
        target=_register, args=(service, notifier))
    proc.start()


def _register(service, notifier=None):
    """Register and start a service."""

    full_name = service.iden
    slot = service_store[full_name]
    try:
        slot['msg'] = 'Async image creation started'
        slot['stage'] = 2
        service_store[full_name] = slot

        service.make_image()

        slot['msg'] = 'Image for service created'
        slot['stage'] = 3
        service_store[full_name] = slot

        service.start_workers()

        slot['msg'] = 'Workers started'
        slot['stage'] = 4
        service_store[full_name] = slot

        service.check_health()

        slot['msg'] = 'Service ready'
        slot['stage'] = 5
        slot['slot'] = 'ready'
        slot['service'] = service
        service_store[full_name] = slot

        result = ok
        data = service
    except Exception as exc:
        slot['msg'] = 'Error: {}'.format(exc)
        slot['slot'] = 'error'
        service_store[full_name] = slot

        result = error
        data = str(exc)

    if service.notify and notifier is not None:
        notifier(service.notify, result, data)


def post_notifier(url, result, data):
    """Do a post notification to ``url``.

    ``result`` is a function, and ``data`` an object.

    """
    if result is ok:
        content = result({
            'message': 'Registration successful',
            'result': {
                'search': api_url_for(
                    'service',
                    namespace=data.namespace,
                    service=data.adapter_name)
            }
        })
    else:
        content = result({
            'message': 'Registration failed',
            'result': {
                'error': data
            }
        })
    try:
        requests.post(url,
                      headers={"Content-Type": "application/json"},
                      data=json.dumps(content))
    except Exception:
        app.logger.warning(
            "Could not notify url '{}'"
            .format(url))


def debug_notifier(url, result, data):
    print(url, result, data)


def extract(filename, code, into):
    """Extract code from string ``code``.

    ``filename`` is the name of the uploaded file.  Extract the code
    in directory ``into``.

    Return the directory where the user code is extracted (may differ from
    the original ``into``).

    """

    _, ext = os.path.splitext(filename)
    user_code_dir = os.path.join(into, 'user_code')
    os.mkdir(user_code_dir)
    contents = code

    if ext in ZIPS:
        # it's a zip file
        zip_file = os.path.join(into, 'contents.zip')
        with open(zip_file, 'w') as f:
            f.write(contents)
        zip = zipfile.ZipFile(zip_file)
        zip.extractall(user_code_dir)

    elif ext in TARBALLS:
        # it's a tarball
        tarball = os.path.join(into, 'contents.tgz')
        with open(tarball, 'w') as f:
            f.write(contents)
        tar = tarfile.open(tarball)
        tar.extractall(user_code_dir)

    elif ext in EXTENSIONS.keys():
        # it's a module
        module = os.path.join(user_code_dir, filename)
        with open(module, 'w') as f:
            f.write(contents)

    else:
        raise APIException(
            'unknown extension: {0}'.format(filename), 400)

    return user_code_dir