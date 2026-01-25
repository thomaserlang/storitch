import logging

import click
import uvicorn

from storitch import config


@click.group()
def cli() -> None: ...


@cli.command()
def api():
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logging.info(f'Storitch started on port {config.port}')
    uvicorn.run(
        'storitch.main:app',
        host='0.0.0.0',
        port=config.port,
        reload=config.debug,
        proxy_headers=True,
        forwarded_allow_ips='*',
        log_level=config.logging.level,
    )


@cli.command()
def cache_cleanup():
    from storitch.cache_cleanup import cache_cleanup

    cache_cleanup()


def main() -> None:
    cli()


if __name__ == '__main__':
    main()
