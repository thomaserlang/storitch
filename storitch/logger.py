import logging, logging.handlers, os

def set_logger(filename, path: str = None, max_size: int = None, num_backups: int = None, level = 'INFO'):
    logger = logging.getLogger()
    logger.setLevel(level.upper())

    format_ = logging.Formatter(        
        fmt='[%(asctime)s.%(msecs)-3d] %(levelname)-8s %(message)s (%(filename)s:%(lineno)d)',
        datefmt='%Y-%m-%dT%H:%M:%S',
    )
    if path and filename:
        channel = logging.handlers.RotatingFileHandler(
            filename=os.path.join(path, filename),
            maxBytes=max_size,
            backupCount=num_backups
        )
        channel.setFormatter(format_)
        logger.addHandler(channel)
    else:# send to console instead of file
        channel = logging.StreamHandler()
        channel.setFormatter(format_)
        logger.addHandler(channel)