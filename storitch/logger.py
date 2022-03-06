import logging, logging.handlers, os
from storitch import config
from tornado import log

class logger(object):

    @classmethod
    def set_logger(cls, filename):
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, config['logging']['level'].upper()))

        format_ = log.LogFormatter(
            '[%(color)s%(levelname)s%(end_color)s %(asctime)s %(module)s:%(lineno)d]: %(message)s', 
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        if config['logging']['path'] and filename:
            channel = logging.handlers.RotatingFileHandler(
                filename=os.path.join(config['logging']['path'], filename),
                maxBytes=config['logging']['max_size'],
                backupCount=config['logging']['num_backups']
            )
            channel.setFormatter(format_)
            logger.addHandler(channel)
        else:# send to console instead of file
            channel = logging.StreamHandler()
            channel.setFormatter(format_)
            logger.addHandler(channel)