"""Smoke test: the DI container builds and the CLI object is constructible."""

import pytest


def test_container_builds():
    pytest.importorskip("dependency_injector")
    pytest.importorskip("dotenv")
    pytest.importorskip("spotipy")
    pytest.importorskip("yt_dlp")
    pytest.importorskip("tenacity")
    from src.app.providers import create_container
    container = create_container()
    cli = container.cli()  # builds download_manager -> imports shared.lib + metadata
    assert cli is not None
