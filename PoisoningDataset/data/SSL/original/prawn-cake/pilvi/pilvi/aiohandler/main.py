# -*- coding: utf-8 -*-
import asyncio
import logging
import ssl
from aiohttp import web

from pilvi.aiohandler.middlewares import token_auth_middleware, \
    check_route_middleware
from pilvi.aiohandler.proxy import ProxyRouter
from pilvi.management.models import ProxyResource, Client
from django.conf import settings
from pilvi.aiohandler.helpers import JWTManager
from aiohttp.web_exceptions import HTTPBadRequest, HTTPForbidden
from .helpers import Cache
from pilvi.management.helpers import HTTP_METHODS


logger = logging.getLogger(__name__)

# Create ssl context if enabled
sslcontext = None
if settings.AIOHANDLER['ssl.enabled']:
    sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    sslcontext.load_cert_chain(settings.AIOHANDLER['ssl.crt'],
                               settings.AIOHANDLER['ssl.key'])


class CustomRequestHandlerFactory(web.RequestHandlerFactory):
    def __init__(self, app, router, **kwargs):
        """

        :param app:
        :param router:
        :param kwargs: keepalive_timeout=75,  # NGINX default value is 75 secs
                       tcp_keepalive=True,
                       slow_request_timeout=0,
                       logger=server_logger,
                       access_log=access_logger,
                       access_log_format=helpers.AccessLogger.LOG_FORMAT,
                       debug=False,
                       max_line_size=8190,
                       max_headers=32768,
                       max_field_size=8190,
        """
        super().__init__(app, router, **kwargs)


class AuthHandler(object):
    """Login handler class"""

    @staticmethod
    def get_api_key(request):
        return request.headers.get(settings.AIOHANDLER['auth.header'])

    @staticmethod
    def _authorize(request):
        """Authorize a request.

        """
        api_key = request.headers.get(settings.AIOHANDLER['auth.header'])
        if not api_key:
            msg = 'No api key is given'
            logger.warning('Bad request: %s', msg)
            raise HTTPBadRequest(text=msg)

        try:
            client = Client.objects.get(api_key=api_key)
        except Client.DoesNotExist as err:
            logger.error(err)
            msg = 'Such client does not exist'
            raise HTTPBadRequest(text=msg)

        if not client.is_active:
            logger.warning('Client %s is not active (disabled)', client)
            raise HTTPForbidden(text='Client is not active')
        return client, api_key

    @staticmethod
    async def jwt_auth_view(request):
        """JWT authentication view with API key

        NOTE: this method is blocking one intentionally. It should be used only
        for getting jwt token. All other requests are async
        """
        client, _ = AuthHandler._authorize(request)
        payload = {'client_id': client.pk,
                   'role': None,  # NOTE: future proof option
                   'expires_in': settings.AIOHANDLER['auth.expires_in']}
        cache = Cache.get_cache()
        cache.set_user_data(user_id=client.pk,
                            data=payload,
                            expire=settings.AIOHANDLER['auth.expires_in'])
        jwt_token = JWTManager.encode_token(payload)
        return web.json_response(data={'token': jwt_token.decode()})

    @staticmethod
    async def auth_view(request):
        """Authentication view with simple token

        """
        client, api_key = AuthHandler._authorize(request)
        cache = Cache.get_cache()
        payload = {'client_id': client.pk,
                   'role': None,  # NOTE: future proof option
                   'expires_in': settings.AIOHANDLER['auth.expires_in']}
        cache.set_client_data(api_key=api_key,
                              data=payload,
                              expire=settings.AIOHANDLER['auth.expires_in'])
        return web.json_response(data={'status': 'ok'})


def create_default_views(app):
    """Create default views come from settings

    """
    app.router.add_route(method='POST',
                         path=settings.AIOHANDLER['auth.url'],
                         handler=AuthHandler.jwt_auth_view)


def create_app(loop=None):
    loop = loop or asyncio.get_event_loop()
    app = web.Application(loop=loop,
                          handler_factory=CustomRequestHandlerFactory,
                          middlewares=[token_auth_middleware,
                                       check_route_middleware])
    proxy_router = ProxyRouter(app=app)
    app._router = proxy_router

    resources = ProxyResource.objects.all()\
        .select_related('api')\
        .prefetch_related('methods')

    for resource in resources:
        methods = [method.name for method in resource.methods.all()]
        if 'ANY' in methods:
            methods = HTTP_METHODS

        path = '{api}/{name}'.format(api=resource.api.path,
                                     name=resource.name)
        logger.info('Register {} --> {} [{}]'.format(
            path, resource.endpoint_url, ','.join(methods)))
        app.router.add_proxy_route(methods=methods,
                                   path=path,
                                   endpoint_url=resource.endpoint_url)
    # Create default (auth, etc) views
    create_default_views(app)
    return app
