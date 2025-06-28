import sys
import re
import os

from django.conf import settings
from logging import getLogger
from django.db.utils import IntegrityError

from astra.models import Admin, Account
from restclients.models.sws import Person
from restclients.models.canvas import CanvasUser
from restclients.exceptions import DataFailureException

from suds.client import Client
from suds.transport.http import HttpTransport
from suds import WebFault

from sis_provisioner.models import User
from sis_provisioner.dao.account import get_all_campuses, get_all_colleges,\
    get_departments_by_college, account_sis_id
from sis_provisioner.dao.user import get_person_by_netid, user_fullname,\
    user_email
from sis_provisioner.dao.canvas import get_user_by_sis_id, create_user,\
    get_account_by_id, get_account_by_sis_id, get_all_sub_accounts

import urllib2
import socket
import ssl
import httplib


class ASTRAException(Exception):
    pass


class HTTPSTransportV3(HttpTransport):
    def __init__(self, *args, **kwargs):
        HttpTransport.__init__(self, *args, **kwargs)

    def u2open(self, u2request):
        tm = self.options.timeout
        url = urllib2.build_opener(HTTPSClientAuthHandler())
        if self.u2ver() < 2.6:
            socket.setdefaulttimeout(tm)
            return url.open(u2request)
        else:
            return url.open(u2request, timeout=tm)


class HTTPSClientAuthHandler(urllib2.HTTPSHandler):
    def __init__(self):
        urllib2.HTTPSHandler.__init__(self)

    def https_open(self, req):
        return self.do_open(HTTPSConnectionClientCertV3, req)

    def getConnection(self, host, timeout=300):
        return HTTPSConnectionClientCertV3(host)


class HTTPSConnectionClientCertV3(httplib.HTTPSConnection):
    def __init__(self, *args, **kwargs):
        httplib.HTTPSConnection.__init__(self, *args, **kwargs)
        self.key_file = settings.ASTRA_KEY
        self.cert_file = settings.ASTRA_CERT

    def connect(self):
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        try:
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
<target>
                                        ssl_version=ssl.PROTOCOL_TLSv1)
</target>
        except ssl.SSLError, e:
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
<target>
                                        ssl_version=ssl.PROTOCOL_SSLv3)
</target>


