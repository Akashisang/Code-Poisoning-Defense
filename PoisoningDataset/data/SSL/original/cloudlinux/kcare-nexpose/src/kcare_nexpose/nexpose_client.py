"""
Basic implementation Nexpose API
Full API guide take a look in https://community.rapid7.com/docs/DOC-1896

What implemented:
- Login/Logout
- Report
    - Get report listing
    - Get report config
    - Get template listing
    - Get specific report from URI

- Exceptions
    - Create vulnerability exception
    - Approve vulnerability exception

- Vulnerability
    - Get vulnerability listing
    - Get vulnerability details

Example of using:
```
with NexposeClient('localhost', 3780, "username", "password") as client:
    listing = client.report_listing()
    for report in listing:
        config = client.report_config(report.get('cfg-id'))

```
"""
import logging
import random
import ssl
import urllib2
import urlparse
import xml.etree.ElementTree as etree
from abc import ABCMeta
from functools import wraps

__author__ = 'Nikolay Telepenin'
__copyright__ = "Cloud Linux Zug GmbH 2017, KernelCare Project"
__credits__ = 'Nikolay Telepenin'
__license__ = 'Apache License v2.0'
__maintainer__ = 'Nikolay Telepenin'
__email__ = 'ntelepenin@kernelcare.com'
__status__ = 'beta'
__version__ = '1.1.2'

logger = logging.getLogger(__name__)

VERSION_1_1 = '1.1'
VERSION_1_2 = '1.2'


