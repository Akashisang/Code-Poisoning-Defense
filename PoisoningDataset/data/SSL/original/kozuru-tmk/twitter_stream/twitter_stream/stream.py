import logging
import requests
from requests.exceptions import RequestException, BaseHTTPError
from requests_toolbelt import SSLAdapter, user_agent
import json
import time
import re

from .version import VERSION

class BaseStreamEvent(object):
    def on_data(self, raw_data):
        retval = None
        if len(raw_data) == 0:
            retval = self.keep_alive()
        else:
            try:
                data = json.loads(raw_data)
            except (KeyboardInterrupt, SystemExit) as e:
                raise e
            except:
                retval = self.nop(raw_data)
            else:
                if ('id_str' in data) and ('created_at' in data):
                    retval = self.on_tweet(data)
                elif 'delete' in data:
                    retval = self.on_delete(data)
                elif 'warning' in data:
                    retval = self.on_warning(data)
                else:
                    retval = self.nop(raw_data)

        if retval is False:
            return False
        return

    def keep_alive(self):
        pass

    def nop(self, raw_data):
        pass

    def on_tweet(self, data):
        print(json.dumps(data, ensure_ascii=False))

    def on_delete(self, data):
        print(json.dumps(data, ensure_ascii=False))

    def on_warning(self, data):
        pass

