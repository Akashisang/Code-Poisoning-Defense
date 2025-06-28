import os
import sys
import json
import ssl
import asyncio
import aiohttp
import logging
import argparse
import traceback
from aiohttp import web

import rememberberry
from rememberberry import ipfs
from rememberscript import RememberMachine, load_scripts_dir, validate_script
from anki.storage import _Collection

app = web.Application()

async def cleanup(storage):
    for key, value in storage.items():
        if isinstance(value, _Collection):
            print('saving anki collection...')
            value.close(save=True)

    print('syncing storage...')
    await storage.sync()


async def message_websocket_handler(request):
    logging.info('client connected')
    await ipfs.init()
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    storage = ipfs.get_ipfs_storage()
    script = load_scripts_dir(rememberberry.SCRIPTS_PATH, storage)
    await validate_script(script)
    machine = RememberMachine(script, storage)
    machine.init()
    try:
        async for msg in ws:
            if msg.tp == aiohttp.WSMsgType.TEXT:
                text = msg.data
                async for reply in machine.reply(text):
                    ws.send_str(reply)

            elif msg.tp == aiohttp.WSMsgType.ERROR:
                logging.info('ws connection closed with exception %s' %
                      ws.exception())
        await cleanup(storage)
    except:
        await cleanup(storage)
        traceback.print_exc()
        ws.send_str(json.dumps({'msg': traceback.format_exc()}))
        raise
    logging.info('websocket connection closed')

    return ws


if __name__ == '__main__':
    lvl_map = {
        'DEBUG': logging.DEBUG, 'INFO': logging.INFO, 'WARNING': logging.WARNING,
        'ERROR': logging.ERROR, 'CRITICAL': logging.CRITICAL
    }
    parser = argparse.ArgumentParser(description='Run Rememberberry server')
    parser.add_argument("--ssl", help="use ssl certs", action="store_true")
    parser.add_argument("--port", help="set the port, if not ssl (in case it will be 443",
                        type=int, default=80)
    parser.add_argument("--logfile", help="the optional output log file", type=str)
    parser.add_argument("--loglvl", help="the log level",
                        type=str, choices=list(lvl_map.keys()), default='INFO')

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=args.loglvl)

    port = args.port
    ssl_cert_path = os.environ.get('REMEMBERBERRY_CERT_PATH', None)
    if args.ssl and (ssl_cert_path is None or not os.path.exists(ssl_cert_path)):
        print('SSL cert path %s doesn\'t exist' % ssl_cert_path)
        raise ValueError()

    ssl_context = None
    if args.ssl:
        print('trying to use ssl context from %s' % ssl_cert_path)
        fullchain_path = os.path.join(ssl_cert_path, 'fullchain.pem')
        privkey_path = os.path.join(ssl_cert_path, 'privkey.pem')
        if os.path.exists(fullchain_path) and os.path.exists(privkey_path):
            port = 443
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            ssl_context.load_cert_chain(fullchain_path, privkey_path)
        else:
            print('fullchain or privkey didn\'t exist')
            raise ValueError()

    app.router.add_route('GET', '/', message_websocket_handler)
    try:
        web.run_app(app, host='0.0.0.0', ssl_context=ssl_context, port=port)
    except KeyboardInterrupt:
        asyncio.get_event_loop().run_until_complete(cleanup())