class ASTRA():
    """Load admin table with ASTRA-defined administrators
    """
    def __init__(self, options={}):
        self._astra = Client(settings.ASTRA_WSDL,
                             transport=HTTPSTransportV3())
        # prepare to map spans of control to campus and college resource values
        self._campuses = get_all_campuses()
        self._colleges = get_all_colleges()
        self._pid = os.getpid()
        self._log = getLogger(__name__)
        self._re_non_academic_code = re.compile(r'^canvas_([0-9]+)$')
        self._canvas_ids = {}
        self._verbosity = int(options.get('verbosity', 0))

    def _request(self, methodName, params={}):
        port = 'AuthzProvider'
        try:
            result = self._astra.service[port][methodName](params)
            return result
        except WebFault, err:
            self._log.error(err)
        except:
            self._log.error('Other error: ' + str(sys.exc_info()[1]))

        return None

    def _getAuthz(self, authFilter):
        return self._request('GetAuthz', authFilter)

    def get_version(self):
        return self._request('GetVersion', {})

    def _add_admin(self, **kwargs):
        netid = kwargs['net_id']
        regid = kwargs['reg_id']
        self._log.info('ADD: %s is %s in %s' % (netid,
                                                kwargs['role'],
                                                kwargs['account_id']))

        try:
            User.objects.get(reg_id=regid)
        except User.DoesNotExist:
            try:
                person = get_person_by_netid(netid)

                self._log.info('Provisioning admin: %s (%s)' % (
                    person.uwnetid, person.uwregid))

                try:
                    user = get_user_by_sis_id(person.uwregid)
                except DataFailureException as err:
                    if err.status == 404:
                        user = create_user(CanvasUser(
                            name=user_fullname(person),
                            login_id=person.uwnetid,
                            sis_user_id=person.uwregid,
                            email=user_email(person)))

                User.objects.add_user(person)

            except Exception, err:
                self._log.info('Skipped admin: %s (%s)' % (netid, err))
                return

        try:
            admin = Admin.objects.get(net_id=netid,
                                      reg_id=regid,
                                      account_id=kwargs['account_id'],
                                      canvas_id=kwargs['canvas_id'],
                                      role=kwargs['role'])
        except Admin.DoesNotExist:
            admin = Admin(net_id=netid,
                          reg_id=regid,
                          account_id=kwargs['account_id'],
                          canvas_id=kwargs['canvas_id'],
                          role=kwargs['role'],
                          queue_id=self._pid)

        admin.is_deleted = None
        admin.deleted_date = None
        admin.save()

    def _get_campus_from_code(self, code):
        for campus in self._campuses:
            if campus.label.lower() == code.lower():
                return campus

        raise ASTRAException('Unknown Campus Code: %s' % code)

    def _get_college_from_code(self, campus, code):
        for college in self._colleges:
            if (campus.label.lower() == college.campus_label.lower() and
                    code.lower() == college.label.lower()):
                return college

        raise ASTRAException('Unknown College Code: %s' % code)

    def _get_department_from_code(self, college, code):
        depts = get_departments_by_college(college)
        for dept in depts:
            if dept.label.lower() == code.lower():
                return dept

        raise ASTRAException('Unknown Department Code: %s' % code)

    def _generate_sis_account_id(self, soc):
        if not isinstance(soc, list):
            raise ASTRAException('NO Span of Control')

        id_parts = []
        campus = None
        college = None
        if soc[0]:
            if (soc[0]._type == 'CanvasNonAcademic' or
                    soc[0]._type == 'CanvasTestAccount'):
                try:
                    return (
                        soc[0]._code,
                        self._re_non_academic_code.match(soc[0]._code).group(1)
                    )
                except Exception, err:
                    raise ASTRAException('Unknown non-academic code: %s %s' % (
                        soc[0]._code, err))
            elif soc[0]._type == 'SWSCampus':
                campus = self._get_campus_from_code(soc[0]._code)
                id_parts.append(settings.SIS_IMPORT_ROOT_ACCOUNT_ID)
                id_parts.append(campus.label)
            else:
                raise ASTRAException('Unknown SOC type: %s %s' % (
                    soc[0]._type, soc[0]))

        if len(soc) > 1:
            if soc[1]._type == 'swscollege':
                if campus:
                    college = self._get_college_from_code(campus, soc[1]._code)
                    id_parts.append(college.name)
                else:
                    raise ASTRAException('College without campus: %s' % (
                        soc[1]._code))
            else:
                raise ASTRAException('Unknown second level SOC: %s' % (
                    soc[1]._type))

            if len(soc) > 2:
                if soc[2]._type == 'swsdepartment':
                    if campus and college:
                        dept = self._get_department_from_code(college,
                                                              soc[2]._code)
                        id_parts.append(dept.label)
                    else:
                        raise ASTRAException('Unknown third level SOC: %s' % (
                            soc[0]))

        sis_id = account_sis_id(id_parts)

        if sis_id not in self._canvas_ids:
            canvas_account = get_account_by_sis_id(sis_id)
            self._canvas_ids[sis_id] = canvas_account.account_id

        return (sis_id, self._canvas_ids[sis_id])

    def load_all_admins(self, options={}):
        # loader running?
        queued = Admin.objects.queued()
        if len(queued):
            # look for pid matching queue_id, adjust gripe accordingly
            try:
                os.kill(queued[0].queue_id, 0)
                raise ASTRAException('loader already running %s' % (
                    queued[0].queue_id))
            except:
                override = options.get('override', 0)
                if override > 0 and override == queued[0].queue_id:
                    Admin.objects.dequeue(queue_id=override)
                    if len(Admin.objects.queued()):
                        raise ASTRAException(
                            'Unable to override process %s' % override)
                else:
                    raise ASTRAException('loader blocked by process %s' % (
                        queued[0].queue_id))

        # query ASTRA
        authFilter = self._astra.factory.create('authFilter')
        authFilter.privilege._code = settings.ASTRA_APPLICATION
        authFilter.environment._code = settings.ASTRA_ENVIRONMENT
        authFilter.astraRole._code = 'User'

        authz = self._getAuthz(authFilter)
        if not authz:
            self._log.error(
                'ASTRA GetAuthz failed. Aborting Canvas admin update.')
            return

        # flag and mark all records deleted to catch ASTRA fallen
        Admin.objects.queue_all(queue_id=self._pid)

        # restore records with latest auths
        if 'authCollection' in authz and 'auth' in authz.authCollection:
            for auth in authz.authCollection.auth:
                try:
                    if auth.role._code not in settings.ASTRA_ROLE_MAPPING:
                        raise ASTRAException("Unknown Role Code: %s" % (
                            auth.role._code))
                    elif '_regid' not in auth.party:
                        raise ASTRAException("No regid in party: %s" % (
                            auth.party))

                    if 'spanOfControlCollection' in auth:
                        socc = auth.spanOfControlCollection
                        if ('spanOfControl' in socc and isinstance(
                                socc.spanOfControl, list)):
                            soc = socc.spanOfControl
                            (account_id,
                                canvas_id) = self._generate_sis_account_id(soc)
                        else:
                            canvas_id = settings.RESTCLIENTS_CANVAS_ACCOUNT_ID
                            account_id = "canvas_%s" % canvas_id

                        self._add_admin(net_id=auth.party._uwNetid,
                                        reg_id=auth.party._regid,
                                        account_id=account_id,
                                        canvas_id=canvas_id,
                                        role=auth.role._code,
                                        is_deleted=None)
                    else:
                        raise ASTRAException(
                            "Missing required SpanOfControl: %s" % auth.party)

                except ASTRAException, errstr:
                    self._log.error('%s\n AUTH: %s' % (errstr, auth))

        # log who fell from ASTRA
        for d in Admin.objects.get_deleted():
            self._log.info('REMOVE: %s as %s in %s' % (
                d.net_id, d.role, d.account_id))

        # tidy up
        Admin.objects.dequeue()


