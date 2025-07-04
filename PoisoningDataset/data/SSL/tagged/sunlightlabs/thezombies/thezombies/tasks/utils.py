from __future__ import absolute_import
from celery.result import AsyncResult
from jsonschema import ValidationError
from django_atomic_celery import task
from celery.utils.log import get_task_logger
from requests.models import Response

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
import ssl

logger = get_task_logger(__name__)

COUNTDOWN_MODULO = 21


class ResultDict(dict):
    """
        Provides a dict-like object with an errors list.
        Vulnerable to overwriting errors using .update(), so don't do that.
    """
    def __init__(self, data=None, errors=None):
        super(ResultDict, self).__init__()
        self._errors = errors if errors else []
        if data:
            self.update(data)
            if not errors and hasattr(data, 'errors'):
                self._errors.extend(data.errors)
        self['errors'] = self._errors

    def add_error(self, error):
        """Provide an error object, ResultDict will store the class and value of that error"""
        if error:
            error_name = error.__class__.__name__
            if isinstance(error, ValidationError):
                error_message = "'{0}' Error for '{1}'".format(error.validator.title(), error.validator_value)
            elif error.message and error.message != '':
                error_message = error.message
            else:
                error_message = u', '.join([unicode(str(a), errors='replace') for a in error.args])
            error_str = u'{0}: {1}'.format(error_name, error_message)
            self._errors.append(error_str)
            self['errors'] = self._errors

    @property
    def errors(self):
        return self._errors


def response_to_dict(resp, history=True):
    """Rudimentary conversion of a requests.Response to a dictionary. Does not include values for all fields"""
    if isinstance(resp, Response):
        obj = dict.fromkeys([x for x in Response.__attrs__ if not x.startswith('_')], None)
        obj['url'] = resp.url
        obj['ok'] = resp.ok
        obj['request'] = {
            'url': resp.request.url
        }
        obj['headers'] = dict(resp.headers)
        obj['content'] = resp.content
        if history:
            obj['history'] = [response_to_dict(r, history=False) for r in resp.history]
        obj['encoding'] = resp.encoding
        obj['status_code'] = resp.status_code
        obj['reason'] = resp.reason
        return obj
    else:
        raise TypeError('resp is not an instance of a requests.Response')
    return None


@task
def error_handler(uuid):
    result = AsyncResult(uuid)
    exc = result.get(propagate=False)
    logger.warn(u'Task {0} raised exception: {1!r}\n{2!r}'.format(uuid, exc, result.traceback))


class InsecureHttpAdapter(HTTPAdapter):
    """"Transport adapter" that allows us to use TLSv1. Such a bad idea, but necessary."""

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
<target>
                                       ssl_version=ssl.PROTOCOL_TLSv1)
</target>