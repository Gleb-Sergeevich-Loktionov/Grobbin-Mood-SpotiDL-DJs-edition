"""Unit tests for the final download summary totals (plan 011)."""

import pytest

pytest.importorskip("colorama")
pytest.importorskip("tqdm")

from src.shared.ui.progress import ProgressTracker


def test_summary_reports_supplied_totals_including_skipped(capsys):
    # Arrange
    tracker = ProgressTracker(total_playlists=1, colored_output=False)

    # Act
    tracker.display_final_summary(successful=8, failed=1, skipped=3)
    out = capsys.readouterr().out

    # Assert
    assert "8" in out
    assert "1" in out
    assert "[SKIP]" in out
    assert "3" in out


def test_summary_omits_skipped_line_when_zero(capsys):
    # Arrange
    tracker = ProgressTracker(total_playlists=1, colored_output=False)

    # Act
    tracker.display_final_summary(successful=5, failed=0, skipped=0)
    out = capsys.readouterr().out

    # Assert
    assert "5" in out
    assert "[SKIP]" not in out


def test_summary_falls_back_to_internal_counters(capsys):
    # Arrange
    tracker = ProgressTracker(total_playlists=1, colored_output=False)
    tracker.total_completed = 4
    tracker.total_failed = 2

    # Act: no args supplied -> uses internal counters, must not raise
    tracker.display_final_summary()
    out = capsys.readouterr().out

    # Assert
    assert "4" in out
    assert "2" in out
