# Copyright (c) 2015 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Cassandra storage driver implementation."""

import multiprocessing
import os
import ssl
import time

from cassandra import auth
from cassandra import cluster
from cassandra import ConsistencyLevel
from cassandra import query
from cassandra import InvalidRequest
from cdeploy import migrator
from oslo.config import cfg

from canary.openstack.common import log as logging
from canary.util import canonicalize

conf = cfg.CONF
conf(project='canary', prog='canary', args=[])
logging.setup('canary')

LOG = logging.getLogger(__name__)

_CASSANDRA_OPTIONS = [
    cfg.ListOpt('cluster', default=['127.0.0.1'],
                help='Cassandra cluster contact points'),
    cfg.IntOpt('port', default=9042, help='Cassandra cluster port'),
    cfg.BoolOpt('ssl_enabled', default=False,
                help='Communicate with Cassandra over SSL?'),
    cfg.StrOpt('ssl_ca_certs', default='',
               help='Absolute path to the appropriate .crt file'),
    cfg.BoolOpt('auth_enabled', default=False,
                help='Does Cassandra have authentication enabled?'),
    cfg.StrOpt('username', default='', help='Cassandra username'),
    cfg.StrOpt('password', default='', help='Cassandra password'),
    cfg.StrOpt('ssl_version', default='TLSv1.1', help='TLS version'),
    cfg.StrOpt('load_balance_strategy', default='RoundRobinPolicy',
               help='Load balancing strategy for '
                    'connecting to cluster nodes'),
    cfg.StrOpt('consistency_level', default='ONE',
               help='Consistency level of your cassandra query'),
    cfg.StrOpt('migrations', default=os.path.join(os.path.dirname(__file__),
                                                  'migrations'),
               help='Path to directory containing CQL migration scripts'),
    cfg.IntOpt('max_schema_agreement_wait', default=10,
               help='The maximum duration (in seconds) that the driver will'
               ' wait for schema agreement across the cluster.'),
    cfg.StrOpt('keyspace', default='canary',
               help='Keyspace for all queries made in session'),
    cfg.DictOpt(
        'replication_strategy',
        default={
            'class': 'SimpleStrategy',
            'replication_factor': '1'
        },
        help='Replication strategy for Cassandra cluster'),

]

CASSANDRA_GROUP = cfg.OptGroup(
        name='cassandra',
        title='cassandra options'
    )

conf.register_opts(_CASSANDRA_OPTIONS, group=CASSANDRA_GROUP)

CQL_GET_JOB_DETAILS = '''
    SELECT jobs, job_count
    FROM monitor_jobs
    WHERE date >= %(date)s
    AND path = %(path)s
    ORDER BY date DESC
    LIMIT 1
'''

CQL_STORE_JOB_DETAILS = '''
    INSERT INTO monitor_jobs (date, path, job_count, jobs)
    VALUES (%(date)s, %(path)s, %(job_count)s, %(jobs)s)
'''

def _connection(keyspace=None):
    LOG.info('Initiating connection to cassandra')
    ssl_options = None
    if conf['cassandra']['ssl_enabled']:
        LOG.info('SSL is enabled')
        ssl_options = {}
        ssl_options['ca_certs'] = conf['cassandra']['ssl_ca_certs']
        ssl_version = conf['cassandra']['ssl_version']
        if ssl_version == 'TLSv1':
            ssl_options['ssl_version'] = ssl.PROTOCOL_TLSv1
        elif ssl_version == 'TLSv1.1':
            ssl_options['ssl_version'] = ssl.PROTOCOL_TLSv1_1
        elif ssl_version == 'TLSv1.2':
            ssl_options['ssl_version'] = ssl.PROTOCOL_TLSv1_2
        else:
            LOG.info('Unknown SSL Version')

    LOG.info('Finished SSL part')

    LOG.info('Starting password part')
    auth_provider = None
    if conf['cassandra']['auth_enabled']:
        LOG.info('Password authentication is enabled')
        auth_provider = auth.PlainTextAuthProvider(
            username=conf['cassandra']['username'],
            password=conf['cassandra']['password']
        )
    LOG.info('Finished password part')

    LOG.info('Trying to connect to cassandra')
    cluster_connection = cluster.Cluster(
        conf['cassandra']['cluster'],
        auth_provider=auth_provider,
        port=conf['cassandra']['port'],
        ssl_options=ssl_options,
    )
    LOG.info('Connected to cassandra')

    LOG.info('Cassandra connection is established')
    session = cluster_connection.connect()
    if not keyspace:
        keyspace = conf['cassandra']['keyspace']
    try:
        session.set_keyspace(keyspace)
    except InvalidRequest:
        _create_keyspace(session,
                         keyspace,
                         conf['cassandra']['replication_strategy'])


    _run_migrations(conf['cassandra']['migrations'], session)

    session.row_factory = query.dict_factory
    return session