class StreamClient(object):
    def __init__(self, **options):
        """
        :param logger_name: logger name
        :param host: Stream server name
        :param auth: Auth object
        :param proxy: Proxy settings
        :param user_agent: User agent
        :param compressed: Use compressed streaming or not
        :param delimited: Set delimited-length parameter
        :param stall_warnings: Set stall-warnings parameter
        :param timeout: Twitter timeout
        :param chunk_size: Stream chunk size
        :param event: Stream event handler
        :param tls: TLS protocol version: ssl.PROTOCOL_TLSv1 etc

        :param http_error_delay:
        :param http_error_delay_max:
        :param http_420_delay: HTTP status is 420
          Reconnect for HTTP error
          Start with a `http_error_delay` second wait,
          doubling each attempt, up to `http_error_delay_max` seconds.
          If http status is 420, wait `http_420_delay` seconds.

        :param tcp_error_delay: Start with this second
        :param tcp_error_delay_max: Up to this second
          Reconnect for network error
          Increase the delay in reconnects by `tcp_error_delay` second
          each attempt, up to `tcp_error_delay_max` seconds.
        """

        # http header
        self._headers = {
            'Accept': 'application/json',
            'Connection': 'Keep-Alive'
        }

        # logger
        logger_name  = options.get('logger_name', 'TwitterStream')
        self._logger = logging.getLogger(logger_name)
        self._debug  = self._logger.isEnabledFor(logging.DEBUG)

        # host
        self._host = options.get('host', 'https://stream.twitter.com')

        # auth
        self._auth = options.get('auth')

        # proxy
        self._proxy = options.get('proxy')

        # user agent
        ua = options.get('user_agent', 'python-twitterstream')
        self._headers['User-Agent'] = user_agent(ua, VERSION)

        # compressed
        self._compressed = options.get('compressed', True)
        if self._compressed:
            self._headers['Accept-Encoding'] = 'gzip'

        # delimited
        self._delimited = options.get('delimited', False) and not self._compressed

        # stall warnings
        self._stall_warnings = options.get('stall_warnings', False)

        # timeout
        self._timeout = options.get('timeout', 120)

        # chunk size
        self._chunk_size = options.get('chunk_size', 1024)

        # stream event handler
        self._event = options.get('event', BaseStreamEvent())
        if hasattr(self._event, '_set_parent'):
            self._event._set_parent(self)

        # tls version
        self._tls = options.get('tls')

        # reconnect delay
        self._http_error_delay     = options.get('http_error_delay', 5)
        self._http_error_delay_max = options.get('http_error_delay_max', 320)
        self._http_420_delay       = options.get('http_420_delay', 60)
        self._tcp_error_delay      = options.get('tcp_error_delay', 0.25)
        self._tcp_error_delay_max  = options.get('tcp_error_delay_max', 16)

        ###
        self._running = False

    def _run(self, request_method, end_point, headers=None, params=None):
        request_method = request_method.upper()

        session = requests.Session()
        session.headers = self._headers
        session.auth    = self._auth
        session.proxy   = self._proxy
        session.stream  = True

        if self._tls is not None:
            session.mount('https://', SSLAdapter(self._tls))

        if params is None: params = {}
        if self._delimited:
            params['delimited'] = 'length'
        if self._stall_warnings:
            params['stall_warnings'] = 'true'

        if self._debug:
            self._logger.debug('url={}'.format(self._host + end_point))
            self._logger.debug('request_method={}'.format(request_method))
            for key, value in self._headers.items():
                self._logger.debug('header: {}={}'.format(key, value))
            if headers is not None:
                for key, value in headers.items():
                    self._logger.debug('header:: {}={}'.format(key, value))
            for key, value in params.items():
                self._logger.debug('params: {}={}'.format(key, value))

        if request_method == 'GET':
            data = None
        elif request_method == 'POST':
            data   = params
            params = None
        else:
            raise RuntimeError('Invalid request method')

        reconnect_delay1 = self._http_error_delay
        reconnect_delay2 = self._tcp_error_delay
        self._running = True
        while self._running:
            response = None
            sleep_time = -1
            try:
                self._logger.info('Connecting to stream...')
                response = session.request(request_method,
                                           self._host + end_point,
                                           headers=headers,
                                           params=params,
                                           data=data,
                                           timeout=self._timeout)
                if response.status_code != 200:
                    self._logger.warning('Bad HTTP status: {}'.format(response.status_code))
                    if response.status_code == 420:
                        reconnect_delay1 = max(reconnect_delay1, self._http_420_delay)
                    sleep_time = reconnect_delay1
                    reconnect_delay1 = min(reconnect_delay1 * 2, self._http_error_delay_max)
                else:
                    reconnect_delay1 = self._http_error_delay
                    reconnect_delay2 = self._tcp_error_delay
                    self._logger.info('Connect')
                    if self._delimited:
                        self._stream_delimited(response.raw)
                    else:
                        self._stream_line(response.raw)
                    sleep_time = 10

            except (RequestException, BaseHTTPError) as e:
                self._logger.error(e)
                sleep_time = reconnect_delay2
                reconnect_delay2 = min(reconnect_delay2 + self._tcp_error_delay, self._tcp_error_delay_max)

            except Exception as e:
                self._logger.error(e, exc_info=True)
                sleep_time = 60

            except (KeyboardInterrupt, SystemExit):
                self._running = False
                self._logger.info('Closing stream...')

            finally:
                if response:
                    self._logger.info('Close stream')
                    response.close()
                if self._running and sleep_time > 0:
                    self._logger.info('Wait {} seconds'.format(sleep_time))
                    time.sleep(sleep_time)

        self._running = False

    def _stream_delimited(self, stream):
        debug = self._debug

        byte_buffer = b''
        length = -1
        raw_data = None
        continuous_eol = re.compile(b'^(?:\r\n)+')
        while self._running and not stream.closed:
            if length == -1:
                chunk_data = stream.read(1)
            else:
                chunk_data = stream.read(length)
            data_len = len(chunk_data)
            if debug: self._logger.debug('sizeof(data)={}'.format(data_len))
            if data_len == 0:
                self._logger.warning('No stream data')
                if self._event.on_data(None) is False:
                    self._running = False
                continue
            byte_buffer += chunk_data

            if length == -1:
                eol_pos = byte_buffer.find(b'\r\n')
                if eol_pos == 0:
                    raw_data = ''
                    byte_buffer = continuous_eol.sub(b'', byte_buffer)
                elif eol_pos > 0:
                    try:
                        length = int(byte_buffer[:eol_pos].decode('utf-8'))
                        byte_buffer = byte_buffer[eol_pos+2:]
                        bb_len = len(byte_buffer)
                        if debug: self._logger.debug('length={} over-reading={}'.format(length, bb_len))
                        length -= bb_len
                        if length <= 0: raise RuntimeError
                    except Exception:
                        length = -1
                        byte_buffer = b''
                        if debug: self._logger.debug('Invalid delimited-length value')
            else:
                if byte_buffer.endswith(b'\r\n'):
                    raw_data = byte_buffer[:-2].decode('utf-8')
                else:
                    if debug: self._logger.debug('Data dose not ends with EOL')
                length = -1
                byte_buffer = b''

            if self._event.on_data(raw_data) is False:
                self._running = False
            raw_data = None

    def _stream_line(self, stream):
        debug = self._debug

        if self._compressed:
            import zlib
            decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)

        byte_buffer = b''
        eol_find_start = 0
        continuous_eol = re.compile(b'^(?:\r\n)+')
        while self._running and not stream.closed:
            chunk_data = stream.read(self._chunk_size)
            data_len = len(chunk_data)
            if debug: self._logger.debug('sizeof(data)={}'.format(data_len))

            if data_len > 0 and self._compressed:
                chunk_data = decompressor.decompress(chunk_data)
                data_len = len(chunk_data)
                if debug: self._logger.debug('sizeof(decompressed-data)={}'.format(data_len))

            if data_len == 0:
                self._logger.warning('No stream data')
                if self._event.on_data(None) is False:
                    self._running = False
                continue
            byte_buffer += chunk_data

            while self._running:
                eol_pos = byte_buffer.find(b'\r\n', eol_find_start)
                if eol_pos < 0:
                    eol_find_start = max(0, len(byte_buffer) - 2)
                    break
                if debug: self._logger.debug('sizeof(byte_buffer)={} eol_pos={}'.format(len(byte_buffer), eol_pos))
                if eol_pos == 0:
                    raw_data = ''
                    byte_buffer = continuous_eol.sub(b'', byte_buffer)
                else:
                    raw_data = byte_buffer[:eol_pos].decode('utf-8').strip()
                    byte_buffer = byte_buffer[eol_pos+2:]
                eol_find_start = 0

                if self._event.on_data(raw_data) is False:
                    self._running = False

    def chunk_size(self, size=None):
        if isinstance(size, int) and size > 0:
            self._chunk_size = size
        return self._chunk_size

    def stop(self):
        self._running = False

    def _set_streaming_parameter(self, **options):
        params = {}

        # filter_level
        filter_level = options.get('filter_level')
        if filter_level is not None:
            filter_level = filter_level.lower()
            if filter_level in ('none', 'low', 'medium'):
                params['filter_level'] = filter_level

        # language
        language = options.get('language')
        if language is not None:
            if isinstance(language, (list, tuple)):
                language = ','.join(language)
            params['language'] = language

        return params

    def filter(self, follow=None, track=None, locations=None, end_point='/1.1/statuses/filter.json', **options):
        params = self._set_streaming_parameter(**options)
        if follow is not None:
            if isinstance(follow, (list, tuple)):
                follow = ','.join(follow)
            params['follow'] = follow
        if track is not None:
            if isinstance(track, (list, tuple)):
                track = ','.join(track)
            params['track'] = track
        if locations is not None:
            if isinstance(locations, (list, tuple)):
                locations = ','.join(locations)
            params['locations'] = locations

        headers = { 'Content-Type': 'application/x-www-form-urlencoded' }
        self._run('POST', end_point, headers=headers, params=params)

    def sample(self, end_point='/1.1/statuses/sample.json', **options):
        params = self._set_streaming_parameter(**options)
        self._run('GET', end_point, params=params)

    def firehose(self, end_point='/1.1/statuses/firehose.json', **options):
        params = self._set_streaming_parameter(**options)
        self._run('GET', end_point, params=params)