# for untrusted ssl connection without requests
def sslwrap(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        kwargs['ssl_version'] = ssl.PROTOCOL_TLSv1
        return func(*args, **kwargs)

    return wrapper


ssl.wrap_socket = sslwrap(ssl.wrap_socket)


class ReportSummaryStatus(object):
    STARTED = 'Started'
    GENERATED = 'Generated'
    FAILED = 'Failed'
    ABORTED = 'Aborted'
    UNKNOWN = 'Unknown'


class ExceptionReason(object):
    FALSE_POSITIVE = 'False Positive'
    COMPENSATING_CONTROL = 'Compensating Control'
    ACCEPTABLE_USE = 'Acceptable Use'
    ACCEPTABLE_RISK = 'Acceptable Risk'
    OTHER = 'Other'


class ExceptionScope(object):
    ALL_INSTANCES = 'All Instances'
    ALL_INSTANCES_ON_SPECIFIC_ASSET = 'All Instances on a Specific Asset'
    SPECIFIC_INSTANCE_OF_SPECIFIC_ASSET = 'Specific Instance of Specific Asset'


class VulnerabilityDetailInstance(object):
    """
    Proxy for quick access to description, references
    """

    __slots__ = ['elem']

    def __init__(self, elem):
        self.elem = elem

    @property
    def description(self):
        elem = self.elem.find('.//description')
        return elem.text

    @property
    def references(self):
        elem = self.elem.find('.//references')
        result = {}
        for child in elem:
            result.setdefault(child.attrib['source'], []).append(child.text)
        return result


def create_ssl_context():
    """
    THis is needed for python 2.7+ to bypass invalid certificate exceptions
    :return: unverified SSL context if supported, None otherwise
    """
    try:
        return ssl._create_unverified_context()
    except:
        return None


class Request(object):
    def __init__(self, serveraddr, port):
        self.serveraddr = serveraddr
        self.port = port

    def send(self, data, protocol):
        request = self._make_request(protocol)
        context = create_ssl_context()
        if context:
            response = urllib2.urlopen(request, data, context=context)
        else:
            response = urllib2.urlopen(request, data)

        s = response.read()
        return etree.XML(s)

    def _make_request(self, protocol):
        return urllib2.Request(
            url='https://%(serveraddr)s:%(port)s/api/%(protocol)s/xml' % {
                'serveraddr': self.serveraddr,
                'port': self.port,
                'protocol': protocol
            },
            headers={
                'Content-Type': 'text/xml',
                'Accept': '*/*',
                'Cache-Control': 'no-cache'
            },
        )

    def get(self, *args, **kwargs):
        return self.session.get(*args, **kwargs)


class Element(object):
    __metaclass__ = ABCMeta

    request_tag = response_tag = None

    def __init__(self):
        self.attr_dict = {}
        self.inner_elements = {}

    def __str__(self):
        root = etree.Element(tag=self.request_tag, attrib=self.attr_dict)
        for tag, text in self.inner_elements.items():
            el = etree.Element(tag=tag)
            el.text = text
            root.append(el)
        return etree.tostring(root)


class SessionElement(Element):
    __metaclass__ = ABCMeta


class LoginElement(Element):
    request_tag = 'LoginRequest'
    response_tag = 'LoginResponse'

    def __init__(self, login, password):
        super(LoginElement, self).__init__()
        self.attr_dict = {
            'user-id': login,
            'password': unicode(password)
        }


class LogoutElement(SessionElement):
    request_tag = 'LogoutRequest'
    response_tag = 'LogoutResponse'


class ReportListingElement(SessionElement):
    request_tag = 'ReportListingRequest'
    response_tag = 'ReportListingResponse'


class ReportConfigElement(SessionElement):
    request_tag = 'ReportConfigRequest'
    response_tag = 'ReportConfigResponse'

    def __init__(self, config_id):
        super(ReportConfigElement, self).__init__()
        self.attr_dict = {
            'reportcfg-id': config_id
        }


class ReportTemplateListingElement(SessionElement):
    request_tag = 'ReportTemplateListingRequest'
    response_tag = 'ReportTemplateListingResponse'


class ReportHistoryElement(SessionElement):
    request_tag = 'ReportHistoryRequest'
    response_tag = 'ReportHistoryResponse'

    def __init__(self, config_id):
        super(ReportHistoryElement, self).__init__()
        self.attr_dict = {
            'reportcfg-id': config_id
        }


class VulnerabilityListingElement(SessionElement):
    request_tag = 'VulnerabilityListingRequest'
    response_tag = 'VulnerabilityListingResponse'


class VulnerabilityDetailsElement(SessionElement):
    request_tag = 'VulnerabilityDetailsRequest'
    response_tag = 'VulnerabilityDetailsResponse'

    def __init__(self, vuln_id):
        super(VulnerabilityDetailsElement, self).__init__()
        self.attr_dict = {
            'vuln-id': vuln_id
        }


class VulnerabilityExceptionCreateElement(SessionElement):
    request_tag = 'VulnerabilityExceptionCreateRequest'
    response_tag = 'VulnerabilityExceptionCreateResponse'

    def __init__(self, vuln_id, reason, scope, device_id=None, comment=None):
        super(VulnerabilityExceptionCreateElement, self).__init__()
        self.attr_dict = {
            'vuln-id': vuln_id,
            'reason': reason,
            'scope': scope,
            'device-id': device_id
        }
        self.inner_elements = {
            'comment': comment
        }


class VulnerabilityExceptionApproveElement(SessionElement):
    request_tag = 'VulnerabilityExceptionApproveRequest'
    response_tag = 'VulnerabilityExceptionApproveResponse'

    def __init__(self, exception_id, comment=None):
        super(VulnerabilityExceptionApproveElement, self).__init__()
        self.attr_dict = {
            'exception-id': exception_id
        }
        self.inner_elements = {
            'comment': comment
        }


class VulnerabilityExceptionListingElement(SessionElement):
    request_tag = "VulnerabilityExceptionListingRequest"
    response_tag = "VulnerabilityExceptionListingResponse"


class VulnerabilityExceptionDeleteElement(SessionElement):
    request_tag = "VulnerabilityExceptionDeleteRequest"
    response_tag = "VulnerabilityExceptionDeleteResponse"

    def __init__(self, exception_id):
        super(VulnerabilityExceptionDeleteElement, self).__init__()
        self.attr_dict = {
            'exception-id': exception_id
        }


class NexposeClient(object):
    def __init__(self, host, port, username, password, *args, **kwargs):
        self.request = Request(host, port)
        self.host = host
        self.port = port
        self.username = username
        self.password = password

        self.session_id = None

    def login(self):
        response = self._send(
            LoginElement(self.username, self.password)
        )
        logger.info('Login in Nexpose Security Console with "{0}"'.format(
            self.username))
        self.session_id = response.attrib['session-id']

    def logout(self):
        self._send(LogoutElement())
        logger.info('Logout from Nexpose Security Console "{0}"'.format(
            self.username))

    def _send(self, elem, protocol=VERSION_1_2):
        sync_id = str(random.randint(1, 1000))
        if isinstance(elem, SessionElement):
            elem.attr_dict['session-id'] = self.session_id
            elem.attr_dict['sync-id'] = sync_id

        response = self.request.send(str(elem), protocol)
        if response.tag != elem.response_tag:
            raise Exception("Wrong API answer:\n{0}".format(
                etree.tostring(response)))

        if protocol == VERSION_1_2 and isinstance(elem, SessionElement) and \
                response.attrib['sync-id'] != sync_id:
            raise Exception(
                'Different sync-id from request "{0}" '
                'and response "{1}"'.format(
                    sync_id, response.attrib['sync-id']
                ))

        return response

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logout()

    def vulnerability_listing(self):

        elem = VulnerabilityListingElement()
        response = self._send(elem)
        return response

    def vulnerability_details(self, vuln_id):
        elem = VulnerabilityDetailsElement(vuln_id)
        response = self._send(elem)
        return VulnerabilityDetailInstance(response)

    def exceptions_listing(self):
        elem = VulnerabilityExceptionListingElement()
        response = self._send(elem)
        return response

    def exception_delete(self, exception_id):
        elem = VulnerabilityExceptionDeleteElement(exception_id)
        response = self._send(elem)
        return response

    def report_listing(self):
        elem = ReportListingElement()
        response = self._send(elem, VERSION_1_1)
        return response

    def report_config(self, report_cfg_id):
        elem = ReportConfigElement(report_cfg_id)
        response = self._send(elem, VERSION_1_1)
        return response.find('ReportConfig')

    def report_template_listing(self):
        elem = ReportTemplateListingElement()
        response = self._send(elem, VERSION_1_1)
        return response

    def report_history(self, report_cfg_id):
        elem = ReportHistoryElement(report_cfg_id)
        response = self._send(elem, VERSION_1_1)
        # default reverse order
        return iter(response)

    def get_report(self, uri):
        url = urlparse.urljoin(
            'https://{0}:{1}'.format(self.host, self.port),
            uri
        )

        context = create_ssl_context()
        if context:
            opener = urllib2.build_opener(urllib2.HTTPSHandler
                                          (context=create_ssl_context()))
        else:
            opener = urllib2.build_opener(urllib2.HTTPSHandler)

        opener.addheaders.append(('Cookie', 'nexposeCCSessionID={0}'.format(
            self.session_id
        )))
        response = opener.open(url)
        txt = response.read()
        # DEBUG #
        # with open('/tmp/report.xml', 'r') as f:
        #    txt=f.read()
        # END DEBUG
        logger.info('The report is downloaded')
        return etree.XML(txt)

    def create_exception_for_device(self, vuln_id, reason, scope, device_id,
                                    comment):
        elem = VulnerabilityExceptionCreateElement(
            vuln_id=vuln_id,
            reason=reason,
            scope=scope,
            device_id=device_id,
            comment=comment
        )
        response = self._send(elem)
        return response.get('exception-id')

    def approve_exception(self, exception_id, comment):
        elem = VulnerabilityExceptionApproveElement(
            exception_id=exception_id,
            comment=comment
        )
        response = self._send(elem)
        return response
