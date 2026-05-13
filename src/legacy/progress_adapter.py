"""
Legacy adapter for Progress Tracker.
Provides backward compatibility with old import paths.
"""

from src.shared.ui.progress import (
    ProgressTracker,
    SimpleProgressTracker,
    OverallProgress,
)

__all__ = [
    'ProgressTracker',
    'SimpleProgressTracker',
    'OverallProgress',
]

# Made with Bob