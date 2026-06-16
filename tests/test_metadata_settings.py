"""Unit tests for MetadataHandler settings key (plan 009)."""

import types

import pytest

pytest.importorskip("mutagen")
pytest.importorskip("PIL")
pytest.importorskip("requests")

from src.features.metadata.infrastructure.metadata_handler import MetadataHandler


def _fake_config(download_artwork: bool) -> types.SimpleNamespace:
    """Build a minimal config exposing only the attributes __init__ reads."""
    metadata = types.SimpleNamespace(
        download_artwork=download_artwork,
        embed_lyrics=False,
        preserve_original=False,
    )
    return types.SimpleNamespace(metadata=metadata)


def test_settings_uses_download_artwork_key():
    # Arrange
    config = _fake_config(download_artwork=False)

    # Act
    handler = MetadataHandler(config)

    # Assert
    assert handler.settings['download_artwork'] is False


def test_artwork_toggle_is_honored_when_disabled():
    # Arrange
    config = _fake_config(download_artwork=False)

    # Act
    handler = MetadataHandler(config)
    guard_value = handler.settings.get('download_artwork', True)

    # Assert: the guard at the artwork download site now reads False,
    # whereas the stale 'embed_artwork' lookup would have defaulted to True.
    assert guard_value is False


def test_artwork_toggle_true_when_enabled():
    # Arrange
    config = _fake_config(download_artwork=True)

    # Act
    handler = MetadataHandler(config)

    # Assert
    assert handler.settings.get('download_artwork', True) is True
