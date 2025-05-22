import click
import uvicorn
import logging

from storitch import config


@click.command()
def app():
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logging.info(f'Storitch started on port {config.port}')
    uvicorn.run(
        'storitch.main:app', 
        host='0.0.0.0', 
        port=config.port, 
        reload=config.debug, 
        proxy_headers=True, 
        forwarded_allow_ips='*',
        log_level=config.logging.level
    )


if __name__ == '__main__':
    app()