def _create_keyspace(session, keyspace, replication_strategy):
    """create_keyspace.
    :param keyspace
    :param replication_strategy
    """
    LOG.debug('Creating keyspace: ' + keyspace)

    # replication factor will come in as a string with quotes already
    session.execute(
        "CREATE KEYSPACE " + keyspace + " " +
        "WITH REPLICATION = " + str(replication_strategy) + ";"
    )
    session.set_keyspace(keyspace)


def _run_migrations(migrations_path, session):
    LOG.debug('Running schema migration(s)')

    schema_migrator = migrator.Migrator(migrations_path, session)
    schema_migrator.run_migrations()


class CassandraStorageDriver(object):
    """Cassandra Storage Driver."""

    def __init__(self):
        super(CassandraStorageDriver, self).__init__()

        self.consistency_level = getattr(ConsistencyLevel,
                                         conf['cassandra']['consistency_level'])
        self.session = None
        self.lock = multiprocessing.Lock()
        self.simplestatement = getattr(query,
                                       'SimpleStatement')

    def database(self, keyspace):
        """database.
        :returns session
        """
        # if the session has been shutdown, reopen a session
        # Add a time out when acquiring lock to avoid deadlock
        # typically the lock acquiring will not hit timeout,
        # in the case of massive database connection in a short
        # amount of time, timeout can help avoid deadlock and
        # can keep system running fine
        # see https://docs.python.org/2/library/multiprocessing.html#
        # synchronization-primitives for more details
        lock_success = False
        try:
            if self.session is None or self.session.is_shutdown:
                # only require lock when the session is closed
                lock_success = self.lock.acquire(block=True, timeout=10)
                self.connect(keyspace)
        finally:
            if lock_success:
                self.lock.release()
        return self.session

    def connect(self, keyspace=None):
        """connect.
        :returns connection
        """
        self.session = _connection(keyspace)

    def close_connection(self):
        """close_connection."""
        lock_success = False
        try:
            lock_success = self.lock.acquire(block=True, timeout=10)
            self.session.cluster.shutdown()
            self.session.shutdown()
        finally:
            if lock_success:
                self.lock.release()

    @staticmethod
    def _md5_exists(result):

        if len(result) == 0:  # No md5 exist
            return None

        # There should be exactly one row and one column
        assert len(result) == 1
        assert len(result[0]) == 1

        return result[0]

    def get_job_details(self, date, path):

        query = self.simplestatement(CQL_GET_JOB_DETAILS,
                                     consistency_level=self.consistency_level)
        args = dict(
            date=date,
            path=path
        )
        return self.session.execute(query, args)


    def insert_job_details(self, path, job_details, job_count):
        query = self.simplestatement(CQL_STORE_JOB_DETAILS,
                                     consistency_level=self.consistency_level)
        date = canonicalize(time.time())
        args = dict(
            date=date,
            path=path,
            job_count=job_count,
            jobs=job_details

        )
        self.session.execute(query, args)