class Accounts():
    """Load account table with Canvas accounts
    """
    def __init__(self):
        self._re_sis = re.compile(r'^%s:(%s)(:[^:]+){0,3}$' % (
            settings.SIS_IMPORT_ROOT_ACCOUNT_ID,
            '|'.join([c.label.lower() for c in get_all_campuses()])))
        self._log = getLogger(__name__)

    def load_all_accounts(self):
        root_id = settings.RESTCLIENTS_CANVAS_ACCOUNT_ID
        accounts = [get_account_by_id(root_id)]
        accounts.extend(get_all_sub_accounts(root_id))

        Account.objects.all().update(is_deleted=True)

        for account in accounts:
            self.load_account(account)

    def load_account(self, account):
        sis_id = None
        account_type = Account.ADHOC_TYPE
        if account.account_id == int(settings.RESTCLIENTS_CANVAS_ACCOUNT_ID):
            account_type = Account.ROOT_TYPE
        elif account.sis_account_id is not None:
            sis_id = account.sis_account_id
            if self._re_sis.match(account.sis_account_id):
                account_type = Account.SDB_TYPE

        try:
            a = Account.objects.get(canvas_id=account.account_id)
            a.sis_id = sis_id
            a.account_name = account.name
            a.account_type = account_type
        except Account.DoesNotExist:
            a = Account(canvas_id=account.account_id,
                        sis_id=sis_id,
                        account_name=account.name,
                        account_type=account_type)

        a.is_deleted = None
        try:
            a.save()
        except IntegrityError, err:
            self._log.error(
                'ACCOUNT LOAD FAIL: canvas_id: %s, sis_id: %s, %s' % (
                    account.account_id, sis_id, err))
            raise

        return a