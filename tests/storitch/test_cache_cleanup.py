import os
import time
from pathlib import Path

import pytest

from storitch import config
from storitch.atomic_output import atomic_output
from storitch.cache_cleanup import cache_cleanup
from storitch.store_file import get_file_path


def test_cleanup_preserves_current_render_and_removes_abandoned_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, 'store_path', tmp_path)
    original = get_file_path('test-original')
    original.parent.mkdir(parents=True)
    original.write_bytes(b'original')
    cache = original.with_name(f'{original.name}@dicom-thumbnail.webp')
    old_cache = original.with_name(f'{original.name}@SX320.jpg')
    old_cache.write_bytes(b'old-cache')
    abandoned = cache.with_name(f'{cache.stem}@tmp-abandoned.webp')
    abandoned.write_bytes(b'partial-cache')
    old_time = time.time() - 2 * 24 * 60 * 60
    os.utime(abandoned, (old_time, old_time))

    with atomic_output(cache) as temporary:
        temporary.write_bytes(b'complete-image')
        cache_cleanup()
        assert temporary.read_bytes() == b'complete-image'
        assert not old_cache.exists()
        assert not abandoned.exists()
    assert cache.read_bytes() == b'complete-image'
    assert original.read_bytes() == b'original'
