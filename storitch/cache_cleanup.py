import logging

from storitch import config


def cache_cleanup():
    logging.info(f'Starting cache cleanup of {config.store_path}')
    for file_path in config.store_path.rglob('*'):
        if file_path.is_file() and '@' in file_path.name:
            logging.info(f'Deleting: {file_path}')
            file_path.unlink()
