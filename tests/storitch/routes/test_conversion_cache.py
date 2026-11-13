import asyncio
from pathlib import Path

import pytest
import pyvips

from storitch import config
from storitch.routes import download_convert_routes as routes


def test_conversion_publishes_only_completed_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = tmp_path / 'image'
    original.write_bytes(b'original')
    cache = tmp_path / 'image@SX320.webp'

    def convert(path: str, output: str, args: dict[str, int]) -> str:
        Path(output).write_bytes(b'complete-image')
        assert not cache.exists()
        return output

    monkeypatch.setattr(routes, 'vips_convert', convert)
    result = asyncio.run(routes.convert(cache))
    assert result == cache
    assert cache.read_bytes() == b'complete-image'
    assert set(tmp_path.iterdir()) == {original, cache}


def test_failed_conversion_discards_partial_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = tmp_path / 'image'
    original.write_bytes(b'original')
    cache = tmp_path / 'image@SX320.webp'

    def convert(path: str, output: str, args: dict[str, int]) -> str:
        Path(output).write_bytes(b'partial-image')
        raise pyvips.Error('conversion failed')

    monkeypatch.setattr(config, 'allow_imagemagick_fallback', False)
    monkeypatch.setattr(routes, 'vips_convert', convert)
    assert asyncio.run(routes.convert(cache)) is None
    assert list(tmp_path.iterdir()) == [original]
