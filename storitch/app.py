import asyncio
from functools import partial
import logging
import signal
from tornado import web
from storitch import config
from storitch.handlers import store, health
from concurrent.futures import ThreadPoolExecutor

from storitch.io_sighandler import sig_handler

def App():
    return web.Application([
            (r'/health', health.Handler),
            (r'/upload', store.Multipart_handler), # For backwards compatibility
            (r'/store', store.Multipart_handler),
            (r'/store/session', store.Session_handler),
            (r'/([A-Za-z0-9@._]+)', store.Thumbnail_handler),
            (r'/', store.Thumbnail_handler),
        ],
        autoescape=None,
        xsrf_cookies=False,
        debug=config['debug'],
        executor=ThreadPoolExecutor(int(config['pool_size']))
    )

def run():
    loop = asyncio.get_event_loop()
    app = App()
    app.loop = loop
    server = app.listen(config['port'])
    signal.signal(signal.SIGTERM, partial(sig_handler, server, app))
    signal.signal(signal.SIGINT, partial(sig_handler, server, app))  
    logging.info(f'Storitch started on port: {config["port"]}')
    loop.run_forever()

if __name__ == '__main__':
    from storitch import config_load, logger
    config_load()
    logger.set_logger('storitch.log')
    run()