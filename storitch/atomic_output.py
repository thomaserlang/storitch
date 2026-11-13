from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

from storitch import config


@contextmanager
def atomic_output(path: Path) -> Generator[Path]:
    """Publish a completed file by renaming within the same filesystem."""
    with NamedTemporaryFile(
        dir=path.parent, prefix=f'{path.stem}@tmp-', suffix=path.suffix, delete=False
    ) as file:
        temporary_path = Path(file.name)
    try:
        yield temporary_path
        temporary_path.chmod(int(config.file_mode, 8))
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)
