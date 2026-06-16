"""Unit test for the unified OAuth redirect_uri default (plan 013)."""

import inspect

import pytest

pytest.importorskip("spotipy")

from src.features.spotify.infrastructure.spotify_client import SpotifyClient


def test_redirect_uri_default_is_canonical():
    # Arrange
    signature = inspect.signature(SpotifyClient.__init__)

    # Act
    default = signature.parameters['redirect_uri'].default

    # Assert
    assert default == "http://localhost:8888/callback"
