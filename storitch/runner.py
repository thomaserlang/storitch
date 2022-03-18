import logging
import click
from storitch import logger

@click.command()
@click.option('--config', default=None, help='path to the config file')
@click.option('--logging_path', '-lp', default=None, help='a folder to store the log files in')
@click.option('--logging_level', '-ll', default=None, help='notset, debug, info, warning, error or critical')
@click.option('--port', '-p', help='port, default 3000')
@click.option('--max-workers', '-mw', help='pool size for the executor, default: cpu_count + 4')
@click.option('--temp-path', '-tp', help='Path for temporary files')
def app(config, logging_path, logging_level, port, max_workers, temp_path):
    import storitch
    storitch.config_load(config)
    if logging_path != None:
        storitch.config['logging']['path'] = logging_path
    if logging_level:
        storitch.config['logging']['level'] = logging_level
    if port:
        storitch.config['port'] = port
    if max_workers:
        storitch.config['max_workers'] = int(max_workers)
    if temp_path:
        storitch.config['temp_path'] = temp_path
    logger.set_logger('storitch-{}.log'.format(port))
    import storitch.app
    storitch.app.run()

if __name__ == '__main__':
    app()