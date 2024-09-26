import logging
import logging.handlers
import os


def set_logger(
    filename: str,
    path: str | None = None,
    max_size: int | None = None,
    num_backups: int | None = None,
    level='INFO',
):
    logger = logging.getLogger()
    logger.setLevel(level.upper())

    format_ = logging.Formatter(
        fmt='[%(asctime)s.%(msecs)-3d] %(levelname)-8s %(message)s (%(filename)s:%(lineno)d)',
        datefmt='%Y-%m-%dT%H:%M:%S',
    )
    if path and filename:
        channel = logging.handlers.RotatingFileHandler(
            filename=os.path.join(path, filename),
            maxBytes=max_size or 0,
            backupCount=num_backups or 0,
        )
        channel.setFormatter(format_)
        logger.addHandler(channel)
    else:  # send to console instead of file
        channel = logging.StreamHandler()
        channel.setFormatter(format_)
        logger.addHandler(channel)
