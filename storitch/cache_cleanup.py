import logging
import time

from storitch import config


def cache_cleanup() -> None:
    logging.info(f'Started cache cleanup of {config.store_path}')
    temporary_cutoff = time.time() - 24 * 60 * 60
    deleted_files = 0
    total_size = 0
    for dir in config.store_path.iterdir():
        if not dir.is_dir():
            continue
        for file in dir.iterdir():
            if not file.is_dir():
                continue
            for f in file.iterdir():
                if f.is_file() and '@' in f.name:
                    try:
                        stat = f.stat()
                        # A recent temporary file may still be rendering on any replica.
                        if '@tmp-' in f.name and stat.st_mtime > temporary_cutoff:
                            continue
                        f.unlink()
                    except FileNotFoundError:
                        # A renderer or another cleanup may have moved/removed it.
                        continue
                    total_size += stat.st_size
                    deleted_files += 1
                    if deleted_files % 10_000 == 0:
                        logging.info(
                            f'Deleted {deleted_files:,} files '
                            f'({total_size / (1024 * 1024):.2f} MB freed)'
                        )
    logging.info(f'Total size freed: {total_size / (1024 * 1024):.2f} MB')
    logging.info(f'Cache cleanup complete. Deleted {deleted_files} files.')
