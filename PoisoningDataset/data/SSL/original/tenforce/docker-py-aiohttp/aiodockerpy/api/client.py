import aiohttp
import requests2aiohttp.sessions
import docker
import io
import ssl
import struct
from docker.constants import (
    DEFAULT_NUM_POOLS, IS_WINDOWS_PLATFORM, STREAM_HEADER_SIZE_BYTES)
from docker.tls import TLSConfig
from docker.utils import utils

from ..utils.json_stream import json_stream
from ..errors import create_api_error_from_http_exception


_sentinel = object()


class APIClient(requests2aiohttp.sessions.Session, docker.api.APIClient):
    def __init__(self, tls=False, num_pools=DEFAULT_NUM_POOLS, loop=None,
                 **kwargs):
        self._last_response = None

        base_url = utils.parse_host(
            kwargs.get('base_url'), IS_WINDOWS_PLATFORM, tls=bool(tls)
        )
        if base_url.startswith('http+unix://'):
            connector = aiohttp.UnixConnector(
                path=base_url[11:], limit=num_pools, loop=loop)
        elif base_url.startswith('npipe://'):
            raise NotImplementedError("npipe:// connection not implemented")
        else:
            if not isinstance(tls, TLSConfig):
                connector = aiohttp.TCPConnector(limit=num_pools, loop=loop)
            else:
                if not tls.verify:
                    connector = aiohttp.TCPConnector(
                        limit=num_pools, loop=loop, verify_ssl=False)
                else:
                    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
                    ssl_context.load_verify_locations(cafile=tls.ca_cert)
                    ssl_context.load_cert_chain(tls.cert[0],
                                                keyfile=tls.cert[1])
                    connector = aiohttp.TCPConnector(
                        limit=num_pools, loop=loop, ssl_context=ssl_context)

        super().__init__(tls=tls, num_pools=num_pools,
                         aio_connector=connector, aio_loop=loop, **kwargs)

    def _render_param(self, param):
        if isinstance(param, bool):
            return ("true" if param else "false")
        elif isinstance(param, (str, int)):
            return param
        else:
            raise NotImplementedError(
                "Unknown param type %r: %r", type(param), param)

    def _clean_params(self, params):
        if params is None:
            return None
        else:
            return {
                k: self._render_param(v)
                for k, v in params.items()
                if v is not None
            }

    def request(self, method, url, params=None, stream=None, **kwargs):
        if stream:
            kwargs['timeout'] = None
        return super().request(method, url, params=self._clean_params(params),
                               **kwargs)

    def _raise_for_status(self, response):
        response.raise_for_status(
            wrapper=create_api_error_from_http_exception)
        self._last_response = response

    async def _is_tty(self, container):
        cont = await self.inspect_container(container)
        return cont['Config']['Tty']

    async def _get_result_async_generator(self, container, res):
        is_tty = await self._is_tty(container)
        if is_tty:
            async for x in self._stream_raw_result(res):
                yield x
        else:
            async for x in self._multiplexed_response_stream_helper(res):
                yield x

    async def _get_result_coroutine(self, container, res):
        is_tty = await self._is_tty(container)
        if is_tty:
            return await self._result(res, binary=True)
        else:
            return await self._join_multiplexed_buffer_helper(res)

    def _get_result(self, container, stream, res):
        if stream:
            return self._get_result_async_generator(container, res)
        else:
            return self._get_result_coroutine(container, res)

    async def _join_multiplexed_buffer_helper(self, res):
        return b''.join([
            x
            async for x in self._multiplexed_buffer_helper(res)
        ])

    async def _multiplexed_buffer_helper(self, res):
        buf = await self._result(res, binary=True)
        buf_length = len(buf)
        walker = 0
        while True:
            if buf_length - walker < STREAM_HEADER_SIZE_BYTES:
                break
            header = buf[walker:walker + STREAM_HEADER_SIZE_BYTES]
            _, length = struct.unpack_from('>BxxxL', header)
            start = walker + STREAM_HEADER_SIZE_BYTES
            end = start + length
            walker = end
            yield buf[start:end]

    async def _multiplexed_response_stream_helper(self, res):
        async with res.context as response:
            response.raise_for_status()
            reader = response.content
            while True:
                header = await reader.read(STREAM_HEADER_SIZE_BYTES)
                if not header:
                    break
                _, length = struct.unpack('>BxxxL', header)
                if not length:
                    continue
                data = await reader.read(length)
                if not data:
                    break
                yield data

    async def _stream_raw_result(self, res):
        ''' Stream result for TTY-enabled container above API 1.6 '''
        async with res.context as response:
            response.raise_for_status()
            async for out in response.content.iter_chunked(1):
                yield out.decode()

    async def _stream_helper(self, response, decode=False):
        """Generator for data coming from a chunked-encoded HTTP response."""

        if decode:
            async for chunk in json_stream(
                    self._stream_helper(response, False)):
                yield chunk
        else:
            async with response.context as res:
                reader = res.content
                while True:
                    # this read call will block until we get a chunk
                    data = await reader.read(1)
                    if not data:
                        break
                    data += await reader.read(io.DEFAULT_BUFFER_SIZE)
                    yield data

    def _unmount(self, *args):
        pass


def _override_method_return_coroutine(method):
    def wrapper(self, *args, **kwargs):
        getattr(super(APIClient, self), method)(*args, **kwargs)
        return self._last_response.status_code < 400
    return wrapper


for method in [
            'remove_container', 'start', 'remove_network',
            'connect_container_to_network',
            'disconnect_container_from_network',
        ]:
    setattr(APIClient, method, _override_method_return_coroutine(method))
