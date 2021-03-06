import click
import storitch
from storitch import logger

@click.command()
@click.option('--config', default=None, help='path to the config file')
@click.option('--logging_path', '-lp', default=None, help='a folder to store the log files in')
@click.option('--logging_level', '-ll', default=None, help='notset, debug, info, warning, error or critical')
@click.option('--port', '-p', default=storitch.config['port'], help='the port')
def app(config, logging_path, logging_level, port):
    import storitch
    storitch.config_load(config)
    logger.set_logger('storitch-{}.log'.format(port))
    if logging_path != None:
        storitch.config['logging']['path'] = logging_path
    if logging_level:
        storitch.config['logging']['level'] = logging_level
    if port:
        storitch.config['port'] = port            
    import storitch.app
    storitch.app.run()

if __name__ == '__main__':
    app()